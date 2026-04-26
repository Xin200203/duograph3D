from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RemoteExperimentPaths:
    host: str = "10.177.69.184"
    user: str = "nebula"
    workspace_root: Path = Path("/home/nebula/xxy")
    scannet_raw_root: Path = Path("/home/nebula/xxy/dataset/scannet_v2")
    replica_root: Path = Path("/home/nebula/xxy/dataset/Replica")
    scannet200_root: Path = Path("/home/nebula/xxy/ESAM/data/scannet200")
    scannet200_sv_root: Path = Path("/home/nebula/xxy/ESAM/data/scannet200-sv")
    duograph3d_artifact_root: Path = Path("/home/nebula/xxy/duograph3d_artifacts")
    esam_exec_root: Path = Path("/home/nebula/xxy/3D_Reconstruction")

    @property
    def scannet_scans_root(self) -> Path:
        return self.scannet_raw_root / "scans"

    @property
    def scannet_pose_centered_root(self) -> Path:
        return self.scannet200_sv_root / "pose_centered"

    @property
    def replica_deva_output_json_root(self) -> Path:
        return self.duograph3d_artifact_root / "deva_runtime_exec_replica_ext_v1" / "deva_output" / "JSONFiles"

    @property
    def scannet_esam_online_monitor_json(self) -> Path:
        return self.esam_exec_root / "work_dirs" / "ESAM_online_scannet200_CA_mv_fast_ab" / "fullval_baseline_dino" / "online_monitor" / "online_monitor.json"
