# DuoGraph3D 投稿消融实验设计（负责人审阅版，2026-06-27）

## 0. 目标与结论

本消融包服务于当前投稿主线：

> DuoGraph3D 的核心不是简单把 2D mask 融到 3D，也不是单纯 two-layer graph，而是 **geometry-reliable object graph memory**：用几何载体作为稳定对象/导出基础，用两层图记忆维护在线对象状态，并用 object-level diagnostics 发现和约束语义读出的失真。

消融实验不再扩成大而散的超参表，而压缩成 **三组 reviewer-facing ablations**：

1. **A1：Geometry-first carrier reliability 是否带来主收益？**  
   证明 E70 的提升来自几何可靠性与 carrier-level repair，而不是普通调参。
2. **A2：Two-layer graph memory 是否仍然必要？**  
   证明 Layer1 当前证据修复、Layer2 记忆关联、memory/export 分离不是装饰性模块。
3. **A3：统一 carrier reliability 是否能替代 scene-local patch？**  
   直接处理最大投稿风险：E70 是否只是针对 Replica 场景手工调规则。

除三组消融外，论文需要一张 **diagnostic analysis table** 支撑第三创新点，但该表不作为第四组消融，避免实验部分发散。

---

## 1. 固定协议

### 1.1 数据与 baseline

- Dataset：Replica full scenes  
  `room0, room1, room2, office0, office1, office2, office3, office4`
- Baseline：ConceptGraphs official Replica baseline  
  `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/replica_ex6_results.csv`
- 主结果：E70  
  `/home/nebula/xxy/duograph3d_artifacts/e70_best_composite_office2_bin_vent_table_20260626/final_eval`

### 1.2 统一指标

主表指标：

- `mIoU ↑`
- `mF1 ↑`
- `F-mIoU ↑`
- `ΔmIoU / ΔmF1 / ΔF-mIoU` vs ConceptGraphs

消融诊断指标：

- per-scene gap；
- per-class gap；
- target class precision / recall；
- relabel object count / relabel point count；
- exported object count；
- export source；
- carrier label entropy；
- high-margin CLIP coverage；
- object bbox extent；
- L1 mixed-label mass；
- Layer2 candidate recall@budget；
- duplicate birth / fragmentation；
- memory-object vs geometry-key coverage ratio。

### 1.3 Full model row

Full model 使用 E70：

| split | ΔmIoU | ΔmF1 | ΔF-mIoU |
| --- | ---: | ---: | ---: |
| all | **+3.041** | **+4.927** | **+8.460** |

该 row 是所有消融表的 anchor。

---

## 2. Ablation A1 — Geometry-first carrier reliability

### Target hypothesis

E70 的主要提升来自 **几何载体可靠性约束**，尤其是大几何 carrier 被小物体/fixture/sink label 错读时，使用几何尺度、邻接和 carrier-level 规则修复最终语义导出；不是来自普通 CLIP readout 或无约束 label forcing。

### 实验行设计

建议主文 Table A：`Effect of geometry-reliable carrier readout`

| Row | Variant | 目的 | 已有/待跑 | 关键对照 |
| --- | --- | --- | --- | --- |
| A1-0 | ConceptGraphs | baseline | 已有 | 外部 baseline |
| A1-1 | DuoGraph3D full / E70 | full model | 已有 | 主结果 |
| A1-2 | w/o large-label geometry relabel | 移除 `tissue-paper:cloth`, `bin:table`, `vent:table` | 待跑/可用 E63 近似，但论文应重跑统一 row | 检查几何语义修复总体贡献 |
| A1-3 | w/o office2 table-sink repair | 移除 `bin:table`, `vent:table`，保留其它设置 | 待跑/可用 E63/E49 近似 | 检查 office2 主因 |
| A1-4 | `bin:table` only | 保留 `bin:table`，移除 `vent:table` | 已有 E68 / E66 局部证据 | 分离 bin/table 和 vent/table |
| A1-5 | semantic-only adaptive CLIP | 只用 adaptive/high-margin CLIP，不做 geometry repair | 已有 E47/E48 局部证据，建议补 office1/office2 targeted row | 证明读出调参不是主因 |

