import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.external_baselines import (
    conceptgraphs_official_target,
    deva_official_target,
    esam_official_target,
    onlineanyseg_official_target,
    render_external_baseline_target_markdown,
)


class ExternalBaselineTargetTests(unittest.TestCase):
    def test_deva_target_and_markdown(self) -> None:
        target = deva_official_target("404a112df77f9644d5c7211811329ccd8174b8c3")
        self.assertEqual(target["baseline_id"], "deva_official_offline")
        self.assertIn("mask_path", target["required_inputs"])
        md = render_external_baseline_target_markdown(target)
        self.assertIn("Tracking-Anything-with-DEVA", md)
        self.assertIn("eval_with_detections.py", md)

    def test_esam_target_and_markdown(self) -> None:
        target = esam_official_target("188fc6de44f7577fecec2d69b75c7adbd9992251")
        self.assertEqual(target["baseline_id"], "esam_official_scannet_mv")
        self.assertIn("config", target["required_inputs"])
        md = render_external_baseline_target_markdown(target)
        self.assertIn("EmbodiedSAM official ScanNet-MV evaluation", md)
        self.assertIn("tools/test.py", md)

    def test_story_aligned_targets_and_markdown(self) -> None:
        online = onlineanyseg_official_target("152466e318f8220bcc6838c03e340cce2f2153b8")
        self.assertEqual(online["baseline_id"], "onlineanyseg_official_scannet")
        self.assertTrue(any("ckpt_final.npz" in item for item in online["required_inputs"]))
        online_md = render_external_baseline_target_markdown(online)
        self.assertIn("OnlineAnySeg official ScanNet", online_md)
        self.assertIn("evaluate_seqs.py", online_md)

        concept = conceptgraphs_official_target("72f5962822b5e8678a446f367a06df1a977d2a4d")
        self.assertEqual(concept["baseline_id"], "conceptgraphs_official_replica")
        self.assertIn("full_pcd_<pred_exp_name>", concept["required_inputs"][0])
        concept_md = render_external_baseline_target_markdown(concept)
        self.assertIn("ConceptGraphs official Replica", concept_md)
        self.assertIn("eval_replica_semseg", concept_md)


if __name__ == "__main__":
    unittest.main()
