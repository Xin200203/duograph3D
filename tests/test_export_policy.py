import unittest

from duograph3d.export_policy import (
    GEOMETRY_EXPORT_SOURCE,
    MEMORY_DENSE_EXPORT_SOURCE,
    MEMORY_EXPORT_SOURCE,
    ExportCoveragePolicy,
    choose_export_source,
    label_cluster_veto,
)


class ExportPolicyTests(unittest.TestCase):
    def test_auto_falls_back_when_memory_is_sparse(self):
        decision = choose_export_source(
            strategy="auto",
            memory_object_count=40,
            key_object_count=2571,
            memory_point_count=6449,
            key_point_budget=300000,
            policy=ExportCoveragePolicy(min_memory_objects=100, min_memory_key_ratio=0.10, min_memory_point_ratio=0.05),
        )
        self.assertEqual(decision["selected_source"], GEOMETRY_EXPORT_SOURCE)
        self.assertEqual(decision["fallback_reason"], "memory_object_count_below_coverage_floor")

    def test_auto_accepts_memory_after_object_and_point_coverage_pass(self):
        decision = choose_export_source(
            strategy="auto",
            memory_object_count=250,
            key_object_count=1000,
            memory_point_count=80000,
            key_point_budget=1000000,
            policy=ExportCoveragePolicy(min_memory_objects=100, min_memory_key_ratio=0.10, min_memory_point_ratio=0.05),
        )
        self.assertEqual(decision["selected_source"], MEMORY_EXPORT_SOURCE)
        self.assertEqual(decision["fallback_reason"], "memory_coverage_pass")

    def test_forced_sources_override_coverage_gate(self):
        sparse = dict(memory_object_count=1, key_object_count=1000, memory_point_count=100, key_point_budget=100000)
        self.assertEqual(choose_export_source(strategy="geometry", **sparse)["selected_source"], GEOMETRY_EXPORT_SOURCE)
        self.assertEqual(choose_export_source(strategy="memory", **sparse)["selected_source"], MEMORY_EXPORT_SOURCE)
        self.assertEqual(
            choose_export_source(strategy="memory-dense", **sparse)["selected_source"],
            MEMORY_DENSE_EXPORT_SOURCE,
        )
        self.assertEqual(
            choose_export_source(strategy="memory_dense", **sparse)["fallback_reason"],
            "forced_memory_dense",
        )

    def test_consolidation_auto_routes_by_ratio(self):
        # office1-like: 46 memory objects over 635 keys = 0.072 -> dense
        dense = choose_export_source(
            strategy="consolidation-auto",
            memory_object_count=46,
            key_object_count=635,
            memory_point_count=10000,
            key_point_budget=100000,
            consolidation_dense_max_ratio=0.175,
        )
        self.assertEqual(dense["selected_source"], MEMORY_DENSE_EXPORT_SOURCE)
        self.assertEqual(dense["fallback_reason"], "consolidation_ratio_dense")
        # office4-like: 135 memory objects over 490 keys = 0.276 -> geometry
        geo = choose_export_source(
            strategy="consolidation-auto",
            memory_object_count=135,
            key_object_count=490,
            memory_point_count=10000,
            key_point_budget=100000,
            consolidation_dense_max_ratio=0.175,
        )
        self.assertEqual(geo["selected_source"], GEOMETRY_EXPORT_SOURCE)
        self.assertEqual(geo["fallback_reason"], "consolidation_ratio_geometry")
        # empty memory always falls to geometry
        empty = choose_export_source(
            strategy="consolidation-auto",
            memory_object_count=0,
            key_object_count=500,
            memory_point_count=0,
            key_point_budget=100000,
        )
        self.assertEqual(empty["selected_source"], GEOMETRY_EXPORT_SOURCE)

    def test_invalid_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_export_source(
                strategy="unknown",
                memory_object_count=1,
                key_object_count=1,
                memory_point_count=1,
                key_point_budget=1,
            )


class LabelClusterVetoTests(unittest.TestCase):
    """Per-pair carrier-preservation gate for CG-style postprocess merging."""

    def test_distinct_well_supported_clusters_are_vetoed(self):
        # office1 archetype: tissue-paper carrier overlapping a cloth-dominated object
        decision = label_cluster_veto(
            {"tissue-paper": 5, "cloth": 1},
            {"cloth": 7, "blanket": 2},
            min_top_share=0.60,
            min_observations=2,
        )
        self.assertTrue(decision["veto"])
        self.assertEqual(decision["reason"], "distinct_label_clusters")
        self.assertEqual(decision["left_top"], "tissue-paper")
        self.assertEqual(decision["right_top"], "cloth")

    def test_same_top_label_fragments_still_merge(self):
        # office2 archetype: table fragments must keep merging
        decision = label_cluster_veto({"table": 9, "desk": 1}, {"table": 4}, min_top_share=0.60, min_observations=2)
        self.assertFalse(decision["veto"])
        self.assertEqual(decision["reason"], "same_top_label")

    def test_weak_support_does_not_veto(self):
        low_share = label_cluster_veto({"vent": 3, "table": 2, "panel": 2}, {"table": 6}, min_top_share=0.60, min_observations=2)
        self.assertFalse(low_share["veto"])
        self.assertEqual(low_share["reason"], "insufficient_top_share")
        few_obs = label_cluster_veto({"vent": 1}, {"table": 6}, min_top_share=0.60, min_observations=2)
        self.assertFalse(few_obs["veto"])
        self.assertEqual(few_obs["reason"], "insufficient_observations")

    def test_empty_or_malformed_counts_never_veto_or_raise(self):
        self.assertFalse(label_cluster_veto({}, {"table": 3})["veto"])
        self.assertEqual(label_cluster_veto({}, {"table": 3})["reason"], "empty_label_counts")
        malformed = label_cluster_veto({"table": "not-a-number", "chair": None}, {"table": 3})
        self.assertFalse(malformed["veto"])

    def test_diagnostics_report_shares_and_observations(self):
        decision = label_cluster_veto({"bin": 3, "table": 1}, {"table": 8, "desk": 2})
        self.assertEqual(decision["left_observations"], 4)
        self.assertEqual(decision["right_observations"], 10)
        self.assertAlmostEqual(decision["left_share"], 0.75)
        self.assertAlmostEqual(decision["right_share"], 0.8)


if __name__ == "__main__":
    unittest.main()
