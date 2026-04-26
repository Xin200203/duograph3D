# DuoGraph3D Baseline 执行路线图（按优先级）

日期：2026-04-23  
状态：prioritized executable baseline roadmap

---

## 1. 这份路线图的目标

这份文档不是重新定义论文故事，而是把已经冻结的 **story-aligned experiment protocol** 进一步拆成：

- 哪些 baseline **科学上最重要**
- 哪些 baseline **现在就能开工**
- 哪些 baseline **应该先做 runnable lane**
- 哪些 baseline **暂时不要抢主线资源**

上位文档：
- `docs/story_aligned_experiment_setup.md`
- `.omx/plans/prd-duograph3d-benchmark-main-table.md`

---

## 2. 优先级判断规则

每个 baseline lane 按四个维度排序：

1. **Story fit**
   - 与“online 3D matching / two-layer graph / object maintenance”贴合程度
2. **Execution readiness**
   - 当前是否已有本地/远端 repo、结果、数据、配置线索
3. **Metric usefulness**
   - 能否回答一个 reviewer 真会问的问题
4. **Integration cost**
   - 引入该 lane 是否需要大量额外环境/数据准备

### 排序原则
- **先做 story fit 高、readiness 高 的 lane**
- 不先做 story fit 低、但 benchmark surface 很好看的 lane
- 不让 auxiliary lane 抢占主线资源

---

## 3. 当前 baseline 候选的真实可执行性盘点

## Lane T0 — DEVA temporal lane

### 角色
- **Block B temporal backbone / carry-over comparison**

### 当前状态
- **已 formalize，可立即使用**

### 证据
- repo target 已 formalize：`src/duograph3d/external_baselines.py`
- 当前 inventory：`docs/phase3_external_baseline_inventory.md`
- 已有 raw artifacts：`docs/baselines/raw/deva_jsonfiles/*.json`
- 已有 generated summaries：`docs/baselines/generated/deva_output_summary.*`

### 优先级判断
- Story fit：**极高**
- Readiness：**极高**
- Metric usefulness：**高**
- Integration cost：**低**

### 结论
> **这是第一个必须继续使用的 baseline lane。**

---

## Lane D1 — OnlineAnySeg direct-neighbor lane

### 角色
- **Block A direct task-neighbor comparison**

### 当前状态
- **远端官方 repo 与独立环境已补齐；official method/evaluator 已完成 fixed subset20 sparse-feature bring-up**

### 新鲜证据
- 本地 repo 路径：
  - `/Users/xin/Research/project/3D重建/repos/conceptgraph_family/OnlineAnySeg`
- 远端 repo 路径：
  - `/home/nebula/xxy/OnlineAnySeg`
- official remote：
  - `https://github.com/yjtang249/OnlineAnySeg.git`
- 当前本地 commit：
  - `152466e318f8220bcc6838c03e340cce2f2153b8`
- 当前远端 commit：
  - `152466e318f8220bcc6838c03e340cce2f2153b8`
- README 明确包含：
  - ScanNet data prep
  - online sequence run
  - evaluation code `eval/evaluate_seqs.py`
  - AP family outputs `all_ap / all_ap_50% / all_ap_25%`
- 本轮新增归档：
  - `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.md`
  - `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/`
  - `docs/official_results/direct_baseline_bringup_20260423.md`
- 当前 fixed subset20 结果：`AP 0.061 / AP50 0.138 / AP25 0.298`，`20/20` scenes，`335 / 572` pred/GT instances。

### 为什么它优先级最高
- 它是当前最贴近 DuoGraph3D 论文故事的 **direct neighbor**
- 同时它又具备相对完整的官方评测入口
- 它有机会成为：
  - story-aligned direct baseline
  - 以及 reviewer-friendly metric bridge

### 优先级判断
- Story fit：**极高**
- Readiness：**高**
- Metric usefulness：**极高**
- Integration cost：**中高**

