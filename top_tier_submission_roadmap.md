# DuoGraph3D 顶会级投稿差距分析与分阶段执行清单

日期：2026-04-23  
项目：`DuoGraph3D / Dual-Consistency Graph Memory`

---

## 1. 这份文档的目标

这份文档不是为了追求“最小可投版本”，而是为了把项目推进到**最终顶会级别的工作质量**。

这里的“顶会级别”默认指：

- 论文主张与代码实现严格对齐
- 真实 object-level evidence，而不是主要依赖 proxy/synthetic observation
- reviewer-credible 的外部 baseline，而不是只有内部 counterfactual
- paper-grade 的主指标、消融、鲁棒性与失败案例分析
- 完整的 paper draft、图表资产与复现路径

因此，本路线图的目标不是“尽快发出去”，而是：

> **把 DuoGraph3D 做成一篇经得起 CVPR / ICCV 级 reviewer 拆解的完整工作。**

---

## 2. 当前项目阶段判断

### 2.1 总体结论

当前项目已经完成了：

1. **研究 framing 和论文主张框架**
2. **v1 双层原型系统**
3. **内部 fair-rival / temporal family / 证据打包框架**
4. **面向 reviewer defense 的材料骨架**

但距离最终顶会投稿，仍然缺少：

1. **真实 observation / object-level evidence 主链**
2. **更强的方法完成度（尤其 graph / geometry 部分）**
3. **reviewer-credible 的外部 baseline**
4. **paper-grade 的主指标和非空结果包**
5. **正式论文稿、图表与复现资产**

### 2.2 当前完成度判断

按“最终顶会投稿版本”衡量，当前完成度大致可视为：

- **约 35%–45%**

这个判断基于：

- 主干原型已经存在
- 写作 framing 很成熟
- 但实证仍以 prototype-backed / proxy evidence 为主

---

## 3. 当前判断所依据的仓库证据

以下是当前仓库中直接支撑上述判断的关键证据点：

### 3.1 已经具备的强项

- `README.md`
  - 仓库已经明确列出当前 scope：object graph memory、layer-1、layer-2、temporal variants、fair rivals。
- `src/duograph3d/pipeline.py`
  - 主流程已经成型：`evidence -> layer1 -> layer2 -> memory`。
- `src/duograph3d/evidence.py`
  - 已经有 DEVA-style temporal propagation 的 evidence 注入逻辑。
- `src/duograph3d/layer1.py`
  - 已经有 current evidence repair 层。
- `src/duograph3d/layer2.py`
  - 已经有 current-to-memory association、birth / reentry / death / lifecycle 更新。
- `src/duograph3d/rivals.py`
  - 已经实现 single-layer rival、dense-authority export rival、full fair counterfactual。
- `examples/refresh_all_evidence.py`
  - 已经能自动生成 mega summary、robustness、casebook、paper metrics、package、G4 docs。
- `tests/`
  - 单元测试完整，当前通过 52 个测试。

### 3.2 当前最关键的不足

- `src/duograph3d/readiness.py`
  - 明确写着：`prototype_backed = True`，`paper_grade = False`。
- `src/duograph3d/data.py`
  - 当前 observation 仍主要由模板 / metadata 驱动生成，不是最终真实 observation 主链。
- `src/duograph3d/paper_metrics.py`
  - 当前 paper-facing metrics 仍然以 proxy 指标为主。
- `src/duograph3d/g3_docs.py`
  - 文档多处明确承认当前证据仍是 prototype-level / proxy-level。
- `src/duograph3d/g4_docs.py`
  - backlog 已经明确指出还缺：真实 object evidence、更真实 rivals、更强 geometry-aware metrics。
- `src/duograph3d/external_baselines.py`
  - 外部 baseline 目前主要还停留在 target 定义层。
- `src/duograph3d/deva_runtime.py`
  - DEVA 接入目前主要还是 runtime probe / wrapper / readiness gate。
- `outputs/bounded_slice_replica_office0.json`
  - 当前仓库中存在空结果样例，说明 repo 内已提交产物不能代表最终完整 paper-grade evidence。

---

