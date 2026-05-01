# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test

```bash
# Run full test suite
python3 -m unittest discover -s tests -v

# Run a single test file
python3 -m unittest tests/test_pipeline.py -v

# Run a single test method
python3 -m unittest tests.test_pipeline.PipelineTests.test_pipeline_births_memory_node_via_layer2 -v

# Smoke-test the local skeleton
PYTHONPATH=src python3 examples/minimal_sequence.py

# Run a bounded-slice experiment
PYTHONPATH=src python3 examples/run_bounded_slice.py --dataset replica --scene office0 --limit 6 --drop-every 2 --output outputs
```

No external Python dependencies. Tests use `unittest` only. Tests import via `sys.path.insert(0, .../src)` then `from duograph3d.xxx import ...`.

## Architecture

**Core pipeline** (`pipeline.py:13` — `DuoGraph3DPipeline.run_sequence`): iterates frames, runs three stages per step, and returns a `SequenceRunResult` + `EventLogger`:

1. **Evidence** (`evidence.py`) — `EvidenceBuilder.build()` converts `FrameInput` → `list[EvidenceItem]`. In DEVA temporal mode, it additionally propagates memory-only objects as synthetic evidence.
2. **Layer 1** (`layer1.py`) — `CurrentEvidenceGraphLayer.repair()` merges/deduplicates evidence within a single frame, producing `list[CurrentObjectHypothesis]`. Uses repair groups, continuity keys, geometry profiles, and shared-history boosts.
3. **Layer 2** (`layer2.py`) — `CurrentToMemoryAssociationLayer.update()` associates current hypotheses with memory objects (birth, update, merge) and manages lifecycle transitions (`ACTIVE → OCCLUDED → DORMANT → RETIRED`).

**Memory** (`memory.py`) — `ObjectGraphMemory` holds the persistent object graph (`nodes: dict[str, MemoryObjectNode]`), relation edges, candidate retrieval, point-cloud storage, and periodic object consolidation/merging.

**Contracts** (`contracts.py`) — All dataclasses and enums. `PipelineConfig` (260+ parameters) is the single knob for all thresholds and budgets. Branch IDs are string constants in `events.py`.

**Rivals** (`rivals.py`) — Fair comparison branches that share the same memory/layer-2 interface but bypass layer-1:
- `BRANCH_DUOGRAPH3D` = `"duograph3d_full"` — full pipeline
- `BRANCH_SINGLE_LAYER` = `"single_layer_rival"` — skips layer-1, one hypothesis per evidence item
- `BRANCH_DENSE_EXPORT` = `"dense_authority_export_rival"` — external baseline adapter
- `BRANCH_COUNTERFACTUAL` = `"full_fair_counterfactual"` — full counterfactual

**Data** (`data.py`) — Dataset loaders for Replica (`build_replica_bounded_slice`) and ScanNet (`build_scannet_bounded_slice`). Returns `BoundedSlice` objects with `FrameInput` lists.

**Remote** (`remote_config.py`) — `RemoteExperimentPaths` centralizes paths to the remote dataset/artifact server at `10.177.69.184` (user: `nebula`).

## Development workflow

**Local (Mac)** → **GitHub** → **Remote server (184)**

```
macOS (local dev)          GitHub                    10.177.69.184 (execution)
  ├── code, test,           ├── Xin200203/              ├── datasets (Replica, ScanNet)
  │   type-check              duograph3D.git            ├── concept-graphs (CG parity ref)
  └── git push ──────────> origin ──────────> git pull └── duograph3d_artifacts/
```

- **Local**: macOS, code development and unittest. Push to GitHub when ready.
- **GitHub**: `git@github.com:Xin200203/duograph3D.git` (SSH via `~/.ssh/id_ed25519_github`, port 443)
- **Remote server (184)**: `10.177.69.184`, user `nebula`, auth via `~/.ssh/id_ed25519`. All heavy experiments (full-scene Replica runs, official eval, ConceptGraphs parity benchmarks) execute here. SSH config alias is `10.177.69.184`.
- After pushing to GitHub, manually `git pull` on the remote server to sync code before running experiments.
- Remote dataset/artifact paths are centralized in `remote_config.py` (`RemoteExperimentPaths`). Key paths on 184:
  - Replica: `/home/nebula/xxy/dataset/Replica`
  - ScanNet: `/home/nebula/xxy/dataset/scannet_v2`
  - DuoGraph3D code (on remote): `/home/nebula/xxy/DuoGraph3D`
  - ConceptGraphs (CG parity ref): `/home/nebula/xxy/concept-graphs-main`
  - Artifacts: `/home/nebula/xxy/duograph3d_artifacts`

## Key conventions

- 4-space indentation, standard-library Python only, explicit type hints
- Module names `snake_case`, classes `PascalCase`, functions/variables `snake_case`
- Branch IDs and dataset keys must remain stable — downstream JSON summaries depend on them
- `outputs/` is generated artifacts; review before committing
- Research framing notes (`research_gap_note.md`, `paper_framing_and_venue_eval.md`) document the paper claim and should stay aligned with implementation
- Commit style: explain **why** first, optional trailers `Constraint:`, `Confidence:`, `Scope-risk:`, `Tested:`