### 结论
> **这是第一个应优先完成的外部 direct baseline；环境与 official `main.py` subset20 路径已跑通，当前下一步是扩大 zero-shot subset 或生成完整官方 mask embeddings，避免 sparse-feature bridge 成为 reviewer 攻击点。**

---

## Lane G1 — ConceptGraphs graph-memory lane

### 角色
- **Block D graph memory / object-maintenance comparison**

### 当前状态
- **本地/远端官方 repo 已存在，DuoGraph3D ConceptGraphs-format export 已归档；`chamferdist`/`gradslam`/evaluator import 已修复，官方评分被 Replica/ScanNet 任务口径阻塞**

### 新鲜证据
- 本地 repo 路径：
  - `/Users/xin/Research/project/3D重建/repos/conceptgraph_family/concept-graphs`
- 远端 repo 路径：
  - `/home/nebula/xxy/concept-graphs`
- official remote：
  - `https://github.com/concept-graphs/concept-graphs.git`
- 当前本地 commit：
  - `93277a02bd89171f8121e84203121cf7af9ebb5d`
- 当前远端 commit：
  - `72f5962822b5e8678a446f367a06df1a977d2a4d`
- README 明确覆盖：
  - Replica RGB-D pipeline
  - object-based mapping
  - semantic evaluation on Replica
- 本轮新增归档：
  - `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.md`
  - `docs/official_results/conceptgraphs_minimal_20260423/raw/duograph3d_conceptgraphs_alignment_manifest.json`
  - `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt`

### 为什么它优先级高
- 它直接对应“graph memory 不是 post-hoc export”的 reviewer 问题
- 与论文的 object-memory identity 更匹配
- 比 ESAM 更符合本文的表示层创新点

### 优先级判断
- Story fit：**高**
- Readiness：**高**
- Metric usefulness：**中高**
- Integration cost：**中高**

### 结论
> **这是第二个应优先完成的外部 baseline lane；环境阻塞已解除，当前下一步是选择 Replica-format export + semantic roots 或 ScanNet-compatible evaluator，并修复 `cfslam_pipeline_batch` 的 `to_tensor` import drift。**

---

## Lane M1 — ConceptFusion / Open-Fusion dense-mapping lane

### 角色
- **Block A / Block D 之间的 dense/open-vocabulary mapping alternative**

### 当前状态
- **当前工作区未发现本地 clone**

### 证据
- 当前 story-aligned protocol 已把它们列为重要对手
- 但目前没有新鲜本地 repo 可直接带起

### 优先级判断
- Story fit：**高**
- Readiness：**低**
- Metric usefulness：**高**
- Integration cost：**高**

### 结论
> **科学上重要，但不应先于 OnlineAnySeg / ConceptGraphs 占用主线资源。**

---

## Lane S0 — ESAM / EmbodiedSAM compatibility lane

### 角色
- **Block E auxiliary benchmark-compatibility reference**

### 当前状态
- **已有资产，但不应再作为主线 baseline lane 推进**

### 证据
- 已有 local normalized summaries：`docs/baselines/generated/esam_*`
- 当前 manuscript 与 protocol 已纠正为 auxiliary-only

### 优先级判断
- Story fit：**低到中**
- Readiness：**高**
- Metric usefulness：**中**
- Integration cost：**低**

### 结论
> **冻结为辅助线，不再作为下一步主执行目标。**

---

## 4. 最终优先级排序

## P0 — 立即保留并继续利用
1. **DEVA temporal lane**
2. **内部 temporal ablation（no-temporal / naive / DEVA-style）**
3. **内部 structure / memory rivals**

### 原因
这些 lane 已经 ready，而且直接支撑核心创新点。

---

## P1 — 第一个应优先 bring-up 的外部 baseline
1. **OnlineAnySeg**

### 这是当前最关键的一条线
因为它同时满足：
- 直接任务邻近
- online
- zero-shot
- object-centric 3D
- 有官方 evaluation code

