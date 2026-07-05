# DuoGraph3D 迁移至 76 号服务器计划

## 目标

将 DuoGraph3D 实验从 184 号服务器 (`10.177.69.184`, nebula) 迁移到 76 号服务器 (`10.176.56.76`, xxy)，利用 7×RTX 4090 的并行计算能力。

## 当前状态

### 76 号服务器 (`10.176.56.76`)

| 项目 | 详情 |
|---|---|
| GPU | 7× RTX 4090 (24GB)，GPU 2-6 完全空闲 |
| Python | 系统 3.10.12 |
| Conda | `/datadisk1/xxy/miniconda3/`，已有 `conceptgraph` 环境 |
| 可用磁盘 | `/datadisk3/xxy/` (剩余 1.3TB), `/datadisk4/` (剩余 668GB) |
| CUDA | 系统 CUDA 11.5，conda 环境内 CUDA 11.8 (torch 2.0.1) |

现有 `conceptgraph` 环境 (Python 3.10.19):
```
torch 2.0.1, torchvision 0.15.2, torchaudio 2.0.2
open3d 0.19.0, open_clip_torch 3.2.0
numpy 1.26.4, pillow 11.1.0, pytorch3d 0.7.4
```

### 184 号服务器 (`10.177.69.184`, 数据源)

| 项目 | 详情 |
|---|---|
| Replica 数据集 | 28GB (`/home/nebula/xxy/dataset/Replica/`) |
| GSA 检测 | 每场景 400 个 pkl.gz, ~1.9GB/场景 |
| ConceptGraphs 代码 | 2.9MB (`/home/nebula/xxy/concept-graphs-main/`) |
| DuoGraph3D 代码 | 53MB (`/home/nebula/xxy/DuoGraph3D/`) |

## 迁移清单

### 1. 磁盘规划

| 目标路径 | 用途 | 预计大小 |
|---|---|---|
| `/datadisk3/xxy/duograph3d/` | 实验主目录 | — |
| `/datadisk3/xxy/duograph3d/DuoGraph3D/` | DuoGraph3D 代码 (git clone) | ~60MB |
| `/datadisk3/xxy/duograph3d/concept-graphs-main/` | ConceptGraphs 参照 | ~3MB |
| `/datadisk3/xxy/duograph3d/dataset/Replica/` | Replica 数据集 | ~28GB |
| `/datadisk3/xxy/duograph3d/artifacts/` | 实验结果输出 | ~10-50GB |

**注意**：现有 conda 环境在 `/datadisk1/xxy/miniconda3`（该盘仅剩 189GB），但 DuoGraph3D 可直接使用已有的 `conceptgraph` 环境，无需额外磁盘开销。

### 2. 代码同步

**方案 A: git clone（推荐）**
```bash
cd /datadisk3/xxy/duograph3d
git clone git@github.com:Xin200203/duograph3D.git DuoGraph3D
cd DuoGraph3D
git checkout conceptgraphs-engineering-optimizations-20260426
```

前提：76 服务器需要配置 GitHub SSH key（`~/.ssh/id_ed25519_github`）。

**方案 B: 从 184 rsync（备选）**
```bash
rsync -avz 10.177.69.184:/home/nebula/xxy/DuoGraph3D/ /datadisk3/xxy/duograph3d/DuoGraph3D/
```

**方案 C: 从本机 scp（当前方式）**
```bash
tar czf - src/ examples/ tests/ | ssh 10.176.56.76 "cd /datadisk3/xxy/duograph3d/DuoGraph3D && tar xzf -"
```

### 3. 数据集同步

**Replica 数据集** (~28GB):
```bash
# 从 184 rsync（推荐，184 和 76 在同一内网）
rsync -avz --progress \
  10.177.69.184:/home/nebula/xxy/dataset/Replica/ \
  /datadisk3/xxy/duograph3d/dataset/Replica/
```

这个命令需要：
- 76 能 SSH 到 184（检查 76→184 的网络连通性）
- 或者反过来从 184 push 到 76

