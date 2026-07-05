# DuoGraph3D 分阶段重构计划 —— 基于代码实际的评估与修订

## 总体判断

优化计划对系统弱点的诊断（majority-label collapse、candidate missing、duplicate birth、greedy merge、export-memory 解耦不足）是准确的，提出的状态空间拆解方向（admission/bridge → signed Layer1 → tentative/promotion → equivalence partition → carrier）也是合理的。但计划存在三个关键偏差：

1. **低估了当前代码已经实现的机制**（部分"新设计"与现有实现差异较小）
2. **高估了核心库的职责边界**（admission、quant_key、memory-dense export 不在核心库内）
3. **时间线和资源估计在 full-val 尺度上偏乐观**

以下逐项对照代码实际进行分析。

## 一、代码架构现状（与计划假设的差异）

### 1.1 核心库 vs 实验脚本的分界

计划将 DuoGraph3D 描述为从 Observation→EvidenceBuilder→Layer1→Layer2→Memory→Export 的完整链路，但实际代码存在清晰的分界：

- **核心库** (`src/duograph3d/`)：通用的 object-centric 3D 图构建框架。`PipelineConfig` 260+ 参数驱动全部行为。`FrameInput` → `EvidenceBuilder.build()` → `Layer1.repair()` → `Layer2.update()` → `SequenceRunResult`。
- **实验脚本** (`examples/run_conceptgraphs_engineered_parity.py`)：包含 GSA 检测加载、`mask_subtract_contained()`、`quant_key()`（0.2m class-agnostic 量化）、depth validation、memory-dense label split、ConceptGraphs-style postprocess、official semantic eval。

**这意味着**: admission（主通道 + bridge 通道）、`quant_key()` 的修改、carrier/label-bucket export 的大部分逻辑，需要同时修改实验脚本和核心库。计划中 "在 `contracts.py` 中新增统一 schema" 的思路是正确的，但不能忽略 `run_conceptgraphs_engineered_parity.py` 中 ~600 行的 admission→payload→export 逻辑。

### 1.2 当前已实现的机制（计划可能低估的部分）

**Candidate retrieval 已有 5 条隐式通道** (`memory.py:59-152`):
```
1. history_object_ids (exact match by ID)
2. exact_geometry_key (same voxel cell)
3. recent (by status recency)
4. spatial scoring (bbox overlap + centroid distance)
5. point_overlap scoring (nearest-neighbour within history_point_overlap_distance)
```
此外还有 per-dimension bucket ranking（spatial/point_overlap/visual/semantic/recency 各取 top-channel_budget）。计划提出的 6-path（history + exact-key + adj-key + dormant + overlap + ANN）中，`adj-key` 和 `ANN` 是真正缺失的，其他 4 个已有不同程度的实现。

**Semantic conflict guard 已较完善** (`memory.py:783-844`):
- dominant_label_conflict: 不同 top label + semantic_score < min
- mixed_root_conflict: merged entropy > max + top_share < min
- protected_small_label_conflict: 小 label 节点被 merge 的保护
- visual_override: 高 visual score 可以 override semantic conflict

**Point-overlap identity gate 已收紧** (`layer2.py:246-298`):
- 需要 spatial_ok + semantic_or_visual_ok
- 与 geometry_key match 的解耦已经实现
- residual absorption 有独立的多重门控 (`layer2.py:352-432`)

**Relation bonus** (`layer2.py:506-519`): 已在 Layer2 scoring 中使用 co-visibility relation edges，计划中未提及但实际已存在。

### 1.3 当前明确缺失的机制（计划正确指出的）

| 缺失机制 | 当前状态 | 影响 |
|---|---|---|
| Bridge admission | 无。只有主通道硬过滤 | room0 recall 受限的直接原因之一 |
| Signed Layer1 (negative edges) | 无。只有正边连通分量 | 异类近邻物体在同 voxel 内可能被误合并 |
| Label distribution 保留 | `_merge_payloads()` 只保留 majority label (`layer1.py:197`) | 不可逆信息损失，影响 downstream semantic guard |
| Tentative fragment + promotion gate | 无。unmatched→direct birth | duplicate birth 的主因 |
| Working/stable memory 分离 | 无。所有 write 等效 | 低置信 write 污染 memory prototype |
| adj-key / ANN retrieval | 无 | candidate missing 的直接原因 |
| Equivalence partition (global) | pairwise greedy merge | canonical ID switch after merge |
| Carrier oracle gap 监控 | 无 | 无法诊断 export vs online memory 的贡献 |
| Per-channel candidate source tracking | 无 | 无法判断哪个通道贡献了 recall |
| Deterministic replay | 无显式支持 | 实验不可复现 |

