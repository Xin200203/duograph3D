import unittest

from duograph3d.scale_priors import (
    DEFAULT_MAX_EXTENT_PRIORS,
    SCANNET_NYU40_MAX_EXTENT_PRIORS,
    scale_prior_violation,
    select_scale_prior_target,
)


class ScalePriorViolationTests(unittest.TestCase):
    def test_office1_tissue_carrier_violates(self):
        decision = scale_prior_violation("tissue-paper", 1.1)
        self.assertTrue(decision["violation"])
        self.assertEqual(decision["reason"], "extent_exceeds_prior")

    def test_office2_bin_carrier_violates(self):
        decision = scale_prior_violation("bin", 1.6)
        self.assertTrue(decision["violation"])

    def test_normal_sized_objects_keep_authority(self):
        self.assertFalse(scale_prior_violation("tissue-paper", 0.3)["violation"])
        self.assertFalse(scale_prior_violation("table", 2.4)["violation"])

    def test_moderate_vent_is_protected_by_prior(self):
        # office4 boundary: vent-like carriers around 1.0-1.2m must not fire
        self.assertFalse(scale_prior_violation("vent", 1.1)["violation"])

    def test_unknown_label_never_violates(self):
        decision = scale_prior_violation("mystery-class", 5.0)
        self.assertFalse(decision["violation"])
        self.assertEqual(decision["reason"], "no_prior_for_label")

    def test_tolerance_scales_the_limit(self):
        self.assertFalse(scale_prior_violation("bin", 1.0, tolerance=1.2)["violation"])
        self.assertTrue(scale_prior_violation("bin", 1.09, tolerance=1.2)["violation"])


class SelectScalePriorTargetTests(unittest.TestCase):
    def test_bin_carrier_targets_declared_table(self):
        decision = select_scale_prior_target(
            {"bin": 2, "table": 5, "desk": 1},
            1.6,
            source_label="bin",
            min_target_share=0.15,
        )
        self.assertEqual(decision["target"], "table")
        self.assertGreater(decision["target_share"], 0.5)

    def test_candidates_must_accommodate_extent(self):
        # tablet (0.5m prior) cannot absorb a 1.6m carrier even if declared
        decision = select_scale_prior_target(
            {"bin": 2, "tablet": 6},
            1.6,
            source_label="bin",
        )
        self.assertEqual(decision["target"], "")
        self.assertEqual(decision["abstain_reason"], "no_scale_compatible_declared_target")

    def test_weak_target_share_abstains(self):
        decision = select_scale_prior_target(
            {"vent": 8, "table": 1},
            1.5,
            source_label="vent",
            min_target_share=0.15,
        )
        self.assertEqual(decision["target"], "")
        self.assertEqual(decision["abstain_reason"], "target_share_below_minimum")

    def test_well_supported_source_keeps_authority(self):
        # room0 guard: a true large cushion declares cushion consistently and
        # the violation is marginal (1.3 vs prior 1.0 = 1.3x < hard ratio)
        decision = select_scale_prior_target(
            {"cushion": 9, "sofa": 3},
            1.3,
            source_label="cushion",
            max_source_share=0.5,
            severity_ratio=1.3,
            hard_violation_ratio=2.0,
        )
        self.assertEqual(decision["target"], "")
        self.assertEqual(decision["abstain_reason"], "source_well_supported")
        self.assertFalse(decision["hard_violation"])

    def test_hard_violation_overrides_consensus_guard(self):
        # office1 case: 70/70 detections declare tissue-paper on a 1.4m carrier
        # (3.1x prior) — systematic detector bias must not keep authority.
        decision = select_scale_prior_target(
            {"tissue-paper": 70},
            1.399,
            source_label="tissue-paper",
            max_source_share=0.60,
            severity_ratio=3.1,
            hard_violation_ratio=2.0,
        )
        self.assertTrue(decision["hard_violation"])
        # consensus guard skipped; declared offers no alternative so selection
        # abstains with no-compatible-target (caller falls back to CLIP re-readout)
        self.assertEqual(decision["target"], "")
        self.assertEqual(decision["abstain_reason"], "no_scale_compatible_declared_target")

    def test_no_declared_evidence_abstains(self):
        decision = select_scale_prior_target({}, 1.5, source_label="bin")
        self.assertEqual(decision["target"], "")
        self.assertEqual(decision["abstain_reason"], "no_declared_evidence")

    def test_priors_table_covers_known_mechanism_labels(self):
        for label in ("tissue-paper", "cloth", "bin", "table", "vent", "cushion", "sofa"):
            self.assertIn(label, DEFAULT_MAX_EXTENT_PRIORS)

    def test_scannet_priors_frozen_and_scoped(self):
        # Structural / person / other-* classes carry no prior (never repaired).
        for label in ("wall", "floor", "ceiling", "door", "window", "person",
                      "otherstructure", "otherfurniture", "otherprop"):
            self.assertNotIn(label, SCANNET_NYU40_MAX_EXTENT_PRIORS)
        for label in ("chair", "table", "pillow", "paper", "box", "television"):
            self.assertIn(label, SCANNET_NYU40_MAX_EXTENT_PRIORS)
        self.assertTrue(all(0.3 <= v <= 4.0 for v in SCANNET_NYU40_MAX_EXTENT_PRIORS.values()))


if __name__ == "__main__":
    unittest.main()
