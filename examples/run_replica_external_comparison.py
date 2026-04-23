from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_contract import export_replica_deva_contract_batch
from duograph3d.deva_readiness import render_deva_readiness_markdown, summarize_deva_contract
from duograph3d.deva_results import render_deva_output_markdown, summarize_deva_output
from duograph3d.deva_runtime import render_deva_runtime_markdown, run_deva_offline
from duograph3d.external_comparison import build_external_comparison, render_external_comparison_markdown
from duograph3d.io_utils import write_json
from duograph3d.paper_metrics import render_paper_metrics_markdown, summarize_paper_metrics
from duograph3d.presets import REPLICA_SCENES, SuiteSpec
from duograph3d.remote_config import RemoteExperimentPaths
from duograph3d.suite_runner import run_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Replica-only DuoGraph3D vs DEVA external comparison pipeline")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--deva-repo", required=True)
    parser.add_argument("--deva-python", required=True)
    parser.add_argument("--deva-model", required=True)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    # DuoGraph3D replica-only pilot
    duo_root = output_root / "duograph3d"
    spec = SuiteSpec(name="replica_only_baseline", scannet_scenes=[], drop_mode="alternate", drop_every=2, limit=args.limit)
    aggregate_path, markdown_path = run_suite(spec, duo_root)
    report_paths = [str(path) for path in (duo_root / spec.name).glob("bounded_slice_*.json")]
    duo_metrics_summary = summarize_paper_metrics(report_paths)
    duo_metrics_dir = output_root / "duograph3d_paper_metrics"
    duo_metrics_dir.mkdir(exist_ok=True)
    write_json(duo_metrics_summary, duo_metrics_dir / "paper_metrics_summary.json")
    (duo_metrics_dir / "paper_metrics_summary.md").write_text(render_paper_metrics_markdown(duo_metrics_summary) + "\n")

    # DEVA contract export
    paths = RemoteExperimentPaths()
    scene_roots = [paths.replica_root / scene for scene in REPLICA_SCENES]
    deva_contract_root = output_root / "deva_contract"
    deva_contract_summary = export_replica_deva_contract_batch(scene_roots, deva_contract_root, limit=args.limit)
    write_json(deva_contract_summary, deva_contract_root / "deva_pilot_summary.json")
    deva_readiness = summarize_deva_contract(deva_contract_root)
    deva_readiness_dir = output_root / "deva_readiness"
    deva_readiness_dir.mkdir(exist_ok=True)
    write_json(deva_readiness, deva_readiness_dir / "deva_readiness_summary.json")
    (deva_readiness_dir / "deva_readiness_summary.md").write_text(render_deva_readiness_markdown(deva_readiness) + "\n")

    # DEVA execution
    deva_runtime_root = output_root / "deva_runtime"
    deva_run = run_deva_offline(
        repo_root=args.deva_repo,
        python_executable=args.deva_python,
        contract_root=deva_contract_root,
        output_dir=deva_runtime_root / "deva_output",
        dataset="demo",
        temporal_setting="semionline",
        chunk_size=1,
        model_path=args.deva_model,
    )
    write_json(deva_run["runtime"], deva_runtime_root / "deva_runtime_report.json")
    (deva_runtime_root / "deva_runtime_report.md").write_text(render_deva_runtime_markdown(deva_run["runtime"]) + "\n")
    write_json(deva_run, deva_runtime_root / "deva_run_report.json")
    if not deva_run["executed"] or deva_run["returncode"] != 0:
        raise RuntimeError("DEVA execution failed or was blocked; inspect deva_runtime/deva_run_report.json")

    # DEVA output summary
    deva_summary = summarize_deva_output(deva_runtime_root / "deva_output")
    deva_summary_dir = output_root / "deva_output_summary"
    deva_summary_dir.mkdir(exist_ok=True)
    write_json(deva_summary, deva_summary_dir / "deva_output_summary.json")
    (deva_summary_dir / "deva_output_summary.md").write_text(render_deva_output_markdown(deva_summary) + "\n")

    # Side-by-side comparison
    comparison = build_external_comparison(duo_metrics_summary, deva_summary)
    comparison_dir = output_root / "external_comparison"
    comparison_dir.mkdir(exist_ok=True)
    write_json(comparison, comparison_dir / "external_comparison_summary.json")
    (comparison_dir / "external_comparison_summary.md").write_text(render_external_comparison_markdown(comparison) + "\n")

    print(aggregate_path)
    print(markdown_path)
    print(duo_metrics_dir / "paper_metrics_summary.md")
    print(deva_readiness_dir / "deva_readiness_summary.md")
    print(deva_runtime_root / "deva_run_report.json")
    print(deva_summary_dir / "deva_output_summary.md")
    print(comparison_dir / "external_comparison_summary.md")


if __name__ == "__main__":
    main()
