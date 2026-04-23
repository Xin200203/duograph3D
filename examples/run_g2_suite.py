from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.presets import SuiteSpec
from duograph3d.suite_runner import run_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a multi-scene G2 suite")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--drop-mode", choices=["none", "alternate", "burst", "random"], default="alternate")
    parser.add_argument("--drop-every", type=int, default=2)
    parser.add_argument("--drop-offset", type=int, default=1)
    parser.add_argument("--burst-size", type=int, default=2)
    parser.add_argument("--burst-start-index", type=int, default=1)
    parser.add_argument("--drop-probability", type=float, default=0.35)
    parser.add_argument("--random-seed", type=int, default=0)
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--replica-scenes", nargs="*", default=None)
    parser.add_argument("--scannet-scenes", nargs="*", default=["scene0008_00", "scene0057_01", "scene0110_01"])
    args = parser.parse_args()

    spec = SuiteSpec(
        name=args.output,
        scannet_scenes=args.scannet_scenes,
        drop_mode=args.drop_mode,
        drop_every=args.drop_every,
        drop_offset=args.drop_offset,
        burst_size=args.burst_size,
        burst_start_index=args.burst_start_index,
        drop_probability=args.drop_probability,
        random_seed=args.random_seed,
        limit=args.limit,
    )
    aggregate_path, markdown_path = run_suite(spec, Path('.'))
    print(aggregate_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
