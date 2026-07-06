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

## substrate 分解结果（定案）

| 配置（ScanNet-50，机制全关除注明） | mIoU |
| --- | ---: |
| CG baseline（在线合并）| 12.02 |
| memdense（forced 两层巩固）| 25.98 |
| geomonly（forced 几何，无巩固）| **26.54** |
| wo_gate（auto+sp）| 26.73 |
| full（auto+门+sp）| 26.42 |

**geomonly ≥ memdense**：两层记忆巩固不是增益来源（无巩固的几何导出反而略高）。
机制惰性 + 记忆巩固惰性 → +14.5 全部来自"我们的批量导出后处理" vs "CG 的在线
合并图"本身。

## 公平性核查（对象/点数）

CG ScanNet：570–3793 对象、0.9–3.4M 点/景；ours：116–443 对象、40–127k 点/景
（对象 6–9×、点 20–40×）。CG 的 Replica 调参迁移到 ScanNet 严重碎片化。最近点
评测混合了地图密度与语义质量。**在不补做 CG-for-ScanNet 调参 + 密度对齐控制前，
+14.5 不能作为可辩护的论文头条。**

## 最终裁决（不粉饰）

ScanNet **降级**：从"头条主表"降为"OOD 安全性/鲁棒性检查"。ScanNet 诚实支持的
只有：**机制在 OOD 真实扫描上安全**（门净 −0.3、sp 164/166 弃权、预注册）——
一个鲁棒性结果，不是精度头条。+14.5 作为"系统在真实数据上产出可用图"的次要
观察报告，并明确标注它是后处理/参数迁移差异、非本文思想贡献所致。

**论文真正可辩护的核心回到 Replica**：merge-manufactured corruption 失败家族 +
决策时刻权威命题（T5）+ 对象级失败归因框架。这是扎实的诊断/机制贡献
（CCF-C 稳、CCF-B borderline），ScanNet 作为支撑性鲁棒性章节。

不再追加 ScanNet 跑动去抢救头条——归因已清楚，更多跑动只会进一步刻画一个
后处理差异，不会把它变成思想贡献。

---

# 附：CCF-B 冲刺的根因排查（2026-07-06 深夜，D1/D2）

## D1 逐类损失分解（Replica dense 基底，final config vs CG）

两种损失模式：
- **模式 A（中小物体整类蒸发）**：office4 tv-screen 0.88→0、clock 0.77→0；
  room2 switch 0.84→0、wall-plug 0.79→0.02；room0 book 0.22→0。
- **模式 B（大家具退化）**：office4 table 0.93→0.22、bench 0.97→0.51；
  room0 sofa 0.75→0.26；office3 clock/cushion/sofa。

## D2 对象级尸检（office4/room2，diagnose_eval_object_assignments）

**dense 基底三联病**，展品 office4 obj#43：
1. **点稀疏**：2121 次检测的对象只导出 1382 点（`max_points_per_obs=160`、
   `MAX_POINTS_PER_OBJECT=4096` 的全局采样预算）；GT tv-screen 105k 点（98.6%）
   + clock 7.4k 点（100%）被最近点评测吸附到这个稀疏错误邻居 → 两类整体蒸发。
   CG 每景 1-3M 点 vs 我们 ~100k——ScanNet 公平性核查发现的密度差在 Replica
   上反向伤害我们自己。
2. **桶混合**：obj#43 横跨 2.48m 的墙带混合桶；room2 GT table 34% 被吸进
   indoor-plant 桶、22% 进 vent 桶（召回仅 43.8%）。
3. **混合读出漂移**：obj#43 声明 monitor、eval CLIP 读出 vent（双错）；
   obj#52 声明 stool、读出 table。

## 点对点修复分派

- **O2c（点稀疏，参数级修复，76 跑动中）**：点预算 160/4096 → 640/16384
  （即 E70-geometry 的全局值），其余不变。
- **O1（基底替代，184 跑动中）**：multires-geometry-everywhere
  （E70-geometry 全局画像：gamma+voxel0.5+minDet8+640/16384+split+multires），
  office1/office2 在此基底上的表现是从未测过的空白。
- O2b（桶混合，Layer2/分裂参数）：待 O1/O2c 结果后决定是否需要。
- 判读：两线赛马，取更强者为统一基底；若 O2c 使 dense 全场景转正，
  机制层（门/sp）在其上的增量重新可辩护。
