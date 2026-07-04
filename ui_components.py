"""
ui_components.py
-----------------
Turns structured agent responses (dicts / lists coming back from the
Career / Resume / Interview agents) into readable Streamlit UI instead
of dumping raw Python dicts on screen.

Works generically for ANY nested dict/list your agents return, with a
few special cases (roadmap steps, scores) styled more richly.
"""

import streamlit as st

AGENT_META = {
    "career": {"icon": "🧭", "name": "Career Coach", "color": "#6C5CE7"},
    "resume": {"icon": "📄", "name": "Resume Reviewer", "color": "#00B894"},
    "interview": {"icon": "🎤", "name": "Interview Coach", "color": "#0984E3"},
    "router_fallback": {"icon": "🤖", "name": "Assistant", "color": "#636E72"},
    "coordinator": {"icon": "🤖", "name": "Assistant", "color": "#636E72"},
}


def agent_badge(agent_used: str):
    meta = AGENT_META.get(agent_used, AGENT_META["coordinator"])
    st.markdown(
        f"""<div style="display:inline-flex;align-items:center;gap:8px;
        background:{meta['color']}22;border:1px solid {meta['color']};
        padding:4px 14px;border-radius:20px;font-size:13px;font-weight:600;
        color:{meta['color']};margin-bottom:10px;">
        {meta['icon']} {meta['name']}
        </div>""",
        unsafe_allow_html=True,
    )


def render_score(label: str, value, max_value: float = 100):
    """Renders a numeric score (e.g. ATS score) as a colored progress bar."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        st.markdown(f"**{label}:** {value}")
        return

    pct = max(0.0, min(1.0, value / max_value)) if max_value else 0.0
    color = "#00B894" if pct >= 0.75 else "#FDCB6E" if pct >= 0.5 else "#D63031"

    st.markdown(f"**{label}**")
    st.progress(pct)
    st.markdown(
        f"<span style='color:{color};font-weight:800;font-size:22px;'>"
        f"{value:.0f}/{max_value:.0f}</span>",
        unsafe_allow_html=True,
    )


def render_roadmap(steps: list):
    """Renders a list of {step, description} dicts as numbered cards."""
    for i, item in enumerate(steps, 1):
        if isinstance(item, dict):
            title = item.get("step") or item.get("title") or f"Step {i}"
            desc = item.get("description") or item.get("desc") or ""
        else:
            title, desc = str(item), ""

        st.markdown(
            f"""<div style="border-left:4px solid #6C5CE7;padding:10px 16px;
            margin-bottom:10px;background:rgba(108,92,231,0.08);border-radius:8px;">
            <div style="font-weight:700;">Step {i}: {title}</div>
            <div style="opacity:0.85;margin-top:4px;font-size:14px;">{desc}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_bullet_list(items: list, icon: str = "•"):
    for item in items:
        st.markdown(f"{icon} {item}")


def render_value(key: str, value, depth: int = 0):
    """Generic recursive renderer used as a fallback for any field name."""
    pretty_key = str(key).replace("_", " ").title()
    lowered = str(key).lower()

    # Roadmap-like lists of steps
    if "roadmap" in lowered and isinstance(value, list) and value:
        st.markdown(f"#### 🗺️ {pretty_key}")
        render_roadmap(value)
        return

    # Score-like scalars
    if "score" in lowered and not isinstance(value, (list, dict)):
        render_score(pretty_key, value)
        return

    if isinstance(value, list):
        if not value:
            return
        st.markdown(f"**{pretty_key}**")
        if all(isinstance(v, dict) for v in value):
            for i, v in enumerate(value, 1):
                with st.expander(f"{pretty_key} {i}", expanded=(depth == 0)):
                    for k2, v2 in v.items():
                        render_value(k2, v2, depth + 1)
        else:
            render_bullet_list(value)
        return

    if isinstance(value, dict):
        if not value:
            return
        st.markdown(f"**{pretty_key}**")
        for k2, v2 in value.items():
            render_value(k2, v2, depth + 1)
        return

    # Plain scalar
    if value in (None, ""):
        return
    if depth == 0:
        st.markdown(f"**{pretty_key}:** {value}")
    else:
        st.markdown(f"{value}")