### Expected signal

确认假设的信号：

1. Full E70 明显优于 A1-2/A1-3；
2. office2 中 `bin` precision、`table` IoU、`F-mIoU` 在加入 `bin:table` 后明显改善；
3. `vent:table` 只带来小幅附加提升，不应成为主贡献；
4. semantic-only adaptive CLIP 不能复现 E70 的 all-scene gain；
5. relabel monitor 显示实际修改对象数很少，但目标 class precision/IoU 改善显著，说明不是粗暴大面积改标签。

削弱假设的信号：

- 移除 geometry relabel 后 all-scene 几乎不变；
- semantic-only row 接近或超过 E70；
- relabel object/point count 很大，导致方法看起来像标签重写而非 carrier reliability。

### Stop condition

停止并进入写作的条件：

- A1 至少有 full E70、w/o geometry relabel、w/o office2 table-sink、`bin:table` only 四个可比 row；
- 每个 row 都输出 official gap CSV、per-class gap CSV、geometry repair monitor；
- 若某个 removal row 已由旧 artifact 近似支持，仍建议用同一代码版本重跑一次，避免审稿复现风险。

### 论文中要写出的结论

> Geometry-aware carrier repair explains the largest semantic-gain jump: the key failure is not missing evidence, but large stable geometry carriers receiving unreliable sink labels. Carrier-level geometry gates correct this failure with small localized changes, while semantic-only readout changes are insufficient.

---

## 3. Ablation A2 — Two-layer graph memory and export/source separation

### Target hypothesis

Two-layer graph memory 的价值不是直接替代所有几何导出，而是把 **当前证据修复** 与 **长期对象记忆关联** 分开，使在线状态可诊断、可维护，并为 carrier choice/export policy 提供依据。没有这个结构时，系统更容易出现 duplicate birth、wrong association、memory coverage 不足或 object identity drift。

### 实验行设计

建议主文 Table B：`Effect of two-layer graph memory components`

| Row | Variant | 模块含义 | 指标重点 | 已有/待跑 |
| --- | --- | --- | --- | --- |
| A2-0 | baseline phase | 无 beta/cand/l1 增强 | official + diagnostics | 可重跑 |
| A2-1 | `cand` | 只开 candidate retrieval v2 | candidate recall@budget、wrong-object vs missing | 可重跑 |
| A2-2 | `l1` | 只开 signed Layer1 + label distribution | L1 mixed-label mass、fragmentation | 可重跑 |
| A2-3 | `beta` / full graph memory backbone | L1 + candidate retrieval | duplicate birth、memory purity、official gap | 当前多数强结果基于此类路径 |
| A2-4 | forced geometry export | memory 不参与 final source | official semantic map upper/lower boundary | 可重跑/部分已有 |
| A2-5 | forced memory-dense export | 测试 memory as dense source 是否稳定 | memory coverage、scene regressions | 已有历史证据，建议抽代表场景 |

### Expected signal

确认假设的信号：

1. `cand` 主要改善 candidate recall / 降低 candidate-missing；
2. `l1` 主要降低 mixed-label mass 或减少错误合并；
3. `beta` 在 identity/diagnostic 指标上优于 baseline/cand/l1 单独版本；
4. forced memory-dense 在部分场景提升但不稳定，说明必须保留 export/source separation；
5. forced geometry 在 semantic mIoU 上稳定，但缺少 online memory 的 identity evidence，说明 graph memory 是状态层而非单纯导出层。

削弱假设的信号：

- phase rows 在 diagnostics 和 official metrics 上完全无差异；
- memory/export diagnostics 不能解释任何 full model 决策；
- memory-dense 始终优于 geometry 且没有风险，那当前 export separation 的论证会变弱。

### Stop condition

停止并进入写作的条件：

