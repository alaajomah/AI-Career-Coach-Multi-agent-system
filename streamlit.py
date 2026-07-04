import streamlit as st
import requests
import io
import os

from pypdf import PdfReader
from utils.pii_masking import mask_pii
from ui_components import render_agent_response, is_awaiting_answer

# BACKEND_URL lets this reach the FastAPI service by container/service name
# when run in Docker (e.g. "http://backend:8000"). Defaults to localhost
# for local development where both run on your machine directly.
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
API_URL = f"{BACKEND_URL}/chat"
END_INTERVIEW_URL = f"{BACKEND_URL}/end_interview"

st.set_page_config(
    page_title="Career Coach AI",
    page_icon="🦾",
    layout="wide",
)

# -------------------------
# Global styling
# -------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at top left, rgba(255,159,67,0.10), transparent 45%),
                        radial-gradient(circle at bottom right, rgba(243,104,224,0.10), transparent 45%);
        }

        .block-container {padding-top: 2rem; max-width: 900px;}

        h1 {
            font-weight: 800;
            background: linear-gradient(90deg, #F368E0, #FF9F43, #FECA57);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        [data-testid="stChatMessage"] {
            border-radius: 16px;
            padding: 10px 8px;
            margin-bottom: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.12);
        }

        /* User message bubble */
        [data-testid="stChatMessage"]:has(img[alt="user avatar"]) {
            background: rgba(243, 104, 224, 0.10);
            border: 1px solid rgba(243, 104, 224, 0.30);
        }

        /* Assistant message bubble */
        [data-testid="stChatMessage"]:has(img[alt="assistant avatar"]) {
            background: rgba(255, 159, 67, 0.08);
            border: 1px solid rgba(255, 159, 67, 0.25);
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255,255,255,0.08);
            background: linear-gradient(180deg, rgba(243,104,224,0.10), rgba(255,159,67,0.06));
        }

        section[data-testid="stSidebar"] h3 {
            color: #FF9F43;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(90deg, #F368E0, #FF9F43);
            color: white;
            border: none;
            font-weight: 600;
            transition: opacity 0.2s ease, transform 0.1s ease;
        }
        .stButton > button:hover {
            opacity: 0.88;
            color: white;
            transform: scale(1.02);
        }

        /* Chat input box */
        [data-testid="stChatInput"] {
            border-radius: 12px;
            border: 1px solid rgba(243, 104, 224, 0.35);
        }

        /* Progress bars (used for scores) */
        .stProgress > div > div {
            background: linear-gradient(90deg, #F368E0, #FF9F43, #FECA57);
        }

        hr {
            border-top: 1px solid rgba(255,159,67,0.25);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Career Coach")
st.caption("Your AI-powered career coach, resume reviewer, and interview simulator.")

# -------------------------
# Session State
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role, content} or {role, reply, agent_used}

if "resume" not in st.session_state:
    st.session_state.resume = ""

if "show_resume_section" not in st.session_state:
    st.session_state.show_resume_section = False

# -------------------------
# Sidebar: profile + resume
# -------------------------
with st.sidebar:
    st.subheader("👨🏻‍💻 Your Profile")
    user_id = st.text_input("User ID", " ")
    career_goal = st.text_input("Career Goal", "AI Engineer")
    level = st.selectbox("Experience Level", ["Junior", "Mid", "Senior"], index=0)

    st.divider()

    resume_header_col, resume_toggle_col = st.columns([5, 1])
    with resume_header_col:
        st.subheader("📄 Resume")
    with resume_toggle_col:
        toggle_icon = "✖️" if st.session_state.show_resume_section else "✏️"
        if st.button(
            toggle_icon,
            key="toggle_resume_section",
            help="Show/hide the resume upload & edit box",
        ):
            st.session_state.show_resume_section = not st.session_state.show_resume_section
            st.rerun()

    if st.session_state.show_resume_section:
        uploaded_file = st.file_uploader("Upload Resume", type=["txt", "pdf"])

        if uploaded_file:
            try:
                file_bytes = uploaded_file.read()

                if uploaded_file.name.lower().endswith(".pdf"):
                    reader = PdfReader(io.BytesIO(file_bytes))
                    resume_text = ""
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            resume_text += page_text + "\n"
                else:
                    resume_text = file_bytes.decode("utf-8", errors="ignore")

                st.session_state.resume = resume_text.strip()
                st.success("Resume uploaded ✅")

            except Exception as e:
                st.warning(f"Could not read this file: {e}")

        with st.expander("Or paste resume text (masked preview)", expanded=True):
            resume_text_manual = st.text_area(
                "Resume text",
                value=mask_pii(st.session_state.resume),
                height=180,
                label_visibility="collapsed",
            )
            if resume_text_manual:
                st.session_state.resume = resume_text_manual

    # Status line always visible, regardless of whether the box is open
    if st.session_state.resume:
        st.caption(f"✅ Resume loaded ({len(st.session_state.resume)} chars) · click ✏️ to edit")
    else:
        st.caption("No resume added yet · click ✏️ to upload one")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# -------------------------
# Ends the interview and appends the final cumulative report to chat
# -------------------------
def end_interview_flow(user_id: str):
    with st.spinner("Preparing your final evaluation..."):
        try:
            end_response = requests.post(
                END_INTERVIEW_URL, json={"user_id": user_id}, timeout=60
            )
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Could not reach the backend: {e}")
            return

    if end_response.status_code == 200:
        data = end_response.json()
        if "error" in data:
            st.error(f"❌ {data['error']}")
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "reply": data.get("response", {}),
                "agent_used": data.get("agent", "interview"),
            })
            st.rerun()
    else:
        st.error(f"❌ Backend Error: {end_response.status_code}")


# -------------------------
# Chat history
# -------------------------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_agent_response(msg["reply"], msg.get("agent_used", "coordinator"))

            is_last_message = (i == len(st.session_state.messages) - 1)
            if is_last_message and is_awaiting_answer(msg["reply"], msg.get("agent_used")):
                if st.button("🏁 End Interview", key=f"end_interview_{i}"):
                    end_interview_flow(user_id)
        else:
            st.markdown(msg["content"])

# -------------------------
# User input
# -------------------------
user_input = st.chat_input("Ask about your career, resume, or interview prep...")

if user_input:

    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # 🔐 Masking before sending
    safe_resume = mask_pii(st.session_state.resume or "")
    safe_message = mask_pii(user_input or "")

    payload = {
        "user_id": user_id,
        "message": safe_message,
        "resume": safe_resume,
        "level": level,
    }

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=60)
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Could not reach the backend: {e}")
                response = None

        if response is not None:
            if response.status_code == 200:
                data = response.json()

                if "error" in data:
                    st.error(f"❌ Backend error: {data['error']}")
                else:
                    reply = data.get("response", "No response received.")
                    agent_used = data.get("agent", "coordinator")

                    render_agent_response(reply, agent_used)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "reply": reply,
                        "agent_used": agent_used,
                    })

                    if is_awaiting_answer(reply, agent_used):
                        if st.button("🏁 End Interview", key="end_interview_live"):
                            end_interview_flow(user_id)
            else:
                st.error(f"❌ Backend Error: {response.status_code}")