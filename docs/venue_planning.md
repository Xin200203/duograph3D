# DuoGraph3D 投稿目标分析（含 CCF A/B 筛选）

## 投稿目标总表

| Venue | CCF 等级 | 领域匹配度 | 难度 | 适合的 DuoGraph3D 版本 | 建议 |
|---|---|---|---|---|---|
| AAAI | **A** | 中高 | 高 | 完整 two-level graph + object memory + 多场景强实验 | 冲刺目标 |
| CVPR / ICCV | **A** | 高 | 极高 | 结果非常强、3D vision 贡献非常硬 | 暂不作为现实目标 |
| ACM MM | **A** | 中 | 高 | 多模态/语义映射/场景表示故事很强 | 远期冲刺 |
| **ICRA** | **B** | **很高** | **中高** | **online object-level mapping / robotics perception** | **最自然的主力冲刺** |
| ICASSP | **B** | 中低 | 中 | 收窄成 signal/multimodal/graph association 子问题 | CCF-B 保底候选 |
| ICME | **B** | 中 | 中 | 多媒体 3D semantic mapping / multimodal scene understanding | 可考虑 |
| ISMAR | **B** | 中高 | 中高 | AR/VR 场景理解、在线 3D map、空间记忆 | 若强调 spatial map，可考虑 |
| 3DV | C | **很高** | 中高 | 3D reconstruction / RGB-D mapping / object memory | 学术匹配强，但 CCF 不是 A/B |
| IROS | C | **高** | 中高 | robotics mapping / embodied perception | 匹配强，但 CCF-C |
| WACV | 非 CCF 核心 | 高 | 中 | 应用型视觉系统、稳健 3D scene understanding | 很现实，但 CCF 价值需确认 |
| ACCV | C | 高 | 中 | CV/3D scene understanding 稳妥版本 | CCF-C 稳妥 |

## 推荐投稿路线

### 内部冲刺目标：AAAI（CCF-A）

前提是 full DuoGraph3D 成型，多场景结果稳定。

论文主张：
```
online 3D reconstruction → two-level object graph → object memory consistency → entity-carrier decoupling
```

必须达到：
- 不只是修 CG，而是清晰 two-level graph framework
- 多场景稳定，不只 room1
- 对比 ConceptGraphs + CGAligned + ablations
- duplicate birth、fragmentation、semantic purity 明显改善
- final mIoU / mRecall / F-mIoU 至少整体不输，最好稳定胜出

### 主力现实目标：ICRA（CCF-B）

**最推荐**。CCF-B + 领域匹配高 + online mapping 叙事自然。

适合题目：
- Online Object Memory Graphs for RGB-D Semantic Mapping
- DuoGraph3D: Two-Level Object Graphs for Online RGB-D Scene Mapping

ICRA 叙事：
- 机器人在室内探索 → 需要在线构建 object-level map
- 单帧检测 noisy → 跨帧 identity 需要 memory
- ConceptGraphs 偏离线后处理 → DuoGraph3D 显式维护 object memory graph

### 保守 CCF-B 目标

| Venue | 适用场景 |
|---|---|
| **ICASSP** | 适合拆出 Layer2 association 或 semantic memory 子问题，不适合完整系统 |
| **ICME** | 多模态 RGB-D semantic mapping |
| **ISMAR** | 空间场景图 / AR map |

## 三层目标设定

```
内部冲刺：AAAI（CCF-A）  ← full DuoGraph3D 成型后
主力现实：ICRA（CCF-B）  ← 最自然的 online mapping 目标
保守保底：ICASSP/ICME   ← 子模块可拆出时
```

## 不因 CCF 而排除的高匹配目标

| Venue | CCF | 为什么仍值得考虑 |
|---|---|---|
| 3DV | C | 3D vision 专门会议，与 3D reconstruction/mapping 非常贴合 |
| IROS | C | 机器人在线感知和建图非常贴合 |
| WACV | 需认定 | 应用型视觉系统很合适，现实成功率高 |
| ACCV | C | CV 稳妥会议，适合中等完整结果 |