如果 76→184 不通，可以先 184→本地→76：
```bash
# 在本地 Mac 上执行中转
rsync -avz 10.177.69.184:/home/nebula/xxy/dataset/Replica/ /tmp/replica/
rsync -avz /tmp/replica/ 10.176.56.76:/datadisk3/xxy/duograph3d/dataset/Replica/
```

预计耗时：28GB，千兆网络约 4-5 分钟。

### 4. ConceptGraphs 参照

```bash
# 从 184 同步（仅 3MB）
rsync -avz 10.177.69.184:/home/nebula/xxy/concept-graphs-main/ \
  /datadisk3/xxy/duograph3d/concept-graphs-main/
```

### 5. 环境配置

76 上已有 `conceptgraph` 环境 (Python 3.10.19, torch 2.0.1)，直接可用。需要确认：

```bash
# 验证所有依赖
/datadisk1/xxy/miniconda3/envs/conceptgraph/bin/python -c "
import numpy, torch, open3d, open_clip, PIL, gzip, pickle, json, csv
print('All imports OK')
"

# 验证 conceptgraph 模块可导入
PYTHONPATH=/datadisk3/xxy/duograph3d/concept-graphs-main \
  /datadisk1/xxy/miniconda3/envs/conceptgraph/bin/python -c "
from conceptgraph.dataset.replica_constants import REPLICA_CLASSES
from conceptgraph.slam.utils import merge_objects, denoise_objects
print('ConceptGraphs imports OK')
"
```

### 6. 路径修改

DuoGraph3D 的 runner 包含硬编码路径，需要修改：

`examples/run_conceptgraphs_engineered_parity.py`:
```python
# 旧 (184)
REPLICA_ROOT = Path("/home/nebula/xxy/dataset/Replica")
sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D/src")
sys.path.insert(0, "/home/nebula/xxy/concept-graphs-main")

# 新 (76)
REPLICA_ROOT = Path("/datadisk3/xxy/duograph3d/dataset/Replica")
sys.path.insert(0, "/datadisk3/xxy/duograph3d/DuoGraph3D/src")
sys.path.insert(0, "/datadisk3/xxy/duograph3d/concept-graphs-main")
```

**建议**：将路径改为环境变量，避免硬编码：
```python
REPLICA_ROOT = Path(os.environ.get("REPLICA_ROOT", "/datadisk3/xxy/duograph3d/dataset/Replica"))
DUOGRAPH3D_SRC = Path(os.environ.get("DUOGRAPH3D_SRC", "/datadisk3/xxy/duograph3d/DuoGraph3D/src"))
CG_MAIN = Path(os.environ.get("CG_MAIN", "/datadisk3/xxy/duograph3d/concept-graphs-main"))
sys.path.insert(0, str(DUOGRAPH3D_SRC))
sys.path.insert(0, str(CG_MAIN))
```

### 7. 运行环境脚本

创建 `/datadisk3/xxy/duograph3d/env.sh`:
```bash
#!/bin/bash
export CONDA_PATH=/datadisk1/xxy/miniconda3
export CONDA_ENV=conceptgraph
export PYTHON=$CONDA_PATH/envs/$CONDA_ENV/bin/python

export REPLICA_ROOT=/datadisk3/xxy/duograph3d/dataset/Replica
export DUOGRAPH3D_SRC=/datadisk3/xxy/duograph3d/DuoGraph3D/src
export CG_MAIN=/datadisk3/xxy/duograph3d/concept-graphs-main
export ARTIFACTS=/datadisk3/xxy/duograph3d/artifacts

export PYTHONPATH=$DUOGRAPH3D_SRC:$CG_MAIN

# 激活 conda
source $CONDA_PATH/bin/activate $CONDA_ENV
```

## 迁移步骤（执行顺序）

### Phase 1: 基础设施 (约 30 分钟)

