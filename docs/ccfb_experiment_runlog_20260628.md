# DuoGraph3D CCF-B experiment runlog — 2026-06-28

## Status

- Lead objective: advance CCF-B package from ConceptGraphs-only positive result to SOTA-aware, auditable, geometry-first method evidence.
- Plan recorded in: `docs/ccfb_execution_plan_20260628.md`.
- Literature review base: `docs/ccfb_sota_critical_review_20260628.md` and `analysis/literature/ccfb_sota_20260628/`.

## Active lanes

| lane | owner | status | output |
| --- | --- | --- | --- |
| online mapping literature | subagent A | running | `analysis/literature/ccfb_sota_20260628/online_mapping_notes.md` |
| OV-3DIS geometry literature | subagent B | running | `analysis/literature/ccfb_sota_20260628/ov3dis_geometry_notes.md` |
| code path audit | subagent C | running | integrated into this runlog / plan |
| carrier reliability gate v2 | main agent | preparing | code + remote subset run |
| AP-style metric bridge | main agent | preparing | parser/proxy or protocol gap doc |
| SOTA baseline bridge | main agent | queued | remote env audit first |

## Evidence log

- 2026-06-28: Created execution plan and runlog.
- 2026-06-28: Spawned three subagents for literature and code-path work.
- 2026-06-28: Code-path audit completed. Key findings: ConceptGraphs-format semantic eval is separate from AP-style external parsers; large-label repair lives in `examples/run_conceptgraphs_engineered_parity.py`; remote path config and hardcoded paths coexist.
- 2026-06-28: Online mapping literature subagent completed. Output: `analysis/literature/ccfb_sota_20260628/online_mapping_notes.md`.
- 2026-06-28: OV-3DIS / geometry literature subagent completed. Output: `analysis/literature/ccfb_sota_20260628/ov3dis_geometry_notes.md`.
- 2026-06-28: Added carrier-v2 branch to the large-label evidence gate. Default remains `off`; new args are `--geometry-repair-large-label-min-observations` and `--geometry-repair-large-label-min-source-share`.
- 2026-06-28: Added AP bridge status doc: `docs/ccfb_ap_metric_bridge_status_20260628.md`. Decision: do not mislabel current semantic-object diagnostics as AP/AP50/AP25.
- 2026-06-28: Local source verification passed: `python3 -m py_compile examples/run_conceptgraphs_engineered_parity.py` and `python3 -m unittest tests/test_conceptgraphs_preprocess_order.py -v`.
- 2026-06-28: Synced `examples/run_conceptgraphs_engineered_parity.py` and `tests/test_conceptgraphs_preprocess_order.py` to 184. Remote verification passed with `PYTHONPATH=src python -m py_compile examples/run_conceptgraphs_engineered_parity.py` and `PYTHONPATH=src python -m unittest discover -s tests -p test_conceptgraphs_preprocess_order.py -v`.
- 2026-06-28: Launched remote 184 subset diagnostic in tmux `ccfb_carrier_v2_20260628`. Artifact root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_carrier_v2_subset_20260628_carrier_v2_subset`. Variants: `Control_E71_active_target_declared`, `CarrierV2_table_z025_rate016`, `CarrierV2_table_z035_rate016`; scenes: `room0, office1, office2, office3, office4`. For subset runs, summary uses per-scene average gap, not the evaluator's synthetic `all` row.
- 2026-06-28: Full local regression suite passed after carrier-v2/source-manifest changes: `PYTHONPATH=src python3 -B -m unittest discover -s tests -v` → 152 tests OK.
- 2026-06-28: Checked optional 73/76 expansion capacity. Default route went through VPN (`utun4`); direct source bind from local `en0` IP `10.163.148.14` to `10.177.69.73/76:22` timed out, while VPN-routed attempts reset. No 73/76 jobs launched; 184 remains the active compute lane.
- 2026-06-28: Remote subset control completed. `Control_E71_active_target_declared` over `room0, office1, office2, office3, office4` produced per-scene-average gaps `+2.657056 mIoU / +3.243100 mF1 / +3.499455 F-mIoU`. This is a subset diagnostic only; its synthetic `all` row is invalid for full-Replica comparison. Notable per-scene mIoU gaps: room0 `+6.532`, office1 `+3.437`, office2 `-0.137`, office3 `+1.699`, office4 `+1.754`. Carrier-v2 variants are still running.
- 2026-06-28: Carrier-v2 subset completed and was mirrored locally to `analysis/raw/ccfb_20260628/carrier_v2_subset_20260628_carrier_v2_subset/`. Result: z025/z035 carrier-v2 variants are lower than the active target-declared control because they over-authorize `vent→table`, especially office4 (`-5.06/-5.16 mIoU`). This weakens the initial “geometry can override missing target label for vent→table” hypothesis.
- 2026-06-28: Launched follow-up no-vent diagnostic tmux `ccfb_carrier_v2_novent_20260628`: only `tissue-paper→cloth` and `bin→table` carrier-v2 rules, excluding `vent→table` because A1 and the new subset show it is a negative/unsafe innovation candidate.
- 2026-06-28: No-vent carrier-v2 subset completed. Variant `CarrierV2_bin_table_no_vent_z025_rate016` produced per-scene-average gaps `+2.791550 mIoU / +3.315545 mF1 / +3.517940 F-mIoU`, beating the active target-declared subset control by `+0.134494 mIoU / +0.072445 mF1 / +0.018485 F-mIoU`. Object-level evidence: no `vent→table` relabels; one `large_bin_to_table` in office3; `tissue-paper→cloth` retained in room0/office1/office3. Mirrored to `analysis/raw/ccfb_20260628/carrier_v2_novent_subset_20260628_carrier_v2_novent/`.
- 2026-06-28: Launched full Replica run on 184 in tmux `ccfb_carrier_v2_novent_full_20260628`: variant `CarrierV2_bin_table_no_vent_full_z025_rate016`, all 8 scenes, official evaluator enabled. Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_carrier_v2_novent_full_20260628_carrier_v2_novent_full`.
- 2026-06-28: Full no-vent carrier-v2 run completed but failed official target: all `+0.668524 mIoU / +2.758818 mF1 / +5.924266 F-mIoU`; official evaluator status `1`. Root mirrored to `analysis/raw/ccfb_20260628/carrier_v2_novent_full_20260628_carrier_v2_novent_full/`. Root cause from code-path/artifact comparison: this run used office1 `phase gamma` whereas E70 uses office1 `phase beta`; more importantly office2 `bin→table` did not trigger under the z-thickness carrier-v2 rule, so the E70 office2 gain was not recovered.
- 2026-06-28: Launched corrected full diagnostic `ccfb_active_novent_full_20260628`: rules `tissue-paper→cloth` and `bin→table`, no `vent→table`; evidence mode `active` with `table` target-declared gate; office1 restored to E70 `phase beta`. This tests whether target-declared `bin→table` recovers office2 without unsafe `vent→table`.
- 2026-06-28: Corrected active/no-vent full run also failed official target: all `+0.239238 mIoU / +1.940370 mF1 / +6.674002 F-mIoU`, status `1`. Mirrored to `analysis/raw/ccfb_20260628/active_novent_full_20260628_active_novent_full/`. Key diagnostic: office2 still did not trigger `bin→table`; office1 beta did not reproduce E70's tissue→cloth behavior under the new combined active rules. Current conclusion: E70 remains the only strong full-Replica result; broad/no-vent shared gate variants are insufficient.
