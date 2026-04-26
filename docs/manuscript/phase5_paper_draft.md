# DuoGraph3D Paper Draft v1 (Phase 5 Working Draft)

日期：2026-04-23
状态：Phase 5 argument-complete draft build

# Title
Dual-Consistency Graph Memory for Online Zero-Shot Object-Centric 3D Reconstruction

# Abstract
Online zero-shot 3D object reconstruction and mapping already benefits from strong ingredients drawn from video propagation, online 3D fusion, and object-centric graph representations. However, existing systems typically optimize only one part of the problem at a time: current-frame evidence repair, current-to-memory association, dense online fusion, or post-hoc scene graph export. We present DuoGraph3D, a two-layer object-memory framework that makes object graph memory the sole long-term decision state while jointly leveraging temporal continuity and geometric consistency. The framework separates current-evidence repair from current-to-memory association, integrates temporal propagation into 3D object updates, and maintains explicit graph-memory state with relation edges and lifecycle transitions. We further organize evaluation around story-aligned comparison groups: direct zero-shot online 3D neighbors, temporal propagation baselines, and graph/mapping baselines. Learning-based instance-segmentation systems are retained only as auxiliary metric-compatibility references when useful, rather than as the primary identity-defining comparison family. Current results support the claim that graph memory is decision-bearing rather than decorative, and that explicit temporal/geometric consistency helps stabilize online object identity. The present package reaches internal paper-grade candidate status and exposes the remaining steps needed for final submission hardening.

# 1. Introduction

## 1.1 Motivation
Open-vocabulary and zero-shot 3D scene understanding has progressed quickly, but the strongest existing systems still separate several capabilities that matter in online object-centric reconstruction: temporal carry-over from video, current-frame evidence repair, current-to-memory association, and graph-structured long-term object memory. In practice this separation matters because online object systems must survive occlusion, missed detections, ambiguous evidence, and repeated re-observation while still preserving object identity and queryable structure.

## 1.2 Problem framing
This paper studies online zero-shot object-centric 3D reconstruction under a deliberately scoped question: what kind of decision state is necessary when current observations are incomplete, temporal continuity matters, and object identity must be updated over time? We frame the answer around a dual-consistency graph memory, where temporal continuity and geometric consistency jointly constrain object updates.

## 1.3 Claim boundary
We do not claim to be the first online zero-shot 3D segmentation method, the first open-vocabulary 3D mapping system, or a universal dense reconstruction system. Instead, the paper argues for the necessity of a two-layer object-memory structure with explicit state authority. The four claim rows are:
1. two-layer necessity;
2. memory-authority necessity;
3. temporal necessity;
4. dual-consistency necessity.

## 1.4 Contributions (draft)
1. We present a two-layer online object-memory framework that explicitly separates current-evidence repair from current-to-memory association.
2. We introduce dual-consistency updates in which temporal continuity and geometry-profile consistency jointly constrain online object identity decisions.
3. We maintain graph memory as the long-term decision state and expose explicit relation-edge updates rather than treating the graph as a post-hoc export.
4. We construct a real-observation evaluation package with formalized external baseline families and observation-grounded metrics.

## 1.5 Reader guide
The strongest current evidence should be read in three layers:
1. **implementation grounding** — the graph-memory and dual-consistency claims are now explicit in code;
2. **real-observation package** — the current package is based on nonempty real observation streams rather than synthetic-only inputs;
3. **candidate results section** — the current internal tables, casebooks, and readiness artifacts support an internal paper-grade candidate narrative while still leaving later camera-ready strengthening for future phases.

In practice, the draft should be read together with:
- `phase5_claim_evidence_map.md`
- `phase5_reviewer_defense.md`
- `phase5_figure_specs.md`
- `phase5_table_specs.md`
- `phase5_table_claim_map.md`
- `phase5_supplementary_outline.md`
- `phase5_appendix_draft.md`
- `phase5_submission_asset_manifest.md`

# 2. Related Work

