from __future__ import annotations

from dataclasses import dataclass


REPLICA_SCENES = ["office0", "office1", "office2", "office3", "office4", "room0", "room1", "room2"]
SCANNET_LARGE = [
    "scene0000_00", "scene0000_01", "scene0000_02", "scene0001_00", "scene0001_01", "scene0002_00",
    "scene0002_01", "scene0003_00", "scene0003_01", "scene0003_02", "scene0004_00", "scene0005_00",
]
SCANNET_HOLDOUT1 = [
    "scene0005_01", "scene0006_00", "scene0006_01", "scene0006_02", "scene0007_00", "scene0008_00",
    "scene0009_00", "scene0009_01", "scene0010_00", "scene0010_01", "scene0011_00", "scene0011_01",
]
SCANNET_HOLDOUT2 = [
    "scene0012_00", "scene0012_01", "scene0012_02", "scene0013_00", "scene0013_01", "scene0013_02",
    "scene0014_00", "scene0015_00", "scene0016_00", "scene0016_01", "scene0017_00", "scene0017_01",
]
SCANNET_HOLDOUT3 = [
    "scene0029_00", "scene0029_01", "scene0029_02", "scene0030_00", "scene0030_01", "scene0030_02",
    "scene0031_00", "scene0031_01", "scene0031_02", "scene0032_00", "scene0032_01", "scene0033_00",
]
SCANNET_HOLDOUT4 = [
    "scene0034_00", "scene0034_01", "scene0034_02", "scene0035_00", "scene0035_01", "scene0036_00",
    "scene0036_01", "scene0037_00", "scene0038_00", "scene0038_01", "scene0038_02", "scene0039_00",
]
SCANNET_HOLDOUT5 = [
    "scene0040_00", "scene0040_01", "scene0041_00", "scene0041_01", "scene0042_00", "scene0042_01",
    "scene0042_02", "scene0043_00", "scene0043_01", "scene0044_00", "scene0044_01", "scene0045_00",
]
SCANNET_HOLDOUT6 = [
    "scene0045_01", "scene0046_00", "scene0046_01", "scene0046_02", "scene0047_00", "scene0048_00",
    "scene0048_01", "scene0049_00", "scene0050_00", "scene0050_01", "scene0051_00", "scene0051_01",
]


@dataclass(frozen=True)
class SuiteSpec:
    name: str
    scannet_scenes: list[str]
    drop_mode: str = "none"
    drop_every: int = 0
    drop_offset: int = 1
    burst_size: int = 2
    burst_start_index: int = 1
    drop_probability: float = 0.35
    random_seed: int = 0
    limit: int = 6


def build_all_suite_specs() -> list[SuiteSpec]:
    return [
        SuiteSpec("outputs_large_baseline", SCANNET_LARGE, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_large_stress", SCANNET_LARGE, drop_mode="alternate", drop_every=3),
        SuiteSpec("outputs_burst_large", SCANNET_LARGE, drop_mode="burst", burst_size=2),
        SuiteSpec("outputs_offset_large", SCANNET_LARGE, drop_mode="alternate", drop_every=3, drop_offset=2),
        SuiteSpec("outputs_lateburst_large", SCANNET_LARGE, drop_mode="burst", burst_size=3, burst_start_index=2, limit=10),
        SuiteSpec("outputs_longburst_large", SCANNET_LARGE, drop_mode="burst", burst_size=4, burst_start_index=3, limit=12),
        SuiteSpec("outputs_random_large_seed7", SCANNET_LARGE, drop_mode="random", drop_probability=0.35, random_seed=7),
        SuiteSpec("outputs_random_large_seed13", SCANNET_LARGE, drop_mode="random", drop_probability=0.35, random_seed=13),
        SuiteSpec("outputs_random_p50_seed21", SCANNET_LARGE, drop_mode="random", drop_probability=0.5, random_seed=21),
        SuiteSpec("outputs_random_p50_seed42", SCANNET_LARGE, drop_mode="random", drop_probability=0.5, random_seed=42),
        SuiteSpec("outputs_random_p65_seed21", SCANNET_LARGE, drop_mode="random", drop_probability=0.65, random_seed=21),
        SuiteSpec("outputs_random_p65_seed42", SCANNET_LARGE, drop_mode="random", drop_probability=0.65, random_seed=42),
        SuiteSpec("outputs_random_p90_seed21", SCANNET_LARGE, drop_mode="random", drop_probability=0.9, random_seed=21),
        SuiteSpec("outputs_random_p90_seed42", SCANNET_LARGE, drop_mode="random", drop_probability=0.9, random_seed=42),
        SuiteSpec("outputs_random_p100_seed0", SCANNET_LARGE, drop_mode="random", drop_probability=1.0, random_seed=0),
        SuiteSpec("outputs_holdout_baseline", SCANNET_HOLDOUT1, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_holdout_burst", SCANNET_HOLDOUT1, drop_mode="burst", burst_size=2),
        SuiteSpec("outputs_holdout2_baseline", SCANNET_HOLDOUT2, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_holdout2_burst", SCANNET_HOLDOUT2, drop_mode="burst", burst_size=2),
        SuiteSpec("outputs_holdout3_baseline", SCANNET_HOLDOUT3, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_holdout3_burst", SCANNET_HOLDOUT3, drop_mode="burst", burst_size=2),
        SuiteSpec("outputs_holdout4_baseline", SCANNET_HOLDOUT4, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_holdout4_burst", SCANNET_HOLDOUT4, drop_mode="burst", burst_size=2),
        SuiteSpec("outputs_holdout5_baseline", SCANNET_HOLDOUT5, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_holdout5_burst", SCANNET_HOLDOUT5, drop_mode="burst", burst_size=2),
        SuiteSpec("outputs_holdout6_baseline", SCANNET_HOLDOUT6, drop_mode="alternate", drop_every=2),
        SuiteSpec("outputs_holdout6_burst", SCANNET_HOLDOUT6, drop_mode="burst", burst_size=2),
    ]


def expected_scene_count() -> int:
    return sum(len(REPLICA_SCENES) + len(spec.scannet_scenes) for spec in build_all_suite_specs())
