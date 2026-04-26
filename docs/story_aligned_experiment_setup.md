# DuoGraph3D 论文故事对齐后的实验设置

日期：2026-04-23  
状态：story-aligned experiment protocol

最新执行注记（2026-04-23 20:30 +08:00）：OnlineAnySeg（fixed subset20 bring-up completed）与 ConceptGraphs（scoring path pending）是当前主 zero-shot external baseline lanes；ESAM/EmbodiedSAM 不再承担主增益 comparator 角色，仅作为 auxiliary compatibility reference。

---

## 1. 这份实验设置要解决什么问题

这份文档用于纠正此前不够合理的实验主线：

- **不能**把 DuoGraph3D 写成“一个要在标准 instance segmentation leaderboard 上正面对标 ESAM 的方法”；
- **不能**让 learning-based 3D instance segmentation family 反过来定义本文的身份；
- **必须**让实验设置服务于当前已经冻结的论文创新点与故事。

因此，实验设计的起点不是“哪张现成 benchmark 表最常见”，而是：

> **这篇工作到底在解决什么新的问题？**

配套执行文档：
- `docs/baseline_execution_roadmap.md`

---

## 2. 当前论文故事的核心

### 2.1 工作身份
DuoGraph3D 的目标不是提出一个新的学习型 3D instance segmentation backbone，
而是提出一个：

- **online**
- **zero-shot / open-vocabulary**
- **object-centric**
- **以在线 3D matching 与 object maintenance 为核心**
- **显式分离 current repair 与 memory association 的两层图框架**
- **让 graph memory 成为 decision-bearing state**

的在线对象级 3D reconstruction / mapping 系统。

### 2.2 三条核心创新点
1. **Online 3D matching / object maintenance**
   - 当前对象如何与历史对象关联
   - 何时 birth / keep / merge / split / retire
   - 如何在长期观测下维持 object identity
2. **Two-layer graph design**
   - Layer-1: current evidence repair
   - Layer-2: current-object ↔ memory-object association
3. **Decision-bearing object graph memory**
   - memory 不是后验 graph export
   - 而是在线 object state 的核心维护机制

### 2.3 直接推出的 baseline 原则
因此，baseline 必须围绕这三条创新点来配，而不是围绕“最容易拿到一个 AP 分数的系统”来配。

---

## 3. 实验设置总原则

### 原则 1：主比较对象必须与论文故事同构
主比较对象应优先是：
- online
- zero-shot / open-vocabulary
- object-centric 3D understanding / mapping
- 需要处理在线 matching / maintenance / merge

而不是主要依靠训练得到 3D instance segmentation 能力的系统。

### 原则 2：learning-based instance segmentation family 只能作为辅助参考
像 **ESAM / EmbodiedSAM** 这样的系统可以保留，但其角色应是：
- **auxiliary metric-compatibility reference**
- 或 supplementary benchmark reference

而**不是**当前论文故事下的 primary direct baseline。

### 原则 3：实验块要与创新点一一对应
最终实验应至少分为：
1. 直接任务对比
2. temporal 对比
3. layer-1 / layer-2 必要性消融
4. graph memory / object maintenance 对比
5. auxiliary benchmark-compatibility reference

---

## 4. 最终推荐的实验分块

## Block A — 直接任务对比（主结果块）

### 目标
证明 DuoGraph3D 在“online zero-shot object-centric 3D matching / reconstruction / mapping”这一更贴合论文故事的问题定义下，优于最直接的邻近方法。

### 主要数据集
- **ScanNet / ScanNet-family**：复杂真实室内场景，适合在线 matching 与 object maintenance
- **Replica**：适合展示更干净的 temporal carry-over 与 object persistence

### 主要指标族
- identity stability / fragmentation
- association and re-entry quality
- object maintenance quality
- object grouping / segmentation quality
- geometry / map quality

### 主要对标工作
1. **OnlineAnySeg**
   - 最接近本文“online + zero-shot + 2D/3D 在线关联”设定的 direct neighbor
2. **ConceptFusion / Open-Fusion**
   - 代表 online open-vocabulary mapping / dense fusion 路线

### 这一块回答的问题
- 我们的 online 3D matching / object maintenance 是否真的优于现有 zero-shot online 3D 方法？
- memory-bearing framework 是否优于 dense/open-vocab map 路线？

---

## Block B — Temporal backbone / carry-over 对比（核心支撑块）

### 目标
证明 temporal propagation 不是装饰，而是 3D object update 的一级先验。

### 主要数据集
- **Replica**（主）
- **ScanNet subset**（辅）

### 主要指标族
- re-entry quality
- persistence / lifetime stability
- identity fragmentation
- association continuity

