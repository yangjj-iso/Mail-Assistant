<p align="center">
  <img src="https://img.icons8.com/fluency/96/mail--v1.png" alt="Mail Assistant Logo" width="96" height="96">
</p>

<h1 align="center">Mail Assistant</h1>

<p align="center">
  <strong>AI-Powered Email Classification & Job Application Tracking</strong>
</p>

<p align="center">
  <a href="#features"><img src="https://img.shields.io/badge/Features-8+-blue?style=flat-square" alt="Features"></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Go-1.22+-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js&logoColor=white" alt="Next.js"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat-square&logo=pytorch&logoColor=white" alt="PyTorch"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#features">Features</a> •
  <a href="#model-pipeline">Model Pipeline</a> •
  <a href="#api-reference">API Reference</a>
</p>

---

## Overview

Mail Assistant is an intelligent email management system that automatically monitors your email accounts via IMAP, classifies incoming messages using a **multi-model ensemble pipeline**, detects job-related emails, extracts key entities (company, position, interview time, round), and tracks your application progress in real-time through an intuitive Kanban board.

<!-- PLACEHOLDER_DEMO_GIF -->

---

## Features

<table>
<tr>
<td width="50%">

### 🎯 Smart Classification
- **Two-Stage Cascade** — Stage 1 filters spam; Stage 2 categorizes into 7 fine-grained labels
- **4-Model Ensemble** — Naive Bayes, LinearSVC, XGBoost, TextCNN with soft/hard fusion
- **99.4% Accuracy** — Production-ready classification performance

</td>
<td width="50%">

### 💼 Job Tracking
- **Auto-Detection** — Identifies recruitment emails automatically
- **Entity Extraction** — BiLSTM-CRF extracts company, position, time, round, location
- **Kanban Board** — Drag-and-drop application stage management

</td>
</tr>
<tr>
<td width="50%">

### ⚡ Real-Time Sync
- **IMAP Monitoring** — Watches multiple accounts concurrently
- **WebSocket Push** — Instant updates to frontend
- **Interview Reminders** — Browser notifications for upcoming interviews

</td>
<td width="50%">

### 🔒 Security First
- **AES-256-GCM** — Encrypted credential storage
- **No External LLM** — All models trained from scratch, data stays local
- **Self-Hosted** — Full control over your data

</td>
</tr>
</table>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Web Frontend (Next.js 16)                          │
│                   Dashboard • Inbox • Kanban • Schedule • Settings          │
│                        React 19 • Tailwind CSS 4 • shadcn/ui                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ REST API + WebSocket
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Go Backend (Gin + GORM)                            │
│              Account Management • IMAP Watcher • WebSocket Hub              │
│                    SQLite • AES-256-GCM • Interview Reminder                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Python ML Service (FastAPI)                            │
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │   Stage 1   │───▶│   Stage 2   │───▶│ Job Detect  │───▶│  NER (CRF)  │ │
│   │  ham/spam   │    │  7 labels   │    │  is_job?    │    │  entities   │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                                             │
│          NB + SVC + XGBoost + TextCNN (PyTorch) → Ensemble Fusion          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Framer Motion, @dnd-kit |
| **Backend** | Go 1.22, Gin, GORM, SQLite, go-imap, Gorilla WebSocket |
| **ML Service** | Python 3.10, FastAPI, PyTorch 2.0, scikit-learn, XGBoost, TorchCRF |
| **Models** | Naive Bayes, Calibrated LinearSVC, XGBoost, TextCNN, BiLSTM-CRF |

---

## Quick Start

### Prerequisites

- Go 1.22+
- Python 3.10+ with CUDA (optional, for GPU training)
- Node.js 20+
- pnpm or npm

### 1. Clone & Setup

```bash
git clone https://github.com/yangjj-iso/Mail-Assistant.git
cd Mail-Assistant
```

### 2. Start Python ML Service

```bash
cd python-backend
pip install -r requirements.txt

# Train models (first time only, ~10 min)
python -m mail_vote train --stage all
python -m mail_vote job-train

# Start API server
python -m mail_vote serve --port 8081
```

### 3. Start Go Backend

```bash
cd go-backend
go run cmd/server/main.go
# Server starts on :8080
```

### 4. Start Web Frontend

```bash
cd web-frontend
pnpm install && pnpm dev
# Open http://localhost:3000
```

---

## Model Pipeline