## 二、逐阶段评估

### 阶段甲：基线冻结、回放与指标契约

**合理性**: ⭐⭐⭐⭐⭐ (非常必要且可行)

**代码实际**:
- `pipeline.py:20-101` 的 `run_sequence()` 已经是纯函数式的（输入→输出，无全局状态），但不保证确定性排序（`memory.candidate_nodes()` 中的 `sorted()` 在多对象同分时不确定；`layer2._score()` 的 scoring 在 tie 时不保证稳定）。
- `EventLogger` (`events.py:22-60`) 已有结构化事件日志，但缺少统一的 schema 导出（parquet/jsonl）。
- 当前没有 `candidate_metrics.py`、`memory_purity.py`、`carrier_gap.py`。

**修订建议**:
```python
# 核心改动点1: 在 contracts.py 增加统一的实验元数据
@dataclass
class ExperimentRunMetadata:
    run_id: str
    branch_id: str
    scene_id: str
    config_snapshot: dict[str, object]
    seed: int
    timestamp: str
    git_commit: str

# 核心改动点2: 在 pipeline.py 增加确定性模式
class DuoGraph3DPipeline:
    def run_sequence(self, ..., seed: int | None = None) -> ...:
        if seed is not None:
            random.seed(seed)  # 影响 memory.consolidate_objects 等
```

**时间评估**: 计划估计 1-2 天工程 + 4-8 小时机器，相对合理。如果 `run_conceptgraphs_engineered_parity.py` 也需要同步重构日志，增加 1 天。

**关键风险**: 实验脚本中的 GSA 加载依赖预计算文件路径，replay 需要确保路径一致性。

### 阶段乙：signed Layer1 与 candidate retrieval 重构

**合理性**: ⭐⭐⭐⭐ (方向正确，但 signed graph 的收益可能被高估)

**代码实际与修订**:

当前 `layer1.py:276-371` 的 `repair()` 方法：
```python
# 现状: 纯正边连通分量
adjacency: dict[int, set[int]] = {index: {index} for index in range(len(evidence_items))}
for left_index, right_index in self._candidate_pair_indices(evidence_items):
    score, reasons = self._edge_score(...)
    if score >= self.config.layer1_merge_threshold:  # 0.9
        adjacency[left_index].add(right_index)
        adjacency[right_index].add(left_index)
# → BFS/DFS 找连通分量
```

修订建议——最小侵入式改动：

```python
# Step 1: 在 contracts.py 给 CurrentObjectHypothesis 增加:
label_distribution: dict[str, float] = field(default_factory=dict)
label_buckets: dict[str, tuple[tuple, ...]] = field(default_factory=dict)

# Step 2: 在 layer1.py 增加负边计算（不改变现有正边逻辑）:
def _negative_edge_score(self, left, right) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []
    # 3D 分离 (基于 bbox/centroid)
    sep_score = self._spatial_separation_score(left, right)  # 新增
    if sep_score > 0:
        score += 0.45 * sep_score
        reasons.append("spatial_separation")
    # 语义冲突 (基于 label distribution 的 JSD)
    if hasattr(left, 'label_distribution') and hasattr(right, 'label_distribution'):
        jsd = self._jsd(left.label_distribution, right.label_distribution)  # 新增
        if jsd > 0.45:
            score += 0.35
            reasons.append("semantic_divergence")
    return score, reasons

# Step 3: 在 _merge_payloads() 保留 label distribution:
# 改 label = label_counts.most_common(1)[0][0]  为:
total = sum(label_counts.values())
label_distribution = {label: count/total for label, count in label_counts.items()}
```

**关键观察**: 当前系统中 `repair_group_id`、`continuity_key`、`geometry_key` 三者在 example runner 中强相关（都源自 `quant_key()`），所以正边已经很强，负边的额外收益主要来自**不同 repair_group 但被误放在同一连通分量的情况**。这类情况在 room0 等大场景中确实存在，但数量有限。

Candidate retrieval v2 的修订建议：

