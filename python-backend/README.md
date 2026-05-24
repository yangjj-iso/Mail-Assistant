# Python Backend — 级联邮件分类服务

基于 TF-IDF + TextCNN 融合的两阶段级联邮件分类系统。

## 架构

```
Stage 1: ham / spam 二分类
    ↓ (ham)
Stage 2: 细分类 → forum / promotions / social_media / updates / verify_code
```

每阶段使用 4 个模型集成：
- Naive Bayes（TF-IDF）
- Calibrated LinearSVC（TF-IDF）
- XGBoost（TF-IDF）
- TextCNN（PyTorch，词级别卷积）

融合模式：
- **soft**：sklearn 三模型平均概率与 TextCNN softmax 加权融合，权重 w 可调
- **hard**：四路模型各自 argmax 后多数投票

## 环境准备

```bash
pip install -r requirements.txt
```

依赖：numpy, pandas, scikit-learn, xgboost, torch, fastapi, uvicorn, datasets, tqdm

## 使用方式

### 训练

```bash
python -m src.mail_vote train --stage all
```

主要参数：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--stage` | all | 训练阶段：1 / 2 / all |
| `--coarse-csv` | data/粗.csv | Stage1 数据路径 |
| `--max-samples-coarse` | 25000 | 粗数据子采样上限，0 为全量 |
| `--fusion-w` | 0.5 | sklearn 概率权重（soft 模式） |
| `--textcnn-epochs` | 6 | TextCNN 训练轮次 |
| `--batch-size` | 64 | 批大小 |
| `--max-len` | 400 | 文本截断长度 |
| `--save-cm` | false | 保存混淆矩阵 PNG |

### 单条推理

```bash
python -m src.mail_vote predict --text "Your email text here"
python -m src.mail_vote predict --file email.txt --mode hard
```

### 测试集评估

```bash
python -m src.mail_vote eval-testset --dataset data/labeled_email_testset/dataset.json
```

### 启动 API 服务

```bash
python -m src.mail_vote serve --port 8081
```

服务参数：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 0.0.0.0 | 监听地址 |
| `--port` | 8081 | 端口 |
| `--reload` | false | 开发热重载 |
| `--api-key` | 空 | 非空则要求请求头 X-API-Key |
| `--cors-origins` | 空 | 逗号分隔的允许跨域源 |

## API 接口

### GET /v1/health

健康检查，返回模型元信息。

```json
{
  "status": "ok",
  "stage1_class_names": ["ham", "spam"],
  "stage2_class_names": ["forum", "promotions", "social_media", "updates", "verify_code"],
  "fusion_weight_sklearn_stage1": 0.5,
  "fusion_weight_sklearn_stage2": 0.5
}
```

### POST /v1/predict

单条邮件分类。

请求体：
```json
{
  "text": "邮件全文",
  "mode": "soft",
  "fusion_weight_sklearn_stage1": 0.6,
  "fusion_weight_sklearn_stage2": null
}
```

响应：
```json
{
  "stage1_label": "ham",
  "stage1_index": 0,
  "final": "good",
  "stage2_label": "updates",
  "stage2_index": 3,
  "effective_fusion_weight_stage1": 0.6,
  "effective_fusion_weight_stage2": 0.5
}
```

### POST /v1/evaluate/batch

批量带金标评估。

请求体：
```json
{
  "items": [
    {"text": "...", "gold_stage1": "ham", "gold_stage2": "updates"}
  ],
  "mode": "soft",
  "include_reports": false
}
```

## 目录结构

```
python-backend/
├── src/mail_vote/
│   ├── __main__.py        # CLI 入口
│   ├── api_app.py         # FastAPI 应用
│   ├── cascade.py         # 级联加载与推理
│   ├── data_io.py         # 数据加载
│   ├── eval_testset.py    # 测试集评估
│   ├── fusion.py          # 概率融合与投票
│   ├── schemas.py         # Pydantic 模型
│   ├── sklearn_ensemble.py # TF-IDF 三模型集成
│   ├── stages.py          # 单阶段训练/评估
│   └── textcnn.py         # TextCNN 模型
├── artifacts/             # 训练产物
│   ├── stage1/            # ham/spam 模型
│   └── stage2/            # 细分类模型
├── data/                  # 训练数据
├── scripts/               # 工具脚本
└── requirements.txt
```

## 注意事项

- 当前模型仅在英文数据集上训练，中文邮件分类效果不佳
- sklearn 版本差异可能产生警告，不影响推理结果
- GPU 可用时自动使用 CUDA 加速 TextCNN 推理
