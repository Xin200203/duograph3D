# DuoGraph3D 论文故事 v2 — carrier preservation is the cause, repair is the patch (2026-07-06)

状态：机制在两个开发场景上验证完毕（office1 +8.171 E70-exact / office2 +8.185 new best），
统一配置全场景验证进行中。本文档固化新叙事骨架，替代 4/23 旧 two-layer-memory 主线。

## 0. 一句话故事

> 在 object-centric open-vocabulary 3D mapping 中，最终语义错误的一个主要来源不是检测
> 也不是重建，而是 **postprocess 合并对 geometry carrier 的破坏与对语义读出的污染**
> （特征平均把碎片的 CLIP top-1 挤成错误标签；被吸收的 carrier 失去自己的读出）。
> DuoGraph3D 用**离散多视角声明证据**做 per-pair 合并否决（连续 CLIP/text 相似度
> 看不见的证据维度），配合尺度先验的语义权威检查处理残余读出错误——全部决策
> object-level 可审计，零场景规则、零 GT 反馈。

## 1. 科学问题（Introduction 骨架）

1. **归因**：OV 3D mapping 的语义错误从哪来？
   我们给出一类此前未被显式刻画的失败：**merge-induced readout corruption**。
   office2 的实证：大桌子被逐帧读出为 table/tablet/tv-stand/switch 碎片；CG-style
   overlap 合并把它们拼成一个 carrier 的同时做特征平均，把合并后 carrier 的
   CLIP top-1 挤成 "bin"（declared 分布里 bin 一票都没有：{table:2, tablet:1,
   tv-stand:1, switch:1, camera:1}，extent 1.56m × z 0.12m）。E70 时代的
   bin→table 修复实际上是在给这个合并伤害打补丁。
2. **判定**：什么时候允许合并、什么时候语义读出有权威？
   合并判定：两个空间重叠对象若各自携带**充分多视角支持的不同声明标签簇**，
   合并会抹掉独立语义证据 → 否决（office1 的 cloth(164 obs)|picture(567 obs)，
   visual_sim 0.94 高于 CG 阈值仍被否决——离散证据否决连续证据）。
   读出判定：readout label 的物理尺度先验容不下 carrier 的 extent，且多视角声明
   分布不支持该 label → 权威撤销，从声明分布中选尺度兼容的替代（或弃权）。
3. **审计**：每个合并/否决/修复/弃权决策都有 object-level 证据记录
   （veto_examples、no_veto_reasons、scale_prior_probe、abstain_reasons）。

## 2. 方法（Method 骨架）

三个机制，全部 scene-independent、GT-free：

- **M1 Label-cluster merge gate（主机制）**：CG merge 循环逐对复刻，附加否决：
  双方 declared top 不同 ∧ 双方 top-share ≥ τ ∧ 双方观测数 ≥ evidence floor。
  证据下限是关键负边界：同物碎片（12-17 obs）证据不足不否决 → 正常拼装；
  真实独立对象（164/567 obs）证据充分 → 否决。
- **M2 Declared-auto source authority（B1）**：evaluator-facing 修复源集合由场景
  自身多视角声明标签推导（计数 ≥ k），替代手写 per-scene keep lists。
- **M3 Scale-prior authority check（B2）**：per-label 物理 max-extent 先验
  （LLM 常识生成、评测前冻结、来源声明），违规时从 declared 分布选尺度兼容
  替代 label；带三重弃权守卫（无声明证据 / 无兼容目标 / 源标签被多视角支持
  ——room0 大 cushion 守卫）。log-only 模式支持"先干跑读诊断、再启用"的
  无 GT 校准流程（本轮实践即如此，有 pre-registered prediction 记录）。
- **骨架**：two-layer graph memory 提供 declared 分布的积累与对象状态维护
  （不声称直接提升精度，A2 证据如旧）。

## 3. 关键实验证据（当前已有）

| 证据 | 数值 | 支持的 claim |
| --- | --- | --- |
| office1 beta+gate | +8.171（E70-exact，30 obj，7/7 veto） | 门在 0.7 合并阈值下恢复了原需 merge-off 的 carrier 保持 |
| office2 beta+gate | +8.185（超 E70 +6.49，无修复触发） | 合并制造误读；防住合并则无需修复 |
| office2 gamma+gate | +3.698（过度否决） | evidence floor 的必要性（负边界） |
| office1 nogate 控制 | +2.787（门关=legacy 完全一致） | 无回归；差异全部归因于门 |
| cloth\|picture veto 记录 | visual 0.94 / text 1.0 仍否决 | 离散证据 ⊥ 连续证据；CG text 阈值在 class-agnostic 模式下失效 |
| bin carrier 画像 | pred=bin, declared 无 bin, z=0.12m | readout 孤证 vs 多视角+几何，权威撤销的教科书案例 |

待补：统一配置全场景（跑中）、min-obs 敏感性、消融矩阵、LOSO/dev-scene 声明。

## 4. 诚实边界（Limitations 骨架）

- 阈值（evidence floor、top-share）在两个开发场景的诊断上校准，其余六场景
  未触碰后验证 + 敏感性扫描；写清 dev/validation 划分。
- Replica 合成数据；ScanNet OOD sanity 为 P1。
- memory-dense split-by-label 导出下 top-share 常为 1.0，veto 实际退化为
  "不同标签 + 双方证据充分"；在非 split 导出下 share 门槛才发挥作用。
- 评测协议是 CG semantic mIoU 族；AP 桥接为 supplementary。

## 5. 表格计划

- T1 主表：CG / DuoGraph3D-unified（全场景 per-scene + all）
- T2 消融：w/o gate、w/o scale-prior（log-only）、w/o auto-keep、gamma 相位、
  oracle E70 composite（上界）
- T3 诊断：veto/merge/abstain/relabel 计数与样例（每场景）
- T4 负边界：gamma 过度否决、min-obs 扫描、room0/office4 弃权行为
- F1 pipeline 图；F2 office2 合并致误读 before/after；F3 cloth|picture veto 案例
