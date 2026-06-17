# ═══════════════════════════════════════════════════════════════════
# PASTE THIS BLOCK into app.py to replace the "main_app" function
# Keep everything else (auth_ui, imports, session state setup) as-is
# ═══════════════════════════════════════════════════════════════════

import streamlit as st
import json
import asyncio
import os
import pandas as pd
from datetime import datetime
from agent_core import IntelligentTaskAgent
from vector_db import VectorMemory
from visualizations import Visualizer
from auth import AuthManager
from telegram_service import TelegramNotifier, send_reminder_sync
from pdf_exporter import PDFExporter

st.set_page_config(page_title="Intelligent Task Planner", layout="wide", page_icon="🧠")

# ── Load CSS ──
try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ── Session State Init ──
if 'auth' not in st.session_state:
    st.session_state.auth = AuthManager()
if 'memory' not in st.session_state:
    st.session_state.memory = VectorMemory()
if 'agent' not in st.session_state:
    st.session_state.agent = IntelligentTaskAgent()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'show_full_history' not in st.session_state:
    st.session_state.show_full_history = False

# ── Intent display labels ──
INTENT_LABELS = {
    "tech_project": "💻 Software Project",
    "devops": "⚙️ DevOps Roadmap",
    "ml_ai": "🤖 ML/AI Project",
    "learning_goal": "📚 Learning Plan",
    "daily_task": "✅ Step-by-Step Guide",
    "business": "📈 Business Plan",
    "general": "🗂️ Action Plan"
}


def auth_ui():
    st.title("🧠 Intelligent Task Planner")
    st.markdown("#### AI-powered task breakdown with dependency visualisation")
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if st.session_state.auth.login(username, password):
                st.session_state.logged_in = True
                st.session_state.user = username
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        new_user = st.text_input("New Username", key="reg_user")
        new_pass = st.text_input("New Password", type="password", key="reg_pass")
        if st.button("Register"):
            if st.session_state.auth.register(new_user, new_pass):
                st.success("Account created! Please login.")
            else:
                st.error("Username already exists")


def main_app():
    # ── Sidebar ──
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    st.title("🧠 Intelligent Task Planner")
    st.markdown("*Ask anything — get a structured, dependency-aware breakdown*")

    # ── Input ──
    task_input = st.text_area(
        "What do you want to accomplish?",
        placeholder="Examples:\n• How to build a DevOps pipeline\n• How to make biryani\n• How to learn machine learning\n• How to start a startup",
        height=100
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        decompose_clicked = st.button("🔍 Plan This", use_container_width=True, type="primary")
    with col2:
        if 'current_result' in st.session_state and st.button("💾 Save to History", use_container_width=True):
            try:
                st.session_state.memory.add_task(
                    st.session_state.user,
                    st.session_state.get('current_task_input', ''),
                    st.session_state.current_result
                )
                st.success("✅ Saved to your history!")
            except Exception as e:
                st.error(f"Save failed: {e}")

    # ── Process query ──
    if decompose_clicked and task_input.strip():
        with st.spinner("🧠 Analysing your request…"):
            try:
                result = st.session_state.agent.decompose_task(task_input.strip())
                st.session_state.current_result = result
                st.session_state.current_task_input = task_input.strip()
            except Exception as e:
                st.error(f"Error: {e}")
                result = None

    # ── Display results ──
    if 'current_result' in st.session_state:
        result = st.session_state.current_result
        subtasks = result.get("subtasks", [])
        intent = result.get("intent", "general")
        summary = result.get("summary", "")
        total_time = result.get("estimated_total_time", "")

        # ── Header ──
        st.markdown("---")
        intent_label = INTENT_LABELS.get(intent, "🗂️ Plan")
        st.markdown(f"### {intent_label}")

        if summary:
            st.info(summary)

        if total_time:
            st.markdown(f"**⏱️ Estimated total time:** {total_time}")

        # ── Tabs: Tasks | Dependency Graph | Timeline | Chat ──
        tab_tasks, tab_dep, tab_timeline, tab_chat = st.tabs([
            "📋 Tasks", "🔗 Dependency Graph", "📅 Timeline", "💬 Explanation"
        ])

        with tab_tasks:
            st.markdown("#### Task Breakdown")
            for i, task in enumerate(subtasks, 1):
                priority = task.get("priority", "Medium")
                color = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(priority, "⚪")
                deps = task.get("depends_on", [])
                dep_str = f" *(after task {deps})*" if deps else ""

                with st.expander(f"📌 {task.get('title', 'Untitled')}", expanded=(i == 1)):
                    depends = f"After Task {', '.join(map(str, deps))}" if deps else "Start Here"
                    description = task.get("description", task.get("explanation", ""))

                    st.markdown(
                        f"""
<div class="task-meta">
{priority} • {task.get('duration', 'N/A')} • {depends}
</div>
<div class="task-description">
{description}
</div>
""",
                        unsafe_allow_html=True,
                    )

                    if task.get("deliverable"):
                        st.markdown(f"**Deliverable:** {task['deliverable']}")

                    tools = task.get("tools_or_resources", [])
                    if tools:
                        st.markdown(f"**Tools:** {', '.join(tools)}")

                    st.markdown("---")

        with tab_dep:
            st.markdown("#### How tasks depend on each other")
            st.caption("Read the arrows as 'must be done before'. Numbered circles = task IDs.")
            try:
                fig_dep = Visualizer.create_dependency_graph(subtasks)
                st.plotly_chart(fig_dep, use_container_width=True)
            except Exception as e:
                st.error(f"Graph error: {e}")

        with tab_timeline:
            st.markdown("#### Estimated project timeline")
            try:
                fig_timeline = Visualizer.create_timeline(subtasks)
                st.plotly_chart(fig_timeline, use_container_width=True)
                fig_effort = Visualizer.create_effort_chart(subtasks)
                st.plotly_chart(fig_effort, use_container_width=True)
            except Exception as e:
                st.error(f"Timeline error: {e}")

        with tab_chat:
            st.markdown(result.get("chat_response", "No explanation available."))

        # ── PDF Export ──
        st.markdown("---")
        if st.button("📄 Download PDF Report", use_container_width=True):
            try:
                pdf_buffer = PDFExporter.generate_task_pdf(
                    result.get("user_request", ""),
                    subtasks
                )
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_buffer,
                    file_name=f"task_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF error: {e}")

    # ── Sidebar history ──
    with st.sidebar:
        st.divider()
        st.subheader("📚 Recent Tasks")
        try:
            history = st.session_state.memory.get_user_history(st.session_state.user, limit=5)
            if history:
                for task in history:
                    title = task.get('user_request', 'Untitled')[:40]
                    intent = task.get('intent', '')
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{title}...**")
                    with col2:
                        if st.button("Load", key=f"load_{task['id']}"):
                            full = st.session_state.memory.get_task_by_id(task['id'])
                            if full and 'result' in full:
                                st.session_state.current_result = full['result']
                                st.session_state.current_task_input = full.get('task_input', '')
                                st.rerun()
            else:
                st.info("No history yet.")
        except Exception as e:
            st.error(f"History error: {e}")


# ── Run ──
if not st.session_state.logged_in:
    auth_ui()
else:
    main_app()