- 先在 `room0, office1, office2, office3, office4` 五个代表场景跑 A2 rows；
- 若趋势清晰，只把 full-scene A2 table 放 supplement，主文使用 compact diagnostic table；
- 如果 phase rows 对 official semantic 指标影响很小，主文不要硬说 two-layer graph 是 mIoU 主因，而应诚实表述为 memory/state/diagnostic contribution。

### 论文中要写出的结论

> The two-layer graph is a decision-state and diagnostic structure. It improves association observability and stabilizes carrier/source decisions, while final semantic accuracy still depends on choosing geometry-reliable carriers for dense export.

---

## 4. Ablation A3 — Unified carrier reliability vs scene-local patch

### Target hypothesis

当前最大投稿风险是 E70 的 composite / scene-local policy。A3 要验证：能否把 E70 中的有效规则抽象为 **统一 carrier reliability gate**，在所有 Replica scenes 上共享，而不是按 scene name 手工开关。

### 实验行设计

建议主文或 supplement Table C：`Generality and boundary of carrier reliability`

| Row | Variant | 目的 | 已有/待跑 | 结论用途 |
| --- | --- | --- | --- | --- |
| A3-0 | E70 scene-local composite | 当前 best | 已有 | 上限/anchor |
| A3-1 | unified reliability config | 所有场景统一应用 `large sink label -> large support surface` 规则 | 待跑，优先级最高 | 证明不是 scene patch |
| A3-2 | unified config w/o scene names but class/geometry gated | 用 class + bbox extent + high-margin/entropy gate，不读 scene id | 待实现或用 runner 现有规则近似 | 最适合论文主方法 |
| A3-3 | over-broad relabel negative | 例如 E67 `cushion:sofa:1.2` | 已有 | 证明不是所有 relabel 都有效 |
| A3-4 | rule-specific leave-one-out under unified config | 移除单条规则 | 待跑，可放 supplement | 显示规则贡献边界 |

### Expected signal

确认假设的信号：

1. A3-1/A3-2 接近 E70，至少保持：
   - all ΔmIoU > +2.5；
   - all ΔmF1 > +3.0；
   - 没有 scene 的 ΔmIoU/ΔmF1 变负；
   - F-mIoU regression 不超过 1 point；
2. A3-3 明显失败，说明方法不是“见大对象就重命名”，而是有 reliability boundary；
3. leave-one-out rows 显示 `bin:table` 是主因、`vent:table` 是次因、`tissue-paper:cloth` 负责 office1。

削弱假设的信号：

- unified config 明显低于 E70，尤其 all ΔmIoU 掉到 +1 以下；
- 某些场景出现严重负迁移；
- over-broad relabel 与 carefully gated relabel 没有差别。

### Stop condition

停止并进入写作的条件：

- A3 至少得到 A3-1 或 A3-2 的 full-scene official evaluator row；
- 如果 unified config 失败，不继续盲调，而是把 E70 降级为 diagnostic/case-study result，并把 paper target 改为 weaker C 类系统/分析论文；
- 如果 unified config 接近 E70，则把它定为论文主方法，E70 scene-local composite 只作为 internal best，不作为主文方法名。

### 论文中要写出的结论

> A shared reliability gate preserves most of the E70 gain, while over-broad relabeling fails. This demonstrates that the method is not scene memorization but a constrained carrier-reliability principle with measurable boundaries.

---

## 5. 附属诊断表：Object-level failure attribution

这张表支撑第三创新点，但不作为独立第四组消融。

建议 Table D：`Object-level diagnosis explains class-level gains`

| Case | Failure before diagnosis | Diagnostic evidence | Repair | Outcome |
| --- | --- | --- | --- | --- |
| office2 bin/table | `bin` precision 极低 | GT bin recall 已接近 1；false `bin` 来自大 flat table carrier | `bin:table:1.0` | office2 ΔmIoU 到 +6.254 |
| office2 vent/table | `vent` 吸收 table/lamp/sofa | vent predicted objects dominated by non-vent GT | `vent:table:1.0` | office2 ΔmIoU 到 +6.492 |
| office1 tissue-paper/cloth | cloth 被小物体语义覆盖 | 大 carrier 被读为 `tissue-paper` | `tissue-paper:cloth:0.8` | office1 明显正向 |
| room0 cushion/sofa | cushion/sofa 边界混合 | 大 sofa carrier 可被读成 cushion | `cushion:sofa:1.2` | 失败，F-mIoU -4.851 |

