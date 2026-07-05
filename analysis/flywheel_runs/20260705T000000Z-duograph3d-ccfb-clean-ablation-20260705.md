# DuoGraph3D CCF-B 实验飞轮归档 — 2026-07-05

- mode: `mixed`
- project_root: `/Users/xin/Research/Code/research/DuoGraph3D`
- team_mode: `team-ready`

## Observation
- 当前输入模式：`mixed`。
- summary 输入：`/Users/xin/Research/Code/research/DuoGraph3D/docs/ccfb_clean_ablation_results_20260704.md`。
- raw artifact 数量：`10`。

## Evidence
识别到 8 个主指标条目。
识别到 5 个诊断指标条目。
发现 10 个原始 artifact 文件。
发现 4 个指标名存在多值冲突。
- `large_tissue-paper_to_cloth = 1` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/docs/ccfb_clean_ablation_results_20260704.md`
- `ptgraphs_postprocess.merge_overlap_thresh = 1.0` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/docs/ccfb_clean_ablation_results_20260704.md`
- `merge_overlap_thresh = 1.0` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/docs/ccfb_clean_ablation_results_20260704.md`
- `gap_miou = 8.171477225712604` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/ccfb_20260704/cgmerge1_probe/clean_summary.tsv`
- `gap_mf1 = 10.361485861961615` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/ccfb_20260704/cgmerge1_probe/clean_summary.tsv`
- `gap_fmiou = 5.940260583584008` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/ccfb_20260704/cgmerge1_probe/clean_summary.tsv`
- 指标冲突：`gap_miou` -> `2.7865177382611535, 6.254106066626264, 6.494515530420873, 8.171477225712604`
- 指标冲突：`gap_mf1` -> `10.361485861961615, 3.6098186732238737, 5.4573574289016875`
- 指标冲突：`gap_fmiou` -> `20.39706484950903, 5.181961505541581, 5.940260583584008, 7.409222685002774`
- 指标冲突：`export_objects` -> `23, 30, 32`

## Hypotheses (<=3)
1. 当前差异可能被 evaluator、threshold 或汇总脚本放大，需要先校验指标口径。
2. 当前负例更像是模块接口/分支触发/配置路径问题，而不是核心想法完全错误。
3. 当前异常可能主要来自数据或 split 条件变化，而不是算法本身退化。

## Claims disallowed / not yet supported
- 当前存在同名指标多值冲突，不能直接把单一数值当作最终结论。
- 当前未附带 literature 搜索结果，不能声称已有工作已直接证明本轮解释。

## Minimal next ablations (<=3)
1. 在同一 checkpoint 上重跑一个最小 evaluator smoke test，核对 threshold 与 report path。
2. 增加一组最小 runtime instrumentation，验证目标 branch 是否真实触发且输出被消费。
3. 对同一 evaluator 下的两个数据切分做最小对照，检查异常是否随 split 消失。

## Literature parallels
- 待在交互式运行中通过网页检索补齐 literature parallels。

## Decision
- 优先按以下判断推进：当前差异可能被 evaluator、threshold 或汇总脚本放大，需要先校验指标口径。