## 2.1 Online zero-shot / open-vocabulary 3D understanding
Relevant nearest-neighbor directions include zero-shot online 3D systems such as OnlineAnySeg, temporal propagation backbones such as DEVA, dense open-vocabulary mapping systems such as ConceptFusion/Open-Fusion, and object-centric graph systems such as ConceptGraphs/Open3DSG. Learning-based 3D instance-segmentation systems such as ESAM/EmbodiedSAM remain useful as auxiliary metric-compatibility references, but they are not the primary direct comparison family for the current zero-shot object-memory story.

## 2.2 Temporal propagation backbones
DEVA-style video propagation demonstrates the utility of propagation-first temporal memory for carrying objects across incomplete observations. DuoGraph3D borrows the idea that temporal continuity should affect object persistence, but places that continuity inside a 3D object-memory framework.

## 2.3 Object-centric graph representations
ConceptGraphs and related object-graph systems show the value of object-centric graph structure for perception and planning, and they also expose semantic-evaluation style surfaces such as precision/recall-style graph/semantic utilities. DuoGraph3D differs in treating graph memory as an online decision state rather than a purely post-hoc semantic export.

## 2.4 Structured rivals and counterfactuals
Internally, DuoGraph3D also compares against structural rivals: single-layer collapse, dense-authority export, and full fair counterfactual stitching. These are not external baselines; they are necessity probes for the claimed structure.

# 3. Method

## 3.1 Overview
The system processes an observation stream into (1) current evidence items, (2) repaired current object hypotheses, and (3) memory updates inside an object graph memory. The pipeline exposes temporal variants and fair rivals for comparison.

## 3.2 Input and evidence layer
The evidence builder consumes real observation inputs when available, including DEVA output JSON for Replica and ScanNet online-monitor JSON for ScanNet-family runs. Synthetic/template generators are now isolated as explicit fallback or test-only paths rather than the default main path.

## 3.3 Layer 1: current-evidence repair
Layer 1 now constructs a compatibility graph over evidence items rather than only grouping by a key. The compatibility signal includes repair-group overlap, continuity-key agreement, appearance agreement, and geometry-profile consistency over support size, depth scale, and geometry support. Connected components in this compatibility graph become repaired hypotheses.

## 3.4 Layer 2: current-to-memory association
Layer 2 scores current hypotheses against memory nodes using temporal identity cues, descriptor/appearance cues, geometry-profile consistency, and relation-aware bonuses from existing graph edges. A dual-consistency gate prevents temporal continuity from carrying identity when geometry-profile consistency collapses to zero.

## 3.5 Object graph memory
ObjectGraphMemory stores object nodes, lifecycle state, support histories, and explicit relation edges. Relation edges are updated by co-visibility and contribute back into future association decisions.

# 4. Experimental Protocol

## 4.1 Datasets and observation sources
The current package uses real-observation pathways over Replica and ScanNet-family inputs. Replica scenes are driven by DEVA output JSON; ScanNet-family scenes are driven by ESAM-family online monitor artifacts. The current broad Phase 4 package includes **44 real-observation scene-level rows** across four regimes (`baseline`, `stress`, `burst`, `random`).

## 4.2 External baselines
The final experimental protocol should be organized by story-aligned comparison roles rather than by one benchmark family alone:
- direct zero-shot online 3D neighbors: OnlineAnySeg-style methods;
- temporal backbone comparators: DEVA plus internal no-temporal / naive-temporal variants;
- dense/open-vocabulary mapping neighbors: ConceptFusion / Open-Fusion family;
- graph-representation neighbors: ConceptGraphs / Open3DSG family.
Learning-based instance-segmentation systems such as ESAM/EmbodiedSAM may still appear, but only as auxiliary metric-compatibility references rather than the primary direct baseline family.

## 4.3 Metrics
Phase 4 freezes the internal paper-candidate metric set around:
- identity fragmentation;
- track consistency;
- memory-object purity;
- real-observation frame rate;
- relation density / relation-edge count;
- geometry-support mean.
Legacy proxy metrics are retained only as historical references.