```python
# memory.py 中新增:
def candidate_nodes_v2(self, geometry_key, budget, ...):
    # 新增 adj-key 通道: 枚举相邻 voxel cells
    adj_keys = self._adjacent_geometry_keys(geometry_key, radius=1)  # 3×3×3-1=26 neighbors
    for adj_key in adj_keys:
        for node in self._geometry_index.get(adj_key, []):
            add(node)
    
    # 新增 ANN 通道: 对 stable/working feature 做最近邻
    # 注意: 这需要维护一个 feature index (FAISS 或简单的 numpy 暴力搜索)
    ann_candidates = self._ann_search(hypothesis.clip_feature, top_k=8)
    for node in ann_candidates:
        add(node)
    
    # 记录每个候选的来源通道 (用于监控)
    for node in selected.values():
        node._candidate_source = ...  # "history" | "exact_key" | "adj_key" | ...
```

**时间评估**: 计划估计 3-5 天工程 + 6-12 小时/dev 轮。考虑需要同时修改 experiment script（`quant_key()` 逻辑可能需要微调），建议 5-7 天工程。

**关键风险**: 
1. adj-key 在 0.2m voxel 下会产生 26 个相邻 cell，可能显著增加候选数量。需要先在 shadow 模式下测量 `adj-key` 的 recall 贡献再决定是否默认开启。
2. ANN 需要额外依赖 (FAISS/numpy)，与项目 "standard-library-only" 的约束冲突。建议先用 brute-force numpy（candidate pool < 200 时可行）。

### 阶段丙：tentative、promotion、working/stable memory

**合理性**: ⭐⭐⭐⭐⭐ (计划中最关键、收益最确定的阶段)

**代码实际**:

当前 `layer2.py:639-782` 的 birth 路径：
```python
# 现状: unmatched hypothesis → 直接创建 MemoryObjectNode 进入 nodes dict
node = memory.create_node(descriptor=..., geometry_key=..., step_id=step_id)
node.register_support(...)
self._update_node_support(node, hypothesis)
memory.fuse_hypothesis(node, hypothesis, step_id=step_id)
# → 这个 node 立即成为 confirmed memory，参与后续所有匹配
```

修订建议——在 `contracts.py` 和 `layer2.py` 中做最小侵入改动：

```python
# contracts.py 新增:
class FragmentStatus(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    RETIRED = "retired"

@dataclass  
class TentativeFragment:
    fragment_id: str
    birth_step: int
    hits: int = 1
    hypotheses: list[dict] = field(default_factory=list)
    # promotion 所需信号
    self_consistency: float = 0.0
    geometry_consistency: float = 0.0
    conflict_count: int = 0

# layer2.py 中修改 birth 路径:
def _handle_unmatched(self, hypothesis, memory, ...):
    # 旧: memory.create_node(...)  # direct birth → confirmed
    # 新:
    fragment = TentativeFragment(
        fragment_id=f"tent-{self._next_tentative_id}",
        birth_step=step_id,
        hits=1,
    )
    memory.tentative_fragments[fragment.fragment_id] = fragment
    
    # promotion gate (在每帧 update 末尾评估):
    for frag in memory.tentative_fragments.values():
        if self._promotion_gate(frag):
            node = memory.promote_to_confirmed(frag)
            # 此时才进入 memory.nodes

# memory.py 中:
def promote_to_confirmed(self, fragment: TentativeFragment) -> MemoryObjectNode:
    node = self.create_node(...)
    # 将 fragment 的累积信息写入 node
    del self.tentative_fragments[fragment.fragment_id]
    return node
```

**working/stable memory 的关键设计决策**:

当前 `fuse_hypothesis()` (`memory.py:703-745`) 已经实现了 weighted blend（`previous_count` + `current_count` 加权），这实际上就是一种 "working memory"。真正需要增加的是一种**不更新 stable prototype 的 write**：

```python
# 两种 write 路径:
# 1. Working write (总是执行): 更新 detection_count, class_counts, points, bbox
#    等同于当前的 fuse_hypothesis()
# 2. Stable write (仅在高置信时): 更新 clip_feature, text_feature (prototype EMA)
#    当前 fuse_hypothesis() 中:
#    node.clip_feature = self._blend_feature(node.clip_feature, current_clip, 
#                                            previous_count, current_count, normalize=True)
#    改为:
#    if stable_write_gate(margin, conflict_rate):
#        node.clip_feature = self._blend_feature(node.clip_feature, current_clip,
#                                                previous_count, current_count, normalize=True)
#        # EMA with lower learning rate for stable
#        node.stable_clip_feature = self._blend_feature(node.stable_clip_feature, current_clip,
#                                                        weight_stable=19, weight_current=1, normalize=True)
```

