# Phase 4 Metric Lock (Paper-Candidate)

日期：2026-04-23

## Purpose
Freeze the Phase 4 paper-candidate metric families so the remaining result-package work stops drifting.

## Frozen DuoGraph3D main metric families

These metrics are now the **paper-candidate** DuoGraph3D metric set for the real-observation Phase 4 package:

1. `identity_fragmentation_count`
   - object identity stability / fragmentation
2. `track_consistency_rate`
   - consistency of track-to-memory assignment under real observation sequences
3. `memory_object_purity`
   - purity of memory-object ownership over observed tracks
4. `real_observation_frame_rate`
   - how much of the package is supported by real observation frames
5. `relation_density`
   - graph-memory interaction density
6. `memory_relation_edge_count`
   - explicit graph-memory activation count
7. `geometry_support_mean`
   - current geometry-backed support signal until a stronger map-quality metric replaces it in later work

## Metric policy
- Old proxy metrics remain available for backward compatibility and historical comparison.
- The above real-observation metrics are the preferred Phase 4 package metrics.
- External baselines remain family-specific and are compared through the external baseline matrix rather than forced into one fake shared scalar table.

## Current package evidence snapshot
- Scene count: `24`
- All old proxy scenes pass: `False`
- All old proxy regimes pass: `False`
- Observation-grounded aggregate rows available: `7`
