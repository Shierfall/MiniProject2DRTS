from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, jsonify, render_template, request

from .analytical import build_alpha_plus_map, compute_cbs_wcrt, compute_sp_wcrt
from .model import CLASS_A, AVB_CLASSES
from .parser import load_scenario
from .simulator import simulate

app = Flask(__name__)

_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = _ROOT / "tsn-test-cases" / "examples"
_CLASS_NAMES = {2: "A", 1: "B", 0: "BE"}


def _list_test_cases() -> list[str]:
    return sorted(
        d.name for d in EXAMPLES_DIR.iterdir()
        if d.is_dir() and (d / "topology.json").exists()
    )


def _read_reference(path: Path) -> dict[int, float]:
    ref: dict[int, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        line = line.strip()
        if line:
            sid, wval = line.split("\t")
            ref[int(sid)] = float(wval.replace(",", "."))
    return ref


def _make_chart(scenario, analytical, simulation) -> str:
    avb = sorted(
        [s for s in scenario.streams if s.priority in AVB_CLASSES],
        key=lambda s: s.stream_id,
    )
    if not avb:
        return ""

    by_id = {s.stream_id: s for s in scenario.streams}
    sids = [s.stream_id for s in avb]
    labels = [f"S{sid}\n({'A' if by_id[sid].priority == CLASS_A else 'B'})" for sid in sids]
    ana_vals = [analytical[sid].total_wcrt_us for sid in sids if sid in analytical]
    sim_vals = [simulation.max_response_time(sid) for sid in sids]
    deadlines = [by_id[sid].deadline_us for sid in sids]

    x = np.arange(len(sids))
    w = 0.35
    fig, ax = plt.subplots(figsize=(max(6, len(sids) * 0.9), 4))
    ax.bar(x - w / 2, ana_vals, w, color="#0072B2", label="Analytical")
    ax.bar(x + w / 2, sim_vals, w, color="#E69F00", label="Simulated")
    for xi, d in zip(x, deadlines):
        ax.hlines(d, xi - w, xi + w, colors="#CC3333", linewidths=1.4, linestyle="--")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("WCRT (μs)")
    ax.set_title("Analytical vs Simulated WCRT (AVB streams)")
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


@app.route("/")
def index():
    return render_template("index.html", test_cases=_list_test_cases())


@app.route("/run", methods=["POST"])
def run():
    try:
        mode = request.form.get("mode", "cbs")
        policy = request.form.get("policy", "fixed")
        alpha_a = float(request.form.get("alpha_a", 0.5))
        alpha_b = float(request.form.get("alpha_b", 0.5))
        raw_dur = request.form.get("duration", "").strip()
        duration = float(raw_dur) if raw_dur else None

        with tempfile.TemporaryDirectory() as _tmp:
            tmp = Path(_tmp)
            source = request.form.get("source", "builtin")

            if source == "builtin":
                case_name = request.form.get("test_case", "test_case_1")
                case_dir = EXAMPLES_DIR / case_name
                topology_path = case_dir / "topology.json"
                streams_path = case_dir / "streams.json"
                routes_path = case_dir / "routes.json"
                ref_path = case_dir / "WCRTs.csv" if (case_dir / "WCRTs.csv").exists() else None
            else:
                def _save(field: str, name: str) -> Path:
                    f = request.files.get(field)
                    if not f or not f.filename:
                        raise ValueError(f"Missing file upload: {field}")
                    p = tmp / name
                    f.save(p)
                    return p

                topology_path = _save("topology_file", "topology.json")
                streams_path = _save("streams_file", "streams.json")
                routes_path = _save("routes_file", "routes.json")
                ref_upload = request.files.get("reference_file")
                if ref_upload and ref_upload.filename:
                    ref_path = tmp / "WCRTs.csv"
                    ref_upload.save(ref_path)
                else:
                    ref_path = None
                case_name = "custom"

            scenario = load_scenario(topology_path, streams_path, routes_path)
            alpha = build_alpha_plus_map(scenario, policy=policy, alpha_a=alpha_a, alpha_b=alpha_b)

            analytical = compute_cbs_wcrt(scenario, alpha) if mode == "cbs" else compute_sp_wcrt(scenario)
            simulation = simulate(
                scenario,
                alpha_plus_by_link=alpha,
                duration_us=duration,
                mode=mode,
                capture_credit_trace=False,
            )

            ref_map = _read_reference(ref_path) if ref_path and ref_path.exists() else {}

            rows = []
            for stream in sorted(scenario.streams, key=lambda s: s.stream_id):
                sid = stream.stream_id
                ana = analytical.get(sid)
                sim_wcrt = simulation.max_response_time(sid)
                ref = ref_map.get(sid)
                rows.append({
                    "id": sid,
                    "class": _CLASS_NAMES.get(stream.priority, str(stream.priority)),
                    "deadline": round(stream.deadline_us, 3),
                    "analytical": round(ana.total_wcrt_us, 3) if ana else None,
                    "simulated": round(sim_wcrt, 3),
                    "schedulable": bool(ana.total_wcrt_us <= stream.deadline_us) if ana else None,
                    "reference": round(ref, 3) if ref is not None else None,
                    "diff_vs_ref": round(ana.total_wcrt_us - ref, 3) if (ana and ref is not None) else None,
                })

            chart = _make_chart(scenario, analytical, simulation)

        return jsonify({
            "ok": True,
            "case": case_name,
            "n_streams": len(scenario.streams),
            "n_links": len(scenario.links),
            "warnings": scenario.warnings,
            "rows": rows,
            "chart": chart,
        })

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


def main():
    app.run(host="127.0.0.1", port=5000, debug=False)
