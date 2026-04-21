"""
Generate all figures for the DRTS Mini-project 2 report.
Run from the project root:  python3 report/generate_figures.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT  = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ── colour palette (colour-blind friendly) ──────────────────────────────────
C_SPI  = "#0072B2"   # blue
C_HPI  = "#D55E00"   # vermillion
C_LPI  = "#CC79A7"   # pink
C_CI   = "#009E73"   # green
C_ANA  = "#0072B2"
C_SIM  = "#E69F00"   # orange
C_SP   = "#D55E00"
C_CBS  = "#0072B2"

FONT = {"family": "serif", "size": 10}
matplotlib.rc("font", **FONT)
matplotlib.rc("axes", titlesize=10, labelsize=9)
matplotlib.rc("xtick", labelsize=8)
matplotlib.rc("ytick", labelsize=8)
matplotlib.rc("legend", fontsize=8)
matplotlib.rc("figure", dpi=150)


# ── helpers ─────────────────────────────────────────────────────────────────

def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def savefig(name: str) -> None:
    path = OUT / name
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  saved {path.name}")


# ── Figure 1: Per-link WCRT breakdown (TC1) ─────────────────────────────────

def fig_wcrt_breakdown_tc1() -> None:
    rows = read_csv(ROOT / "output_data/test_case_1/analytical_per_link_breakdown.csv")
    # Sum contributions over all links per stream
    streams: dict[str, dict] = {}
    for r in rows:
        sid = r["ID"]
        if sid not in streams:
            streams[sid] = {"SPI": 0.0, "HPI": 0.0, "LPI": 0.0, "Ci": 0.0}
        streams[sid]["SPI"] += float(r["SPI_us"])
        streams[sid]["HPI"] += float(r["HPI_us"])
        streams[sid]["LPI"] += float(r["LPI_us"])
        streams[sid]["Ci"]  += float(r["C_i_us"])

    # Priority labels from analytical CSV
    ana = {r["ID"]: r for r in read_csv(ROOT / "output_data/test_case_1/analytical_WCRTs.csv")}
    prio_label = {sid: ("A" if ana[sid]["Priority"] == "2" else "B")
                  for sid in streams if sid in ana}

    sids  = [s for s in sorted(streams, key=int) if s in prio_label]
    labels = [f"S{s}\n(Cl.{prio_label[s]})" for s in sids]
    spi = np.array([streams[s]["SPI"] for s in sids])
    hpi = np.array([streams[s]["HPI"] for s in sids])
    lpi = np.array([streams[s]["LPI"] for s in sids])
    ci  = np.array([streams[s]["Ci"]  for s in sids])

    fig, ax = plt.subplots(figsize=(7, 3.2))
    x = np.arange(len(sids))
    w = 0.55

    b1 = ax.bar(x, ci,  w, label=r"$C_i$ (own TX)", color=C_CI)
    b2 = ax.bar(x, lpi, w, bottom=ci,          label="LPI (BE blocking)", color=C_LPI)
    b3 = ax.bar(x, hpi, w, bottom=ci+lpi,      label="HPI (Class A credit)", color=C_HPI)
    b4 = ax.bar(x, spi, w, bottom=ci+lpi+hpi,  label="SPI (same-class)", color=C_SPI)

    total = ci + lpi + hpi + spi
    for xi, tot in zip(x, total):
        ax.text(xi, tot + 3, f"{tot:.0f}", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("WCRT (μs)")
    ax.set_title("Per-stream WCRT breakdown — Test Case 1 (α = 0.5, 100 Mb/s)")
    ax.legend(loc="upper left", ncol=2)
    ax.set_ylim(0, max(total) * 1.18)
    ax.axhline(1000, color="red", linewidth=0.8, linestyle="--", label="Deadline")
    ax.spines[["top", "right"]].set_visible(False)
    savefig("fig_wcrt_breakdown_tc1.png")


# ── Figure 2: Analytical vs Simulated across all test cases ─────────────────

def fig_analytical_vs_sim() -> None:
    tc_labels = ["TC1", "TC2", "TC3"]
    tc_dirs   = ["test_case_1", "test_case_2", "test_case_3"]

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=False)

    for ax, lbl, td in zip(axes, tc_labels, tc_dirs):
        ana = read_csv(ROOT / f"output_data/{td}/analytical_WCRTs.csv")
        sim = {r["ID"]: float(r["Simulated_WCRT_us"])
               for r in read_csv(ROOT / f"output_data/{td}/simulation_results.csv")}

        avb = [r for r in ana if r["Priority"] in ("1", "2")]
        sids  = [r["ID"] for r in avb]
        a_wc  = np.array([float(r["Analytical_WCRT_us"]) for r in avb])
        s_wc  = np.array([sim[r["ID"]] for r in avb])
        dead  = np.array([float(r["Deadline_us"]) for r in avb])
        plab  = ["A" if r["Priority"] == "2" else "B" for r in avb]
        xlabs = [f"S{s}\n({p})" for s, p in zip(sids, plab)]

        x = np.arange(len(sids))
        w = 0.35
        ax.bar(x - w/2, a_wc, w, color=C_ANA, label="Analytical")
        ax.bar(x + w/2, s_wc, w, color=C_SIM, label="Simulated")
        for xi, d in zip(x, dead):
            ax.hlines(d, xi - w, xi + w, colors="red", linewidth=1.2)

        ax.set_xticks(x); ax.set_xticklabels(xlabs, fontsize=7)
        ax.set_title(f"{lbl}", fontsize=10)
        ax.set_ylabel("WCRT (μs)" if ax is axes[0] else "")
        ax.spines[["top", "right"]].set_visible(False)

        # ratio annotation
        for xi, av, sv in zip(x, a_wc, s_wc):
            ratio = av / sv if sv > 0 else 0
            ax.text(xi, max(av, sv) + 10, f"×{ratio:.2f}", ha="center",
                    fontsize=6.5, color="#444444")

    # shared legend
    han = [mpatches.Patch(color=C_ANA, label="Analytical"),
           mpatches.Patch(color=C_SIM, label="Simulated (max)"),
           plt.Line2D([0], [0], color="red", lw=1.2, label="Deadline")]
    axes[2].legend(handles=han, loc="upper right", fontsize=7)
    fig.suptitle("Analytical vs. Simulated WCRT (CBS, α = 0.5)", y=1.01)
    fig.tight_layout()
    savefig("fig_analytical_vs_sim.png")


# ── Figure 3: CBS vs SP comparison (TC1) ────────────────────────────────────

def fig_cbs_vs_sp() -> None:
    rows = read_csv(ROOT / "output_data/test_case_1/cbs_vs_sp_comparison.csv")
    avb  = [r for r in rows if r["Class"] in ("1", "2")]

    sids  = [r["ID"] for r in avb]
    plab  = ["A" if r["Class"] == "2" else "B" for r in avb]
    xlabs = [f"S{s}\n(Cl.{p})" for s, p in zip(sids, plab)]

    cbs_ana = np.array([float(r["CBS_Analytical_us"]) for r in avb])
    cbs_sim = np.array([float(r["CBS_Simulated_WCRT_us"]) for r in avb])
    sp_ana  = np.array([float(r["SP_Analytical_us"]) for r in avb])
    sp_sim  = np.array([float(r["SP_Simulated_WCRT_us"]) for r in avb])
    dead    = np.array([float(r["Deadline_us"]) for r in avb])

    x = np.arange(len(sids))
    w = 0.2
    fig, ax = plt.subplots(figsize=(8, 3.5))

    ax.bar(x - 1.5*w, cbs_ana, w, color=C_CBS,       label="CBS Analytical",  alpha=0.95)
    ax.bar(x - 0.5*w, cbs_sim, w, color=C_CBS,       label="CBS Simulated",   alpha=0.50, hatch="//")
    ax.bar(x + 0.5*w, sp_ana,  w, color=C_SP,        label="SP Analytical",   alpha=0.95)
    ax.bar(x + 1.5*w, sp_sim,  w, color=C_SP,        label="SP Simulated",    alpha=0.50, hatch="//")

    for xi, d in zip(x, dead):
        ax.hlines(d, xi - 2*w, xi + 2*w, colors="red", linewidth=1.0, linestyle="--")

    ax.set_xticks(x); ax.set_xticklabels(xlabs)
    ax.set_ylabel("WCRT (μs)")
    ax.set_title("CBS vs. Strict Priority — Test Case 1 (α = 0.5)")
    ax.legend(ncol=2, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    savefig("fig_cbs_vs_sp.png")


# ── Figure 4: Credit trace (TC1, Link2, Class B) ────────────────────────────

def fig_credit_trace() -> None:
    rows = read_csv(ROOT / "output_data/test_case_1/credit_trace_Link2.csv")
    t = np.array([float(r["time_us"]) for r in rows])
    cr = np.array([float(r["class_b_credit"]) for r in rows])

    # Show first 2.5 ms
    mask = t <= 2500
    t = t[mask]; cr = cr[mask]

    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.step(t, cr, where="post", color=C_CBS, linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.7, linestyle="--", alpha=0.6)
    ax.fill_between(t, cr, 0, step="post",
                    where=(cr < 0), alpha=0.15, color="red",  label="Negative credit (blocked)")
    ax.fill_between(t, cr, 0, step="post",
                    where=(cr >= 0), alpha=0.15, color="green", label="Non-negative credit (eligible)")

    ax.set_xlabel("Simulation time (μs)")
    ax.set_ylabel("Class B credit (μs equivalent)")
    ax.set_title("CBS Class B credit evolution — TC1, Link 2 (first 2.5 ms)")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    savefig("fig_credit_trace.png")


# ── Figure 5: Bound tightness ratio across test cases ───────────────────────

def fig_bound_tightness() -> None:
    tc_dirs = ["test_case_1", "test_case_2", "test_case_3"]
    tc_lbl  = ["TC1", "TC2", "TC3"]
    colors  = [C_CBS, "#F0A500", C_SP]

    all_class_a: list[list[float]] = []
    all_class_b: list[list[float]] = []

    for td in tc_dirs:
        rows = read_csv(ROOT / f"output_data/{td}/cbs_vs_sp_comparison.csv")
        ca = [float(r["CBS_Ratio_Analytical_over_Sim"])
              for r in rows if r["Class"] == "2" and r["CBS_Ratio_Analytical_over_Sim"]]
        cb = [float(r["CBS_Ratio_Analytical_over_Sim"])
              for r in rows if r["Class"] == "1" and r["CBS_Ratio_Analytical_over_Sim"]]
        all_class_a.append(ca)
        all_class_b.append(cb)

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=True)
    for ax, data, title in zip(axes,
                                [all_class_a, all_class_b],
                                ["Class A (highest AVB priority)", "Class B (lower AVB priority)"]):
        for i, (vals, lbl, col) in enumerate(zip(data, tc_lbl, colors)):
            x = np.full(len(vals), i)
            ax.scatter(x, vals, color=col, zorder=3, s=40)
            ax.errorbar(i, np.mean(vals), yerr=[[np.mean(vals) - min(vals)],
                                                  [max(vals) - np.mean(vals)]],
                        fmt="none", color=col, capsize=5, linewidth=1.8)

        ax.axhline(1.0, color="red", linewidth=0.9, linestyle="--", label="Ratio = 1 (tight)")
        ax.set_xticks(range(3)); ax.set_xticklabels(tc_lbl)
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)

    axes[0].set_ylabel("Analytical / Simulated WCRT")
    axes[0].legend(fontsize=7)
    fig.suptitle("Bound tightness (CBS): ratio ≥ 1 confirms upper-bound property", y=1.01)
    fig.tight_layout()
    savefig("fig_bound_tightness.png")


# ── Figure 6: BE response times CBS vs SP ───────────────────────────────────

def fig_be_comparison() -> None:
    tc_dirs = ["test_case_1", "test_case_2", "test_case_3"]
    tc_lbl  = ["TC1", "TC2", "TC3"]

    be_cbs: list[float] = []
    be_sp:  list[float] = []

    for td in tc_dirs:
        rows = read_csv(ROOT / f"output_data/{td}/cbs_vs_sp_comparison.csv")
        be_rows = [r for r in rows if r["Class"] == "0"]
        if be_rows:
            be_cbs.append(np.mean([float(r["CBS_Simulated_WCRT_us"]) for r in be_rows]))
            be_sp.append (np.mean([float(r["SP_Simulated_WCRT_us"])  for r in be_rows]))
        else:
            be_cbs.append(0.0); be_sp.append(0.0)

    x = np.arange(len(tc_lbl))
    w = 0.3
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    ax.bar(x - w/2, be_cbs, w, color=C_CBS, label="CBS")
    ax.bar(x + w/2, be_sp,  w, color=C_SP,  label="SP")

    for xi, vc, vs in zip(x, be_cbs, be_sp):
        ax.text(xi - w/2, vc + 5, f"{vc:.0f}", ha="center", va="bottom", fontsize=7)
        ax.text(xi + w/2, vs + 5, f"{vs:.0f}", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(x); ax.set_xticklabels(tc_lbl)
    ax.set_ylabel("Mean simulated WCRT (μs)")
    ax.set_title("Best-Effort worst-case response time: CBS vs. SP")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)

    note = ("Under CBS, BE frames benefit from credit-controlled bursting:\n"
            "Class A/B cannot monopolise the link indefinitely, limiting BE delay.\n"
            "Under SP, BE is fully pre-empted by any higher-priority activity.")
    ax.text(0.5, -0.28, note, transform=ax.transAxes, ha="center",
            fontsize=7, style="italic", color="#444")
    savefig("fig_be_comparison.png")


# ── Figure 7: Schedulability summary ─────────────────────────────────────────

def fig_schedulability() -> None:
    """Scatter: analytical WCRT vs deadline, colour = class."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))

    for ax, td, title in zip(axes,
                              ["test_case_1", "test_case_2", "test_case_3"],
                              ["Test Case 1", "Test Case 2", "Test Case 3"]):
        rows = read_csv(ROOT / f"output_data/{td}/analytical_WCRTs.csv")
        for r in rows:
            if r["Priority"] not in ("1", "2"):
                continue
            wcrt = float(r["Analytical_WCRT_us"])
            dead = float(r["Deadline_us"])
            col  = C_CBS if r["Priority"] == "2" else C_SP
            mk   = "^" if r["Priority"] == "2" else "o"
            sched = wcrt <= dead
            ax.scatter(dead, wcrt, color=col, marker=mk, s=55,
                       zorder=3, edgecolors="black" if not sched else "none", linewidths=0.8)

        lim = ax.get_xlim()[1]
        ax.plot([0, lim], [0, lim], "k--", linewidth=0.8, alpha=0.5, label="WCRT = Deadline")
        ax.set_xlabel("Deadline (μs)")
        ax.set_ylabel("Analytical WCRT (μs)" if ax is axes[0] else "")
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)

    a_patch = mpatches.Patch(color=C_CBS, label="Class A")
    b_patch = mpatches.Patch(color=C_SP,  label="Class B")
    miss_pt = plt.scatter([], [], marker="o", facecolors="none",
                          edgecolors="black", s=55, label="Deadline missed")
    axes[2].legend(handles=[a_patch, b_patch, miss_pt], fontsize=8)
    fig.suptitle("Schedulability: analytical WCRT vs. deadline (CBS, α = 0.5)", y=1.01)
    fig.tight_layout()
    savefig("fig_schedulability.png")


# ── run all ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating figures…")
    fig_wcrt_breakdown_tc1()
    fig_analytical_vs_sim()
    fig_cbs_vs_sp()
    fig_credit_trace()
    fig_bound_tightness()
    fig_be_comparison()
    fig_schedulability()
    print("Done — figures in", OUT)
