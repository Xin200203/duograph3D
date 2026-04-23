# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/duograph3d/`. Keep pipeline contracts in `contracts.py`, event/logging helpers in `events.py`, memory/state logic in `memory.py`, evidence and layer logic in `evidence.py`, `layer1.py`, and `layer2.py`, and experiment/report helpers in `experiments.py`, `g2.py`, `metrics.py`, and `io_utils.py`. Example runners live in `examples/`. Unit tests live in `tests/`. Research framing notes (`research_gap_note.md`, `paper_framing_and_venue_eval.md`) document the paper claim and should stay aligned with implementation changes. Generated reports belong in `outputs/`.

## Build, Test, and Development Commands
- `python3 -m unittest discover -s tests -v` — run the full test suite.
- `PYTHONPATH=src python3 examples/minimal_sequence.py` — smoke-test the local skeleton.
- `PYTHONPATH=src python3 examples/remote_smoke_test.py` — verify configured remote dataset roots.
- `PYTHONPATH=src python3 examples/run_bounded_slice.py --dataset replica --scene office0 --limit 6 --drop-every 2 --output outputs` — run a bounded-slice experiment and emit JSON reports.

## Coding Style & Naming Conventions
Use 4-space indentation and standard-library-only Python unless a dependency is explicitly approved. Prefer small dataclasses, explicit type hints, and pure helper functions. Module names use `snake_case`; classes use `PascalCase`; functions, variables, and test methods use `snake_case`. Keep branch IDs, event types, and dataset keys stable because downstream JSON summaries depend on them.

## Testing Guidelines
Use `unittest` and add tests in `tests/test_<area>.py`. Every behavior change should include a focused regression test plus, when relevant, a runner/report test. Cover both positive paths and claim-bearing failure paths (temporal triplet, memory authority, rival divergence).

## Commit & Pull Request Guidelines
There is no useful local git history yet; follow the workspace Lore commit protocol. Commit messages should explain **why** first, then add trailers such as `Constraint:`, `Confidence:`, `Scope-risk:`, and `Tested:`. PRs should summarize the claim impact, changed files, executed commands, generated outputs, and any remaining risks. Link experiments or JSON report paths when results change.

## Security & Configuration Tips
Do not hardcode secrets. Keep remote dataset paths centralized in `remote_config.py`. Treat `outputs/` as generated artifacts; review before committing. When changing fairness rules or dataset roots, update both code and planning docs under `.omx/plans/`.
