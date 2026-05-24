# Mail Assistant

**An intelligent email classification and job application tracking system powered by ensemble machine learning.**

Mail Assistant automatically monitors your email accounts via IMAP, classifies incoming messages using a multi-model ensemble pipeline, detects job-related emails, extracts key entities (company, position, interview round), and tracks your application progress in real time.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Web Frontend (Next.js)                        │
│            Inbox · Kanban Board · Schedule · Settings             │
└────────────────────────────┬─────────────────────────────────────┘
                             │  REST + WebSocket
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Go Backend (Gin + SQLite)                      │
│         Account Management · IMAP Watcher · WebSocket Hub        │
└────────────────────────────┬─────────────────────────────────────┘
                             │  HTTP
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                 Python Backend (FastAPI + PyTorch)                │
│    Stage1 (ham/spam) → Stage2 (fine-grained) → Job Detection     │
│         Naive Bayes · LinearSVC · XGBoost · TextCNN              │
└──────────────────────────────────────────────────────────────────┘
```

## Features

- **Two-Stage Cascade Classification** — Stage 1 filters spam; Stage 2 categorizes ham into forums, promotions, social, updates, and verification codes.
- **4-Model Ensemble per Stage** — Naive Bayes, Calibrated LinearSVC, XGBoost (TF-IDF), and TextCNN (PyTorch) with soft/hard fusion.
- **Job Email Intelligence** — Detects recruitment emails, classifies application stage, and extracts named entities (company, position, round, location, timeline).
- **Real-Time IMAP Monitoring** — Watches multiple email accounts concurrently with instant WebSocket push to the frontend.
- **Application Tracker** — Kanban-style board to manage job applications, interview reminders, and stage progression.
- **Secure Credential Storage** — AES-256-GCM encryption for all stored email passwords.

## Modules

| Module | Tech Stack | Description |
|--------|-----------|-------------|
| `go-backend` | Go, Gin, GORM, SQLite, go-imap, Gorilla WebSocket | API gateway, IMAP watcher, account & email persistence |
| `python-backend` | Python, FastAPI, PyTorch, scikit-learn, XGBoost | ML inference service with cascade classification and NER |
| `web-frontend` | Next.js 16, React 19, Tailwind CSS 4, shadcn/ui, Framer Motion | Responsive dashboard with real-time updates |

## Getting Started

### Prerequisites

- Go 1.22+
- Python 3.10+
- Node.js 20+
- pnpm (or npm)

### 1. Start the Python ML Service

```bash
cd python-backend
pip install -r requirements.txt

# Train models (first time only)
python -m mail_vote train --stage all

# Start the API server
python -m mail_vote serve --port 8081
```

### 2. Start the Go Backend

```bash
cd go-backend
go run cmd/server/main.go
```

The API server starts on port `8080` by default.

### 3. Start the Web Frontend

```bash
cd web-frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Configuration

### Go Backend

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | `8080` | HTTP server port |
| `ML_SERVICE_URL` | `http://127.0.0.1:8081` | Python backend URL |
| `DB_PATH` | `data.db` | SQLite database file path |
| `ENCRYPTION_KEY` | — | AES-256 key for password encryption |

### Python Backend

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MAIL_VOTE_ARTIFACT_ROOT` | `./artifacts` | Model artifacts directory |
| `MAIL_VOTE_CORS_ORIGINS` | `*` | Allowed CORS origins |
| `MAIL_VOTE_API_KEY` | — | Optional API key for authentication |

### Web Frontend

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8080` | Go backend URL |

## API Reference

### Go Backend

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/accounts` | Add an email account |
| `GET` | `/api/emails` | List classified emails (paginated) |
| `GET` | `/api/stats` | Get label distribution statistics |
| `GET` | `/api/applications` | List job applications |
| `PATCH` | `/api/applications/:id` | Update application stage |
| `GET` | `/ws` | WebSocket connection for real-time updates |

### Python Backend

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/predict` | Classify a single email |
| `POST` | `/v1/job/predict` | Job detection + NER extraction |
| `POST` | `/v1/evaluate/batch` | Batch evaluation on labeled data |
| `GET` | `/v1/health` | Model metadata and health check |

## Model Architecture

```
Input Email
    │
    ▼
┌─────────────────────────────────────┐
│  Stage 1: Binary Classification     │
│  (ham / spam)                       │
│                                     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐ │
│  │ NB  │ │ SVC │ │ XGB │ │ TCNN │ │
│  └──┬──┘ └──┬──┘ └──┬──┘ └──┬───┘ │
│     └───────┴───────┴───────┘      │
│              Fusion                  │
└─────────────────┬───────────────────┘
                  │ (if ham)
                  ▼
┌─────────────────────────────────────┐
│  Stage 2: Fine-Grained Labels       │
│  (forum / promo / social / update / │
│   verification)                     │
│                                     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐ │
│  │ NB  │ │ SVC │ │ XGB │ │ TCNN │ │
│  └──┬──┘ └──┬──┘ └──┬──┘ └──┬───┘ │
│     └───────┴───────┴───────┘      │
│              Fusion                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Job Detection & NER                │
│  - Is this a job email?             │
│  - Company / Position / Round /     │
│    Location / Timeline              │
└─────────────────────────────────────┘
```

**Fusion Modes:**
- **Soft** — Weighted average of sklearn probabilities and TextCNN softmax output (configurable weight).
- **Hard** — Majority voting across all four models.

## Training

```bash
cd python-backend

# Train all stages
python -m mail_vote train --stage all

# Train specific stage
python -m mail_vote train --stage 1

# Custom parameters
python -m mail_vote train \
  --stage all \
  --fusion-w 0.5 \
  --textcnn-epochs 6 \
  --batch-size 64 \
  --max-len 400 \
  --max-features 50000

# Train job detection models
python -m mail_vote job-train

# Evaluate on test set
python -m mail_vote eval-testset
```

## Project Structure

```
mail-assistant/
├── go-backend/
│   ├── cmd/server/          # Application entry point
│   └── internal/
│       ├── classifier/      # ML service HTTP client
│       ├── config/          # Environment configuration
│       ├── handler/         # REST API handlers
│       ├── imap/            # IMAP watcher & manager
│       ├── model/           # GORM models & database
│       └── ws/              # WebSocket hub
├── python-backend/
│   ├── artifacts/           # Trained model weights (gitignored)
│   ├── data/                # Training datasets (gitignored)
│   └── src/mail_vote/
│       ├── api_app.py       # FastAPI application
│       ├── cascade.py       # Two-stage cascade pipeline
│       ├── fusion.py        # Model fusion strategies
│       ├── sklearn_ensemble.py  # Traditional ML models
│       ├── textcnn.py       # PyTorch TextCNN
│       └── job/             # Job detection & NER
└── web-frontend/
    └── src/
        ├── app/             # Next.js pages
        ├── components/      # UI components
        └── lib/             # API client & hooks
```

## Contributing

We welcome contributions from the community. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
