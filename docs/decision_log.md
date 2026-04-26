# Decision Log

## 2026-04-23 — Phase 0 claim freeze

### Decision 1
- Freeze the project against a **top-tier final-quality target**, not a minimum publishable version.
- Rationale: the approved roadmap explicitly prioritizes final CVPR/ICCV-grade quality over minimum completion.

### Decision 2
- Use an **ICCV-style unified framework positioning** as the current primary submission target.
- Rationale: existing framing notes indicate the project is strongest as a unified object-memory framework paper rather than a pure benchmark-driven claim.

### Decision 3
- Keep strong claims on graph memory and dual consistency as **frozen final-paper target claims**.
- Rationale: the project is explicitly targeting top-tier final quality rather than a minimum publishable downgrade, so later phases are obligated to strengthen implementation/evidence until those claims are reviewer-safe.

### Decision 4
- Freeze external baseline targets now, with DEVA as mandatory and one online 3D nearest neighbor plus one dense/open-vocabulary mapping nearest neighbor as required.
- Rationale: later phases must optimize against known reviewer expectations rather than expanding comparison scope ad hoc.

### Decision 5
- Keep the strong graph-memory and geometry-consistency claims as **final-paper target claims**.
- Rationale: the project is explicitly pursuing top-tier final quality rather than a minimum publishable downgrade, so claim weakening should happen only via explicit blocker escalation, not by default during Phase 0.

## 2026-04-23 — Phase 1 real observation path replacement

### Decision 6
- Treat the prior `to_frame_inputs(...)` generators as explicitly synthetic paths and isolate them under `to_synthetic_frame_inputs(...)`.
- Rationale: later phases need a real-observation main path, and the codebase must stop conflating synthetic/test generation with submission-grade evidence input.

### Decision 7
- Use executed **DEVA output JSON** as the first real Replica observation source.
- Rationale: this is the strongest already-available real per-frame object stream accessible within the current project boundary.

### Decision 8
- Use **ScanNet online monitor JSON** as the first real ScanNet observation source for Phase 1.
- Rationale: it provides a real track-bearing online stream sufficient to unblock the Phase 1 replacement step, even though later phases still need stronger semantic/geometry-rich evidence.

### Decision 9
- Accept the remaining ScanNet label-mesh artifact gap as a tracked risk, not a Phase 1 blocker.
- Rationale: Phase 1 requires a real observation chain and nonempty runs, which were achieved despite the missing label mesh files.

## 2026-04-23 — Phase 2 method strengthening

### Decision 10
- Introduce explicit relation edges into `ObjectGraphMemory` rather than keeping graph memory as node-state rhetoric only.
- Rationale: the top-tier frozen claim requires graph structure to exist in implementation, not only in paper wording.

### Decision 11
- Upgrade layer-1 from grouping-only repair to an evidence-graph compatibility process with edge reasons and connected components.
- Rationale: Phase 2 must make the current-evidence graph operationally real, not merely diagrammatic.

### Decision 12
- Make layer-2 relation-aware by adding candidate bonuses from historical co-visibility edges.
- Rationale: this is the smallest implementation step that turns object memory from independent nodes into interacting graph state.

### Decision 13
- Treat nonzero relation-edge activation on real ScanNet validation as the Phase 2 measurable activation check.
- Rationale: Phase 2 needs a concrete signal that the new graph machinery is active on real-observation runs rather than existing only in unit tests.

### Decision 14
- Replace scalar-only geometry matching with an explicit **geometry-profile consistency** operator over support size, depth scale, and geometry support.
- Rationale: Phase 2 must close the “geometry consistency is overstated” reviewer attack by making geometry compatibility a named multi-signal operator rather than a single scalar hint.

### Decision 15
- Enforce a **dual-consistency gate** in association: temporal continuity alone is no longer enough when geometry-profile consistency collapses to zero.
- Rationale: this makes temporal and geometric evidence jointly constrain identity updates instead of letting continuity alone carry the decision.

## 2026-04-23 — Phase 3 external baseline system build-out

### Decision 16
- Treat DEVA official offline as the first fully formalized external baseline family for DuoGraph3D.
- Rationale: it already had official repo provenance plus executed artifacts and is directly aligned with the temporal-baseline requirement.

