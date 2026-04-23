from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ExternalBaselineTarget:
    baseline_id: str
    label: str
    repo_url: str
    repo_commit: str
    paper_url: str
    family: str
    integration_mode: str
    faithfulness: str
    required_inputs: list[str] = field(default_factory=list)
    reference_commands: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def deva_official_target(repo_commit: str) -> dict[str, object]:
    target = ExternalBaselineTarget(
        baseline_id="deva_official_offline",
        label="DEVA official offline integration",
        repo_url="https://github.com/hkchengrex/Tracking-Anything-with-DEVA",
        repo_commit=repo_commit,
        paper_url="https://arxiv.org/abs/2309.03903",
        family="external_official_target",
        integration_mode="offline_detections",
        faithfulness="official_repo_target",
        required_inputs=["mask_path", "img_path", "output"],
        reference_commands=[
            "python evaluation/eval_with_detections.py --mask_path [path to detections] --img_path [path to images] --dataset demo --temporal_setting semionline --output [output directory] --chunk_size 1",
            "python evaluation/eval_with_detections.py --mask_path [path to detections] --img_path [path to images] --dataset burst --save_all --temporal_setting [online/semionline] --output [output directory] --chunk_size 4",
        ],
        notes=[
            "Official DEVA docs state that offline integration with custom detections is supported.",
            "This target is the first reviewer-credible stronger temporal comparison lane for DuoGraph3D.",
        ],
    )
    return asdict(target)


def render_external_baseline_target_markdown(target: dict[str, object]) -> str:
    lines = [
        "# External Baseline Target",
        "",
        f"- Baseline: {target['label']} (`{target['baseline_id']}`)",
        f"- Repo: {target['repo_url']}",
        f"- Commit: {target['repo_commit']}",
        f"- Paper: {target['paper_url']}",
        f"- Family: {target['family']}",
        f"- Integration mode: {target['integration_mode']}",
        f"- Faithfulness: {target['faithfulness']}",
        "",
        "## Required inputs",
        "",
    ]
    for item in target.get("required_inputs", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Reference commands", ""])
    for command in target.get("reference_commands", []):
        lines.append(f"- `{command}`")
    notes = target.get("notes", [])
    if notes:
        lines.extend(["", "## Notes", ""])
        for note in notes:
            lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