def render_dict_fields(d: dict, depth: int = 0):
    """Renders every key/value in a dict, leading with a summary line
    if one is present. Shared by the top-level response and by
    sub-sections like an embedded evaluation block."""
    if not d:
        return

    for summary_key in ("executive_summary", "summary", "overview"):
        if d.get(summary_key):
            st.markdown(f"> {d[summary_key]}")
            break

    for key, value in d.items():
        if key in ("executive_summary", "summary", "overview"):
            continue
        render_value(key, value, depth)


def render_final_interview_summary(reply: dict):
    """Renders the aggregated end-of-interview report."""
    st.markdown("### 🏁 Interview Summary")

    if reply.get("message"):
        st.info(reply["message"])
        return

    questions_answered = reply.get("questions_answered", 0)
    st.caption(f"{questions_answered} question(s) answered this session")

    if reply.get("average_score") is not None:
        render_score("Average Score", reply["average_score"], reply.get("score_out_of", 10))

    strengths = reply.get("top_strengths") or []
    if strengths:
        st.markdown("**✅ Top Strengths**")
        render_bullet_list(strengths, icon="✅")

    improve = reply.get("areas_to_improve") or []
    if improve:
        st.markdown("**📈 Focus On / Improve**")
        render_bullet_list(improve, icon="📈")


def is_awaiting_answer(reply, agent_used: str) -> bool:
    """True when the interview agent just asked a question and is
    waiting on the candidate's answer (i.e. NOT a final summary)."""
    if agent_used != "interview" or not isinstance(reply, dict):
        return False

    if "average_score" in reply or str(reply.get("message", "")).startswith("No interview"):
        return False  # this is the final summary report, interview already ended

    return "next_question" in reply or "question" in reply


def render_agent_response(reply, agent_used: str):
    """Main entry point: call this to render whatever the backend sent back."""
    agent_badge(agent_used)

    if isinstance(reply, str):
        st.markdown(reply)
        return

    if isinstance(reply, dict):
        if not reply:
            st.info("The agent returned an empty response.")
            return

        # Final, end-of-interview aggregated report
        if agent_used == "interview" and (
            "average_score" in reply or reply.get("message", "").startswith("No interview")
        ):
            render_final_interview_summary(reply)
            return

        # Combined "evaluation + immediately-following next question"
        # (the normal shape once an interview is under way)
        if agent_used == "interview" and "evaluation" in reply and "next_question" in reply:
            st.markdown("#### 📝 Feedback on your answer")
            evaluation = reply["evaluation"]
            if not isinstance(evaluation, dict):
                evaluation = evaluation.__dict__ if hasattr(evaluation, "__dict__") else {}
            render_dict_fields(evaluation)

            st.divider()

            st.markdown("#### ❓ Next Question")
            next_q = reply["next_question"]
            if not isinstance(next_q, dict):
                next_q = next_q.__dict__ if hasattr(next_q, "__dict__") else {}
            question_text = next_q.get("question") or str(next_q)
            st.markdown(question_text)
            st.caption("💬 Type your answer in the chat below to get feedback on it, "
                       "or click **🏁 End Interview** below when you're done.")
            return

        render_dict_fields(reply)

        # If this is a freshly generated interview question (not an
        # evaluation), make it obvious the next chat message is the answer.
        is_question = "question" in reply
        is_evaluation = any(k in reply for k in ("score", "evaluation", "strengths"))
        if agent_used == "interview" and is_question and not is_evaluation:
            st.caption("💬 Type your answer in the chat below to get feedback on it, "
                       "or click **🏁 End Interview** below when you're done.")
        return

    if isinstance(reply, list):
        if all(isinstance(v, dict) for v in reply):
            for i, v in enumerate(reply, 1):
                with st.expander(f"Item {i}"):
                    for k2, v2 in v.items():
                        render_value(k2, v2, depth=1)
        else:
            render_bullet_list(reply)
        return

    st.write(reply)