### Decision 17
- Formalize ESAM / EmbodiedSAM as the second external baseline family using official repo provenance and executed ScanNet-MV family artifacts from the tracked local fork lane.
- Rationale: this satisfies the need for a strong online 3D nearest-neighbor family while staying honest about executed provenance.

### Decision 18
- Keep the provenance caveat explicit: ESAM metrics currently come from a documented fork execution root rather than a fresh rerun inside the official checkout.
- Rationale: reviewer credibility depends more on transparent provenance than on pretending the execution path was more official than it was.

### Decision 19
- Leave ConceptGraphs as a discovered official comparison target for later phases, but do not claim it as a completed executed baseline lane yet.
- Rationale: Phase 3 requires two external baseline families; DEVA + ESAM satisfy that threshold without inventing results for ConceptGraphs.

### Decision 20
- Generate a unified external baseline matrix to make the external lanes comparison-ready by axis, even when metric families differ across datasets.
- Rationale: Phase 3 needs a concrete comparison surface rather than isolated summary artifacts.

### Decision 21
- Attempt a direct official ESAM rerun from the official checkout before accepting the documented fork-executed lane.
- Rationale: this tests whether the provenance caveat can be removed inside the current scope; the observed environment drift is therefore fresh blocker evidence rather than an assumption.

## 2026-04-23 — Phase 4 paper-candidate metric layer

### Decision 22
- Freeze a first paper-candidate real-observation metric set around identity fragmentation, track consistency, memory purity, observation frame rate, relation density, relation edge count, and geometry support mean.
- Rationale: Phase 4 needs a stable metric target before the larger real-observation result package can be expanded.

### Decision 23
- Keep old proxy pass summaries as historical context, but stop treating them as the primary Phase 4 evidence surface.
- Rationale: the roadmap requires the main table to stop depending on proxy-only evidence.

### Decision 24
- Promote the regime-matrix summaries into explicit Phase 4 analysis artifacts: main-table candidate, ablation table candidate, worst/best analysis, and failure casebook.
- Rationale: Phase 4 requires more than raw metrics; it needs analysis surfaces that can directly evolve into paper results sections.

### Decision 25
- Broaden the Phase 4 regime matrix to a larger ScanNet real-observation subset selected from high nonempty-frame scenes in the ESAM online-monitor artifact.
- Rationale: Phase 4 needs broader real-observation evidence before any honest paper-grade readiness judgment can be made.

### Decision 26
- Use local mature-work inspection (ESAM and ConceptGraphs) to keep Phase 4 metric evolution aligned with reviewer-familiar evidence surfaces.
- Rationale: when Phase 4 stalls, the correct recovery path is not arbitrary metric invention but triangulation against mature adjacent systems.
### Decision 27
- Keep Phase 4 external baseline families in a parallel comparison table rather than force-merging them into one misleading scalar main table.
- Rationale: DEVA and ESAM currently expose different evidence surfaces, so honest paper-candidate packaging should preserve that distinction instead of flattening it.

### Decision 28
- Make Phase 4 readiness explicit through a structured readiness artifact instead of relying on ad hoc narrative judgments.
- Rationale: the package is now large enough that readiness status must be machine-checkable and reviewer-facing summaries must distinguish “candidate package complete” from “paper-grade candidate”.

### Decision 29
- Downgrade the legacy Phase 0–3 proxy gates to historical reference for the broad Phase 4 real-observation package.
- Rationale: fresh evidence shows all 44 real-observation reports have zero ambiguity and zero memory-authority events, while fragmentation and consistency remain meaningfully measurable, so the old ambiguity/authority-centric proxy gates no longer diagnose package quality.

### Decision 30
- Use the structured Phase 4 readiness artifact as the authoritative internal paper-candidate readiness check.
- Rationale: after the proxy transition, readiness should be decided by the complete real-observation package plus analysis surfaces, not by legacy proxy gates that no longer match the current evidence mode.
### Decision 31
- Distinguish Phase 4 completion from final camera-ready completion: Phase 4 now targets an internal paper-grade candidate package, while Phases 5–6 remain responsible for final manuscript and submission hardening.
- Rationale: the roadmap requires Phase 4 to reach paper-grade candidate status, not to finish every later submission-strengthening task.