### 主要对标工作 / 设置
1. **DEVA official offline lane**
2. **w/o temporal propagation**
3. **naive frame-wise masks**
4. **DEVA-style temporal backbone**

### 这一块回答的问题
- 为什么不是只靠当前帧 mask + 3D overlap？
- 为什么视频时序记忆必须进入 3D object maintenance？

---

## Block C — Two-layer necessity / Layer-1 current repair 对比（结构支撑块）

### 目标
证明 current evidence repair 与 current-to-memory association 必须解耦，不能塌成一个 matching heuristic。

### 主要数据集
- **ScanNet subset**
- 必要时补 **Replica subset**

### 主要指标族
- current-frame over-fragmentation
- object grouping quality
- downstream association robustness

### 主要对标工作
1. **Open3DIS**
2. **SAI3D**
3. **MaskClustering**
4. **single-layer rival**（内部）

### 这一块回答的问题
- 为什么 Layer-1 不是拍脑袋分层？
- 为什么 current evidence graph 有必要存在？

---

## Block D — Graph memory / object maintenance 对比（表示支撑块）

### 目标
证明 graph memory 不是 decorative export，而是 decision-bearing long-term object state。

### 主要数据集
- **ScanNet**
- **Replica**

### 主要指标族
- long-term identity maintenance
- object persistence / reactivation
- relation-aware association quality
- graph usefulness / graph-consistent maintenance

### 主要对标工作
1. **ConceptGraphs**
2. **Open3DSG**
3. **dense-authority export rival**（内部）
4. **full fair counterfactual**（内部）

### 这一块回答的问题
- 为什么不是 dense map + post-hoc graph export？
- 为什么 object graph memory 要放在 reconstruction backbone 内部？

---

## Block E — Auxiliary benchmark-compatibility reference（辅助参考块）

### 目标
保留与 reviewer-familiar benchmark 的沟通接口，但不让它反过来定义本文身份。

### 数据集
- **ScanNet200 / ScanNet-MV evaluator surface**（若输出桥接成熟）

### 指标
- `all_ap`
- `all_ap_50%`
- `all_ap_25%`

### 参考对象
- **ESAM / EmbodiedSAM**

### 角色说明
- 这是 **auxiliary compatibility table**
- 不是 primary direct-baseline table
- 不能作为整篇论文的唯一主结果

### 这一块回答的问题
- 如果 reviewer 想看标准 AP surface，我们是否能给出一个兼容参考？
- 但这张表不承担定义本文创新点的任务。

---

## 5. 数据集 × 指标 × baseline 的最终矩阵

| 实验块 | 数据集 | 指标族 | 主要 baseline | 角色 |
| --- | --- | --- | --- | --- |
| Block A 直接任务对比 | ScanNet + Replica | matching / maintenance / grouping / geometry | OnlineAnySeg, ConceptFusion / Open-Fusion | 主结果块 |
| Block B temporal | Replica + ScanNet subset | re-entry / persistence / fragmentation | DEVA, no-temporal, naive-temporal | 核心支撑块 |
| Block C two-layer necessity | ScanNet subset | grouping / over-fragmentation / downstream robustness | Open3DIS, SAI3D, MaskClustering, single-layer rival | 结构支撑块 |
| Block D graph memory | ScanNet + Replica | long-term maintenance / graph usefulness | ConceptGraphs, Open3DSG, dense-authority export rival | 表示支撑块 |
| Block E auxiliary compatibility | ScanNet200 surface | all_ap / all_ap_50 / all_ap_25 | ESAM / EmbodiedSAM | 辅助参考块 |

---

## 6. 哪些旧设置现在应视为不合理

以下设置现在应明确降级或废弃：

1. **“把 ScanNet200 AP + ESAM 作为整篇论文唯一主线”**
   - 不合理原因：它会把论文错误地改写成一个 learning-based instance segmentation 对标故事。

2. **“用 ESAM 作为 primary direct baseline”**
   - 不合理原因：ESAM 更适合做 auxiliary metric-compatibility reference，而不是最贴近本文创新点的 direct neighbor。

3. **“先追求 AP 主表，再倒推论文故事”**
   - 不合理原因：这会让实验设置反过来损坏已冻结的创新点与 claim boundary。

---

## 7. 接下来实验推进的正确顺序

1. 先按 **Block A–D** 冻结 story-aligned comparison protocol。
2. 先确定每个创新点到底由哪张表来回答。
3. 再判断哪些指标需要新实现，哪些 baseline 需要优先 runnable。
4. **最后**才决定是否补 Block E 的 AP compatibility table。

换句话说：

> **先让实验服务论文故事，再决定 benchmark compatibility 如何接入；而不是先追一个不对口的 benchmark 表。**


相关输出对齐文档：
- `docs/alignment_output_protocol.md`
