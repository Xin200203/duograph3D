# DuoGraph3D E70 投稿前实验总评

- mode: `mixed`
- project_root: `.`
- team_mode: `team-ready`

## Observation
- 当前输入模式：`mixed`。
- summary 输入：`/Users/xin/Research/Code/research/DuoGraph3D/.omx/goals/performance/duograph3d-accuracy/diagnostic-results-20260623.md`。
- raw artifact 数量：`7`。

## Evidence
识别到 8 个主指标条目。
识别到 6 个诊断指标条目。
发现 7 个原始 artifact 文件。
发现 18 个指标名存在多值冲突。
- `duograph_miou = 28.38199425023049` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/e69_office2/duograph_monitored_gap_vs_conceptgraphs.csv`
- `conceptgraphs_miou = 21.890415933012264` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/e69_office2/duograph_monitored_gap_vs_conceptgraphs.csv`
- `gap_miou = 6.491578317218227` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/e69_office2/duograph_monitored_gap_vs_conceptgraphs.csv`
- `duograph_mrecall = 35.74483203701675` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/e69_office2/duograph_monitored_gap_vs_conceptgraphs.csv`
- `conceptgraphs_mrecall = 36.03573411674006` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/e69_office2/duograph_monitored_gap_vs_conceptgraphs.csv`
- `gap_mrecall = -0.2909020797233097` 来源：`/Users/xin/Research/Code/research/DuoGraph3D/analysis/raw/e69_office2/duograph_monitored_gap_vs_conceptgraphs.csv`
- 指标冲突：`sofa` -> `0.04, 1.2`
- 指标冲突：`eval_points` -> `0, 25834, 932942`
- 指标冲突：`true_positive` -> `0, 915754`
- 指标冲突：`duograph_miou` -> `27.829317716152772, 28.38199425023049`
- 指标冲突：`conceptgraphs_miou` -> `21.3348021857319, 21.890415933012264`
- 指标冲突：`gap_miou` -> `6.491578317218227, 6.494515530420873`
- 指标冲突：`duograph_mrecall` -> `35.74483203701675, 40.409076732137926`
- 指标冲突：`conceptgraphs_mrecall` -> `36.03573411674006, 38.33523945953778`
- 指标冲突：`gap_mrecall` -> `-0.2909020797233097, 2.0738372726001444`
- 指标冲突：`duograph_mprecision` -> `36.38738382142037, 39.27510507080866`
- 指标冲突：`conceptgraphs_mprecision` -> `29.432649671545498, 33.32671835232759`
- 指标冲突：`gap_mprecision` -> `3.0606654690927826, 9.842455399263159`
- 指标冲突：`duograph_mf1score` -> `32.48046406692669, 33.63844560022845`
- 指标冲突：`conceptgraphs_mf1score` -> `25.27255634427201, 26.959262573243926`
- 指标冲突：`gap_mf1score` -> `5.521201493682767, 8.36588925595644`
- 指标冲突：`duograph_fmiou` -> `57.443943850681514, 61.923687262002744`
- 指标冲突：`conceptgraphs_fmiou` -> `40.48213544774193, 50.03472116567874`
- 指标冲突：`gap_fmiou` -> `21.441551814260812, 7.409222685002774`

## Hypotheses (<=3)
1. 当前差异可能被 evaluator、threshold 或汇总脚本放大，需要先校验指标口径。
2. 当前负例更像是模块接口/分支触发/配置路径问题，而不是核心想法完全错误。
3. 当前结果更像是优化/训练稳定性问题，而不是单纯模块未接入。

## Claims disallowed / not yet supported
- 当前存在同名指标多值冲突，不能直接把单一数值当作最终结论。
- 当前未附带 literature 搜索结果，不能声称已有工作已直接证明本轮解释。

## Minimal next ablations (<=3)
1. 在同一 checkpoint 上重跑一个最小 evaluator smoke test，核对 threshold 与 report path。
2. 增加一组最小 runtime instrumentation，验证目标 branch 是否真实触发且输出被消费。
3. 固定当前实现，只改训练/校准配置，验证主指标是否回到最近 anchor 邻域。

## Literature parallels
- 待在交互式运行中通过网页检索补齐 literature parallels。

## Decision
- 优先按以下判断推进：当前差异可能被 evaluator、threshold 或汇总脚本放大，需要先校验指标口径。
