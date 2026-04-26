# DuoGraph3D Submission Lock (Top-Tier Quality Freeze)

日期：2026-04-23

## 1. Target venue freeze

### Primary target
- **ICCV-tier / CVPR-tier unified framework submission**

### Current primary venue decision
- **Primary target: ICCV-style submission**

### Why this is frozen now
Current DuoGraph3D framing is strongest when presented as a **unified object-memory framework** rather than a narrow benchmark-only trick. Existing internal notes already indicate that the representation + unified-system story is more natural for ICCV-style positioning than a pure headline-benchmark framing.

This does **not** lower the quality bar. It means the project will optimize for:
- method clarity
- unified structure
- reviewer-proof claim boundaries
- strong experimental support across multiple attack surfaces

## 2. Frozen core claim

DuoGraph3D aims to establish the following final claim:

> **A dual-consistency, two-layer, object-memory framework is operationally necessary for online zero-shot object-centric 3D reconstruction/mapping when long-term identity, temporal carry-over, and memory authority must be maintained under ambiguous evidence.**

### This frozen claim decomposes into four claim rows
1. **Two-layer necessity**
   - current-evidence repair and current-to-memory association should not be collapsed into one undifferentiated mechanism
2. **Memory-authority necessity**
   - object graph memory must be decision-bearing state, not just a post-hoc export layer
3. **Temporal necessity**
   - 2D temporal propagation must affect 3D object decisions, not just polish intermediate masks
4. **Dual-consistency necessity**
   - temporal continuity and geometric consistency must jointly constrain object lifecycle and association

## 3. Explicit non-claims

The final paper must **not** claim any of the following unless later phases produce overwhelming direct evidence:

- not “the first online zero-shot 3D segmentation method”
- not “the first open-vocabulary 3D mapping system”
- not “state-of-the-art on all online 3D segmentation benchmarks”
- not “a universal dense 3D reconstruction system”
- not “full scene-graph reasoning” unless explicit relation edges become first-class in the implementation and evaluation

## 4. Likely reviewer attacks to freeze against

1. **Why is this not just stronger online merge?**
2. **Why is the graph necessary rather than decorative?**
3. **Why is temporal propagation not the only real contribution?**
4. **Why is this not just association engineering with extra terminology?**
5. **Why are the external baselines insufficient or unfair?**

All later method and experiment work must directly help answer at least one of these five attacks.

## 5. Frozen baseline list

### Internal structural baselines (must keep)
- DuoGraph3D full
- single-layer rival
- dense-authority export rival
- full fair counterfactual
- temporal none / naive / DEVA family

### External baselines (must target)
1. **DEVA official offline lane**
   - reviewer-credible temporal comparison lane
2. **One online zero-shot / object-centric direct nearest neighbor**
   - priority candidate: OnlineAnySeg-style comparison
3. **One dense/open-vocabulary online mapping nearest neighbor**
   - priority family: ConceptFusion / Open-Fusion style comparison
4. **One graph-representation / object-memory nearest neighbor**
   - priority family: ConceptGraphs / Open3DSG style comparison
5. **Learning-based online 3D instance-segmentation reference (auxiliary only)**
   - example family: ESAM / EmbodiedSAM
   - role: metric-compatibility or supplementary reference, **not** the primary direct baseline family for the main paper story


### Current zero-shot baseline focus (2026-04-23 20:30 +08:00)
- Primary external zero-shot lanes under active execution: **OnlineAnySeg** (fixed subset20 bring-up completed) and **ConceptGraphs** (evaluator import repaired; scoring path pending).
- ESAM/EmbodiedSAM remains auxiliary compatibility evidence; it is not a blocker if it does not show the paper's main gain.

### Baseline quality rule
A baseline counts only when it has:
- documented inputs
- reproducible command path
- recorded output artifact
- metric mapping into the final result tables
- a comparison role that matches the paper story rather than convenience alone

## 6. Frozen metric families

The final paper must contain **paper-grade** metrics from the following families:

1. **Identity stability / fragmentation**
2. **Association and re-entry quality**
3. **Object grouping / segmentation quality**
4. **Geometry / map quality**
5. **Ablation-specific method metrics**
6. **Efficiency / online practicality** if required by final venue framing
7. **Auxiliary benchmark-compatibility rows** only when they do not redefine the paper as a learning-based segmentation system

### Proxy metric policy
Existing proxy metrics may remain only as:
- debugging aids
- internal analysis tools
- supplementary interpretation rows

They must **not** remain the sole basis of the final main results. Likewise, auxiliary AP-style benchmark rows must not become the sole identity of the paper when they are not the most story-aligned comparison surface.

## 7. Frozen figure list

The final paper must at minimum contain:

1. overall pipeline figure
2. layer-1 / layer-2 structure figure
3. object graph memory figure
4. qualitative temporal carry-over case figure
5. qualitative fragmentation-vs-memory-authority case figure
6. failure case figure
7. main result table
8. ablation table
9. robustness / regime table

## 8. Frozen strong-claim decisions

### Graph-memory claim
- **Keep strong graph-memory claim as a final-paper target claim.**
- This is now a frozen top-tier direction choice, not a provisional maybe.
- Therefore later phases are required to strengthen implementation and evidence until this claim is reviewer-safe.
- If later phases fail to meet that bar, the correct outcome is **blocker escalation**, not silent claim weakening.

### Geometry-consistency claim
- **Keep strong geometry-consistency claim as a final-paper target claim.**
- Later phases must replace scalar-only proxy support with explicit geometry-aware evidence or operators.
- If that strengthening fails, roadmap execution should treat it as a blocker against final submission quality.

### Reconstruction / mapping claim
- **Keep scoped reconstruction/mapping claim** for the final paper.
- Do **not** let it drift into generic dense reconstruction language or dense-map state-of-the-art rhetoric.
- The intended final framing remains object-centric online reconstruction/mapping under decision-bearing memory.

## 9. Exit criteria for Phase 0

Phase 0 is complete only when:
- this submission lock exists
- PRD and test-spec artifacts exist
- required docs are updated
- repository verification is green
- architect review agrees that downstream phases can now execute against this freeze
