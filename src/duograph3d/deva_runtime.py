from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REQUIRED_MODULES = ("torch", "torchvision", "numpy", "PIL", "cv2")


def probe_python_modules(
    python_executable: str,
    modules: tuple[str, ...] = REQUIRED_MODULES,
    *,
    extra_pythonpath: tuple[str, ...] = (),
) -> dict[str, object]:
    script = (
        "import importlib, json\n"
        f"mods = {modules!r}\n"
        "out = {}\n"
        "for mod in mods:\n"
        "    try:\n"
        "        importlib.import_module(mod)\n"
        "        out[mod] = {'ok': True, 'detail': ''}\n"
        "    except Exception as exc:\n"
        "        out[mod] = {'ok': False, 'detail': f'{type(exc).__name__}: {exc}'}\n"
        "print(json.dumps(out))\n"
    )
    env = os.environ.copy()
    if extra_pythonpath:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join([*extra_pythonpath, *( [existing] if existing else [] )])
    completed = subprocess.run(
        [python_executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        return {
            "python_executable": python_executable,
            "ok": False,
            "modules": {},
            "detail": (completed.stderr or completed.stdout).strip(),
        }
    return {
        "python_executable": python_executable,
        "ok": True,
        "modules": json.loads(completed.stdout),
        "detail": "",
    }


def build_deva_offline_command(
    *,
    repo_root: str | Path,
    python_executable: str,
    img_path: str | Path,
    mask_path: str | Path,
    output_dir: str | Path,
    dataset: str = "demo",
    temporal_setting: str = "semionline",
    chunk_size: int = 1,
    model_path: str | Path | None = None,
) -> list[str]:
    command = [
        python_executable,
        "evaluation/eval_with_detections.py",
        "--mask_path",
        str(mask_path),
        "--img_path",
        str(img_path),
        "--dataset",
        dataset,
        "--temporal_setting",
        temporal_setting,
        "--output",
        str(output_dir),
        "--chunk_size",
        str(chunk_size),
    ]
    if model_path is not None:
        command.extend(["--model", str(model_path)])
    return command


def evaluate_deva_runtime(
    *,
    repo_root: str | Path,
    python_executable: str,
    contract_root: str | Path,
    model_path: str | Path | None = None,
) -> dict[str, object]:
    repo_root = Path(repo_root)
    contract_root = Path(contract_root)
    img_path = contract_root / "img_path"
    mask_path = contract_root / "mask_path"
    module_probe = probe_python_modules(
        python_executable,
        modules=REQUIRED_MODULES + ("deva",),
        extra_pythonpath=(str(repo_root),),
    )
    blockers: list[str] = []
    if not repo_root.exists():
        blockers.append(f"missing repo root: {repo_root}")
    if not (repo_root / "evaluation" / "eval_with_detections.py").exists():
        blockers.append("missing DEVA evaluation/eval_with_detections.py")
    if not img_path.exists():
        blockers.append(f"missing contract img_path: {img_path}")
    if not mask_path.exists():
        blockers.append(f"missing contract mask_path: {mask_path}")
    if not module_probe["ok"]:
        blockers.append(f"python probe failed: {module_probe['detail']}")
    else:
        for module, status in module_probe["modules"].items():
            if not status["ok"]:
                blockers.append(f"missing python module `{module}`: {status['detail']}")
    model_exists = None
    if model_path is not None:
        model_exists = Path(model_path).exists()
        if not model_exists:
            blockers.append(f"missing model path: {model_path}")
    return {
        "repo_root": str(repo_root),
        "python_executable": python_executable,
        "contract_root": str(contract_root),
        "img_path": str(img_path),
        "mask_path": str(mask_path),
        "model_path": str(model_path) if model_path is not None else None,
        "model_exists": model_exists,
        "module_probe": module_probe,
        "blockers": blockers,
        "ready": len(blockers) == 0,
    }


def run_deva_offline(
    *,
    repo_root: str | Path,
    python_executable: str,
    contract_root: str | Path,
    output_dir: str | Path,
    dataset: str = "demo",
    temporal_setting: str = "semionline",
    chunk_size: int = 1,
    model_path: str | Path | None = None,
) -> dict[str, object]:
    runtime = evaluate_deva_runtime(
        repo_root=repo_root,
        python_executable=python_executable,
        contract_root=contract_root,
        model_path=model_path,
    )
    if not runtime["ready"]:
        return {"executed": False, "runtime": runtime, "command": [], "returncode": None, "stdout": "", "stderr": ""}
    command = build_deva_offline_command(
        repo_root=repo_root,
        python_executable=python_executable,
        img_path=Path(contract_root) / "img_path",
        mask_path=Path(contract_root) / "mask_path",
        output_dir=output_dir,
        dataset=dataset,
        temporal_setting=temporal_setting,
        chunk_size=chunk_size,
        model_path=model_path,
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(repo_root), *( [os.environ["PYTHONPATH"]] if "PYTHONPATH" in os.environ and os.environ["PYTHONPATH"] else [] )]
            ),
        },
    )
    return {
        "executed": True,
        "runtime": runtime,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def render_deva_runtime_markdown(report: dict[str, object]) -> str:
    lines = [
        "# DEVA Runtime Report",
        "",
        f"- Repo root: {report['repo_root']}",
        f"- Python executable: {report['python_executable']}",
        f"- Contract root: {report['contract_root']}",
        f"- Ready: {'Yes' if report['ready'] else 'No'}",
        "",
    ]
    probe = report["module_probe"]
    lines.extend(["## Python modules", "", "| Module | Status | Detail |", "| --- | --- | --- |"])
    for module, status in probe.get("modules", {}).items():
        lines.append(f"| `{module}` | {'OK' if status['ok'] else 'Missing'} | {status['detail']} |")
    lines.extend(["", "## Blockers", ""])
    blockers = report.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def find_deva_runtime_candidates(search_roots: list[str | Path], *, max_depth: int = 3) -> dict[str, object]:
    candidates = []
    seen: set[str] = set()
    for root in search_roots:
        root = Path(root)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(path.relative_to(root).parts) > max_depth:
                continue
            if path.name not in {"python", "python3"}:
                continue
            if not path.is_file() or not os.access(path, os.X_OK):
                continue
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            probe = probe_python_modules(str(path))
            candidates.append(
                {
                    "python_executable": str(path),
                    "all_required_modules": probe["ok"] and all(
                        status["ok"] for status in probe.get("modules", {}).values()
                    ),
                    "module_probe": probe,
                }
            )
    return {
        "search_roots": [str(Path(root)) for root in search_roots],
        "candidate_count": len(candidates),
        "ready_candidates": [
            candidate["python_executable"] for candidate in candidates if candidate["all_required_modules"]
        ],
        "candidates": candidates,
    }


def render_deva_runtime_candidates_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# DEVA Runtime Candidate Scan",
        "",
        f"- Search roots: {', '.join(summary['search_roots'])}",
        f"- Candidate count: {summary['candidate_count']}",
        f"- Ready candidates: {len(summary['ready_candidates'])}",
        "",
        "| Python | Ready | Missing modules |",
        "| --- | --- | --- |",
    ]
    for candidate in summary["candidates"]:
        missing = [
            name
            for name, status in candidate["module_probe"].get("modules", {}).items()
            if not status["ok"]
        ]
        lines.append(
            f"| `{candidate['python_executable']}` | {'Yes' if candidate['all_required_modules'] else 'No'} | {', '.join(missing) or 'none'} |"
        )
    lines.append("")
    return "\n".join(lines)
