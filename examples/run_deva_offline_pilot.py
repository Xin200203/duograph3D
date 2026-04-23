from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_runtime import evaluate_deva_runtime, render_deva_runtime_markdown, run_deva_offline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or probe a DEVA offline pilot against an exported contract")
    parser.add_argument("repo_root")
    parser.add_argument("contract_root")
    parser.add_argument("--python-executable", default="python3")
    parser.add_argument("--output-dir", default="outputs_deva_runtime")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--dataset", default="demo")
    parser.add_argument("--temporal-setting", default="semionline")
    parser.add_argument("--chunk-size", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = evaluate_deva_runtime(
        repo_root=args.repo_root,
        python_executable=args.python_executable,
        contract_root=args.contract_root,
        model_path=args.model_path,
    )
    runtime_json = output_dir / "deva_runtime_report.json"
    runtime_md = output_dir / "deva_runtime_report.md"
    runtime_json.write_text(json.dumps(runtime, indent=2) + "\n")
    runtime_md.write_text(render_deva_runtime_markdown(runtime) + "\n")
    print(runtime_json)
    print(runtime_md)
    if args.execute:
        run_report = run_deva_offline(
            repo_root=args.repo_root,
            python_executable=args.python_executable,
            contract_root=args.contract_root,
            output_dir=output_dir / "deva_output",
            dataset=args.dataset,
            temporal_setting=args.temporal_setting,
            chunk_size=args.chunk_size,
            model_path=args.model_path,
        )
        run_json = output_dir / "deva_run_report.json"
        run_json.write_text(json.dumps(run_report, indent=2) + "\n")
        print(run_json)


if __name__ == "__main__":
    main()
