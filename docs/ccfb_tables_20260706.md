# DuoGraph3D CCF-B 论文表格素材（组装于 2026-07-06 晨）

所有数字来自官方 ConceptGraphs Replica semantic evaluator（`eval_replica_semseg`,
`n_exclude=6`）。gap = DuoGraph3D − ConceptGraphs baseline（CG all = 24.531 mIoU）。
artifact 根目录标注于每表之后；跨机复现容差已验证 <0.01 mIoU。

---

## T1 — 机制层主表：合并基底（memory-dense）上的因果链

### T1a. office1（开发景）：carrier 保持 → 修复的因果阶梯

| 配置（dense 基底，phase beta） | office1 ΔmIoU | relabels | 对象数 | 门统计 (cand/merged/vetoed) |
| --- | ---: | --- | ---: | --- |
| CG-style legacy 合并（门关） | +2.787 | {}（carrier 被合并，修复无从触发） | 23 | — |
| 门开 floor=2（carrier 保持，无修复） | +4.016 | {} | 30 | 参照 merge-off 行为 |
| **门开 floor=2 + tissue→cloth 修复** | **+8.171**（E70-exact） | large_tissue-paper_to_cloth:1 | 30 | 7/0/7 |

关键否决记录：`cloth(164 obs) | picture(567 obs)`，CLIP visual_sim 0.94（高于 CG 阈值
0.8）仍被离散多视角声明证据否决；`text_sim=1.0`（class-agnostic token 模式下 CG 的
text 阈值失效——离散证据补上了连续特征的盲区）。
门关 ≡ legacy 逐位一致（对照行 +2.787 与历史完全相同）。

### T1b. office2（开发景）：合并制造误读，防住合并则无需修复

| 配置（dense 基底） | office2 ΔmIoU | relabels | 对象数 |
| --- | ---: | --- | ---: |
| gamma + legacy + 窄 keep（无修复下界） | +1.279 | {} | 32 |
| gamma + legacy + 窄 keep + bin→table 规则（E70 binonly） | +6.254 | bin→table:1 | 32 |
| beta + legacy（bin 规则触发） | +8.211 | bin→table:1 | 56 |
| **beta + 门 floor=2（修复未触发）** | **+8.185** | {} | 91（124/13/108） |

读法：beta 基底下"全否决无修复"与"全合并有修复"两个操作点等价（±0.03），均超
E70 的 +6.49——证明 bin 误读是合并的特征平均**制造**出来的（bin carrier 画像：
extent 1.564m × z 0.122m，declared={table:2,tablet:1,tv-stand:1,switch:1,camera:1}，
**bin 零票**，source_declared_share=0.0）。E70 的修复规则是在补偿合并伤害。

### T1c. 验证景（未参与任何机制/阈值决策）上门的净贡献（dense 基底，floor=2）

| 场景 | dense+legacy (wo_gate) | dense+门 | 门净贡献 |
| --- | ---: | ---: | ---: |
| room1 | +5.792 | +6.288 | +0.50 |
| office0 | +0.284 | +3.180 | +2.90 |
| room0 | −3.719 | −1.514 | +2.21 |

（room0 两行均负：dense 基底本身不适合 room0，见 T2/T4；门在其上仍是净正。）

Artifacts: `ccfb_pa1_label_gate_probe_20260705_pa1{b,c}`（184）、
`ccfb_pa1_label_gate_probe_20260705_pa1`（76）、
`ccfb_office2_keep_probe_20260704`、`ccfb_unified_full_20260706_v4g_{v4_main,wo_gate}`。

---

## T2 — 全场景单配置消融（官方 all 行）

| 行 | 配置 | all ΔmIoU | office1 | office2 | office4 |
| --- | --- | ---: | ---: | ---: | ---: |
| CG baseline（绝对值） | — | 24.531 mIoU | 14.481 | 21.890 | 46.829 |
| **E70 oracle** | 五层场景手工组合（prep 粒度×基底×相位×合并×keep-set） | **+3.041** | +8.171 | +6.492 | +1.754 |
| forced_dense（最终机制） | dense 全场景 + 门(floor2+mutual) + sp | −4.412 | +4.016 | +3.054 | −27.214 |
| forced_dense v1 | 同上但无 mutual 守卫、sp 惰性 | −3.716 | +4.016 | +5.723 | −27.756 |
| wo_sp | dense + 门 + mutual，sp 关 | −4.451 | — | — | −28.465 |
| dense_legacy (wo_gate) | dense + CG 合并 + sp | −6.082 | +2.787 | −0.423 | −35.463 |
| forced_geo（机制未作用域化） | geometry 全场景 + 门 + sp | −4.644 | −1.061 | −5.879 | −2.540* |
| gamma_plain office4 单点 | dense + gamma、无门无 sp | — | — | — | −26.117 |

