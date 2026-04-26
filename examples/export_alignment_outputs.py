from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.alignment_exports import export_conceptgraphs_alignment, export_onlineanyseg_alignment
from duograph3d.io_utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Export DuoGraph3D reports into story-aligned external-evaluator surfaces.")
    parser.add_argument("--report", required=True, help="Path to a bounded_slice_*.json report")
    parser.add_argument("--output", required=True, help="Output root for alignment exports")
    parser.add_argument("--geometry", default=None, help="Optional dense alignment geometry JSON with points and object point_indices")
    parser.add_argument("--branch-id", default="duograph3d_full")
    parser.add_argument("--default-class-id", type=int, default=1)
    parser.add_argument("--default-class-name", default="object")
    parser.add_argument("--points-per-object", type=int, default=128)
    parser.add_argument("--conceptgraphs-feature-dim", type=int, default=512)
    parser.add_argument("--conceptgraphs-exp-name", default="duograph3d_alignment")
    args = parser.parse_args()

    output = Path(args.output)
    online_manifest = export_onlineanyseg_alignment(
        args.report,
        output / "onlineanyseg",
        branch_id=args.branch_id,
        default_class_id=args.default_class_id,
        default_class_name=args.default_class_name,
        points_per_object=args.points_per_object,
        geometry_path=args.geometry,
    )
    concept_manifest = export_conceptgraphs_alignment(
        args.report,
        output / "conceptgraphs",
        branch_id=args.branch_id,
        pred_exp_name=args.conceptgraphs_exp_name,
        default_class_id=args.default_class_id,
        default_class_name=args.default_class_name,
        feature_dim=args.conceptgraphs_feature_dim,
        points_per_object=args.points_per_object,
        geometry_path=args.geometry,
    )
    combined = {
        "status": "alignment_exports_written",
        "report": str(Path(args.report)),
        "geometry": str(Path(args.geometry)) if args.geometry else "",
        "onlineanyseg": online_manifest,
        "conceptgraphs": concept_manifest,
    }
    write_json(combined, output / "alignment_export_manifest.json")
    print(output / "alignment_export_manifest.json")


if __name__ == "__main__":
    main()