## 4. 距最终顶会投稿的核心差距

下面按五个维度系统整理当前 gap。

### 4.1 方法层差距

#### 当前状态

- 已有 two-layer 框架
- 已有 memory authority 叙事
- 已有 temporal propagation 逻辑
- 已有 object node state

#### 主要差距

- `layer-1` 还偏 grouped repair，不够像更强的 graph reasoning
- `layer-2` 还偏 heuristic scoring + lifecycle rules
- `graph memory` 目前更像 node-state memory，relation graph 还不够强
- `3D geometric consistency` 目前仍偏 scalar support，而不是更强的 geometry operator

#### 顶会级要求

- 论文中“graph / geometry / dual-consistency”的每一条方法主张，都必须有代码中的清晰对应物
- reviewer 不能轻易指出“这只是命名上的 graph，不是方法上的 graph”

---

### 4.2 实验输入与证据层差距

#### 当前状态

- 当前实验框架已经能跑大量 regime
- 但 observation 主链仍主要来自 synthetic/template 化构造

#### 主要差距

- 缺少真实 object-level observation 主链
- 缺少真实 masks / tracks / proposals 到 `FrameInput` 的稳定适配
- 当前结果更接近“结构性原型验证”，而不是“真实系统实验”

#### 顶会级要求

- 主结果必须来自真实 scene observation
- synthetic/template path 只能保留给测试或补充实验，不能成为主证据

---

### 4.3 baseline 与比较层差距

#### 当前状态

- 内部 rivals 已经很系统
- 外部 baseline 的接入方向已确定，优先是 DEVA

#### 主要差距

- 还没有形成 reviewer-credible 的外部 baseline 结果表
- “为什么不是现有方法 X” 目前更多是结构性回答，不是正式量化对比

#### 顶会级要求

- 至少要有 1–2 个真正跑通的外部强 baseline
- 主表中必须出现 reviewer 会优先想到的邻近对手

---

### 4.4 指标与论证层差距

#### 当前状态

- 已有 fragmentation、reentry、authority activation、geometry support 等 proxy 指标
- 已有 robustness、casebook、reviewer attack matrix

#### 主要差距

- 当前主指标还是 proxy-heavy
- 还缺少真正 paper-grade 的 object identity / segmentation / geometry / mapping 指标组合
- 当前结果包更适合内部研究推进，不足以直接进入最终主论文

#### 顶会级要求

- 主指标必须是 reviewer 熟悉且认可的
- proxy 指标最多作为补充解释，不应承担整篇工作的主证据角色

---

### 4.5 写作与提交资产层差距

#### 当前状态

- 题目、claim stack、paper outline、camera-ready risk list 都已经有了

#### 主要差距

- 还没有正式 manuscript
- 还没有最终 pipeline figure / ablation figure / qualitative figure
- 还没有 supplementary / appendix / reproducibility package

#### 顶会级要求

- 不只是“能写成文”，而是要形成一个完整、严谨、可提交的 paper package

---

## 5. 当前最重要的 submission blockers

以下是必须优先解决的 blocker，按优先级排序：

1. **真实 observation 主链未替换 synthetic 主链**
2. **graph / geometry 方法表达与实现之间仍存在落差**
3. **缺少 reviewer-credible 外部 baseline 正式结果**
4. **paper metrics 仍主要是 proxy metrics**
5. **repo 内尚无 paper-grade 非空 evidence package**
6. **正式论文稿与图表资产尚未生成**
7. **clean reproducibility / final submission hardening 尚未开始**

---

## 6. 顶会级目标的执行原则

从现在开始，项目推进应遵守以下原则：

### 原则 1：不追求最小可投

不为了“赶紧交一版”而牺牲：

- baseline 质量
- 指标质量
- claim-implementation 对齐
- experiment completeness

### 原则 2：优先修复证据质量，而不是先堆写作

在最终投稿里，真正决定接受概率的不是 outline，而是：

- 主结果是否可信
- baseline 是否扎实
- reviewer 最尖锐的问题有没有被真正回答

### 原则 3：方法与 claim 必须共同收敛

如果方法最终没有做强，就收缩 claim。  
如果要保持当前 claim 强度，就必须补强 method。

