# Phase 5 Reviewer Defense Pack

日期：2026-04-23  
状态：Phase 5 argument-complete reviewer-defense asset

---

## 1. Why not just stronger online merge?

### Short answer
DuoGraph3D is not only a stronger merge heuristic. Its contribution is the separation between:

1. current-evidence repair
2. current-to-memory association
3. graph memory as long-term decision authority

### Current supporting evidence
- Phase 4 broad package shows nontrivial identity fragmentation differences across regimes.
- The method now contains:
  - explicit evidence-graph repair
  - explicit relation-edge memory
  - explicit dual-consistency gate

### Safe phrasing
> We do not claim that DuoGraph3D is simply a more aggressive merge strategy. The current implementation and evidence package instead support the need for a structured current-repair + memory-association decomposition under real observations.

---

## 2. Why is the graph necessary rather than decorative?

### Short answer
The graph is no longer only a naming layer:
- relation edges are stored in memory
- co-visibility updates are explicit
- relation bonuses feed back into association

### Current supporting evidence
- relation-edge counts are nonzero on real ScanNet runs
- Phase 2 introduced explicit graph-memory activation
- Phase 4 metrics include relation density and relation-edge count

### Safe phrasing
> In the current package, graph memory is decision-bearing rather than post-hoc only, because relation edges are updated online and can influence later association scores.

---

## 3. Why isn’t temporal propagation the only real contribution?

### Short answer
Temporal continuity is necessary but not sufficient. DuoGraph3D now explicitly blocks continuity-only association when geometry-profile consistency collapses to zero.

### Current supporting evidence
- Phase 2 added the dual-consistency gate
- continuity-without-geometry regression is explicitly tested

### Safe phrasing
> Our current implementation does not treat temporal propagation as the full solution. Instead, it is one side of a dual-consistency decision, with geometry-profile consistency acting as a co-constraint.

---

## 4. Why is this not just association engineering?

### Short answer
Because the contribution is not a single matching heuristic, but the coordinated system structure:
- evidence graph repair
- memory association
- explicit graph-memory state
- temporal/geometric co-constraint

### Safe phrasing
> The central claim is structural: online object-centric reconstruction benefits from a particular decomposition and state authority design, not merely from local score tuning.

---

## 5. Why don’t the external baselines collapse into one scalar table?

### Short answer
Because the baseline set should be organized by **story-aligned roles**, not flattened into one convenience-driven number.

### Current supporting evidence
- DEVA addresses the temporal-backbone question
- OnlineAnySeg-style systems address the direct zero-shot online 3D question
- ConceptFusion / Open-Fusion address dense online mapping alternatives
- ConceptGraphs / Open3DSG address graph/object-memory alternatives
- ESAM is at most an auxiliary metric-compatibility reference, not the defining direct baseline

### Safe phrasing
> We group external comparisons by the question each baseline answers. This is more faithful to the paper's contribution than collapsing all methods into one misleading scalar table.

---

## 6. Nearest-neighbor comparison block (draft paragraph)

The closest neighboring systems contribute important ingredients but do not fully subsume the current DuoGraph3D formulation. OnlineAnySeg is the nearest direct zero-shot online 3D comparator; DEVA provides the strongest temporal propagation backbone; ConceptFusion / Open-Fusion represent dense online open-vocabulary mapping alternatives; and ConceptGraphs / Open3DSG represent object-centric graph structure alternatives. DuoGraph3D instead targets the missing conjunction: current-evidence repair, current-to-memory association, and graph memory as decision-bearing long-term state under explicit temporal and geometric co-constraints.

---

## 7. Claim boundary statement

### Safe final boundary
This paper does **not** claim:
- first-ever online zero-shot 3D segmentation
- first-ever open-vocabulary 3D mapping
- universal dense reconstruction superiority

This paper **does** claim:
- a structured two-layer object-memory design is operationally useful
- graph memory should be decision-bearing rather than decorative
- temporal continuity and geometry consistency should jointly constrain identity updates

---

## 8. Reviewer attack matrix (Phase 5 draft)

| Reviewer type | Likely attack | Current answer type | Current strength |
| --- | --- | --- | --- |
| 3D segmentation reviewer | why not just better online merge? | structural + regime results | medium |
| graph reviewer | why is the graph necessary? | implementation-backed | medium-high |
| video reviewer | why isn’t temporal propagation enough? | dual-consistency gate | high |
| tracking reviewer | why not just better association? | structural decomposition | medium |
| baseline reviewer | why are comparisons grouped by role instead of one scalar table? | story-aligned comparison protocol | medium |

---

## 9. Immediate strengthening targets for final draft

1. tighten the nearest-neighbor paragraph
2. connect each reviewer attack to a specific table/figure
3. avoid overclaiming baseline comparability
4. keep all novelty language inside the frozen claim boundary

---

## 10. Asset linkage notes

- “why not just stronger online merge?” should point to:
  - internal regime main table
  - ablation table
  - layer-1 / layer-2 figures
- “why is the graph necessary?” should point to:
  - graph-memory figure
  - relation-edge metrics
  - representative casebook excerpts
- “why aren’t comparisons cleaner?” should point to:
  - external baseline family table
  - provenance note
  - supplementary provenance appendix if needed
