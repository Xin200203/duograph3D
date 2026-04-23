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

    @property
    def scannet_scans_root(self) -> Path:
        return self.scannet_raw_root / "scans"

    @property
    def scannet_pose_centered_root(self) -> Path:
        return self.scannet200_sv_root / "pose_centered"
