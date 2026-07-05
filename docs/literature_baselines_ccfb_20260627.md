# DuoGraph3D CCF-B 目标下的 Zero-shot / Open-vocabulary 3D Baseline 与 Grounded-SAM 调研（2026-06-27）

## 0. 目标判断

如果目标是 CCF-B 级别会议，尤其 ICRA / ECCV 这类目录内 B 类会议，DuoGraph3D 不能只与 ConceptGraphs 做单一主表。需要把横向对比扩成三类：

1. **Open-vocabulary 3D mapping / graph mapping**：证明我们不是只改 ConceptGraphs；
2. **Online zero-shot 3D instance segmentation**：证明我们在 online embodied setting 中有直接竞争力；
3. **Offline / upper-bound OV-3D instance segmentation**：证明我们知道当前 SOTA 上界，并解释 DuoGraph3D 的在线性、记忆性、诊断性优势。

CCF 官方 AI 目录中 ECCV 和 ICRA 是 B 类会议，IROS 是 C 类会议。因此若要冲 B，最现实目标应优先考虑 **ICRA**；ECCV 对视觉方法统一性和大规模 benchmark 的要求更高，当前风险明显更大。

## 1. 最应该作为横向对比的工作

### Tier 1：必须对比 / 必须在论文中讨论

#### 1. ConceptGraphs

- 类型：open-vocabulary 3D scene graph / object graph mapping。
- 相关性：最高；当前 E70 已在其 Replica official-format setting 下超过它。
- 成熟方法：2D foundation model outputs + multi-view association -> compact graph-structured 3D scene representation。
- 我们要强调的差异：ConceptGraphs 是强 object graph baseline；DuoGraph3D 的新意应放在 online graph memory、auditable carrier reliability、object-level failure attribution。

#### 2. OnlineAnySeg

- 类型：online zero-shot 3D segmentation。
- 相关性：非常高，是当前最贴近 DuoGraph3D online setting 的 direct baseline。
- 成熟方法：用 voxel hashing 高效查询 3D overlap，将 2D VFM masks 在线合并成 3D instances；结合 spatial overlap 和 multimodal similarity。
- 我们可借鉴：把 mask association 从 pairwise threshold 扩展为 **carrier-level evidence graph**，同时记录 view-consensus / overlap support 作为 reliability metric。

#### 3. EmbodiedSAM / ESAM

- 类型：online real-time SAM-assisted 3D instance segmentation。
- 相关性：非常高，且 ICLR 2025 oral，审稿人很可能问。
- 成熟方法：SAM 2D masks -> geometric-aware query lifting -> dual-level query decoder -> fast query merging。
- 我们可借鉴：用 query-level memory/merge 解释 online efficiency；把我们的 Layer2 memory 指标对齐到 ESAM 的 online instance matching/merging问题。

### Tier 2：强横向 / offline upper-bound

#### 4. Open3DIS

- 类型：open-vocabulary 3D instance segmentation with 2D mask guidance。
- 相关性：高；CVPR 2024，支持 ScanNet200/S3DIS/Replica，且官方说明支持 Grounding DINO、SAM、YOLO-World、RAM++。
- 成熟方法：aggregate 2D instance masks across frames，映射到 geometrically coherent point cloud regions，再与 3D class-agnostic proposals 结合。
- 我们可借鉴：2D mask guidance 不直接变 final label，而先变成 3D coherent object proposal；这与我们的 geometry-carrier reliability 很契合。

#### 5. OpenMask3D

- 类型：zero-shot open-vocabulary 3D instance segmentation。
- 相关性：高，NeurIPS 2023，Replica/ScanNet200 上有结果。
- 成熟方法：先预测 class-agnostic 3D instance masks，再通过 multi-view CLIP image embedding 聚合 per-mask features。
- 我们可借鉴：per-mask feature aggregation，而不是 per-point/per-frame noisy readout；可作为我们 carrier-level semantic reliability 的上位类比。

#### 6. OpenScene

- 类型：zero-shot open-vocabulary 3D semantic segmentation / dense 3D CLIP features。
- 相关性：中高；它是 semantic segmentation 强基线，但不是 online object memory。
- 成熟方法：multi-view feature fusion + 3D distillation + 2D-3D ensemble。
- 我们可借鉴：2D-3D ensemble 和 feature reliability；但 DuoGraph3D 不应变成 dense CLIP feature field，而应突出 object carrier / memory / diagnostic。

