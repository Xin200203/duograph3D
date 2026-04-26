# DuoGraph3D Appendix Draft v0

日期：2026-04-23  
状态：Phase 5 appendix argument-complete draft

---

## A. Expanded claim boundary

### A.1 What the paper claims
The main paper claims that DuoGraph3D benefits from:
1. a two-layer decomposition between current-evidence repair and current-to-memory association;
2. graph memory as decision-bearing state;
3. temporal continuity and geometry consistency as joint identity constraints.

### A.2 What the paper does not claim
The paper does not claim:
- first-ever online zero-shot 3D segmentation;
- first-ever open-vocabulary 3D mapping;
- universal dense reconstruction superiority;
- a fully unified benchmark-leading cross-method comparison table.

### A.3 Why this boundary matters
The appendix should preserve the same frozen claim boundary as the main paper and should never use provenance-heavy details to silently expand the novelty claim.

---

## B. Additional implementation details

### B.1 Evidence builder
- current observations are converted into evidence items
- real-observation adapters are available for:
  - DEVA output JSON on Replica
  - generic frame observation JSON
  - ScanNet online-monitor JSON
- synthetic generators are explicit fallback/test-only pathways

### B.2 Layer-1 repair details
- compatibility graph uses:
  - repair-group agreement
  - continuity agreement
  - appearance agreement
  - geometry-profile consistency
- repaired hypotheses are connected components of this graph

### B.3 Layer-2 association details
- association scores combine:
  - temporal identity cues
  - descriptor / appearance cues
  - geometry-profile consistency
  - relation-edge bonus
- dual-consistency gate blocks continuity-only carry-over when geometry-profile consistency collapses

### B.4 Graph memory details
- node state
- lifecycle state
- support history
- explicit relation edges
- co-visibility updates

---

## C. External baseline provenance

### C.1 DEVA
- official offline family
- local formalized artifact package exists

### C.2 ESAM / EmbodiedSAM (auxiliary compatibility reference)
- official-family external baseline lane is formalized
- current executed metrics come from a documented fork execution root
- a fresh official-rerun attempt was blocked by environment drift

### C.3 Why this still belongs in the paper package
These provenance details are important for reviewer trust, but they are usually better placed in the appendix/supplementary than in the main narrative unless the reviewer explicitly challenges them.

---

## D. Real-observation package construction

### D.1 Observation sources
- Replica:
  - DEVA output JSON
- ScanNet-family:
  - ESAM-family online monitor artifacts

### D.2 Regime matrix
The broad Phase 4 package uses:
- real-observation scenes from Replica and ScanNet-family data
- four regimes:
  - baseline
  - burst
  - random
  - stress

### D.3 Legacy proxy transition
The older proxy gates are retained as historical references only. The broad Phase 4 package shows that:
- all reports have zero ambiguity counts,
- all reports have zero memory-authority-event counts,
- fragmentation and consistency remain meaningfully measurable.

This justifies separating the current real-observation evidence surface from the earlier proxy gate logic.

---

## E. Extended result interpretation

### E.1 Internal regime interpretation
The baseline regime maximizes observation coverage but also shows the strongest fragmentation. This suggests that the current system still over-absorbs difficult streams when observation density is high.

### E.2 Failure frontier
The strongest current failure cluster is concentrated in a subset of ScanNet scenes. These scenes are the real stress frontier and should be treated as central analysis cases rather than awkward outliers.

### E.3 Why the external baseline table stays parallel
DEVA and ESAM should be retained only as auxiliary appendix material unless a later story-aligned protocol justifies a stronger role. The appendix should reinforce why convenience-driven flattening would distort the paper story.

---

## F. Reproducibility notes

The appendix should eventually include:
- key artifact paths
- scripts that generated the current Phase 4 package
- a compact explanation of how main-paper tables relate to the artifact tree

Current starting points:
- `docs/phase4_candidate_result_package.md`
- `docs/phase4_paper_candidate_tables.md`
- `docs/phase4_metric_mapping_from_mature_work.md`
