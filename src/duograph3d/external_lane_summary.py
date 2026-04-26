from __future__ import annotations

import re
from pathlib import Path


_AP_ROW_RE = re.compile(
    r"average\s*:\s*(?P<ap>[0-9.]+)\s+(?P<ap50>[0-9.]+)\s+(?P<ap25>[0-9.]+)"
)
_COUNT_RE = re.compile(
    r"Final pred instance num:\s*(?P<pred>\d+);\s*final GT instance num\s*(?P<gt>\d+)"
)
_BEGIN_SEQUENCE_RE = re.compile(r"Begin to process sequence\s+(?P<scene>\S+)")
_SEQUENCE_RE = re.compile(
    r"There are\s*(?P<selected>\d+)\s*sequences needed to be evaluated totally,\s*(?P<missing>\d+)\s*selected sequences are missing"
)


def parse_onlineanyseg_eval_log(text: str) -> dict[str, object]:
    ap_match = _AP_ROW_RE.search(text)
    count_matches = list(_COUNT_RE.finditer(text))
    sequence_match = _SEQUENCE_RE.search(text)
    sequence_counts: list[dict[str, object]] = []
    current_scene = ""
    for line in text.splitlines():
        begin_match = _BEGIN_SEQUENCE_RE.search(line)
        if begin_match:
            current_scene = begin_match.group("scene")
            continue
        count_match = _COUNT_RE.search(line)
        if count_match:
            sequence_counts.append(
                {
                    "scene": current_scene,
                    "pred_instance_count": int(count_match.group("pred")),
                    "gt_instance_count": int(count_match.group("gt")),
                }
            )
    return {
        "selected_sequences": int(sequence_match.group("selected")) if sequence_match else 0,
        "missing_sequences": int(sequence_match.group("missing")) if sequence_match else 0,
        "pred_instance_count": sum(int(match.group("pred")) for match in count_matches),
        "gt_instance_count": sum(int(match.group("gt")) for match in count_matches),
        "sequence_instance_counts": sequence_counts,
        "all_ap": float(ap_match.group("ap")) if ap_match else 0.0,
        "all_ap_50": float(ap_match.group("ap50")) if ap_match else 0.0,
        "all_ap_25": float(ap_match.group("ap25")) if ap_match else 0.0,
        "evaluator_completed": "scans processed:" in text and ap_match is not None,
    }


def parse_health_log(text: str) -> dict[str, object]:
    rows: dict[str, object] = {"checks": []}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line and not line.endswith((" OK", "FAIL")):
            key, value = line.split("=", 1)
            rows[key] = value
        elif " OK" in line or " FAIL " in line:
            rows.setdefault("checks", []).append(line)
    rows["has_failures"] = any(" FAIL " in str(item) for item in rows.get("checks", []))
    return rows


def build_external_lane_summary(
    *,
    lane_id: str,
    role: str,
    status: str,
    health_log_path: str | Path,
    artifacts: dict[str, str],
    evaluator_log_path: str | Path | None = None,
    boundary: str = "",
    next_steps: list[str] | None = None,
) -> dict[str, object]:
    health_text = Path(health_log_path).read_text()
    summary: dict[str, object] = {
        "lane_id": lane_id,
        "role": role,
        "status": status,
        "health": parse_health_log(health_text),
        "artifacts": artifacts,
        "boundary": boundary,
        "next_steps": next_steps or [],
    }
    if evaluator_log_path is not None:
        eval_text = Path(evaluator_log_path).read_text()
        summary["evaluator_smoke"] = parse_onlineanyseg_eval_log(eval_text)
    return summary


def render_external_lane_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        f"# {summary['lane_id']} Lane Summary",
        "",
        f"- Role: {summary['role']}",
        f"- Status: {summary['status']}",
        f"- Boundary: {summary.get('boundary', '')}",
        "",
        "## Health",
        "",
    ]
    health = summary.get("health", {})
    if isinstance(health, dict):
        for key in ("repo", "commit", "remote", "env", "blocker"):
            if key in health:
                lines.append(f"- {key}: `{health[key]}`")
        checks = health.get("checks", [])
        if checks:
            lines.extend(["", "### Checks", ""])
            for item in checks:
                lines.append(f"- `{item}`")
    if "evaluator_smoke" in summary:
        smoke = summary["evaluator_smoke"]
        if isinstance(smoke, dict):
            lines.extend(
                [
                    "",
                    "## Evaluator smoke",
                    "",
                    f"- Completed: {smoke['evaluator_completed']}",
                    f"- Selected sequences: {smoke['selected_sequences']}",
                    f"- Missing sequences: {smoke['missing_sequences']}",
                    f"- Pred / GT instances: {smoke['pred_instance_count']} / {smoke['gt_instance_count']}",
                    f"- AP / AP50 / AP25: {smoke['all_ap']:.3f} / {smoke['all_ap_50']:.3f} / {smoke['all_ap_25']:.3f}",
                ]
            )
            sequence_counts = smoke.get("sequence_instance_counts", [])
            if sequence_counts:
                lines.extend(["", "### Per-sequence instances", ""])
                for item in sequence_counts:
                    if isinstance(item, dict):
                        scene = item.get("scene", "")
                        pred = item.get("pred_instance_count", 0)
                        gt = item.get("gt_instance_count", 0)
                        lines.append(f"- {scene}: {pred} / {gt}")
    artifacts = summary.get("artifacts", {})
    if isinstance(artifacts, dict) and artifacts:
        lines.extend(["", "## Artifacts", ""])
        for name, path in artifacts.items():
            lines.append(f"- {name}: `{path}`")
    next_steps = summary.get("next_steps", [])
    if next_steps:
        lines.extend(["", "## Next steps", ""])
        for item in next_steps:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