```
                              Input Email (subject + body)
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
          ┌─────────────────┐                         ┌─────────────────┐
          │    TF-IDF       │                         │   TextCNN       │
          │  Vectorizer     │                         │   (PyTorch)     │
          └────────┬────────┘                         └────────┬────────┘
                   │                                           │
     ┌─────────────┼─────────────┐                            │
     ▼             ▼             ▼                            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐                  ┌─────────────┐
│   NB    │  │   SVC   │  │   XGB   │                  │  Conv1D ×3  │
│ (0.33)  │  │ (0.33)  │  │ (0.33)  │                  │  MaxPool    │
└────┬────┘  └────┬────┘  └────┬────┘                  │  FC + Softmax│
     │            │            │                       └──────┬──────┘
     └────────────┴────────────┘                              │
                   │                                          │
                   ▼                                          │
          ┌─────────────────┐                                 │
          │  Sklearn Proba  │◀────────────────────────────────┘
          │    (weight α)   │         TextCNN Proba (weight 1-α)
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  Soft Fusion    │
          │  argmax(blend)  │
          └────────┬────────┘
                   │
                   ▼
              Final Label
```

**Fusion Strategy:**
- `α = 0.5` by default (equal weight sklearn vs TextCNN)
- Soft fusion: weighted average of probability distributions
- Hard fusion: majority voting (fallback)

---

## API Reference

### Go Backend (`:8080`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/accounts` | Add email account (IMAP) |
| `GET` | `/api/accounts` | List all accounts |
| `GET` | `/api/emails` | List emails (paginated, filterable) |
| `GET` | `/api/stats` | Classification statistics |
| `GET` | `/api/stats/job` | Job application statistics |
| `GET` | `/api/applications` | List job applications |
| `GET` | `/api/applications/:id/emails` | Get related emails |
| `GET` | `/api/applications/:id/ical` | Export to iCal |
| `PATCH` | `/api/applications/:id` | Update stage/notes |
| `GET` | `/ws` | WebSocket (real-time updates) |

### Python ML Service (`:8081`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/predict` | Classify email (cascade) |
| `POST` | `/v1/job/predict` | Job detection + NER |
| `POST` | `/v1/job/feedback` | Submit correction (active learning) |
| `GET` | `/v1/health` | Model metadata & health |

---

## Configuration

### Environment Variables

```bash
# Go Backend
PORT=8080
ML_SERVICE_URL=http://127.0.0.1:8081
DB_PATH=data.db
ENCRYPTION_KEY=your-32-byte-key

# Python Backend
MAIL_VOTE_ARTIFACT_ROOT=./artifacts
MAIL_VOTE_CORS_ORIGINS=*

# Web Frontend
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WS_URL=ws://localhost:8080/ws
```

---

## Project Structure

```
Mail-Assistant/
├── go-backend/
│   ├── cmd/server/              # Entry point
│   └── internal/
│       ├── classifier/          # ML service client
│       ├── handler/             # REST handlers + reminder service
│       ├── imap/                # IMAP watcher
│       ├── model/               # GORM models
│       └── ws/                  # WebSocket hub
│
├── python-backend/
│   ├── artifacts/               # Trained models (gitignored)
│   ├── data/                    # Datasets (gitignored)
│   └── src/mail_vote/
│       ├── api_app.py           # FastAPI app
│       ├── cascade.py           # Two-stage pipeline
│       ├── fusion.py            # Ensemble fusion
│       ├── textcnn.py           # PyTorch TextCNN
│       └── job/                 # Job detection & BiLSTM-CRF NER
│
└── web-frontend/
    └── src/
        ├── app/                 # Next.js pages
        ├── components/          # UI components
        └── lib/                 # API client & hooks
```

---

## Training

```bash
cd python-backend

# Full training pipeline
python -m mail_vote train --stage all

# Train with custom parameters
python -m mail_vote train \
  --stage all \
  --fusion-w 0.5 \
  --textcnn-epochs 6 \
  --batch-size 64 \
  --max-len 400

# Train job detection models
python -m mail_vote job-train

# Evaluate on test set
python -m mail_vote eval-testset
```

---

## Performance

| Model | Stage 1 (ham/spam) | Stage 2 (7-class) | Job Detection |
|-------|-------------------|-------------------|---------------|
| Naive Bayes | 97.2% | 94.1% | 96.8% |
| LinearSVC | 98.1% | 95.3% | 97.2% |
| XGBoost | 98.4% | 96.2% | 97.8% |
| TextCNN | 98.6% | 97.1% | 98.3% |
| **Ensemble** | **99.1%** | **99.4%** | **99.2%** |

*Accuracy on held-out test set*

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/yangjj-iso">yangjj-iso</a>
</p>