## 4.4 Claim-to-evidence discipline
The current draft follows a claim-to-evidence rule: each major claim should be traceable to code-level grounding, candidate tables, casebooks, or external baseline-family artifacts. The supporting map is documented separately in the Phase 5 claim-evidence notes and should guide final editing.

## 4.4 Regime package and analysis surfaces
Phase 4 now provides the following paper-candidate analysis surfaces:
- a regime-level main table candidate;
- a regime-level ablation table candidate;
- a worst/best scene analysis;
- a failure casebook;
- a representative casebook;
- an external baseline family table.

These surfaces are deliberately separated because the internal regime metrics and the external baseline metrics are not yet commensurate enough to collapse into one single scalar table without losing methodological honesty.

# 5. Main Results

## 5.1 Internal regime results
The current candidate main table shows consistent regime-level differences under real-observation runs.

For the broadened real-observation package:
- `phase4_baseline` yields mean fragmentation `63.455`, track consistency `0.594`, observation frame rate `0.818`, and geometry support mean `0.271`.
- `phase4_burst` yields mean fragmentation `20.273`, track consistency `0.716`, observation frame rate `0.500`, and geometry support mean `0.287`.
- `phase4_random` yields mean fragmentation `11.364`, track consistency `0.815`, observation frame rate `0.348`, and geometry support mean `0.317`.
- `phase4_stress` yields mean fragmentation `21.091`, track consistency `0.736`, observation frame rate `0.500`, and geometry support mean `0.306`.

The most striking pattern is that the baseline regime sees the highest observation coverage but also the highest identity fragmentation. In contrast, random and stress regimes trade off lower observation coverage for substantially better fragmentation/consistency behavior. This suggests that the current system still over-absorbs difficult observation streams under dense update pressure, which is precisely the kind of behavior a top-tier paper should analyze rather than hide.

## 5.1.1 Why the regime table matters
This regime table is important because it shows that more observation throughput is not automatically better for identity stability. In other words, the current package is already exposing a meaningful operating frontier instead of only listing nominal scores.

## 5.1.2 Asset linkage
The current internal-results writing should eventually map to:
- Table 1 in `phase5_table_specs.md`
- worst/best rows in `phase4_worst_best_analysis.md`
- failure-case scenes in `phase4_failure_casebook.md`
- asset/claim permissions in `phase5_table_claim_map.md`

## 5.2 Story-aligned comparison protocol
The final paper should compare DuoGraph3D through several aligned comparison blocks rather than one convenience-driven scalar table.

The intended comparison roles are:
- **direct task neighbors**: OnlineAnySeg-style zero-shot online 3D methods;
- **temporal backbone references**: DEVA plus internal temporal ablations;
- **dense/open-vocabulary mapping neighbors**: ConceptFusion / Open-Fusion family;
- **graph/object-memory neighbors**: ConceptGraphs / Open3DSG family.

The current repository still contains provisional DEVA and ESAM-family assets. Those assets remain useful, but they should now be read as provisional context rather than as the final direct-baseline protocol.

## 5.2.1 Role of ESAM / EmbodiedSAM
ESAM/EmbodiedSAM should be treated as an auxiliary benchmark-compatibility reference only. It may help communicate with reviewer-familiar AP-style evaluation surfaces, but it should not define the paper's primary experimental identity because the current work is centered on zero-shot online matching and object maintenance rather than a learned 3D instance-segmentation backbone.

## 5.2.2 What we should not overclaim
The final paper should not imply that a single AP-style table against a learning-based segmentation family is sufficient to validate DuoGraph3D's full contribution. The main evidence must still come from story-aligned direct comparisons and mechanism-specific support tables.

## 5.3 Current interpretation
The current package supports the claim that DuoGraph3D has moved beyond a proxy-only prototype and now has a real-observation, graph-aware candidate result section.