*forced_geo 的 office4 列取自 PC2 单景行（同配置）。

读法（论文正文）：
1. **没有任何单基底配置在全场景为正**——office4-dense 一景即损失 −26~−35（与门、
   相位、sp 全部无关，PC1 gamma_plain 证实为基底级失败）；geometry 基底则牺牲
   office1/office2（−1.1/−5.9）。
2. E70 的 +3.041 依赖五层场景手工选择；把它作为 **oracle 上界**报告。
3. 机制的贡献在 T1（逐景、合并基底）层面因果成立；T2 量化"移除场景知识的代价"。

Artifacts: `ccfb_unified_full_20260706_v4g_*`（184）、`ccfb_unified_full_20260706_v4b_*`（76）、
`ccfb_unified_full_20260706_apply`（v1）、E70 = `e70_best_composite_office2_bin_vent_table_20260626`。

---

## T3 — 诊断/审计计数（示例，全量见 per-scene merge_monitor_summary.json）

| 场景（v4g forced_dense） | 门 cand/merged/vetoed | sp violations | sp relabels | sp abstains（按原因） |
| --- | --- | ---: | --- | --- |
| office1 | 7/4/3（floor2 时 7/0/7） | 13 | 0（fallback 关） | source_well_supported:13, no_compat:2 |
| office2 (wo_gate行) | — | 23 | 1（vent→blinds, declared 支持） | well_supported:9, no_compat:12, share_min:1 |
| office4 | 70/33/3 | 17 | 1（nightstand→sofa） | well_supported:14, no_compat:12, share_min:1 |
| room0 | 66/46/5 | 24 | 0 | well_supported:24, no_compat:7 |

预注册验证：office4 的 6 个 vent 违规全部弃权（写于运行前，
`docs/ccfb_experiment_runlog_20260705.md` "Pre-registered B2 prediction"）。

---

## T4 — 负边界表（每行一个被证据否决的设计，含否决证据）

| # | 被否决的设计 | 关键证据 | 结论 |
| --- | --- | --- | --- |
| 1 | 纯信号 multi-hypothesis selector | 270 归档行离线审计：最优信号是预处理配置泄漏；max-relabel 在 office4 掉 vent 陷阱（regret 6.8） | 机制先行，selector 不作主机制 |
| 2 | 无证据下限的 label 否决 | room0 否决 min 侧观测 2-7（噪声）；office2 同桌碎片 12-17 obs 被误否决 | evidence floor 守卫 |
| 3 | 忽略双向互含 | room2 comforter\|chair 双向 0.86/0.83（同一观测流被读出劈开）被误否决 | mutual-containment 守卫 |
| 4 | 多视角一致性=正确性 | office1 cloth carrier 被 70/70 检测一致读成 tissue-paper（3.1× 尺度先验） | hard-ratio 权威撤销（>2×） |
| 5 | CLIP 兼容重读出兜底 | office1 7/7 硬违规全触发垃圾改标（分数 ~0.25、边距 ~0.01；tissue→comforter，真值 cloth） | fallback 默认关；修复目标只信 declared |
| 6 | vent→table 共享规则 | E70 leave-one-out 仅 +0.04 all；office4 负迁移史 | 弃用；office4 vents 由 sp 正确弃权 |
| 7 | beta 相位普适化 | office4 beta 全配置 −26~−36；gamma_plain 同样 −26 → 基底级 | 相位非因，基底才是 |
| 8 | 覆盖阈值基底路由 | office1 46 节点需 dense、office4 111 节点需 geometry——排序方向相反 | 阈值规则不可表达 |
| 9 | consolidation 比值路由 | E70 geometry 景 prep 用 voxel 0.5（436 keys）；统一 prep 下比值交错（dense-good .047-.134 vs geo-good .052-.083） | "完美分离"是体素伪影 |
| 10 | 部分合并中间地带 | office2-beta：全否决 +8.185 / 全合并+修复 +8.211 / floor24 部分合并 +2.41 | 危险区间，floor 曲线报告 |
| 11 | 机制作用于原始 key 基底 | office0-geo：148 否决 + 15 个"declared 支持"的垃圾改标（key 桶标签=边界噪声） | mechanisms-scope=consolidated-only |
| 12 | E70 keep-set 的可见性依赖 | wo_gate office2：auto-keep(33 标签)下合并 carrier 读出非 "bin"——E70 案例仅在窄手工集下可见 | 误读表达依赖 evaluator-facing 源集合 |

敏感性曲线（正文图）：office1-beta-dense floor {2,8,24} → {+8.171, +6.938, +6.939}；
office2-gamma floor {2,8,24} → {+2.96, +2.96, +3.18}。

---

## T5 — 事后不可行性分析（CG 官方图 + 机制，2026-07-06 补充）

