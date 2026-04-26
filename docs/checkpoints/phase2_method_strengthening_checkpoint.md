# Phase 2 Checkpoint Report — Method Strengthening

## Phase goal
Strengthen the current DuoGraph3D method so that the graph / geometry / dual-consistency claims are better grounded in the implementation.

## Deliverables produced
- `src/duograph3d/contracts.py`
  - added `MemoryRelationEdge`
  - sequence results can now carry relation-edge snapshots
- `src/duograph3d/memory.py`
  - explicit relation-edge storage and co-visibility registration
- `src/duograph3d/layer1.py`
  - moved from pure grouping to explicit evidence-graph compatibility and connected-component repair
  - introduced explicit geometry-profile consistency in current-evidence repair
- `src/duograph3d/layer2.py`
  - added explicit geometry-profile compatibility, temporal-consistency gating, and relation-aware association bonus
- `src/duograph3d/metrics.py`
  - result summaries now expose `memory_relation_edge_count`
- `tests/test_pipeline.py`
  - added regression coverage for graph repair reasons, relation-aware preference, and relation-edge summaries

## Validation results
- Local pipeline tests: **PASS**
  - `python3 -m unittest tests.test_pipeline -v`
  - Result: `Ran 12 tests` / `OK`
- Full local test suite: **PASS**
  - `python3 -m unittest discover -s tests -v`
  - Result: `Ran 60 tests` / `OK`
- Local smoke run: **PASS**
  - `PYTHONPATH=src python3 examples/minimal_sequence.py`
- Remote real-observation regression: **PASS**
  - Replica / `office0` / DEVA-output path:
    - `frames_with_observations = 6`
    - `memory_nodes = 1`
    - `memory_relation_edge_count = 0`
  - ScanNet / `scene0568_00` / online-monitor path:
    - `frames_with_observations = 5`
    - `memory_nodes = 119`
    - `memory_relation_edge_count = 1797`
    - `event_count = 413`

## Exit criteria status
- method graph/geometry claims better grounded in code: yes
- explicit graph structure now exists in long-term memory: yes
- layer-1 repair now uses explicit graph compatibility rather than grouping alone: yes
- layer-2 uses explicit temporal + geometry joint constraints before association: yes
- layer-2 uses relation-aware association bonus: yes
- measurable activation beyond pure code complexity exists: yes
  - relation-edge count is now exposed and nonzero on real ScanNet validation
- ready to advance: yes

## Architect verification
- Verdict: **APPROVED**
- Summary:
  - Phase 2 now clears review for both graph-memory and geometry/dual-consistency grounding.
  - Documentation and validation evidence are internally consistent with the final post-fix test set.

## Remaining risks
- The new graph machinery and geometry-profile operator are structurally stronger, but later phases still need paper-grade quantitative gains and stronger geometry-rich evidence.
- Replica DEVA-output validation remains sparse across scenes; this is acceptable for Phase 2 but remains a later baseline/evidence risk.