### Decision 32
- Start Phase 5 from a grounded markdown manuscript draft before choosing a final latex / submission template path.
- Rationale: the highest risk at this point is argument structure and evidence alignment, not document tooling.
### Decision 33
- Keep a dedicated claim-to-evidence map during Phase 5 so the manuscript cannot drift away from currently supported evidence.
- Rationale: the biggest remaining risk in Phase 5 is overclaiming while the draft becomes more polished.
### Decision 34
- Add a section-completion matrix and table-spec document so Phase 5 can be managed as a writing-completion problem rather than only as a free-form drafting problem.
- Rationale: once manuscript drafting begins, progress can silently stall unless each section and table has a tracked completion surface.
### Decision 35
- Add an appendix draft and submission asset manifest during Phase 5 so the manuscript lane is prepared for later formatting/hardening without losing provenance structure.
- Rationale: once writing assets multiply, a manifest and appendix draft reduce the risk of a brittle final handoff.
### Decision 36
- Materialize Phase 5 figures as standalone rendered assets and compile a PDF draft even before final camera-ready polishing.
- Rationale: Phase 5 needs concrete manuscript assets on disk, not only specs, before it can be reviewed honestly.

### Decision 37
- Treat the current Phase 5 bar as an argument-complete manuscript package with a verified PDF draft, not as final camera-ready formatting.
- Rationale: Phase 6 is explicitly reserved for submission hardening, so Phase 5 should close once the manuscript package is handoff-ready rather than perfectly typeset.

### Decision 38
- Reject the earlier AP/ESAM-first experiment framing as the primary paper story.
- Rationale: DuoGraph3D's frozen novelty centers on zero-shot online 3D matching, two-layer graph decomposition, and object maintenance, so a learning-based instance-segmentation family cannot define the main direct-baseline lane.

### Decision 39
- Reorganize experiments into story-aligned blocks: direct zero-shot online 3D neighbors, temporal backbone comparisons, two-layer necessity comparisons, graph-memory/object-maintenance comparisons, and only then auxiliary benchmark-compatibility references.
- Rationale: baseline selection must answer the innovation rows directly; benchmark compatibility is useful, but it is downstream of the paper story rather than upstream of it.
### Decision 40
- Prioritize baseline bring-up by story fit first, then readiness, rather than by the availability of a convenient AP surface.
- Rationale: OnlineAnySeg and ConceptGraphs are more faithful to the paper's core innovation rows than ESAM-style learning-based segmentation baselines, so they should be brought up before any further AP-compatibility work.

### Decision 41
- Set the immediate baseline execution order to: DEVA temporal lane maintenance -> OnlineAnySeg direct-neighbor bring-up -> ConceptGraphs graph-memory bring-up -> ConceptFusion/Open-Fusion acquisition -> ESAM auxiliary only.
- Rationale: this order maximizes story alignment while still exploiting what is already locally available and runnable.
### Decision 42
- Implement format-aligned DuoGraph3D exports for OnlineAnySeg and ConceptGraphs before claiming external benchmark numbers.
- Rationale: the fastest safe path is to align output contracts first while explicitly marking the current geometry as proxy until dense point/mask assignments are available.


## Decision 43 — Dense geometry sidecar is the official bridge into external evaluator surfaces
- Date: 2026-04-23
- Rationale: output-format alignment must not pretend that placeholder masks are benchmark evidence. A sidecar schema lets DuoGraph3D keep object identity as the source of truth while accepting real point assignments, class ids, colors, and object features from whichever mature upstream extraction path proves most reliable.
- Rejected: serialize large dense masks directly into every bounded-slice summary | this would bloat normal experiment reports and make lightweight internal runs harder to inspect.
- Consequence: OnlineAnySeg / ConceptGraphs exports can now be generated in three clearly labeled states: proxy geometry, dense geometry not yet official-ready, and official-ready surface when required metadata is declared.

## Decision 44 — Treat the first AP result as a subset stepping stone, not a final main-table claim
- Date: 2026-04-23
- Rationale: the fresh ScanNet200 subset5 rerun beats the strict online baseline on AP/AP50/AP25, but it is not yet full-validation and does not beat every stronger candidate-budget baseline family.
- Constraint: top-tier submission quality requires full-split validation and same-budget ablations before claiming a main-table advantage.
- Rejected: promote the subset5 win directly into the manuscript main table | insufficient split coverage and possible budget mismatch.
- Confidence: high
- Scope-risk: moderate
- Directive: use this as evidence that the evaluator path is live; continue with controlled same-budget ablations before making paper claims.
