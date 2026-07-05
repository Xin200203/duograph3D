# DuoGraph3D CCF-B 实验推进计划 — 2026-06-28

## 0. 负责人目标

作为当前实验第一负责人，本轮目标不是继续做局部调参，而是把 CCF-B 所需证据闭环推进到可投稿状态：

1. **文献对齐**：把 OVI-MAP、ESAM、OnlineAnySeg、Open3DIS、Details Matter、MV3DIS、OV3D-CG、Open-YOLO 3D、GeoGuide 等工作精读成可复用笔记，明确当前 SOTA、pipeline 与可借鉴模块。
2. **方法抽象**：把 E70 中的局部 `tissue-paper→cloth`、`bin→table` 经验提升为无 scene-id 的 geometry-first semantic authority control / carrier reliability gate。
3. **指标补齐**：在 ConceptGraphs-format mIoU/mF1 之外，补 AP/AP50/AP25 或至少形成协议桥，避免与 OV-3DIS SOTA 指标错位。
4. **实验闭环**：先跑局部诊断小实验，再跑 Replica 全场景；每次实验记录 object/frame/memory/export 诊断，不只看 final mIoU。
5. **代码维护**：所有新增实验脚本和指标解析必须有 regression tests；远程 184 跑实验，本地只跑轻量单测/文档生成。

## 1. 当前证据边界

已支持：

- E70 在 ConceptGraphs-format Replica official 评测中超过 ConceptGraphs：`+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`。
- A1 clean leave-one-out 证明主要正向来自：
  - office1 `tissue-paper→cloth`，约 `+1.800 all mIoU`；
  - office2 `bin→table`，约 `+1.153 all mIoU`；
  - `vent→table` 不是主贡献。
- A2 证明 graph memory 当前不是 final mIoU 直接来源；memory-dense forced export 为负，应定位为 state/diagnostic/export-gating infrastructure。
- E71 证明 target-declared unified evidence gate 不足，不能声称通用 repair 已解决。

未支持：

- DuoGraph3D 是 open-vocabulary 3D segmentation SOTA。
- two-layer graph memory 直接驱动 final mIoU 提升。
- 当前 large-label repair 可跨场景无 scene-id 泛化。
- 当前结果已与 OVI-MAP / ESAM / OnlineAnySeg / Open3DIS 系列同协议公平对比。

## 2. 并行任务分解

### Subagent A — online mapping / online segmentation 文献精读

范围：OVI-MAP、ESAM/EmbodiedSAM、OnlineAnySeg、OpenTrack3D。  
输出：`analysis/literature/ccfb_sota_20260628/online_mapping_notes.md`。  
关注：online pipeline、incremental metrics、runtime、view selection、tracker/memory 设计，与 DuoGraph3D 的冲突和可借鉴点。

### Subagent B — OV-3DIS / geometry consistency 文献精读

范围：Open3DIS、Details Matter、MV3DIS、Open-YOLO 3D、OV3D-CG、GeoGuide、OpenMask3D。  
输出：`analysis/literature/ccfb_sota_20260628/ov3dis_geometry_notes.md`。  
关注：2D mask→3D proposal、multi-view consistency、object-centric semantic readout、geometry-semantic consistency。

### Subagent C — 代码路径审计

范围：metric/eval/export/large-label repair/AP bridge/remote config。  
输出：只读审计结果；若需要由主 agent 整合入计划。  
关注：最小改动文件、现有 AP parser 是否可复用、风险路径。

## 3. 三个最小实验（Ablation Planner）

### Ablation 1 — Shared carrier reliability gate v2

**Target hypothesis**  
如果 E70 的真正机制是 geometry-first semantic authority control，而不是 scene-local patch，那么一个不读取 scene id 的 gate 应该能在 full Replica 上保留大部分 `tissue→cloth` 与 `bin→table` 收益，同时阻止 E71 中大量 unsafe `vent→table`。

**Expected signal**

确认：

- full Replica all ΔmIoU > `+2.0`，最好 > `+2.5`；
- 无 scene mIoU/mF1 明显负迁移；
- office1 cloth 与 office2 bin/table 目标指标接近 E70；
- blocked relabel examples 集中在 office3/office4 vent/table false positives；
- relabel object/point mass 有上限且可解释。

削弱：

- 结果接近 E71 `+0.665`；
- 漏掉 office2 `bin→table` carrier；
- 出现 office4/room0 大面积误伤；
- gate 仍需 scene-specific rule 才能工作。

**Stop condition**