```bash
# 1. 创建目录结构
ssh 10.176.56.76 "mkdir -p /datadisk3/xxy/duograph3d/{DuoGraph3D,concept-graphs-main,dataset/Replica,artifacts}"

# 2. 克隆代码（或同步）
ssh 10.176.56.76 "cd /datadisk3/xxy/duograph3d && git clone git@github.com:Xin200203/duograph3D.git DuoGraph3D"

# 3. 同步 ConceptGraphs
rsync -avz 10.177.69.184:/home/nebula/xxy/concept-graphs-main/ \
  10.176.56.76:/datadisk3/xxy/duograph3d/concept-graphs-main/

# 4. 验证环境
ssh 10.176.56.76 "
  /datadisk1/xxy/miniconda3/envs/conceptgraph/bin/python -c '
    import numpy, torch, open3d, open_clip
    print(\"Core deps OK\")
  '
"
```

### Phase 2: 数据集 (约 1-2 小时，取决于网络)

```bash
# 从 184 同步 Replica 数据集到 76
# 方式1: 76 拉取
ssh 10.176.56.76 "
  rsync -avz --progress \
    10.177.69.184:/home/nebula/xxy/dataset/Replica/ \
    /datadisk3/xxy/duograph3d/dataset/Replica/
"

# 方式2: 本地中转 (Mac)
rsync -avz 10.177.69.184:/home/nebula/xxy/dataset/Replica/ /tmp/replica/
rsync -avz /tmp/replica/ 10.176.56.76:/datadisk3/xxy/duograph3d/dataset/Replica/
```

### Phase 3: 路径适配与验证 (约 30 分钟)

```bash
# 1. 修改 runner 中的硬编码路径
# 2. 创建 env.sh
# 3. 运行 smoke test
ssh 10.176.56.76 "
  source /datadisk3/xxy/duograph3d/env.sh
  cd /datadisk3/xxy/duograph3d/DuoGraph3D
  PYTHONPATH=src \$PYTHON -c 'from duograph3d.pipeline import DuoGraph3DPipeline; print(\"DuoGraph3D OK\")'
"
```

### Phase 4: 小规模验证 (约 10 分钟)

```bash
# 单场景测试 (office3, 50 帧, stride=40)
ssh 10.176.56.76 "
  source /datadisk3/xxy/duograph3d/env.sh
  cd /datadisk3/xxy/duograph3d/DuoGraph3D
  DUOGRAPH_PHASE=baseline \$PYTHON -u \
    examples/run_conceptgraphs_engineered_parity.py \
    --scenes office3 \
    --root /datadisk3/xxy/duograph3d/artifacts/verify \
    --pred-exp-name verify \
    --export-source memory-dense
"
```

## 风险与注意事项

1. **76↔184 网络连通性**：需要先验证两台服务器之间能否互相 SSH
2. **GitHub SSH key**：76 上如果没有配置 GitHub SSH key，需要用 rsync 同步代码
3. **磁盘不足**：`/datadisk1` 仅剩 189G，conda 环境已占 1.3TB。新数据和结果必须放在 `/datadisk3` 或 `/datadisk4`
4. **GPU 抢占**：GPU 1 常被其他用户占满（100% 训练）。实验应指定使用 GPU 2-6
5. **CUDA 版本**：conceptgraph 环境的 torch 2.0.1 需要 CUDA 11.8，76 系统 CUDA 是 11.5。需要验证兼容性或安装匹配的 CUDA toolkit
6. **Python 3.8 兼容性**：DuoGraph3D 在 184 上用 Python 3.8，76 的 conceptgraph 环境是 3.10。代码已经用 `from __future__ import annotations` 处理了类型注解兼容性，应该可以正常工作

## 可选的并行化改进

76 有 5 张空闲 GPU，可以并行跑实验：

```bash
# 同时跑 5 个场景，每个场景用一张 GPU
for scene in room0 room1 room2 office0 office1; do
  CUDA_VISIBLE_DEVICES=$((i % 5)) \
    python run_conceptgraphs_engineered_parity.py \
    --scenes $scene --root $ARTIFACTS/$scene &
  i=$((i+1))
done
```

预计 8 场景串行 ~40 分钟，5 卡并行 ~10 分钟。
