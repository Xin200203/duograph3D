import unittest

from duograph3d.export_policy import (
    GEOMETRY_EXPORT_SOURCE,
    MEMORY_DENSE_EXPORT_SOURCE,
    MEMORY_EXPORT_SOURCE,
    ExportCoveragePolicy,
    choose_export_source,
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

    def test_invalid_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_export_source(
                strategy="unknown",
                memory_object_count=1,
                key_object_count=1,
                memory_point_count=1,
                key_point_budget=1,
            )


if __name__ == "__main__":
    unittest.main()