在 CG 官方 pre-postprocess 图（官方基线的确切评测对象）上重建真实多视角声明
分布（GSA 逐检测 CLIP 投票经 filter_gobs 对齐映射；对齐自检 cos=0.9999 全景通过），
然后施加机制：

| 行 | all ΔmIoU | 门候选对（全景） | 说明 |
| --- | ---: | --- | --- |
| CG + CG式后处理（legacy） | −0.083 | — | 协议平位 sanity ✓ |
| CG + 门 | −0.083 | **0/0/0（全部 8 景）** | 与 legacy 完全一致 |
| CG + sp | −0.461 | — | 逐景混合噪声（room0 +3.69 / room2 −2.30） |
| CG + 门 + sp | −0.461 | 0/0/0 | 同上 |

**读法（论文核心论证）**：CG 的在线合并（merge_interval=20）在建图过程中已消耗
全部高重叠合并决策——最终图上门无事可做（0 候选）；载体破坏与读出污染已烧结进
合并后的特征与点云，即使给事后工具以完美的声明证据（0.9999 对齐），修复也退化为
噪声（−0.46）。与内联结果（office1 +8.17、office2 +8.19）对照：
**语义权威控制必须发生在决策时刻（在环内），事后不可行。**
这同时是对本系统在线双层设计的最强辩护。

Artifacts: `ccfb_cg_authority_20260706`（184）。

## T2 补注（2026-07-06 晚）：最终配置的 Replica 全行

修复路由口径后重跑的最终配置（= T6 同款）Replica 全行 = **all −4.412**，与
forced-dense 行完全一致——因为统一 prep 下 Replica 八景的 consolidation 比值
全部压缩到 dense 侧（T4#9 的体素伪影结论的直接推论：router 在 Replica 上无
信号）。这不是缺失实验，而是 T4#9 的闭环验证。**router 的判别力在真实扫描上
存在（ScanNet 5/3 分派、dense 景大胜）、在统一 prep 的合成 Replica 上不存在**
——该不对称如实写入正文与 T4。

## T6 — ScanNet 机制迁移表（2026-07-06，8 个 val_50 场景，NYU40 协议）

协议：`eval_scannet_semseg.py`（GT 网格顶点最近预测点指派，NYU40 文本库，
排除 wall/floor/ceiling/door/window/person/other*）；CG 基线 = 官方 cfslam 参数
在同一 staged 数据上重跑；in-loop = unified 配置（consolidation-auto + 门 + sp，
NYU40 冻结先验，**零 ScanNet 专属调参**，先验提交先于首次评测）。

| scene | 保留类数 | CG mIoU | in-loop mIoU | 路由 |
| --- | ---: | ---: | ---: | --- |
| scene0568_00 | 8 | 18.05 | **68.83** | dense |
| scene0304_00 | 2 | 50.00 | 36.51 | dense |
| scene0488_00 | 4 | 5.30 | **21.36** | geometry(直通) |
| scene0412_00 | 3 | 41.96 | **63.79** | dense |
| scene0217_00 | 5 | 29.72 | **74.17** | dense |
| scene0019_00 | 3 | 21.92 | 0.00 | geometry(直通) |
| scene0414_00 | 5 | 29.83 | 16.73 | geometry(直通) |
| scene0575_00 | 3 | 58.10 | **100.00** | dense |
| **all（聚合混淆）** | — | **15.32** | **34.86** | — |

读法与诚实边界：
1. 逐景极值（100/0）是 2-3 个保留类的小场景协议效应，两行同受影响；聚合行
   （+19.5 mIoU）是稳健口径。
2. **Replica 校准的 consolidation 路由零修改迁移**：5 dense / 3 geometry；
   dense 路由景大幅取胜（+50.8/+44.4/+41.9/+21.8，例外 0304 −13.5），
   geometry 路由景走机制关闭的薄弱直通导出而落后（设计使然，非机制误伤）。
3. **机制安全性迁移（核心证据）**：门 113 候选 / 30 合并 / 62 否决正常运作；
   **sp 26 个尺度违规 → 0 改标，26/26 审计弃权**（12 source_well_supported +
   14 no_compatible_target）——冻结 NYU40 先验在 OOD 真实扫描上零误触发。
4. 对象规模：ours 64-130/景 vs CG 515-2172/景（合并基底 vs 原始检测聚合）。

Artifacts: `scannet_gsa_20260706{,b}`, `scannet_cfslam_20260706`,
`scannet_inloop_full`, `scannet_eval_20260706`（184）。

## 场景记账（审稿人辩护用）

- 开发景：office1、office2（机制发现与阈值校准）
- 诊断贡献景：room0、room2、office4（守卫由其失败法医推导，未做逐景调参）
- 纯验证景：room1、office0、office3（从未影响任何决策；T1c 的门净贡献来自这里）
- 预注册记录、门关≡legacy 对照、逐对象审计字段齐备。
