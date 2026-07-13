# Dafoor AI — Study Suite

An AI-powered study tool that generates quizzes from your PDF documents using Google Gemini.

## Tech Stack

- **Backend**: FastAPI + Uvicorn (Python 3.11)
- **Database**: SQLite (embedded, no external DB needed)
- **AI**: Google Gemini API (key provided per-request by the user)
- **Frontend**: Vanilla HTML/CSS/JS (served as a static SPA)

---

## Local Development

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run the dev server
./run.sh
# App will be available at http://127.0.0.1:8000
```

---

## Docker

### Build locally

```bash
docker build -t dafoor-ai .
```

### Run locally

```bash
docker run -p 8080:8080 dafoor-ai
# App will be available at http://localhost:8080
```

---

## Deploy to Google Cloud Run

### Prerequisites

1. [Install the `gcloud` CLI](https://cloud.google.com/sdk/docs/install)
2. Authenticate: `gcloud auth login`
3. Set your project: `gcloud config set project YOUR_PROJECT_ID`
4. Enable required APIs:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     artifactregistry.googleapis.com
   ```
5. Create an Artifact Registry Docker repository:
   ```bash
   gcloud artifacts repositories create dafoor-ai \
     --repository-format=docker \
     --location=us-central1 \
     --description="Dafoor AI container images"
   ```

### Option A — Manual deploy (one command)

```bash
gcloud run deploy dafoor-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --port 8080
```

### Option B — Cloud Build CI/CD pipeline

```bash
# Submit a one-off build
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions _REGION=us-central1,_REPO=dafoor-ai,_SERVICE=dafoor-ai \
  .
```

To automate on every `git push`, connect your repository to a **Cloud Build Trigger** in the GCP Console and point it at `cloudbuild.yaml`.

### Override substitution variables

| Variable   | Default        | Description                         |
|------------|---------------|-------------------------------------|
| `_REGION`  | `us-central1` | GCP region for Cloud Run & registry |
| `_REPO`    | `dafoor-ai`   | Artifact Registry repository name  |
| `_SERVICE` | `dafoor-ai`   | Cloud Run service name              |

---

## Environment Variables (Cloud Run)

| Variable      | Default        | Description                          |
|---------------|---------------|--------------------------------------|
| `PORT`        | `8080`        | Port Uvicorn listens on (set by Cloud Run automatically) |
| `ENVIRONMENT` | `production`  | Runtime environment label            |

> **Note on the Gemini API key**: The API key is supplied by each user at quiz-generation time and is never stored server-side.

---

## API Endpoints

| Method | Path                    | Description                  |
|--------|------------------------|------------------------------|
| GET    | `/health`              | Health check (Cloud Run probe) |
| POST   | `/api/auth/signup`     | Register a new account       |
| POST   | `/api/auth/login`      | Log in                       |
| POST   | `/api/auth/logout`     | Log out                      |
| GET    | `/api/auth/me`         | Get current user             |
| POST   | `/api/pdfs/upload`     | Upload a PDF                 |
| GET    | `/api/pdfs`            | List uploaded PDFs           |
| DELETE | `/api/pdfs/{id}`       | Delete a PDF                 |
| POST   | `/api/quizzes/generate`| Generate a quiz from a PDF   |
| POST   | `/api/quizzes/submit`  | Submit quiz answers          |
| GET    | `/api/analytics`       | Get performance analytics    |

Interactive API docs available at `/docs` when running.

---

## Project Structure

```
ai-study-suite/
├── backend/
│   ├── main.py          # FastAPI app & all API routes
│   ├── auth.py          # Password hashing & session management
│   ├── database.py      # SQLite helpers
│   ├── pdf_parser.py    # Gemini-powered quiz generation
│   ├── requirements.txt
│   └── data/            # Runtime data (gitignored)
│       └── pdfs/        # Uploaded PDF files
├── static/              # Frontend SPA (HTML/CSS/JS)
├── Dockerfile           # Multi-stage production image
├── .dockerignore
├── cloudbuild.yaml      # Cloud Build CI/CD pipeline
├── run.sh               # Local development launcher
└── README.md
```
