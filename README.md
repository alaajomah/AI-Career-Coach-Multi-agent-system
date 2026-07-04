# 🎯 AI Career Coach

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-green?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-Multi--Agent-orange)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1-black?logo=openai)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A multi-agent AI system that helps users with **career guidance**, **resume review**, and **interview preparation** — powered by LangChain, OpenAI, FastAPI, and Streamlit.

A **Coordinator Agent** routes each user message to the right specialist agent (Career / Resume / Interview), and the Interview Agent runs a full **continuous mock-interview loop**: it asks a question, evaluates your answer, immediately asks the next one, and keeps going until you choose to end the session.

---

## ✨ Features

- **🧭 Career Agent** : generates a structured career roadmap, required skills, recommended projects, and certifications for a stated goal.
- **📄 Resume Agent** : reviews an uploaded resume against a career goal and returns an ATS score, strengths/weaknesses, missing skills, an improved summary, and section-by-section feedback.
- **🎤 Interview Agent** : runs a continuous mock interview:
  - generates a question for the target role/level
  - evaluates the candidate's answer (score, strengths, weaknesses, missing points, improved answer)
  - immediately generates the **next** question, avoiding repeats of anything already asked
  - loops until the user explicitly clicks **End Interview**, then returns a session summary (average score, transcript)
- **🤖 Coordinator Agent** : an LLM router that decides which agent should handle a message, with structured (Pydantic) output.
- **🔒 Privacy-aware resume handling** : resumes are parsed from PDF (via `Pypdf`) and PII (emails, phone numbers, LinkedIn/GitHub URLs) is masked **before** any text reaches the LLM.
- **📊 Observability** : Prometheus metrics (`/metrics`), structured logging, and per-request execution traces.
- **🖥️ Streamlit UI** : chat interface with agent-labeled responses, conditional resume upload, and an interview-mode input flow.
- **🐳 Dockerized** — backend and frontend each run in their own container, wired together with `docker-compose`.

---

## 🏗️ Architecture

```
                        ┌─────────────────────┐
                        │   Streamlit UI      │
                        │  (streamlit_app.py) │
                        └─────────┬───────────┘
                                  │ POST /chat
                                  ▼
                        ┌────────────────────┐
                        │     FastAPI        │
                        │      (app.py)      │
                        └─────────┬──────────┘
                                  │
                                  ▼
                        ┌──────────────────────┐
                        │  CoordinatorAgent    │
                        │  (coordinator.py)    │
                        │                      │
                        └───┬────────┬────────┬┘
                            │        │        │
                  ┌─────────▼──┐ ┌───▼─────┐ ┌▼───────────┐
                  │CareerAgent │ │ResumeAgent│ │InterviewAgent│
                  └────────────┘ └──────────┘ └─────────────┘
```

Each agent binds a `ChatOpenAI` model to a **Pydantic schema** via `with_structured_output(...)`, so every response is a validated, typed object — not free-form text.

Interview session state (current question, job role/level, answered-question history) lives in `interview_state.py`, keyed per `user_id`, so the Coordinator can tell an "answer to a pending question" apart from "a brand-new request" without re-running the router.

---

## 📁 Project Structure

```
.
├── app.py                      # FastAPI entrypoint (/chat, /metrics)
├── coordinator.py              # Routing + interview-loop orchestration
├── interview_state.py          # Per-user interview session store
├── memory.py                   # User memory (career goal, history)
├── logging_config.py           # Structured logging setup
├── traces.py                   # Per-request execution trace saving
├── metrics.py                  # Prometheus counters/histograms
├── ui_components.py            # Turns structured agent responses
├── streamlit.py                # Streamlit chat UI
│
├── agents/
│   ├── career_agent.py
│   ├── resume_agent.py
│   └── interview_agent.py
│
├── schemas/
│   ├── career.py               # CareerAdvice, CareerRoadmapStep, ...
│   ├── resume_review.py        # ResumeReview, MissingSkills, ...
│   ├── interview.py            # InterviewQuestion, InterviewEvaluation
│   └── router.py               # RouterDecision
│
├── prompts/
│   ├── career_prompt.txt
│   ├── resume_prompt.txt
│   ├── interview_question_prompt.txt
│   └── interview_evaluation_prompt.txt
│
├── utils/
│   ├── prompt_loader.py        # Loads prompts into ChatPromptTemplat
│   └── pii_masking.py          # mask_pii(text) 
│── Dockerfile                  # Backend image (FastAPI)
├── Dockerfile.streamlit        # Frontend image (Streamlit)
├── docker-compose.yml          # Wires backend + frontend together
├── .dockerignore
└── requirements.txt
```

---

## ⚙️ Setup

You can run this project either locally with a virtualenv, or with Docker Compose.

### Option A — Local (venv)

### 1. Clone & install dependencies

```bash
git clone https://github.com/alaajomah/AI-Career-Coach-Multi-agent-system.git
cd AI-Career-Coach-Multi-agent-system
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the backend (FastAPI)

```bash
uvicorn app:app --reload --port 8000
```

- Chat endpoint: `POST http://localhost:8000/chat`
- Metrics endpoint: `GET http://localhost:8000/metrics`

### 4. Run the UI (Streamlit)

In a separate terminal:

```bash
streamlit run streamlit.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).

![Streamlit Demo](UI.png)

### Option B — Docker Compose

#### 1. Add your `.env` file (same as above)

```env
OPENAI_API_KEY=your_openai_api_key_here
```

#### 2. Build and start both containers

```bash
docker compose up --build
```

This starts two containers:

| Service    | Image built from        | Port   | Notes                                   |
|------------|--------------------------|--------|------------------------------------------|
| `backend`  | `Dockerfile`              | `8000` | FastAPI app, loads `.env` via `env_file` |
| `frontend` | `Dockerfile.streamlit`    | `8501` | Streamlit UI, depends on `backend`, talks to it via `BACKEND_URL=http://backend:8000` |

#### 3. Open the app

- UI: `http://localhost:8501`
- Backend API: `http://localhost:8000`
- Metrics: `http://localhost:8000/metrics`

#### 4. Stop everything

```bash
docker compose down
```

`.dockerignore` keeps `venv/`, `__pycache__/`, `.env`, `.git`, and `.streamlit/` out of the build context, so secrets and local artifacts never end up baked into an image.

---

## 🧠 How the Interview Loop Works

1. User asks for interview prep → router selects `interview` → a session starts (`interview_state.start_session`) and the first question is generated and stored as *pending*.
2. User answers → the Coordinator sees an active session with a pending question, so it **skips the router entirely**, evaluates the answer, and generates the next question.
3. This repeats indefinitely.
4. User clicks **🏁 End Interview** → the UI sends the `__END_INTERVIEW__` sentinel → the Coordinator closes the session and returns a summary (questions answered, average score, full transcript).

---

## 🔐 Privacy

- Resumes are parsed locally from PDF using `Pypdf`— no external parsing service.
- `mask_pii()` strips emails, phone numbers, and LinkedIn/GitHub URLs from resume text **before** it is sent to the LLM.

---

## 🛠️ Tech Stack

- **LangChain** + **OpenAI (`gpt-4.1-mini`)** : structured LLM calls via Pydantic output parsing
- **FastAPI** : backend API
- **Streamlit** : chat UI
- **pypdf** : PDF text extraction
- **Prometheus client** : metrics
- **Pydantic** : schema validation for every agent response
- **Docker / docker-compose** — containerized backend + frontend



