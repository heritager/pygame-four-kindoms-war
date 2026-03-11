# Google Colab 一键训练

这个项目已经提供一条命令跑完整训练流程（采样 -> 训练 -> 评估 -> 输出摘要）：

- 入口模块：`python -m four_kingdoms.ml.one_click_train`
- 训练后会默认更新运行时模型路径（`models/mlp_policy.npz` 或 `models/linear_policy.npz`）

## 1. Colab 初始化

```python
from google.colab import drive
drive.mount('/content/drive')
```

```bash
%cd /content
!git clone https://github.com/heritager/pygame-four-kindoms-war.git
%cd /content/pygame-four-kindoms-war
!pip install -r requirements.txt
```

## 2. 一键跑完整流程（推荐 MLP）

```bash
!python -m four_kingdoms.ml.one_click_train \
  --dataset-dir /content/drive/MyDrive/four_kingdoms/data/expert_run_01 \
  --output-model /content/drive/MyDrive/four_kingdoms/models/mlp_policy_run_01.npz \
  --summary-json /content/drive/MyDrive/four_kingdoms/models/mlp_run_01_summary.json \
  --model-type mlp \
  --games 80 \
  --max-decisions 1500 \
  --epochs 12 \
  --batch-size 64 \
  --learning-rate 0.02 \
  --hidden-sizes 64,32 \
  --eval-games 16 \
  --eval-opponent normal
```

## 3. 更快试跑（先确认流程）

```bash
!python -m four_kingdoms.ml.one_click_train \
  --dataset-dir data/expert_smoke \
  --output-model models/mlp_policy_smoke.npz \
  --summary-json stats/ml_runs/smoke.json \
  --games 2 \
  --max-decisions 120 \
  --epochs 2 \
  --eval-games 2 \
  --eval-max-rounds 20 \
  --eval-max-moves 120
```

## 4. 线性模型版本（更省资源）

```bash
!python -m four_kingdoms.ml.one_click_train \
  --model-type linear \
  --dataset-dir /content/drive/MyDrive/four_kingdoms/data/expert_linear_01 \
  --output-model /content/drive/MyDrive/four_kingdoms/models/linear_policy_run_01.npz \
  --epochs 10 \
  --learning-rate 0.05 \
  --eval-games 12
```

## 参数说明（常用）

- `--games`：采样局数，越大越慢但数据更充分
- `--max-decisions`：每局最多记录多少决策样本
- `--model-type`：`mlp` 或 `linear`
- `--eval-games`：评估对局数量
- `--no-update-default-policy`：不覆盖仓库默认运行时模型（通常不建议）
- `--skip-eval`：只训练不评估

## 输出结果

- 训练模型：`--output-model` 指定路径
- 运行摘要：`--summary-json` 指定路径（包含数据量、训练参数、评估指标）
- 终端输出中会打印 `win_rate`、`wins`、`duration_seconds`
