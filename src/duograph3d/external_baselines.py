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


def esam_official_target(repo_commit: str) -> dict[str, object]:
    target = ExternalBaselineTarget(
        baseline_id="esam_official_scannet_mv",
        label="EmbodiedSAM official ScanNet-MV evaluation",
        repo_url="https://github.com/xuxw98/ESAM",
        repo_commit=repo_commit,
        paper_url="https://arxiv.org/abs/2408.11811",
        family="external_official_target",
        integration_mode="official_scannet_mv_eval",
        faithfulness="official_repo_target",
        required_inputs=["config", "checkpoint", "work_dir"],
        reference_commands=[
            "CUDA_VISIBLE_DEVICES=0 python tools/test.py configs/ESAM_CA/ESAM_online_scannet200_CA.py work_dirs/ESAM_online_scannet200_CA/epoch_128.pth --work-dir work_dirs/ESAM_online_scannet200_CA/",
            "CUDA_VISIBLE_DEVICES=0 python vis_demo/stream_demo.py --data_root <data_root>",
        ],
        notes=[
            "Official ESAM docs include evaluation commands for ScanNet200-MV and custom-data stream demos.",
            "This target serves as the second reviewer-credible external baseline family for DuoGraph3D Phase 3.",
        ],
    )
    return asdict(target)


def onlineanyseg_official_target(repo_commit: str) -> dict[str, object]:
    target = ExternalBaselineTarget(
        baseline_id="onlineanyseg_official_scannet",
        label="OnlineAnySeg official ScanNet online 3D segmentation",
        repo_url="https://github.com/yjtang249/OnlineAnySeg",
        repo_commit=repo_commit,
        paper_url="https://arxiv.org/abs/2503.01309",
        family="external_direct_neighbor",
        integration_mode="official_scannet_eval_surface",
        faithfulness="official_repo_target",
        required_inputs=[
            "result_dir/<scene>/final.ply",
            "result_dir/<scene>/ckpt_final.npz",
            "scannet scan root",
            "scannet gt segmentation txt",
        ],
        reference_commands=[
            "python main.py -c config/scannet_cropformer.yaml --seq_name <scene> -d <sequence_dir> -i <seg_sequence_dir> -o <output_dir>",
            "PYTHONPATH=<OnlineAnySeg_root> python eval/evaluate_seqs.py --result_dir <output_dir> --seq_name <scene> --gt_dir <scannet_root> --gt_pc_pattern %s/%s_vh_clean_2.ply --gt_seg_dir <gt_seg_dir> --gt_seg_pattern %s.txt --dataset scannet",
        ],
        notes=[
            "This is the first story-aligned direct-neighbor lane because it targets online zero-shot 3D instance segmentation.",
            "The evaluator surface is now verified separately from full method execution; full OnlineAnySeg main execution still depends on a compatible MinkowskiEngine/FCGF stack.",
        ],
    )
    return asdict(target)


def conceptgraphs_official_target(repo_commit: str) -> dict[str, object]:
    target = ExternalBaselineTarget(
        baseline_id="conceptgraphs_official_replica",
        label="ConceptGraphs official Replica object-map semantic evaluation",
        repo_url="https://github.com/concept-graphs/concept-graphs",
        repo_commit=repo_commit,
        paper_url="https://arxiv.org/abs/2309.16650",
        family="external_graph_memory_neighbor",
        integration_mode="official_replica_object_map_eval_surface",
        faithfulness="official_repo_target",
        required_inputs=[
            "replica_root/<scene>/pcd_saves/full_pcd_<pred_exp_name>*.pkl.gz",
            "replica semantic root",
            "rgb_cloud reconstruction h5",
            "object CLIP/text features",
        ],
        reference_commands=[
            "python -m conceptgraph.scripts.eval_replica_semseg --replica_root <replica_root> --replica_semantic_root <replica_semantic_root> --pred_exp_name <pred_exp_name>",
        ],
        notes=[
            "This lane is the first graph/object-memory external comparison target.",
            "The DuoGraph3D exporter now writes a ConceptGraphs-style object-map payload; official semantic evaluation still requires a compatible chamferdist/gradslam runtime and Replica semantic roots.",
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
