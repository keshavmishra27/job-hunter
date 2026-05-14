# Job Hunter 

AI-powered internship discovery + ranking + outreach assistant.

## Architecture

```
Resume → Profile Builder → Job Fetchers → Normalizer → Deduper → Ranker → Draft Generator → Review Queue → SMTP Sender → Sent Log
```

## Quick Start

### 1. Backend

```bash
cd d:\kfiles\job-hunter
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill in your keys
copy .env.example .env

# Run the API
uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the Swagger UI.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Modules

| File | Responsibility |
|------|---------------|
| `backend/modules/resume_parser.py` | PDF → structured profile |
| `backend/modules/fetchers/internshala_fetcher.py` | Internshala scraper |
| `backend/modules/fetchers/indeed_fetcher.py` | Indeed India scraper |
| `backend/modules/fetchers/linkedin_fetcher.py` | LinkedIn via Playwright |
| `backend/modules/normalizer.py` | Common job schema |
| `backend/modules/deduper.py` | Hash-based dedup |
| `backend/modules/ranker.py` | Hard filters + soft scoring |
| `backend/modules/vector_store.py` | FAISS semantic search |
| `backend/modules/draft_generator.py` | LLM outreach drafts |
| `backend/modules/sender.py` | SMTP with throttle + retry |

## Environment Variables

See `.env.example`. Minimum required for Phase 1:

- `OPENAI_API_KEY`, `GROQ_API_KEY`, or `OPENROUTER_KEY` — for draft generation (uses best available free model on OpenRouter)
- `SMTP_USER` + `SMTP_PASSWORD` — Gmail app password for sending

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/profile/upload-resume` | Upload PDF |
| POST | `/profile/parse/{id}` | Extract profile |
| GET | `/profile/{user_id}` | Get profile |
| POST | `/jobs/fetch` | Fetch + rank jobs |
| GET | `/jobs/ranked/{user_id}` | Top ranked jobs |
| POST | `/drafts/generate/{user}/{job}` | Generate draft |
| GET | `/drafts/{user_id}` | List drafts |
| PATCH | `/drafts/{id}` | Edit draft |
| POST | `/drafts/approve/{id}` | Approve draft |
| POST | `/send/` | Send approved draft |
| GET | `/send/log` | Sent log |
| GET | `/dashboard/stats/{user}` | Stats |

## MVP Phase Order

- **Phase 1** (now): Resume, profile, Internshala, ranking, draft generation 
- **Phase 2**: Approval UI, SMTP, dedup 
- **Phase 3**: LinkedIn + Indeed, FAISS search, follow-up tracker