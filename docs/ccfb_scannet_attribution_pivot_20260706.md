# ScanNet 归因转向：+14.4 来自基底，不是机制（2026-07-06 晚）

## 触发事件

ScanNet-50 wo_gate 消融行：**26.73 mIoU**，vs full（gate+sp）**26.42**，vs
CG baseline **12.02**。门在 ScanNet 聚合上净贡献 ≈ −0.3（微负）；尺度先验在
50 景 166 个违规中只改了 2 个标签（其余全弃权）。

## 硬结论（不粉饰）

**ScanNet 上 +14.4 的头条增益几乎全部来自 consolidated memory-dense 导出基底，
不是论文命名的 carrier-authority 机制（门 + 尺度先验）。** 两个机制在真实扫描上
基本惰性——安全（不伤害、正确弃权）但不驱动增益。

这与 Replica 的故事相反：
- **Replica**：门有局部因果价值（office1 +8.17 exact recovery、merge-manufactured
  corruption 的 office2 案例）；基底是混合结果（office4-dense −27）。
- **ScanNet**：基底驱动全局增益；机制惰性但安全。

## 审稿人必问 & 正在回答的控制实验

Q：+14.4 是"两层记忆巩固"还是仅仅"你们的批量导出后处理比 CG 的在线合并干净"？

正在跑的 substrate 分解（机制全关，同一 ScanNet 检测）：
- `memdense`：forced memory-dense（完整两层巩固）
- `geomonly`：forced geometry-key coverage（无巩固，仅导出卫生）

判读：
- memdense ≫ geomonly → 增益是两层记忆巩固（支持系统贡献）；
- memdense ≈ geomonly → 增益只是导出卫生（批量 vs 在线），两层记忆不是主因，
  需进一步用 single-layer rival 控制。

## 对论文主张的影响（诚实重构）

不能再写的：
- "carrier-authority 机制在 ScanNet 上带来 +14.4"——数据不支持。
- 单一统一机制在所有数据集靠机制取胜。

仍可辩护的（分两条独立贡献，而非硬凑统一头条）：

1. **失败家族 + 决策时刻命题（Replica，因果）**：merge-manufactured semantic
   corruption 是真实、新颖、可 exact-recovery 复现的失败（office2 bin、office1
   cloth）；权威控制必须在决策时刻（T5 事后不可行）。这是诊断 + 因果机制贡献，
   证据独立于 ScanNet。

2. **系统贡献（ScanNet，若 memdense≫geomonly 成立）**：consolidated 两层对象
   记忆在真实扫描上产出显著优于 CG 在线合并的语义图（+14.4）；carrier-authority
   机制作为**安全、可审计、会弃权**的附加层（在 OOD 上不伤害、166 违规仅 2 改标、
   预注册弃权），而非 ScanNet 增益来源。

## 与历史 A2 的关系（需在文中厘清）

A2（Replica）曾报 forced memory-dense −2.48 vs geometry。这与 ScanNet 的
memory-dense +14.4 vs CG **不矛盾**：A2 比较的是"我们的 memory-dense vs 我们的
geometry"，ScanNet 比较的是"我们的 memory-dense vs CG 的在线合并图"——不同参照。
substrate 分解的 geomonly 行正是补上 ScanNet 的"我们的 geometry"参照，使两数据集
可同口径对话。

## 结论

这不是坏消息，是**范围诚实化**：把 ScanNet 头条从"机制取胜"如实改为"系统/基底
取胜 + 机制作为安全附加层"，并保留 Replica 的机制因果贡献。审稿人更可能因为
"诚实、证据分层清晰"而非"夸大统一性"给分。等 substrate 分解数字定案后更新
T6/故事 v3。