先跑 `office1, office2, office3, office4, room0` 代表场景，若 all-subset ΔmIoU < `+1.5` 或目标 carrier 未触发，停止全场景，回到 gate diagnostics；若通过，再跑 full Replica。

### Ablation 2 — AP-style metric bridge for current official outputs

**Target hypothesis**  
当前 E70 的 semantic mIoU gain 需要被转换/补充为 OV-3DIS 可理解的 AP/AP50/AP25 证据；若 mIoU 提升主要来自少数大 carrier label 修复，AP-style instance metric 可能只部分提升，这会约束论文 claim。

**Expected signal**

确认：

- E70 vs no-large/E71 的 AP25/AP50/APall 差异方向与 target carrier 修复一致；
- semantic AP 与 class-agnostic AP 分开后，可以说明增益来自 semantic authority 而不是 instance boundary；
- protocol bridge 文档能清楚解释与 Open3DIS/OVI-MAP 指标的差别。

削弱：

- AP 完全不提升甚至下降；
- object boundary / duplicate prediction 问题掩盖 semantic mIoU gain；
- 现有 output 不足以可靠计算 AP。

**Stop condition**

先用 E70、w/o large-label、E71 三个已有 artifact 计算或解析 AP-style proxy；若工具链不可复用，则至少输出 protocol-gap audit 和实现缺口，不把 AP 写成主结果。

### Ablation 3 — SOTA protocol/baseline bridge sanity

**Target hypothesis**  
CCF-B 稿不能只比 ConceptGraphs；至少需要把 OVI-MAP / OnlineAnySeg / ESAM / Open3DIS-family 的协议边界写清楚，并优先选一个可在 184 上跑通的 direct bridge。

**Expected signal**

确认：

- 找到至少一个可运行 direct bridge（优先 OnlineAnySeg 或 OVI-MAP，如果环境可行）；
- 输出输入/输出/metric/online/runtime 对齐表；
- 如果不能公平跑，给出明确 blocker 与替代证据，不把其结果混入主表。

削弱：

- baseline 环境不可用且无 artifact；
- 只能使用非官方 sparse bridge；
- 指标/数据协议差异过大，不能支撑定量主表。

**Stop condition**

先做 remote env + artifact audit；若 2 小时内不能确认可运行 baseline，则冻结为 baseline bridge 文档，继续主方法 gate/AP 实验，不让 baseline bring-up 阻塞所有实验。

## 4. 实验记录规范

每个远程 run 必须输出并同步：

- run root / command / commit or file snapshot / environment；
- final mIoU/mF1/F-mIoU；
- AP/AP50/AP25（如果该 lane 支持）；
- relabel counts / relabel points / blocked relabel examples；
- object-level target class table：office1 cloth/tissue, office2 bin/table, office3/office4 vent/table, room0 cushion/sofa；
- memory diagnostics：birth rate, weak-id, no-candidate, fragmentation, export source；
- negative result decision：是否进入论文主 claim、supplement、或 limitation。

## 5. 代码维护约束

- 新增参数默认必须保持 legacy behavior。
- 不引入新依赖。
- 每个 source-level 入口必须有 unittest 防止参数/diagnostic 字段丢失。
- 远程实验脚本写入 artifact root；本地只跑单测，不跑重实验。
- 任何 scene-specific 规则必须标记为 diagnostic composite，不能混入 final method claim。

## 6. 当前下一步执行顺序

1. 等待/整合 subagent 文献与代码路径报告。
2. 主 agent 同步实现：
   - carrier reliability gate v2 的 source-level 参数和 diagnostics；
   - AP-style proxy/bridge 脚本或文档化 gap；
   - remote run script for Ablation 1 subset。
3. 本地跑 unittest。
4. sync 到 184，先跑 subset diagnostic；若通过，扩到 full Replica。
5. 更新 `docs/ccfb_experiment_runlog_20260628.md` 与 raw artifact mirror。

## 7. 2026-06-28 launched subset run

Remote artifact root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_carrier_v2_subset_20260628_carrier_v2_subset`.

Variants:

1. `Control_E71_active_target_declared`: previous active/target-declared evidence gate, subset control.
2. `CarrierV2_table_z025_rate016`: table-like horizontal support with `max_z_extent=0.25`, `carrier-v2`, point-rate cap `0.16`.
3. `CarrierV2_table_z035_rate016`: looser table thickness `max_z_extent=0.35`, `carrier-v2`, point-rate cap `0.16`.

Stop/readout rule: use per-scene average gap over `room0, office1, office2, office3, office4` plus object-level `geometry_repair_summary`; do not interpret subset composite `all` row as a full-Replica result.