### 原则 4：所有阶段都必须有退出条件

每个阶段必须明确：

- 本阶段的交付物
- 本阶段的验收标准
- 进入下一阶段前必须满足的条件

---

## 7. 分阶段可执行清单（顶会级版本）

---

## Phase 0 — 顶会级 claim freeze

### 目标

锁定**最终顶会版本**的问题定义、主张边界、baseline 范围、主表结构。  
这个阶段不是为了缩成最小版本，而是为了避免后续工作在高标准下失焦。

### 任务

- [ ] 写一页 `submission-lock` 文档，明确：
  - [ ] 最终投稿 target venue（如 CVPR / ICCV）
  - [ ] 核心 claim
  - [ ] 不做的 claim
  - [ ] reviewer 最可能攻击的 5 个点
- [ ] 冻结最终论文主问题定义
- [ ] 冻结最终 baseline 清单
- [ ] 冻结最终主表指标清单
- [ ] 冻结最终 figure list
- [ ] 明确当前版本是否坚持：
  - [ ] graph memory 的强表述
  - [ ] geometry consistency 的强表述
  - [ ] reconstruction / mapping 的强表述

### 验收标准

- [ ] 有 1 份明确的顶会级 claim lock 文档
- [ ] baseline / metrics / figures 不再反复漂移
- [ ] 后续实验都能映射到 frozen claim

### 风险提醒

- 如果这一阶段不冻结，后面容易边做边改题，导致实验无底洞

---

## Phase 1 — 真实 observation 主链替换

### 目标

把当前 prototype-backed 的 observation 输入，替换成真实 object-level evidence 主链。

### 任务

- [ ] 将 `data.py` 中 synthetic/template observation 生成路径隔离为：
  - [ ] test/synthetic only
  - [ ] 不再承担主结果输入
- [ ] 设计真实 observation adapter：
  - [ ] mask / detection / track -> `Observation`
  - [ ] 保留 continuity / appearance / geometry support 接口
- [ ] 跑通 Replica 的真实 observation 主链
- [ ] 跑通 ScanNet 的真实 observation 主链
- [ ] 为真实 observation 主链补测试：
  - [ ] adapter correctness
  - [ ] ordering consistency
  - [ ] missing/occluded case
  - [ ] frame alignment
- [ ] 输出首批真实 qualitative cases：
  - [ ] raw observation
  - [ ] repaired hypothesis
  - [ ] association decision
  - [ ] memory evolution

### 验收标准

- [ ] 主结果的 `bounded_slice_*.json` 不再依赖 synthetic-only observation
- [ ] 至少 6 个 scene 生成非空真实结果
- [ ] 可以展示真实输入 -> method output 的完整链路

### 退出条件

- [ ] 只有在主结果输入已经真实化后，才能进入后续 paper-grade baseline / metric 阶段

---

## Phase 2 — 方法增强到顶会级

### 目标

把现有 two-layer prototype 强化为能支撑顶会 claim 的方法实现。

### 任务

#### 2.1 Layer-1 强化

- [ ] 明确 layer-1 最终形式：
  - [ ] 更强的 merge / repair graph
  - [ ] 显式 edge 定义
  - [ ] current evidence conflict resolution
- [ ] 增强 same-frame / short-window evidence repair
- [ ] 增加与 temporal / geometry consistency 的更清晰接口

#### 2.2 Layer-2 强化

- [ ] 明确 current-to-memory association 是否需要 relation-aware 扩展
- [ ] 评估是否需要从纯 heuristic score 升级为更结构化 matching
- [ ] 把 ambiguity resolution 从日志事件提升为更清晰的方法模块

#### 2.3 Memory 强化

- [ ] 明确最终 memory 是否包含显式 relation edges
- [ ] 若论文继续强调 graph memory，则需：
  - [ ] 存 relation
  - [ ] 更新 relation
  - [ ] 在结果和图中展示 relation
- [ ] 增强 object state 的长期稳定性设计：
  - [ ] support history
  - [ ] lifecycle state
  - [ ] confidence / authority

#### 2.4 Geometry 强化