### P1 的最小交付物
- repo health audit
- dataset contract audit（ScanNet）
- minimal runnable scene / subset
- official eval command note
- in-repo normalized lane summary
- 与 DuoGraph3D 的 first comparison sketch

---

## P2 — 第二个应优先 bring-up 的外部 baseline
1. **ConceptGraphs**

### 原因
- 它最适合支撑 graph-memory / object-maintenance 这一创新点
- 与论文 identity 更匹配
- 本地已存在官方 repo

### P2 的最小交付物
- repo health audit
- Replica contract audit
- first runnable mapping/eval note
- normalized lane summary
- graph-memory comparison note

---

## P3 — 第三个外部扩展方向
1. **ConceptFusion 或 Open-Fusion（二选一）**

### 原因
- 需要有一个 dense/open-vocab mapping alternative
- 但当前没有 ready repo，因此排在 OnlineAnySeg / ConceptGraphs 之后

### P3 触发条件
- P1 与 P2 至少有一条完成 runnable lane
- 主线资源允许再扩 baseline 家族

---

## P4 — 明确不抢主线资源
1. **ESAM / EmbodiedSAM**

### 说明
- 继续保留现有资产
- 仅用于 auxiliary compatibility / supplementary reference
- 不再作为 primary direct-neighbor bring-up 目标

---

## 5. 可执行推进顺序

## Sprint 1 — 先做真正对口且 runnable 的两条线

### Sprint 1A
**OnlineAnySeg bring-up**

#### 任务
1. 审计 repo、依赖、数据约定、评测入口
2. 确定 ScanNet 上最小 runnable subset
3. 跑通至少一个最小 scene 或 subset
4. 写入 normalized lane summary

#### 退出条件
- 有 official command note
- 有 fixed subset20 runnable evidence（已完成）
- 有 evaluation output schema 记录
- 下一阶段有更大 zero-shot subset 或完整 official mask embeddings

### Sprint 1B
**DEVA temporal lane 固化**

#### 任务
1. 继续补 temporal block 的直接表格定义
2. 固定 Replica / ScanNet subset 上 temporal comparison protocol
3. 让 DEVA 成为最终 paper temporal block 的稳定 reference

#### 退出条件
- temporal block 的 dataset / metric / protocol 冻结
- DEVA 不再只是 artifact inventory，而是真正 paper-ready comparison lane

---

## Sprint 2 — 补 graph-memory 对口 lane

### Sprint 2A
**ConceptGraphs bring-up**

#### 任务
1. 审计 ConceptGraphs 的 Replica pipeline 与 eval surfaces
2. 选择最贴合 DuoGraph3D 的 comparison surface
3. 形成 graph-memory comparison note

#### 退出条件
- 有 normalized lane
- 有至少一张能支撑 graph/object-memory claim 的 comparison surface

---

## Sprint 3 — 再决定要不要扩 dense mapping family

### Sprint 3A
**ConceptFusion / Open-Fusion acquisition**

#### 任务
1. 确定只选一个代表方法
2. 获取 repo / data / eval contract
3. 判断它是 runnable lane 还是 literature-position-only lane

#### 退出条件
- 明确 go / no-go
- 若 go，则形成 baseline acquisition note

---

## 6. 每条 lane 的验收模板

每个 baseline lane 完成时，至少要有：

1. repo path / remote / commit
2. dataset contract
3. command path
4. output artifact path
5. evaluation summary
6. provenance caveat
7. role in paper story
8. does it answer which reviewer question

---

## 7. 当前建议的第一步

### 立刻执行顺序
1. **先 bring up OnlineAnySeg**
2. **同时固定 DEVA temporal block**
3. **然后 bring up ConceptGraphs**
4. **ESAM 保持冻结为 auxiliary**

### 一句话总结
> **下一步不是继续追一个更漂亮的 AP 表，而是先把最贴合论文创新点、且已经具备现实可执行性的 baseline lane 真正跑起来。**


相关输出对齐文档：
- `docs/alignment_output_protocol.md`