### Tier 3：方法启发 / 可选 baseline

#### 7. SAI3D / SAMPro3D / SAM3D / MaskClustering

- 类型：SAM-based zero-shot 3D instance segmentation / multi-view mask merging。
- 相关性：方法启发高，是否作为主 baseline 取决于能否跑通同一数据与指标。
- 成熟方法：
  - SAM3D：2D SAM masks 投影到 3D，bottom-up / adjacent-frame merging；
  - SAI3D：几何 primitives + SAM semantic cues，progressive merge；
  - SAMPro3D：定位 3D prompts，在多视角投影成一致 2D prompts；
  - MaskClustering：mask graph + view consensus rate。
- 我们可借鉴：view-consensus rate 和 prompt consistency，直接可转化为 carrier reliability score。

#### 8. ConceptFusion / VLMaps / OpenFusion / LERF

- 类型：open-set / language-aware 3D mapping。
- 相关性：作为 related work 和 optional comparison；不一定是主要 segmentation baseline。
- 成熟方法：把 CLIP/VLM features 融入 3D map / radiance field / spatial map。
- 我们可借鉴：language-query evaluation 和 feature fusion；但 DuoGraph3D 要避免被看作又一个 dense feature map。

#### 9. OpenIns3D / Open-YOLO 3D

- 类型：3D-input-only 或 2D-detector-assisted OV 3D instance segmentation。
- 相关性：中等；可作为 offline comparison 或 related work。
- 成熟方法：Mask-Snap-Lookup、2D detector/classifier 插件化、CLIP ranking/filtering。
- 我们可借鉴：把 2D open-world detector 作为 semantic proposal generator，而不是最终权威标签。

## 2. CCF-B 目标下推荐 baseline 组合

### Minimum acceptable for ICRA-B attempt

1. ConceptGraphs：当前已强对齐，必须保留。
2. OnlineAnySeg：online zero-shot direct baseline，优先级最高。
3. ESAM / EmbodiedSAM：online SAM-based strong baseline，至少需要同协议或可解释 protocol bridge。
4. Open3DIS 或 OpenMask3D：offline upper-bound / open-vocabulary instance comparison，至少选一个。

### Stronger package for reviewer defense

- Main table：ConceptGraphs + OnlineAnySeg + ESAM + DuoGraph3D。
- Upper-bound table：Open3DIS/OpenMask3D/OpenScene 作为 offline / non-online reference。
- Diagnostic table：DuoGraph3D 的 object-level carrier failure attribution，展示其他方法没有给出的可解释性。

## 3. 这些工作中的成熟方法模式

### Pattern A：2D foundation masks -> 3D mask association

代表：OnlineAnySeg、SAM3D、MaskClustering、Open3DIS。

可借鉴点：

- 用 3D overlap / voxel hashing / graph clustering 做跨视角合并；
- 记录 view consensus，避免单帧 mask 决定 3D object；
- 把 association confidence 作为后续 semantic reliability 的输入。

### Pattern B：class-agnostic 3D proposal + open-vocabulary semantic readout

代表：OpenMask3D、Open3DIS、OpenIns3D。

可借鉴点：

- final semantic readout 应在 object/mask 层聚合，而不是把单帧 CLIP top-1 直接作为权威；
- 对每个 object 维护多视角 semantic evidence、top-share、entropy、CLIP margin、text prompt agreement。

### Pattern C：geometry primitives / support surfaces constrain semantic merging

代表：SAI3D、Open3DIS，和我们 E65/E70 的经验一致。

可借鉴点：

- table/bin/vent 这类问题不能只靠 label relabel；需要几何 primitives、surface orientation、support relation、邻接关系；
- geometry 应该是 carrier repair 的必要条件，而不是充分条件。

### Pattern D：query / memory representation for online efficiency

代表：ESAM、OnlineAnySeg。

可借鉴点：

- 我们的 Layer2 memory 应对齐到 query/mask association 问题，输出 candidate recall@K、duplicate birth、fragmentation、memory purity；
- 这样 two-layer graph memory 才能被写成 CCF-B reviewer 可接受的系统贡献。

## 4. Grounded-SAM / GroundingDINO / SAM 可以借鉴什么

### Directly useful

1. **作为 2D mask front-end 替换/增强当前 GSA detections**  
   GroundingDINO 根据文本生成 boxes，SAM 根据 boxes 出 masks。可用于我们关心的 failure classes：table/bin/vent/cloth/tissue/pillow/sofa/cushion。