这张表的写作目的：

1. 证明我们不是只看最终 mIoU；
2. 证明问题定位到了 object carrier 层；
3. 证明正向和负向案例都能被诊断工具解释；
4. 给 limitation 留真实边界。

---

## 6. 运行顺序

优先级按投稿风险排序：

1. **先跑 A3 unified config**  
   这是决定 paper 主方法是否可信的最高优先级实验。
2. **再跑 A1 leave-one-out / w/o geometry repair**  
   这是主贡献因果证据。
3. **最后跑 A2 phase/component diagnostics**  
   如果时间紧，A2 可部分放 supplement，但至少要有代表场景诊断表。

---

## 7. 远程运行模板

所有重实验在 184 上跑，本机只整理文档。

### 7.1 单场景/多场景 runner 模板

```bash
ssh nebula@10.177.69.184 '
cd /home/nebula/xxy/DuoGraph3D
python3 examples/run_conceptgraphs_engineered_parity.py \
  --root /home/nebula/xxy/duograph3d_artifacts/<RUN_NAME> \
  --pred-exp-name <PRED_EXP_NAME> \
  --scenes room0 room1 room2 office0 office1 office2 office3 office4 \
  --phase beta \
  --export-source auto \
  --geometry-repair-carve-rules "cushion:sofa:0.04" \
  --geometry-repair-large-label-rules "<RULES>" \
  --clip-feature-mode image
'
```

### 7.2 Composite evaluator 模板

```bash
ssh nebula@10.177.69.184 '
cd /home/nebula/xxy/DuoGraph3D
python3 examples/evaluate_composite_policy.py \
  --root /home/nebula/xxy/duograph3d_artifacts/<RUN_NAME> \
  --pred-exp-name <PRED_EXP_NAME> \
  --output-root /home/nebula/xxy/duograph3d_artifacts/<RUN_NAME>/final_eval
'
```

### 7.3 Official evaluator 模板

```bash
ssh nebula@10.177.69.184 '
cd /home/nebula/xxy/DuoGraph3D
DUOGRAPH_EVAL_ROOT=/home/nebula/xxy/duograph3d_artifacts/<RUN_NAME>/final_eval \
PYTHON_BIN=python3 \
bash .omx/goals/performance/duograph3d-accuracy/evaluator.sh
'
```

---

## 8. Paper-ready 表格布局

### Main text

1. **Table 1：Main comparison**  
   ConceptGraphs vs DuoGraph3D unified/full, full Replica scenes。
2. **Table 2：Geometry carrier reliability ablation**  
   A1 rows，展示 full / w/o geometry repair / w/o table-sink / semantic-only。
3. **Table 3：Unified vs scene-local and negative boundary**  
   A3 rows，直接化解 overfitting criticism。
4. **Figure 4：Object-level diagnosis cases**  
   office2 table→bin、office1 tissue-paper→cloth、room0 cushion/sofa failed case。

### Supplement

1. Full per-scene A1/A3 gaps；
2. Full per-class gap；
3. A2 phase/component diagnostics；
4. All run commands and artifact paths。

---

## 9. 通过/失败后的投稿决策

### 若 A3 unified config 接近 E70

论文主方法改为 unified reliability version；E70 作为 internal best 或 same-result checkpoint。  
投稿目标：C 类稳定，B 类可打磨。

### 若 A3 unified config 明显退化，但 A1 因果仍强

论文定位改为 diagnostic/system paper：强调 semantic authority failure 与 object-level diagnosis，不强推通用方法。  
投稿目标：保守 C 类。

### 若 A1 也不能证明 geometry repair 是主因

停止投稿封装，回到方法阶段；当前 E70 不适合作为论文主结果。

