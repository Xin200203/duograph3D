# Phase 1 Checkpoint Report — Real Observation Path Replacement

## Phase goal
Replace the synthetic/template-only main evidence path with explicit real-observation adapters and validate them on Replica and ScanNet.

## Deliverables produced
- `src/duograph3d/data.py`
  - synthetic path isolated into explicit `to_synthetic_frame_inputs(...)`
  - real-observation adapters added for:
    - generic frame observation JSON
    - DEVA output JSON
    - ScanNet online monitor JSON
- `examples/run_bounded_slice.py`
  - accepts `--observation-json`, `--observation-format`, `--require-real-observations`
- `examples/remote_smoke_test.py`
  - fixed ScanNet label handoff bug
- `tests/test_real_observation_paths.py`
  - new regression coverage for real-observation adapters
- `docs/phase1_real_observation_cases.md`

## Validation results
- Local targeted tests: **PASS**
  - `python3 -m unittest tests.test_real_observation_paths -v`
  - Result: `Ran 4 tests` / `OK`
- Full local test suite: **PASS**
  - `python3 -m unittest discover -s tests -v`
  - Result: `Ran 56 tests` / `OK`
- Remote real-observation validation: **PASS with recorded risk**
  - Replica real source: DEVA output JSON
  - ScanNet real source: online monitor JSON
  - Nonempty real-observation scenes:
    - Replica: `office0`, `office2`, `office3`
    - ScanNet: `scene0568_00`, `scene0568_01`, `scene0568_02`
  - Total nonempty scenes: `6`

## Exit criteria status
- synthetic path isolated from the real main-path adapters: yes
- real observation adapters implemented: yes
- Replica real-observation chain validated: yes
- ScanNet real-observation chain validated: yes
- at least 6 scenes with nonempty real evidence: yes
- first qualitative cases documented: yes
- ready to advance: yes

## Architect verification
- Verdict: **APPROVED**
- Summary:
  - Phase 1 exit criteria are satisfied.
  - Remaining ScanNet semantic-strength and label-mesh issues are tracked risks for later phases, not Phase 1 blockers.

## Remaining risks
- The current ScanNet online monitor path is real but semantically weak; later phases still need stronger object-level semantics and geometry-backed evidence.
- Several remote scenes still report missing ScanNet label mesh artifacts; this did not block Phase 1 but remains a data-quality risk for later phases.
