# 🎯 AI Career Coach

A multi-agent AI system that helps users with **career guidance**, **resume review**, and **interview preparation** — powered by LangChain, OpenAI, FastAPI, and Streamlit.

A **Coordinator Agent** routes each user message to the right specialist agent (Career / Resume / Interview), and the Interview Agent runs a full **continuous mock-interview loop**: it asks a question, evaluates your answer, immediately asks the next one, and keeps going until you choose to end the session.

---

## ✨ Features

- **🧭 Career Agent** — generates a structured career roadmap, required skills, recommended projects, and certifications for a stated goal.
- **📄 Resume Agent** — reviews an uploaded resume against a career goal and returns an ATS score, strengths/weaknesses, missing skills, an improved summary, and section-by-section feedback.
- **🎤 Interview Agent** — runs a continuous mock interview:
  - generates a question for the target role/level
  - evaluates the candidate's answer (score, strengths, weaknesses, missing points, improved answer)
  - immediately generates the **next** question, avoiding repeats of anything already asked
  - loops until the user explicitly clicks **End Interview**, then returns a session summary (average score, transcript)
- **🤖 Coordinator Agent** — an LLM router that decides which agent should handle a message, with structured (Pydantic) output.
- **🔒 Privacy-aware resume handling** — resumes are parsed from PDF (via `PyMuPDF` / `fitz`) and PII (emails, phone numbers, LinkedIn/GitHub URLs) is masked **before** any text reaches the LLM.
- **📊 Observability** — Prometheus metrics (`/metrics`), structured logging, and per-request execution traces.
- **🖥️ Streamlit UI** — chat interface with agent-labeled responses, conditional resume upload, and an interview-mode input flow.

---

## 🏗️ Architecture

```
                        ┌────────────────────┐
                        │   Streamlit UI      │
                        │  (streamlit_app.py) │
                        └─────────┬───────────┘
                                  │ POST /chat
                                  ▼
                        ┌────────────────────┐
                        │     FastAPI          │
                        │      (app.py)        │
                        └─────────┬───────────┘
                                  │
                                  ▼
                        ┌────────────────────┐
                        │  CoordinatorAgent    │
                        │  (coordinator.py)    │
                        │                      │
                        │  1. Active interview │
                        │     session? →       │
                        │     evaluate + next  │
                        │     question         │
                        │  2. Else → LLM router│
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
├── app.py                     # FastAPI entrypoint (/chat, /metrics)
├── coordinator.py              # Routing + interview-loop orchestration
├── interview_state.py          # Per-user interview session store
├── memory.py                   # User memory (career goal, history)
├── logging_config.py           # Structured logging setup
├── traces.py                   # Per-request execution trace saving
├── metrics.py                  # Prometheus counters/histograms
├── streamlit_app.py            # Streamlit chat UI
│
├── agents/
│   ├── career_agent.py
│   ├── resume_agent.py
│   └── interview_agent.py
│
├── schemas/
│   ├── career.py                # CareerAdvice, CareerRoadmapStep, ...
│   ├── resume_review.py          # ResumeReview, MissingSkills, ...
│   ├── interview.py               # InterviewQuestion, InterviewEvaluation
│   └── router.py                  # RouterDecision
│
├── prompts/
│   ├── career_prompt.txt
│   ├── resume_prompt.txt
│   ├── interview_question_prompt.txt
│   └── interview_evaluation_prompt.txt
│
├── utils/
│   ├── prompt_loader.py           # Loads prompts/*.txt into ChatPromptTemplate
│   └── pii_masking.py              # mask_pii(text) -> str
│
└── requirements.txt
```

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/<your-username>/ai-career-coach.git
cd ai-career-coach
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
streamlit run streamlit_app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).

---

## 🔌 API Reference

### `POST /chat`

**Request body**

```json
{
  "user_id": "string",
  "message": "string",
  "resume": "string | null",
  "level": "Junior | Mid | Senior"
}
```

**Response body**

```json
{
  "agent": "career | resume | interview | unknown",
  "type": "advice | review | question | evaluation | session_end | no_session | error",
  "response": { "...": "shape depends on agent/type, see schemas/" },
  "memory": { "...": "stored user memory" }
}
```

To end an active interview session, send `message` as the exact control string `__END_INTERVIEW__` — this is a literal sentinel, never inferred from natural language, so a genuine interview answer can never accidentally end the session.

### `GET /metrics`

Prometheus-formatted metrics: request count, error count, and request latency.

---

## 🧠 How the Interview Loop Works

1. User asks for interview prep → router selects `interview` → a session starts (`interview_state.start_session`) and the first question is generated and stored as *pending*.
2. User answers → the Coordinator sees an active session with a pending question, so it **skips the router entirely**, evaluates the answer, records it in the session history, and generates the next question — passing in every previously-asked question so the model doesn't repeat itself.
3. This repeats indefinitely.
4. User clicks **🏁 End Interview** → the UI sends the `__END_INTERVIEW__` sentinel → the Coordinator closes the session and returns a summary (questions answered, average score, full transcript).

---

## 🔐 Privacy

- Resumes are parsed locally from PDF using `PyMuPDF` (`fitz`) — no external parsing service.
- `mask_pii()` strips emails, phone numbers, and LinkedIn/GitHub URLs from resume text **before** it is sent to the LLM.
- User IDs are hashed (SHA-256) before being written to logs.

---

## 🛠️ Tech Stack

- **LangChain** + **OpenAI (`gpt-4.1-mini`)** — structured LLM calls via Pydantic output parsing
- **FastAPI** — backend API
- **Streamlit** — chat UI
- **PyMuPDF (`fitz`)** — PDF text extraction
- **Prometheus client** — metrics
- **Pydantic** — schema validation for every agent response

---

## 📌 Roadmap / Ideas

- [ ] Persist interview/session state in Redis instead of in-memory
- [ ] Auto-end interview after N questions
- [ ] Multi-turn resume revision (iterate on suggestions)
- [ ] Auth + per-user history in a real database

---

## 📄 License

MIT — feel free to fork and adapt.
