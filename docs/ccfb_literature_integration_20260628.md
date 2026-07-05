# DuoGraph3D literature integration memo — 2026-06-28

## Read artifacts

- Online / mapping notes: `analysis/literature/ccfb_sota_20260628/online_mapping_notes.md`
- OV-3DIS / geometry notes: `analysis/literature/ccfb_sota_20260628/ov3dis_geometry_notes.md`
- SOTA critical review: `docs/ccfb_sota_critical_review_20260628.md`

## Cross-paper pattern

The mature pipeline pattern is:

1. Stabilize a 3D carrier / proposal / instance track.
2. Aggregate multi-view evidence around that carrier.
3. Perform object-centric semantic readout.
4. Use geometry / view / depth / context consistency to suppress false semantic authority.
5. Export only when source coverage and evidence reliability pass gates.

## Directly useful for DuoGraph3D

| Source | Useful pattern | DuoGraph3D hook |
| --- | --- | --- |
| OVI-MAP | decouple instance reconstruction from semantic inference; object-centric view coverage | export-source gate; view/evidence budget monitor |
| ESAM | 3D query / geometry-aware pooling; query-based merge | future memory node representation; association diagnostics |
| OnlineAnySeg | append-only mask bank + mapping table; spatial association dominates feature similarity | graph memory update discipline; no-candidate / wrong-candidate monitor |
| Open3DIS | 2D masks aggregated into geometrically coherent 3D proposals | carrier formation and repair family framing |
| Details Matter | tracking-based proposal aggregation, AlphaCLIP, SMS false-positive filtering | object-centric readout; semantic false-positive guard |
| MV3DIS | 3D-guided mask matching + depth consistency weight | carrier-v2 reliability signal: projection/depth support |
| OV3D-CG | context-aware MLLM reasoning after proposal | optional future semantic readout probe, not current core claim |
| GeoGuide | hierarchical geometry-semantic consistency | frame/key/object/inter-object reliability diagnostics |

## Immediate implementation decision

Carrier reliability gate v2 should be **soft and layered**, not a hard target-label veto:

- geometry authority can substitute for missing target label only when a rule has explicit support-shape constraints;
- source evidence should still require enough observations / source-label share when available;
- point-mass budget remains a global safety guard;
- all applied/blocked decisions must be logged with object count, point count, shape diagnostics, detection count, source/target support, and projected relabel point rate.

## Claim boundary

Literature supports the general principle that multi-view geometry and object-centric readout improve OV-3D reliability. It does **not** prove DuoGraph3D's E70 local rules generalize. That must be established by the carrier-v2 ablation.