- [ ] 增加比当前 scalar `geometry_support` 更强的 geometry operator
- [ ] 引入真实的 multi-view / overlap / projection consistency
- [ ] 明确 dual-consistency 在代码中的具体落点

### 验收标准

- [ ] 论文方法图中每个关键模块都能在代码中一一对应
- [ ] reviewer 不能轻易把“graph”或“geometry consistency”判为表述过强
- [ ] 方法增强带来可量化收益，而不是只增加复杂度

### 风险提醒

- 如果这一步做弱了，就必须收缩 claim，不能硬顶顶会级表述

---

## Phase 3 — reviewer-credible baseline 体系

### 目标

把当前“内部对照为主”的结构，升级为 reviewer-credible 的 baseline 体系。

### 任务

#### 3.1 内部 baseline 固化

- [ ] 固化 single-layer rival
- [ ] 固化 dense-authority export rival
- [ ] 固化 full fair counterfactual
- [ ] 固化 temporal family（none / naive / DEVA）

#### 3.2 外部 baseline 真正跑通

- [ ] 先把 DEVA official lane 跑通到可出结果
- [ ] 选择并落地至少 1 个强外部邻近 baseline
- [ ] 若 claim 涉及更强 mapping / online object reconstruction，需要再补一个更贴近主问题的外部方法

#### 3.3 baseline 公平性与可信度

- [ ] 明确每个 baseline 的：
  - [ ] 数据输入
  - [ ] 配置
  - [ ] 运行脚本
  - [ ] 结果口径
- [ ] 建立 baseline audit 文档，避免 reviewer 质疑 unfair comparison

### 验收标准

- [ ] 至少 2 个外部 baseline 形成正式结果文件
- [ ] 主表能回答“为什么不是方法 X / Y”
- [ ] baseline 设置可以被复现和复查

### 风险提醒

- baseline 不可信，是顶会稿最常见的直接拒稿点之一

---

## Phase 4 — paper-grade 指标与大规模结果包

### 目标

把当前 proxy-heavy 的结果体系升级为顶会级 main results package。

### 任务

#### 4.1 指标升级

- [ ] 冻结 paper-grade 主指标组合：
  - [ ] identity stability / fragmentation
  - [ ] reentry / association quality
  - [ ] object grouping / segmentation quality
  - [ ] geometry / map quality
  - [ ] 必要时 queryability / graph usefulness
- [ ] 明确哪些 proxy 指标保留为补充分析，哪些退出主表

#### 4.2 结果运行

- [ ] 跑锁定后的 full suite
- [ ] 跑关键 regime：
  - [ ] baseline
  - [ ] stress
  - [ ] burst/random
  - [ ] holdout
- [ ] 更新 mega summary、robustness、statistics、paper metrics、paper main table

#### 4.3 结果分析

- [ ] 补 representative cases
- [ ] 补 failure cases
- [ ] 补 worst-scene / best-scene analysis
- [ ] 补核心 ablations：
  - [ ] layer-1
  - [ ] layer-2
  - [ ] temporal branch
  - [ ] memory authority
  - [ ] graph/geometry enhancement模块

### 验收标准

- [ ] 主表不再依赖 proxy 指标作为唯一证据
- [ ] 有完整非空 results package
- [ ] 结果能够支撑 frozen claim

### 退出条件

- [ ] readiness 不再只是 `prototype_backed`
- [ ] 至少内部评估上达到“paper-grade candidate”

---

## Phase 5 — 正式论文稿与图表资产

### 目标

把当前 outline / defense notes 升级为正式投稿稿。

### 任务

#### 5.1 完整论文草稿

- [ ] Abstract
- [ ] Introduction
- [ ] Related Work
- [ ] Method
- [ ] Experimental Setup
- [ ] Main Results
- [ ] Ablations
- [ ] Failure Analysis
- [ ] Limitations
- [ ] Conclusion

#### 5.2 图表资产

- [ ] Overall pipeline figure
- [ ] Layer-1 / Layer-2 method figure
- [ ] Memory structure figure
- [ ] Qualitative figure
- [ ] Failure case figure
- [ ] Main table
- [ ] Ablation table
- [ ] Robustness table