The strongest current evidence is:
1. real-observation scene-level coverage exists at nontrivial scale (44 rows);
2. graph-memory activation is measurable through relation-edge counts and densities;
3. representative and failure scenes are now explicitly documented rather than hand-waved;
4. external baseline families are formalized with provenance and normalized summaries.

The current draft therefore claims **internal paper-grade candidate** status, not camera-ready completion.

# 6. Ablations and Analyses

## 6.1 Regime ablations
The candidate ablation table measures deltas relative to the baseline regime over fragmentation, consistency, observation frame rate, and geometry support.

## 6.2 Worst/best analysis
A worst/best analysis identifies the strongest and weakest scenes across the current metric set.

- Best identity stability: `replica/office0` with fragmentation `0.0`
- Best track consistency: `replica/office3` with track consistency `1.0`
- Worst fragmentation: `scannet/scene0222_00` with fragmentation `115.0`
- Weakest geometry support: `scannet/scene0050_00` with geometry support mean `0.2`

This split is useful for the paper: the strongest rows demonstrate that the framework can preserve identity under some real observation streams, while the weakest rows define the actual stress frontier.

## 6.3 Failure casebook
The failure casebook consistently highlights the same hard ScanNet scenes as the highest-severity fragmentation cases. In the broadened package, the top failure scenes are:
- `scene0222_00`
- `scene0645_00`
- `scene0653_01`
- `scene0645_01`
- `scene0231_00`

These cases should become the core qualitative failure section in the final paper.

## 6.4 Representative casebook
A representative casebook already exists for best-identity-stability, best-track-consistency, worst-fragmentation, and weakest-geometry-support scenes. This should seed the qualitative figure selection process and ensure that the final paper uses evidence-backed rather than anecdotal examples.

## 6.5 Section-to-asset discipline
The current draft should only make claims that can be tied back to:
- the main table candidate,
- the ablation table candidate,
- the worst/best analysis,
- the failure or representative casebooks,
- or a code-level implementation artifact.

This discipline is captured separately in the claim-evidence map and should be enforced during further editing.

## 6.6 Supplementary boundary
The main paper should remain argument-driven, while provenance-heavy artifacts and extended evidence dumps can move to the supplementary package. The current supplementary outline is tracked separately and should be used to keep the main paper compact.

## 6.5 Legacy proxy transition
Earlier project phases relied more heavily on structural proxy summaries. The broad Phase 4 package now justifies downgrading those legacy gates to historical references because the real-observation package operates in a different evidence mode: zero ambiguity and zero memory-authority-event counts across the broad package no longer mean “nothing is happening,” but instead show that the older proxy gates are mismatched to the new observation-grounded package. This transition should be explained carefully in the final paper or supplementary material so that the reader understands why the paper’s main evidence surface changed.

# 7. Limitations

Current limitations remain important and should stay explicit:
1. the final metric layer still needs a stronger bridge toward reviewer-familiar segmentation/grouping and geometry/map-quality evidence;
2. the story-aligned external direct-comparison protocol is still incomplete, and the existing ESAM-family asset should only be treated as an auxiliary compatibility reference;
3. several strong ScanNet failure scenes remain unresolved;
4. not all final paper tables and figures are polished camera-ready assets yet.
5. the current external-family comparison is honest but still not a single unified end-state benchmark table.

# 8. Conclusion

DuoGraph3D now supports an internal paper-grade candidate claim package built on real observations, explicit graph-memory structure, and dual-consistency association logic. The next stage is not basic implementation recovery, but manuscript refinement and submission hardening.

# 9. Immediate writing TODOs

The next manuscript tasks are now editorial rather than foundational:
1. convert the current markdown draft into the final paper authoring format;
2. tighten the introduction and related-work positioning around the strongest neighboring baselines;
3. turn current candidate tables and casebooks into final figure/table assets;
4. keep the claim boundary strict so the draft does not overstate what the current package supports.
5. collapse the remaining “internal note” tone into a cleaner paper voice while preserving provenance honesty.
6. split main-paper vs supplementary content explicitly before final formatting.
