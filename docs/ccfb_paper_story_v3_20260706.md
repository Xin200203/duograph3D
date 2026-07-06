# DuoGraph3D 论文故事 v3 — 定稿主线（2026-07-06 晨）

取代 v2（v2 写于基底/prep 发现之前，其"单配置统一方法"预期已被夜间证据链修正）。
表格素材：`docs/ccfb_tables_20260706.md`。证据日志：`docs/ccfb_experiment_runlog_20260705.md`。

## 0. 一句话故事

> 在 object-centric open-vocabulary 3D mapping 中，**语义读出不是天然权威**：我们用
> 对象级法医证据展示三类此前未被显式刻画的权威失败——合并制造的读出污染、
> 在多视角投票下存活的系统性检测偏差、以及把边界噪声当作证据的基底错配——并给出
> 一族可审计、可弃权、带证据前提的 carrier-authority 机制，在合并对象基底上以
> exact-recovery 实验确立因果；同时诚实刻画单配置全场景组合的开放性
>（先前 SOTA 式组合实为五层场景手工选择，我们给出其 oracle 上界与完整负结果链）。

## 1. 三条贡献（与证据一一对应）

### C1 — Carrier-authority 机制族（主贡献，~45%）

三个机制 + 三个守卫，全部 GT-free、对象级可审计、带明确证据前提：

- **M1 per-pair label-cluster 合并门**：离散多视角声明证据否决连续 CLIP/text
  相似度放行的破坏性合并。守卫：evidence floor（T4#2）、mutual-containment
  （T4#3）。因果证据：office1 阶梯 +2.79→+4.02（保 carrier）→+8.17（E70-exact，
  T1a）；验证景净贡献 +0.5/+2.9/+2.2（T1c）。
- **M2 合并致误读的预防**：office2 双操作点等价证明（全否决无修复 +8.185 ≈
  全合并+修复 +8.211，均超 E70 的 +6.49）——修复是补丁，carrier 保持是因（T1b）。
- **M3 尺度先验语义权威检查**：物理 max-extent 先验（LLM 常识生成、评测前冻结）
  + declared-only 目标选择 + 三重弃权守卫 + hard-ratio 权威撤销（一致性≠正确性，
  T4#4）。log-only 干跑校准协议 + 预注册预测（office4 vents 6/6 正确弃权）。
- **机制作用域原则**：证据前提只在合并对象基底成立；原始 key 桶的标签分布是
  边界噪声（T4#11）→ `mechanisms-scope consolidated-only`。

### C2 — 对象级失败归因框架（~30%）

每个合并/否决/修复/弃权决策的证据链落盘（veto_examples、no_veto_reasons、
scale_prior_probe、declared 分布、预注册记录）。论文中以 12 行负边界表（T4）
展示框架的判别力：每个被否决的设计都有可指认的对象级反例。这是与
OVI-MAP/ESAM/Details Matter 等邻居的核心差异——它们优化精度，我们让权威决策
可审计。

### C3 — 组合性开放问题的定量刻画（~25%）

- 8×2 基底矩阵：没有单基底配置在全场景为正（office4-dense 一景 −27，基底级）；
- E70 式强组合（+3.041）被解剖为五层场景手工选择（prep 粒度×基底×相位×合并×
  keep-set），作为 **oracle 上界**报告；
- 路由信号的系统性否决（覆盖阈值排序反向、consolidation 比值为体素伪影）——
  "scene-independent substrate selection" 被确立为该设置下的开放问题。

## 1.5 在环性论证（2026-07-06 CG-substrate 实验后新增，升格为主线论证）

把机制事后施加到 CG 官方图上（真实声明分布重建、对齐 0.9999）：门零候选
（CG 在线合并已消耗全部合并决策）、sp 退化为噪声（all −0.46）。与内联应用
（office1 +8.17 / office2 +8.19）对照，得到论文的中心命题：

> **Semantic authority control is only effective at decision time.**
> 破坏性合并发生在建图环内；证据（独立的声明簇、未污染的读出）随合并销毁，
> 事后不可恢复。因此权威控制必须内嵌于在线建图循环——这正是双层图记忆
> 存在的理由（Layer1/Layer2 维护决策时刻所需的证据状态）。

该实验同时是协议有效性检查（legacy 行 −0.08 ≈ 官方平位）。

## 2. 与 SOTA 的关系（照 6/28 审查更新）

- 不声称 OV-3DIS SOTA、不声称 AP、不声称统一方法超过 CG 全场景；
- 声称：在官方 CG semantic 协议的合并基底场景上，机制以 exact-recovery 因果
  超过 CG（office1 +8.17 / office2 +8.19 / room1 +6.29 / office0 +3.18）；
- OVI-MAP（解耦为效率）/GeoGuide（训练型一致性）对比点：我们是无训练、在线、
  可审计的权威判定，且给出失败归因基准；
- E70 oracle +3.041 仍可引用为"含场景知识的组合上界"，其与机制行的差 =
  "无场景知识的代价"，量化呈现。

## 3. 结构与图表

| 章节 | 内容 | 素材 |
| --- | --- | --- |
| Intro | 三类权威失败 + 贡献 | bin carrier 画像、70/70 tissue 案例 |
| Method | M1-M3 + 守卫 + 作用域 + 审计字段 | 代码已全部落地（172 tests） |
| Exp §1 | T1 机制因果（阶梯、双操作点、验证景净贡献） | T1a/b/c |
| Exp §2 | T2 组合消融 + E70 oracle 解剖 | T2 |
| Exp §3 | T3 审计计数 + 预注册 | T3 |
| Exp §4 | T4 负边界 + floor/敏感性曲线 | T4 |
| Limitation | 单配置开放、合成数据、semantic 协议族 | — |
| F1 | pipeline + 权威判定流 | — |
| F2 | office2 合并致误读 before/after 点云 | e70/pa1c artifacts |
| F3 | cloth\|picture 否决案例可视化 | pa1b veto record |

## 4. 剩余工作（P1，投稿前）

1. ScanNet OOD sanity（73 的 8×3090：GSA 检测生成 → 机制在 OOD 合并基底上的
   fire/abstain 行为）；
2. Replica instance AP evaluator（supplementary 协议桥）；
3. CG-Detector baseline 行 + OVI-MAP/OnlineAnySeg/ESAM protocol bridge 表；
4. 手稿重写（4/23 旧稿全部主线替换为本文档）；
5. 阈值敏感性补全（mutual thresh、share、tolerance 各 ±）。

## 5. 审稿人 Q&A 预案

- "机制阈值是不是调出来的？" → 场景记账（office1/office2 开发、room1/office0/
  office3 纯验证）+ floor/敏感性曲线 + 预注册记录 + 门关≡legacy 对照。
- "为什么不给统一方法？" → T4#8/#9 的路由否决证据 + T2 全负格局：这是设置本身
  的开放问题，我们是第一个用对象级证据定量刻画它的工作。
- "office1 的修复规则来自哪里？" → 诚实：declared 与 CLIP 都不含 cloth 答案
  （T4#5），tissue→cloth 属 oracle 知识；机制行不依赖它（+4.02 无修复行独立成立），
  E70 行单列为上界。