#### 5.3 Reviewer-facing defense assets

- [ ] Why-not-X paragraph set
- [ ] nearest-neighbor comparison block
- [ ] reviewer attack matrix
- [ ] claim boundary statement

### 验收标准

- [ ] 形成完整 PDF draft
- [ ] 所有主图主表都有最终版本
- [ ] 所有关键 claim 都能在文中被结果直接支撑

### 风险提醒

- 文稿不能继续沿用“prototype-backed”语气
- 但也绝不能超出最终实验边界去夸张表述

---

## Phase 6 — submission hardening

### 目标

把“有论文草稿”推进到“可正式提交”。

### 任务

- [ ] clean environment 复现主表
- [ ] clean environment 复现关键图
- [ ] 整理 supplementary / appendix
- [ ] 检查代码与实验匿名化/开源策略
- [ ] 最终 bibliographic sanity check
- [ ] figure caption / table caption 全面检查
- [ ] 与 claim lock 做最终逐项对照

### 验收标准

- [ ] 可以从干净环境复现关键结果
- [ ] 可以打包完整 submission assets
- [ ] 不存在明显 reviewer 一眼可抓的 consistency 问题

---

## 8. Critical Path（必须串行）

以下主线必须按顺序推进：

1. **Phase 0：claim freeze**
2. **Phase 1：真实 observation 主链**
3. **Phase 2：方法增强**
4. **Phase 3：外部 baseline**
5. **Phase 4：paper-grade results package**
6. **Phase 5：正式论文稿**
7. **Phase 6：submission hardening**

---

## 9. 可并行子任务

在不破坏主线依赖关系的前提下，可以并行推进：

### 可并行 A：写作与图表模板

- [ ] 在 Phase 2–4 期间同步搭建 figure templates
- [ ] 在 Phase 3–4 期间同步搭建 table templates
- [ ] 在 Phase 4 末期并行起草 intro / related work

### 可并行 B：baseline 工程

- [ ] 外部 baseline 环境搭建
- [ ] baseline 数据契约整理
- [ ] baseline result summarizer

### 可并行 C：复现与工程清理

- [ ] 整理 clean run scripts
- [ ] 记录环境依赖
- [ ] 整理 artifact 路径规范

---

## 10. 近期优先级（接下来最应该先做什么）

如果按“顶会质量优先”的原则，接下来最优先的顺序是：

### Priority 1

- [ ] 写 `submission-lock`
- [ ] 明确最终 claim、baseline、metrics

### Priority 2

- [ ] 真实 observation 主链替换 synthetic 主链
- [ ] 让主结果从真实 evidence 出发

### Priority 3

- [ ] 决定 graph / geometry 部分到底是“增强实现”还是“收缩表述”

### Priority 4

- [ ] 跑通第一个 reviewer-credible 外部 baseline（优先 DEVA）

### Priority 5

- [ ] 重建 paper-grade metrics 与 main table

---

## 11. 顶会级退出标准（最终）

只有当以下条件同时满足，才能认为项目真正接近最终顶会投稿状态：

- [ ] 主结果来自真实 object-level evidence
- [ ] 方法中的 graph / geometry / temporal claim 与代码严格对齐
- [ ] 至少 2 个 reviewer-credible 外部 baseline 有正式结果
- [ ] 主表使用 paper-grade 指标，而不是主要依赖 proxy 指标
- [ ] 结果包完整、非空、可复现
- [ ] 正式论文稿完成
- [ ] 图表与 supplementary 完成
- [ ] clean environment 能复现关键结果

---

## 12. 最后结论

当前 DuoGraph3D 已经具备：

- 强 framing
- 强问题意识
- 可运行的原型
- 优秀的研究组织与证据打包意识

但要达到**最终顶会级别**，必须从“prototype-backed 结构原型”升级为“paper-grade 真实系统证据”。

因此，接下来的工作重点不应是继续微调叙事，而应是：

> **用真实 object-level evidence、可信 baseline、扎实指标和完整结果包，把当前漂亮的研究结构真正落成一篇硬论文。**

