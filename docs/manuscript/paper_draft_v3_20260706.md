# Semantic Authority Must Be Earned at Decision Time: Auditable Carrier-Authority Control for Online Open-Vocabulary 3D Mapping

Working draft v3 — 2026-07-06.  Supersedes the 2026-04-23 phase5 draft entirely.
Numbers source: `docs/ccfb_tables_20260706.md`; narrative source: `docs/ccfb_paper_story_v3_20260706.md`.

## Abstract (draft)

Object-centric open-vocabulary 3D mapping systems fuse per-frame vision-language
readouts into persistent object maps under an implicit assumption: whatever the
semantic fusion produces is authoritative.  We show, with object-level forensic
evidence on the official ConceptGraphs Replica protocol, that this assumption
fails in three previously uncharacterized ways: (i) *merge-manufactured
corruption* — feature averaging across merged fragments fabricates readout
labels that no detection ever voted for (a 1.56 m table carrier read as "bin"
with zero bin votes in its own detections); (ii) *consensus-surviving bias* —
systematic detector errors persist through multi-view voting (a cloth carrier
declared "tissue-paper" by 70/70 detections at 3.1× the physically plausible
extent); and (iii) *substrate mismatch* — treating boundary-noise label mixtures
on raw geometry buckets as if they were object-level evidence.  We propose a
family of carrier-authority mechanisms — a per-pair label-cluster merge veto
with evidence-floor and mutual-containment guards, and a scale-prior authority
check with declared-evidence targets and audited abstention — each of which
requires only GT-free, scene-independent global constants, and each of whose
decisions is logged with its object-level evidence.  On the consolidated-memory
substrate the mechanisms are causal: they recover the strongest known per-scene
results exactly (+8.17 mIoU on office1 over ConceptGraphs, ablating cleanly to
the +2.79 legacy baseline), and prevent — rather than repair — the fabricated
readouts (+8.19 on office2 with no repair fired, versus +6.49 for the best
repair-based prior result).  Applying the same mechanisms *post hoc* to
ConceptGraphs' own released maps is provably inert: its online merging leaves
zero recoverable merge decisions, and even with perfectly reconstructed
detection-level evidence (alignment 0.9999), post-hoc repair degenerates to
noise.  Authority control is only effective at decision time — which is, we
argue, the reason online object memories should exist.  We release the full
audit trail, twelve pre-registered negative boundaries, and a quantitative
dissection of the scene-composition open problem.

## 1. Introduction

Paragraph plan:

1. **Setting.**  Online OV 3D mapping (ConceptGraphs lineage): per-frame
   class-agnostic masks + CLIP features, incrementally associated and merged
   into an object map; semantics read out from fused features.
2. **The implicit authority assumption** and its three failure families, each
   introduced by its forensic exhibit (bin carrier profile; 70/70 tissue
   consensus; office0 geometry-bucket junk relabels).  Each exhibit is a real
   object record from our audit logs, not an illustration.
3. **Claim.**  Semantic readout must *earn* authority at each decision point:
   merging two carriers requires that no well-supported independent label
   cluster is erased; a readout keeps naming rights only while it is physically
   plausible and multi-view supported; and these checks are only meaningful on
   substrates that carry object-level evidence.
4. **Why online/in-the-loop** (the T5 result up front): post-hoc application to
   CG's own maps is inert — zero merge candidates remain, and repair without
   decision-time context is noise.  The two-layer online memory exists to keep
   the evidence alive until each authority decision is made.
5. **Contributions** (three, matching story v3 §1).

## 2. Related Work

- Object-centric OV mapping: ConceptGraphs, ConceptFusion, HOV-SG (protocol
  kin); our work adds decision-time authority control + auditability.
- Online 3D segmentation: OVI-MAP (decouples reconstruction from semantics for
  efficiency; no authority verdicts, no audit), OnlineAnySeg, ESAM.
- OV-3DIS recipes: Open3DIS, Details Matter, OpenMask3D (object-centric
  aggregation; offline, AP-protocol — bridged in supplement, not compared on
  the main table).
- Geometry-semantic consistency: GeoGuide (trained, offline) — supports the
  premise that geometry should constrain semantics; we provide the untrained,
  online, per-decision version.