**时间评估**: 计划估计 4-6 天工程 + 8-16 小时/dev。合理。但 promotion gate 的阈值调参可能需要额外的 shadow 实验周期。

**关键风险**: 
1. promotion 太慢 → recall 下降（tentative fragment 不参与 candidate retrieval，进一步加重 candidate missing）
2. 建议: tentative fragment 也应该参与 candidate retrieval（以 lower priority），这样 promotion 慢只是推迟了 identity 确认，不会导致 duplicate birth

### 阶段丁：equivalence partition 取代 greedy object merge

**合理性**: ⭐⭐⭐ (理论上正确，但工程风险和收益比不如前三个阶段)

**代码实际**: `memory.py:940-966` 的 `merge_duplicate_objects()` 是 O(n²) pairwise greedy：

```python
for left_index, left in enumerate(active_nodes):
    for right in active_nodes[left_index + 1:]:
        score, components = self.object_affinity(left, right)
        if score < self.config.object_merge_threshold:  # 0.88
            continue
        if components["spatial"] < self.config.object_merge_spatial_threshold:  # 0.15
            continue
        if components.get("semantic_conflict"):
            continue
        self.merge_nodes(left, right)
```

**修订建议**: 分两步走，而不是一步跳到 full multicut：

```python
# Step 1 (低风险): 将 pairwise 改为 scored-edge + union-find with conflict pruning
# Step 2 (仅在 Step 1 成功后): 小组件上 exact multicut

def merge_duplicate_objects_v2(self) -> list[dict]:
    # 1. 生成 scored edges (复用现有 object_affinity)
    edges = []
    for i, left in enumerate(active):
        for j, right in enumerate(active):
            if j <= i: continue
            score, components = self.object_affinity(left, right)
            edges.append((i, j, score, components))
    
    # 2. 构造 signed graph
    pos_edges = [(i,j,s) for i,j,s,c in edges if s >= 0.95 and not c.get("semantic_conflict")]
    neg_edges = [(i,j,s) for i,j,s,c in edges if s <= 0.05]
    
    # 3. Union-find on positive edges, respecting negative constraints
    parent = list(range(n))
    for i, j, _ in pos_edges:
        # union if no negative edge between the two components
        if not any_conflict(parent, i, j, neg_edges):
            union(parent, i, j)
    
    # 4. 仅在小组件 (|V| <= 20) 上尝试 exact multicut
    # 当前 Replica room0 的 active nodes 约 50-200，全图 multicut 不可行
```

**时间评估**: 计划估计 5-7 天 + 10-20 小时/dev。对于 Step 1 来说偏长（3-4 天足够），对于 full multicut 来说偏短。

**关键风险**:
1. 当前 O(n²) 在 n=200 时仅 40K 对比较，尚可接受。图 partition 的 overhead 可能比 pairwise 更大。
2. 这是唯一可能出现 "做了但收益不明显" 的阶段。当前的 semantic conflict guard + pairwise greedy 已经相对保守。

### 阶段戊：carrier selection、export policy 与 official eval 闭环

**合理性**: ⭐⭐⭐⭐ (对 room0 问题至关重要，但依赖前序阶段)

**代码实际**:

当前 `export_policy.py:34-88` 的 `choose_export_source()` 只能选择 `geometry`/`memory`/`memory-dense`/`auto` 四种策略。`auto` 模式用简单的 coverage 门限检查。

真正的 memory-dense export 逻辑在 `run_conceptgraphs_engineered_parity.py` 中（~200 行），包括：
- Memory root 控制 identity
- Dense geometry key 控制几何
- Label bucket split（`MEMORY_DENSE_SPLIT_BY_LABEL`）
- Root label entropy/entropy split 条件

**修订建议**: 将 export 逻辑从实验脚本提升到核心库：

```python
# 新增 export_policy.py 中的 CarrierCandidate:
@dataclass
class CarrierCandidate:
    carrier_id: str
    carrier_type: str  # "memory" | "memory-dense" | "label-bucket" | "geometry-fallback"
    entity_id: str
    points: tuple[...]
    label: str
    coverage_score: float
    purity_score: float
    semantic_confidence: float
    geometry_quality: float
    duplicate_risk: float

def build_carrier_candidates(entity, memory, config) -> list[CarrierCandidate]: ...
def select_primary_carrier(entity, carriers, config) -> CarrierCandidate: ...
def oracle_gap(entity, carriers, gt) -> float: ...
```

