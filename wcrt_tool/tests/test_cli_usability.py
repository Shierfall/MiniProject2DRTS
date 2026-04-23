from __future__ import annotations

from pathlib import Path

import pytest

from wcrt_tool.__main__ import _parse_args, _resolve_input_paths


def _write_case_dir(case_dir: Path, with_reference: bool = True) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "topology.json").write_text("{}", encoding="utf-8")
    (case_dir / "streams.json").write_text("{}", encoding="utf-8")
    (case_dir / "routes.json").write_text("{}", encoding="utf-8")
    if with_reference:
        (case_dir / "WCRTs.csv").write_text("ID\tWCRT\n", encoding="utf-8")


def test_positional_case_path_resolves_default_files_and_output(tmp_path: Path) -> None:
    case_dir = tmp_path / "test_case_1"
    _write_case_dir(case_dir, with_reference=True)

    args = _parse_args([str(case_dir)])
    topology, streams, routes, reference, output = _resolve_input_paths(args)

    assert topology == case_dir / "topology.json"
    assert streams == case_dir / "streams.json"
    assert routes == case_dir / "routes.json"
    assert reference == case_dir / "WCRTs.csv"
    assert output == Path("output_data") / "test_case_1"


def test_explicit_paths_mode_still_supported(tmp_path: Path) -> None:
    case_dir = tmp_path / "tc"
    _write_case_dir(case_dir, with_reference=False)

    args = _parse_args(
        [
            "--topology",
            str(case_dir / "topology.json"),
            "--streams",
            str(case_dir / "streams.json"),
            "--routes",
            str(case_dir / "routes.json"),
        ]
    )
    topology, streams, routes, reference, output = _resolve_input_paths(args)

    assert topology == case_dir / "topology.json"
    assert streams == case_dir / "streams.json"
    assert routes == case_dir / "routes.json"
    assert reference is None
    assert output == Path("results")


def test_parse_rejects_both_case_forms(tmp_path: Path) -> None:
    case_dir = tmp_path / "tc"
    _write_case_dir(case_dir)

    with pytest.raises(SystemExit):
        _parse_args([str(case_dir), "--input-dir", str(case_dir)])


def test_parse_rejects_mixing_case_and_explicit_paths(tmp_path: Path) -> None:
    case_dir = tmp_path / "tc"
    _write_case_dir(case_dir)

    with pytest.raises(SystemExit):
        _parse_args([str(case_dir), "--topology", str(case_dir / "topology.json")])


def test_resolve_fails_on_missing_required_case_files(tmp_path: Path) -> None:
    case_dir = tmp_path / "broken_case"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "topology.json").write_text("{}", encoding="utf-8")

    args = _parse_args([str(case_dir)])
    with pytest.raises(SystemExit):
        _resolve_input_paths(args)
