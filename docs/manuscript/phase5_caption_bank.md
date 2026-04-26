# Phase 5 Caption Bank

日期：2026-04-23  
状态：Phase 5 drafting in progress

---

## Figure captions

### Figure 1 — Overall pipeline
**Caption draft:** DuoGraph3D processes real observations into evidence items, repairs them in a current-evidence graph, associates them against graph memory under dual temporal/geometric consistency, and commits updates into a decision-bearing object graph memory.

### Figure 2 — Layer-1 current-evidence graph
**Caption draft:** Layer-1 builds a compatibility graph over evidence items using continuity, appearance, and geometry-profile consistency before collapsing connected components into repaired current hypotheses.

### Figure 3 — Layer-2 current-to-memory association
**Caption draft:** Layer-2 scores current hypotheses against memory nodes using temporal identity cues, geometry-profile consistency, and relation-edge bonuses. A dual-consistency gate prevents continuity-only identity carry-over when geometry consistency collapses.

### Figure 4 — Graph-memory structure
**Caption draft:** Object graph memory stores online node state and explicit relation edges. Relation edges are updated by co-visibility and feed back into later association decisions.

### Figure 5 — Representative DEVA / Replica case
**Caption draft:** Representative Replica case under DEVA-derived observations. The system preserves a stable long-term object identity across repeated observations in a low-fragmentation scene.

### Figure 6 — Worst fragmentation ScanNet case
**Caption draft:** Failure case from the broadened ScanNet real-observation package. Dense object turnover produces high fragmentation, defining the current stress frontier for DuoGraph3D.

---

## Table captions

### Table 1 — Internal regime main table
**Caption draft:** Observation-grounded internal regime comparison across baseline, burst, random, and stress settings. Lower fragmentation and higher consistency indicate stronger identity stability under real observation streams.

### Table 2 — Internal ablation table
**Caption draft:** Regime deltas relative to the baseline regime. Positive deltas indicate improved performance under the metric direction used in the Phase 4 metric lock.

### Table 3 — External baseline family table
**Caption draft:** Story-aligned comparison protocol. External baselines are grouped by the question they answer—direct zero-shot online 3D comparison, temporal carry-over, graph/object-memory alternatives, dense mapping alternatives, and auxiliary benchmark-compatibility reference—rather than collapsed into one misleading scalar table.

### Table 4 — Readiness / package summary (supplementary)
**Caption draft:** Internal Phase 4 readiness summary showing that the current package reaches internal paper-grade candidate status while final camera-ready strengthening remains future work.

---

## Caption writing rules

1. Every caption should say what the reader should learn, not only what is displayed.
2. Figure captions must stay within the frozen claim boundary.
3. Table captions must not imply stronger cross-method comparability than the current package actually supports.