## 3. Method

### 3.1 System substrate (brief)
Two-layer online graph memory (Layer1 current-evidence repair; Layer2
current-to-memory association; consolidated memory-dense export).  The memory
is not claimed to improve accuracy per se (A2 ablation); it exists to maintain
the evidence state — per-object multi-view declared-label distributions,
detection counts, geometry — that authority decisions consume (per T5, that
evidence is unrecoverable after the fact).

### 3.2 M1: per-pair label-cluster merge veto
CG-style postprocess merging with a veto: a candidate pair (spatial containment
> 0.7, visual sim > 0.8) is refused when both sides carry distinct,
well-supported declared clusters.  Guards, each derived from a named forensic
failure: evidence floor (min-side observations; office2's same-table fragments
at 12–17 obs vs office1's true distinct pair at 164/567), mutual-containment
skip (room2's comforter|chair at 0.86/0.83 both ways = one observation stream
split by readout noise), and gate-off ≡ legacy bit-exactness.

### 3.3 M2: prevention over repair
The office2 dual-operating-point result: with carriers preserved, the
fabricated "bin" readout never exists (+8.19, no repair fired) — matching the
best repair-based result (+8.21) and exceeding the prior scene record (+6.49).
Prevention and repair are the same mechanism seen before/after the corruption
event; prevention is strictly more general (T5: repair-after-the-fact fails).

### 3.4 M3: scale-prior authority check with audited abstention
Frozen commonsense max-extent priors per class name (LLM-generated, committed
before evaluation; separate frozen table per vocabulary — Replica and NYU40).
A readout violating its prior loses naming rights only if: the multi-view
declared distribution does not itself support it (consensus band), or the
violation is physically impossible (hard-ratio ≥ 2×, the office1 70/70 case).
Replacement labels come from declared evidence only (the CLIP re-ranking
fallback was measured as noise and is disabled); otherwise the object abstains,
and every abstention is logged with its reason (office4's six vent violations
all abstained — pre-registered).

### 3.5 Mechanism scope
The evidence premises hold only on consolidated substrates; on raw geometry
buckets declared mixtures are boundary noise (office0: 148 vetoes + 15
declared-backed junk relabels) — mechanisms scope to consolidated exports,
raw-coverage exports pass through.

## 4. Experiments

Protocol: official ConceptGraphs Replica semantic evaluation
(`eval_replica_semseg`, n_exclude=6), gaps vs the reproduced official CG
baseline (all = 24.531 mIoU).  Scene accounting: office1/office2 development;
room0/room2/office4 diagnostic (guards derived from their failures, no
per-scene tuning); room1/office0/office3 untouched validation.

- **4.1 Mechanism causality (T1)** — office1 ladder; office2 dual operating
  points; validation-scene gate deltas (+0.50/+2.90/+2.21).
- **4.2 Post-hoc infeasibility (T5)** — CG's own maps: legacy −0.08 (protocol
  parity), gate zero candidates on all scenes, sp noise −0.46 with alignment
  0.9999.  The in-the-loop thesis.
- **4.3 Composition open problem (T2)** — no single-substrate config is
  positive at full scale; E70 dissected as a five-layer scene-choice oracle
  (+3.041) and reported as the ceiling; the honest cost-of-no-scene-knowledge.
- **4.4 Audit & pre-registration (T3)** — decision counts and the office4
  abstention prediction written before the run.
- **4.5 Negative boundaries (T4)** — twelve rejected designs, each with its
  object-level counterexample; floor/threshold sensitivity curves.
- **4.6 Transfer (T6, pending)** — ScanNet NYU40 subset with frozen priors:
  mechanism fire/abstain sanity and gate behavior on real-world scans.

## 5. Limitations

Single-config full-scene composition remains open (quantified, not hidden);
Replica is synthetic (ScanNet transfer is sanity-scale, not a full benchmark);
the protocol family is semantic mIoU (AP bridge in supplement); the office1
repair delta beyond carrier preservation requires knowledge outside all GT-free
evidence streams (documented as the oracle gap).

## 6. Reproducibility

Every table row maps to an artifact root + commit; all thresholds are global
constants committed before their first evaluation; audit JSONs ship per scene.