**时间评估**: 计划估计 3-5 天 + 6-12 小时/dev。考虑到需要从实验脚本中提取和重构 ~200 行逻辑，建议 5-7 天。

## 三、关键遗漏与补充建议

### 3.1 计划未覆盖但代码已暴露的问题

1. **`quant_key()` 的 class-agnostic 设计代价**: 当前 `geometry_key = (scene, gsa, item, floor(centroid/0.2))` 在有语义冲突的相邻物体间会产生碰撞。Signed Layer1 可以缓解，但不能根除。应该考虑是否在某些场景下恢复 class-aware key（至少在 bridge admission 中使用）。

2. **`mask_subtract_contained()` 的顺序效应**: 当前在 example runner 中是 `filter_then_subtract`（先过滤低质量 mask，再 subtract contained）。ConceptGraphs 原文可能是其他顺序。这会影响哪些 observation 进入 pipeline。

3. **DEVA-style propagation 的 identity 风险**: `evidence.py:40-88` 的 DEVA propagation 为 propagated evidence 创建 `affinity=1.0` 的 history candidate，这可能导致在没有真实 observation 的情况下强制关联。当前 `propagation_keepalive_misses=2` 限制了传播时长，但如果 miss_count 跟踪不准（比如 absorb 重置了 miss_count），传播可能过度。

4. **`descriptor_fused` 的 class-agnostic 约束**: `memory.py:277-283` 明确注释 "Do not rewrite descriptor_fused with a semantic class label"，但 `fuse_hypothesis()` 中 `node.descriptor_recent = hypothesis.descriptor` (line 708) 可能会在 hypothesis.descriptor 是语义 label 时引入不一致。

### 3.2 建议增加的阶段间依赖验证

```python
# 在每阶段完成后运行的自动化检查:
def validate_phase_transition(prev_results, new_results):
    checks = {
        "memory_node_count_no_explosion": 
            len(new_results.memory_nodes) <= len(prev_results.memory_nodes) * 1.5,
        "birth_count_no_spike":
            new_results.birth_count >= prev_results.birth_count * 0.8,  # 不能因 promotion 太慢而翻倍
        "candidate_recall_no_regression":
            new_results.cr_raw >= prev_results.cr_raw - 0.02,
        "export_consistency":
            new_results.exported_label_map.overlap(prev_results) >= 0.90,
    }
```

### 3.3 实验脚本同步重构的必要性

计划聚焦于核心库的重构，但以下实验脚本改动也必须同步进行：

| 核心库改动 | 实验脚本对应改动 |
|---|---|
| 新增 `label_distribution` in `CurrentObjectHypothesis` | `object_payload_from_arrays()` 需要传递 label distribution |
| Signed Layer1 的 cannot-link | 可能需要在 `quant_key()` 中保留更多区分信息 |
| Candidate v2 (adj-key, ANN) | 无直接改动，但需要新的监控输出 |
| Tentative fragment | 不影响 admission |
| Carrier selection | 需要将 memory-dense export 逻辑从 experiment script 迁移到核心库的 `export_policy.py` |

## 四、修订后的优先级与时间线

### 建议的四阶段（合并丁、戊）

| 阶段 | 内容 | 工程时间 | 机器时间/dev轮 | 优先级 |
|---|---|---|---|---|
| 甲 | 基线冻结、replay、指标契约 | 2-3 天 | 6-12h | P0 |
| 乙 | Signed Layer1 + label distribution + candidate v2 | 5-7 天 | 8-16h | P0 |
| 丙 | Tentative + promotion + working/stable memory | 5-7 天 | 10-20h | P0 |
| 丁 | 简化版 partition (UF+conflict) + carrier selection | 5-7 天 | 8-16h | P1 |

总工程时间: 17-24 天 (vs 原计划的 18-25 天)，但通过合并减少了不必要的 full multicut 探索。

### 推荐的启动顺序