2. **构建 class-specific diagnostic probes**  
   对每个可疑 carrier，使用 prompt bank：`table`, `dining table`, `flat table`, `bin`, `trash bin`, `vent`, `cloth`, `tissue paper` 等，观察多视角 prompt agreement。

3. **提供 object-level semantic support，而不是 final authority**  
   Grounded-SAM 的输出应用作 evidence：是否多个视角都支持 table？是否与几何 flat support surface 一致？不能直接一票否决当前 label。

4. **用 Grounded-SAM 2 / SAM2 tracking 思路增强 temporal consistency**  
   Grounded-SAM 2 结合 GroundingDINO/SAM2 做 open-world video tracking。我们可借鉴其“tracking/identity prior”作为 Layer2 candidate 的一类外部 evidence。

### High-risk / 不应直接照搬

1. 单帧 Grounded-SAM mask 容易 prompt-sensitive，不应直接写入 3D memory。
2. 自动 labeler（BLIP/RAM + GroundingDINO + SAM）会产生语义幻觉，必须通过 geometry/multiview gate。
3. Grounded-SAM 本身是 2D pipeline，不解决 3D carrier merge、view consistency、memory authority；这些仍是 DuoGraph3D 的核心空间。

## 5. 面向 CCF-B 的下一步实验建议

### P0：横向 baseline bring-up

1. OnlineAnySeg：把已有 subset/sparse bridge 扩到更完整 setting，至少与当前 Replica/ScanNet protocol 对齐一个主表。
2. ESAM：复核现有 ScanNet200/SceneNN/3RScan 结果，并建立与 DuoGraph3D 的共同评测桥。
3. Open3DIS 或 OpenMask3D：选一个作为 offline upper-bound；优先 Open3DIS，因为它支持 Replica 且支持 GroundingDINO/SAM。

### P1：方法深化实验

1. Grounded-SAM diagnostic probe：对 E65 失败 carriers 做多视角 prompt agreement，验证能否形成 scene-independent reliability evidence。
2. Evidence-gated carrier repair：gate 输入包括 geometry flatness/support、multiview prompt support、label entropy、CLIP margin、neighbor relation。
3. A2 memory diagnostics：让 Layer2 graph memory 的贡献从“代码结构”变成可量化指标。

### P2：论文叙事调整

DuoGraph3D 的 B 会版主线应写成：

> Online open-vocabulary 3D mapping fails when semantic readout overrides stable geometry carriers. DuoGraph3D introduces an auditable graph-memory representation and carrier-level diagnostics to detect such failures, and uses bounded, multi-view evidence-gated carrier repair to improve dense semantic evaluation while exposing failure boundaries.

## 6. Sources

- ConceptGraphs project / arXiv: https://concept-graphs.github.io/ ; https://arxiv.org/abs/2309.16650
- OnlineAnySeg project / GitHub: https://yjtang249.github.io/OnlineAnySeg/ ; https://github.com/yjtang249/OnlineAnySeg
- EmbodiedSAM / ESAM project / GitHub: https://xuxw98.github.io/ESAM/ ; https://github.com/xuxw98/ESAM
- Open3DIS GitHub / paper: https://github.com/VinAIResearch/Open3DIS ; https://openaccess.thecvf.com/content/CVPR2024/papers/Nguyen_Open3DIS_Open-Vocabulary_3D_Instance_Segmentation_with_2D_Mask_Guidance_CVPR_2024_paper.pdf
- OpenMask3D project: https://openmask3d.github.io/
- OpenScene project / paper: https://pengsongyou.github.io/openscene ; https://openaccess.thecvf.com/content/CVPR2023/papers/Peng_OpenScene_3D_Scene_Understanding_With_Open_Vocabularies_CVPR_2023_paper.pdf
- Grounded-Segment-Anything / GroundingDINO / SAM: https://github.com/IDEA-Research/Grounded-Segment-Anything ; https://github.com/IDEA-Research/GroundingDINO ; https://arxiv.org/abs/2304.02643
- SAI3D / SAMPro3D / MaskClustering / SAM3D: https://arxiv.org/abs/2312.11557 ; https://mutianxu.github.io/sampro3d/ ; https://pku-epic.github.io/MaskClustering/ ; https://arxiv.org/abs/2306.03908
- CCF AI directory: https://www.ccf.org.cn/Academic_Evaluation/AI/
