# 🧠 Intelligent Task Planner

An AI-powered task decomposition app built with Streamlit, OpenRouter (Gemini), ChromaDB, and Plotly.
Type any goal — software project, cooking recipe, learning plan, business idea — and get a structured,
dependency-aware roadmap with interactive visualizations.

---

## ✨ Features

- **AI Task Decomposition** — breaks any goal into 5–7 ordered, practical subtasks
- **Intent Detection** — automatically classifies queries (tech, DevOps, ML, learning, daily tasks, business)
- **Dependency Graph** — interactive DAG showing which tasks must come before others
- **Gantt Timeline** — visual project timeline respecting task dependencies
- **Effort Chart** — horizontal bar chart showing time estimates per task
- **Task History** — ChromaDB vector memory stores and retrieves past plans
- **PDF Export** — download any plan as a formatted PDF report
- **User Auth** — multi-user login with SQLite (includes admin account)
- **Telegram Notifications** — send reminders to your Telegram chat
- **Speech Input** — voice-to-text task entry (local only)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd intelligent_task_planner
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Python 3.9–3.11 recommended.** ChromaDB may have issues on Python 3.12+.

### 3. Set up your API key

Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
DEFAULT_MODEL=google/gemini-2.0-flash-exp:free
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here   # optional
```

Get a free OpenRouter key at [openrouter.ai/keys](https://openrouter.ai/keys).
The default model (`gemini-2.0-flash-exp:free`) is **completely free**.

### 4. Initialize the database

```bash
python init_db.py
```

This creates `users.db` with an admin account and three test users.

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🔑 Default Login Credentials

| Username   | Password     | Role  |
|------------|--------------|-------|
| admin      | admin123     | admin |
| john_doe   | password123  | user  |
| jane_smith | password456  | user  |
| test_user  | test123      | user  |

> ⚠️ Change passwords before deploying to production.

---

## 📁 Project Structure

```
intelligent_task_planner/
├── app.py                  # Main Streamlit UI
├── agent_core.py           # LLM intent detection + task decomposition
├── vector_db.py            # ChromaDB semantic memory
├── visualizations.py       # Plotly dependency graph, timeline, effort chart
├── auth.py                 # SQLite user authentication
├── pdf_exporter.py         # ReportLab PDF generation
├── telegram_service.py     # Telegram bot notifications
├── speech_handler.py       # Speech-to-text input
├── init_db.py              # Database setup script
├── style.css               # Streamlit custom styling
├── chat_styles.css         # Chat interface styles
├── requirements.txt        # Python dependencies
├── .env                    # API keys (never commit this)
└── README.md               # This file
```

---

## 🏗️ Architecture

```
User Input
    │
    ▼
agent_core.py ──► OpenRouter API (Gemini)
    │                   │
    │            Intent Detection
    │            Task Decomposition
    │            JSON Response
    │
    ▼
app.py (Streamlit UI)
    ├── Tasks Tab ──────────────── Task cards with priority/duration
    ├── Dependency Graph Tab ───── visualizations.py → Plotly DAG
    ├── Timeline Tab ───────────── visualizations.py → Gantt chart
    └── Explanation Tab ─────────  Markdown chat response
    │
    ├── vector_db.py ──────────── ChromaDB (save/load history)
    ├── pdf_exporter.py ────────── ReportLab PDF download
    └── telegram_service.py ────── Telegram reminders
```

---

## 🤖 How the AI Works

1. **Intent Detection** — The LLM classifies your query into one of 7 categories:
   `tech_project`, `devops`, `ml_ai`, `learning_goal`, `daily_task`, `business`, `general`

2. **Prompt Selection** — A domain-specific system prompt is chosen for that category.
   A DevOps query gets a DevOps engineer persona; a cooking query gets a practical expert.

3. **Structured Output** — The LLM returns a JSON object with:
   - Ordered subtasks with IDs
   - `depends_on` arrays (task dependency graph)
   - Priority, duration, deliverable, tools for each task

4. **Fallback** — If the API is unavailable, intent-aware hardcoded templates kick in.

---

## 📊 Example Queries

| Query | Detected Intent | Result |
|---|---|---|
| "Build a CI/CD pipeline with Docker and GitHub Actions" | `devops` | 6-step DevOps roadmap |
| "How to learn machine learning from scratch" | `learning_goal` | Progressive study plan |
| "How to make chicken biryani" | `daily_task` | Step-by-step cooking guide |
| "Build a React e-commerce website" | `tech_project` | Full-stack dev roadmap |
| "Start a SaaS business for freelancers" | `business` | Go-to-market plan |

---

## 🐛 Known Issues & Fixes

### `import re` error in visualizations.py
The original `visualizations.py` has `import re` at the bottom of the file, causing
`NameError` when duration helper functions are called. **Fix:** use the updated
`visualizations.py` from this repo where `import re` is at the top.

### ChromaDB on Python 3.12
ChromaDB may fail to install on Python 3.12. Use Python 3.10 or 3.11:
```bash
pyenv install 3.11.9
pyenv local 3.11.9
pip install -r requirements.txt
```

### Telegram "Chat not found"
1. Search for your bot on Telegram and send `/start`
2. Get your Chat ID by messaging [@userinfobot](https://t.me/userinfobot)
3. Enter that numeric ID in the app's Telegram settings

---

## 🌐 Deployment

### Deploy on Render (free tier)

1. Push your code to GitHub (make sure `.env` is in `.gitignore`)
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Add environment variables in the Render dashboard

### Deploy on Railway

```bash
railway login
railway init
railway up
```

Add your `OPENROUTER_API_KEY` in the Railway environment variables panel.

---

## 🔧 Customization

### Add a new intent category
1. Add a new key to `INTENT_PROMPTS` in `agent_core.py`
2. Add the same key to `INTENT_LABELS` in `app.py`
3. Add keyword patterns to `_keyword_intent_fallback()` in `agent_core.py`
4. Add a fallback template to `_structured_fallback()` in `agent_core.py`

### Change the AI model
Update `DEFAULT_MODEL` in your `.env`. Any OpenRouter model works:
- `google/gemini-2.0-flash-exp:free` — free, fast
- `anthropic/claude-3.5-haiku` — paid, very capable
- `meta-llama/llama-3.3-70b-instruct:free` — free, open source

---

## 📄 License

MIT License. Free to use, modify, and deploy.