```
Week 1-2:   Phase 甲 (baseline freeze)
Week 2-4:   Phase 乙 (signed Layer1 + candidate v2)
            └── 在此期间并行跑 Phase 甲 full-val
Week 4-6:   Phase 丙 (tentative/promotion/stable)
            └── 在此期间并行跑 Phase 乙 full-val  
Week 6-8:   Phase 丁 (simplified partition + carrier)
```

### 关键决策点

1. **Week 2 末**: 如果 `CR_raw` 提升 < 3pp，暂停乙阶段，先排查 candidate source 分布
2. **Week 4 末**: 如果 `DBR_confirmed` 下降 < 20%，调整 promotion gate 阈值再跑一轮
3. **Week 6 末**: 如果 carrier oracle gap < 0.03 但 official mIoU 未改善，结论为 "online memory 已改善但 export-postprocess 链路有其他瓶颈"

## 五、计划中数学建模的准确性校验

### 5.1 Layer1 正边分数公式

计划给出的公式:
```
s_1(i,j) = 0.75·1[r_i=r_j] + 0.70·1[c_i=c_j] + 0.35·1[a_i=a_j] 
         + 0.20·1[d_i=d_j] + 0.45·1[g_i=g_j] + φ_geo(i,j) + 0.45·ρ_hist(i,j)
```

实际代码 (`layer1.py:61-98`):
```python
score = 0.0
if repair_group_id match:  score += 0.75   # ✅
if continuity_key match:   score += 0.70   # ✅
if appearance_key match:   score += 0.35   # ✅
if descriptor match:       score += 0.20   # ✅
if geometry_key match:     score += 0.45   # ✅
+ geometry_profile_consistency             # φ_geo (max 0.35) ✅ 但实际是独立计算
+ shared_history_boost                     # 0.45 * max_shared_affinity ✅
```

公式基本准确。唯一差异: `φ_geo` 的上限实际是 0.35（`layer1.py:122`），计划未说明。

### 5.2 Layer2 关联阈值

计划: `τ_assoc = 1.7`，实际: `association_threshold = 1.7` ✅

计划描述的正向关联条件 `s_2(h,m*) >= 1.7 ∧ I_id(h,m*) = 1` 与实际代码一致 (`layer2.py:569-573`)。

### 5.3 memory merge 分数

计划: `s_merge = 0.50·s_spatial + 0.25·s_visual + 0.20·s_semantic + 0.05·s_size + w_po·s_point-overlap`

实际代码 (`memory.py:887`):
```python
base_score = round(0.50 * spatial_score + 0.25 * visual_score 
                 + 0.20 * semantic_score + 0.05 * size_score, 4)
score = round(min(base_score + point_overlap_weight * point_overlap_score, 1.0), 4)
```
`point_overlap_weight = 0.12` ✅ 完全一致。

### 5.4 majority-label collapse

计划的分析完全准确。`_merge_payloads()` (`layer1.py:196-197`):
```python
label_counts = Counter(payload.label for payload in payloads if payload.label)
label = label_counts.most_common(1)[0][0] if label_counts else ""
```

完整 label 分布被压缩为 single delta label。信息损失 = `H(q_h)`。这是整个链路上最确定的信息瓶颈。

## 六、总结

**计划的核心判断是正确的**: 当前系统的主要瓶颈不是 "scorer 不够强"，而是 (1) 候选召回不完整、(2) Layer1 信息坍缩、(3) birth 机制缺少 tentative/promotion、(4) merge 缺少全局一致性、(5) export 与 memory 耦合不足。提出的五阶段结构也是合理的。

**但以下修订是必要的**:
1. 承认 admission 和 export 逻辑在实验脚本中，需要同步重构
2. 承认当前 candidate retrieval 已有 4/6 的隐式通道，真正缺失的是 adj-key 和 ANN
3. 承认 semantic conflict guard 和 point-overlap identity gate 已相对完善
4. Phase 丁的 full multicut 应该降级为 union-find + conflict pruning
5. Phase 丙是最关键且收益最确定的阶段，应该给予最多时间
6. 每阶段必须先在 shadow 模式下跑通全部监控指标，再进行 subset 和 full-val

**最重要的实施建议**（与计划一致但更具体）: 
> Phase 甲-丙（replay/metrics → signed Layer1 + candidate → tentative/promotion）三件事做好之前，不要在 learned edge 或 full multicut 上花时间。Phase 甲最关键的第一步是让 `run_conceptgraphs_engineered_parity.py` 的行为在 `seed=0` 下完全可复现——否则所有后续的 ablation 结论都不可信。
