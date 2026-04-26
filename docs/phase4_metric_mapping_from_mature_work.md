# Phase 4 Metric Mapping from Mature Work

日期：2026-04-23

## Purpose
Capture how mature adjacent systems currently evaluate related capabilities, so DuoGraph3D can keep aligning its Phase 4 metric layer with reviewer-familiar evidence surfaces.

## Source 1 — EmbodiedSAM / ESAM

### Local evidence used
- Official repo on remote machine: `/home/nebula/xxy/ESAM`
- README and `docs/run.md`
- Config files under `configs/ESAM_CA/*.py`
- Result artifacts:
  - official-family ScanNet-MV metrics captured from executed artifacts

### What ESAM uses
- `all_ap`
- `all_ap_50%`
- `all_ap_25%`
- ScanNet/ScanNet200 instance-segmentation evaluation surface

### Implication for DuoGraph3D
DuoGraph3D still needs a stronger eventual mapping from its current observation-grounded package into reviewer-familiar segmentation/grouping quality numbers when possible. The current Phase 4 metrics are valuable for internal paper-candidate analysis, but they are not yet a full substitute for AP-style evidence.

## Source 2 — ConceptGraphs

### Local evidence used
- Official repo on remote machine: `/home/nebula/xxy/concept-graphs`
- README / streamlined README / eval scripts

### What ConceptGraphs exposes
- scene-graph construction and world-graph structure
- semantic-segmentation-style evaluation utilities
- metrics such as `precision`, `recall`, `mrecall`, `fmiou`

### Implication for DuoGraph3D
For the graph-memory side, reviewer-familiar evidence may eventually require more than relation-edge counts and densities. Later phases should be ready to connect DuoGraph3D graph outputs to more explicit graph/usefulness or semantic-evaluation surfaces.

## Current Phase 4 position

### What DuoGraph3D already has
- identity stability / fragmentation
- track consistency
- memory-object purity
- real-observation coverage
- graph relation density / edge count
- geometry support mean

### What still remains beyond the current package
- stronger segmentation/grouping quality mapping toward AP-like evidence
- stronger geometry / map-quality metric than the current geometry-support surrogate
- potentially stronger graph usefulness / graph quality evidence beyond relation counts

## Conclusion
The current Phase 4 metric lock is a justified **internal paper-grade candidate** layer. Mature adjacent systems still indicate that DuoGraph3D should keep strengthening its bridge toward reviewer-familiar segmentation/grouping/geometry evidence in later phases, but that remaining work is now a **post-Phase-4 strengthening objective**, not a blocker to concluding Phase 4 itself.
