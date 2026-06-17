import os
import json
import re
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

print("LOADED NEW AGENT_CORE.PY")

# ─────────────────────────────────────────────
# INTENT CATEGORIES — what the LLM can detect
# ─────────────────────────────────────────────
INTENT_PROMPTS = {
    "tech_project": """You are an expert software engineering mentor helping a student build a technical project.
Break the following into EXACTLY 5-7 concrete, ordered subtasks a student can actually execute.
Each task must have realistic dependencies (what must be done first).
Think like a senior developer guiding a junior — be specific about tools, commands, and deliverables.""",

    "devops": """You are a DevOps engineer creating a hands-on learning roadmap.
Break the following into EXACTLY 5-7 practical subtasks covering infrastructure, automation, and deployment.
Include specific tools (Docker, Kubernetes, Jenkins, etc.) and show clear dependencies between tasks.
Each task should result in something the student can demo or verify.""",

    "ml_ai": """You are an ML engineer creating a project roadmap for a student.
Break the following into EXACTLY 5-7 subtasks covering data, model, training, and deployment.
Be specific about libraries (scikit-learn, TensorFlow, etc.), dataset sources, and evaluation metrics.
Show dependencies clearly — you can't train before cleaning data, can't deploy before evaluating, etc.""",

    "learning_goal": """You are a study coach creating a structured learning plan.
Break the following learning goal into EXACTLY 5-7 progressive study tasks.
Order them from foundational to advanced. Each task should produce a testable outcome.
Include specific resources (books, courses, practice sites) and realistic time estimates.""",

    "daily_task": """You are a productivity expert helping someone accomplish a real-world task.
Break the following into EXACTLY 4-6 clear, actionable steps a person can follow right now.
Be practical and specific — include exact ingredients, tools, or materials needed.
Steps should be sequential with clear dependencies (you can't do step 3 before step 2).""",

    "business": """You are a startup advisor helping plan a business initiative.
Break the following into EXACTLY 5-7 business execution tasks covering research, planning, and launch.
Include dependencies (market research must precede product development, etc.).
Be specific about deliverables — a business plan, MVP, landing page, etc.""",

    "technical_explanation": """You are a senior software architect and technical mentor.
Provide deep technical explanations.
Always include:
- Explanation
- Core theory
- Architecture concepts
- Technical keywords
- Best practices
- Common mistakes
- Real-world industry usage
Never respond with generic advice.""",

    "general": """You are a smart project planner helping someone accomplish their goal.
Break the following into EXACTLY 5-7 clear, actionable tasks with logical ordering.
Think about what must happen first, what can happen in parallel, and what comes last.
Be specific and practical — give steps someone can actually follow."""
}


class IntelligentTaskAgent:
    def __init__(self, model_name: str = None):
        self.api_key = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = model_name or os.getenv("DEFAULT_MODEL", "google/gemini-2.0-flash-exp:free")

    # ─────────────────────────────────────────
    # STEP 1: Detect what kind of query this is
    # ─────────────────────────────────────────
    def detect_intent(self, user_request: str) -> str:
        """
        Ask the LLM to classify the query into one of our intent categories.
        Falls back to keyword matching if LLM is unavailable.
        """
        if not self.api_key:
            return self._keyword_intent_fallback(user_request)

        classification_prompt = f"""Classify this user request into EXACTLY ONE of these categories:
- tech_project: building software, apps, websites, coding projects
- devops: CI/CD, Docker, Kubernetes, cloud infrastructure, deployment pipelines
- ml_ai: machine learning, AI models, data science, neural networks
- learning_goal: studying a topic, taking a course, learning a skill
- daily_task: cooking, cleaning, exercise, shopping, hobbies, everyday activities
- business: startups, marketing, business plans, product launch
- general: anything that doesn't clearly fit the above

User request: "{user_request}"

Reply with ONLY the category name, nothing else. No explanation, no punctuation."""

        try:
            response = self._call_api([{"role": "user", "content": classification_prompt}], max_tokens=20)
            if response:
                detected = response.strip().lower().replace(".", "").replace("'", "")
                if detected in INTENT_PROMPTS:
                    print(f"✅ Intent detected: {detected}")
                    return detected
        except Exception as e:
            print(f"Intent detection failed: {e}")

        return self._keyword_intent_fallback(user_request)

    def _keyword_intent_fallback(self, user_request: str) -> str:
        """Simple keyword fallback — only used when LLM is completely unavailable."""
        r = user_request.lower()
        if any(w in r for w in ["docker", "kubernetes", "devops", "ci/cd", "pipeline", "deploy", "cloud", "aws", "terraform"]):
            return "devops"
        if any(w in r for w in ["machine learning", "ml", "neural", "model", "dataset", "train", "tensorflow", "pytorch", "sklearn"]):
            return "ml_ai"
        if any(w in r for w in ["cook", "recipe", "make tea", "food", "bake", "clean", "exercise", "gym", "shop"]):
            return "daily_task"
        if any(w in r for w in ["learn", "study", "course", "tutorial", "understand", "skill", "beginner"]):
            return "learning_goal"
        if any(w in r for w in ["startup", "business", "market", "launch", "product", "customer", "revenue"]):
            return "business"
        if any(w in r for w in ["app", "application", "software", "code", "develop", "build", "website", "web", "api"]):
            return "tech_project"
        if any(w in r for w in ["what is", "how does", "explain", "architecture", "concept", "theory"]):
            return "technical_explanation"
        return "general"

    # ─────────────────────────────────────────
    # STEP 2: Decompose with intent-aware prompt
    # ─────────────────────────────────────────
    def decompose_task(self, user_request: str) -> Dict[str, Any]:
        """
        Main entry point. Detects intent, picks the right prompt,
        calls LLM, and returns structured JSON result.
        """
        # Detect what kind of query this is
        intent = self.detect_intent(user_request)

        if not self.api_key:
            print("⚠️ No API key. Using structured fallback.")
            return self._structured_fallback(user_request, intent)

        # Pick the right system prompt for this intent
        system_prompt = INTENT_PROMPTS[intent]

        # Ask LLM for structured JSON output
        user_prompt = f"""Request: "{user_request}"

Return ONLY a valid JSON object in this exact structure (no markdown, no explanation, just JSON):

{{
  "user_request": "{user_request}",
  "intent": "{intent}",
  "summary": "2-3 sentence overview of the plan",
  "estimated_total_time": "total time estimate e.g. 2-3 weeks",
  "tasks": [
    {{
      "id": 1,
      "title": "Clear task title",
      "description": "What exactly to do and why it matters",
      "priority": "High",
      "duration": "3 days",
      "depends_on": [],
      "tools_or_resources": ["specific tool/resource 1", "specific tool/resource 2"],
      "deliverable": "what you will have when this task is done"
    }},
    {{
      "id": 2,
      "title": "Next task title",
      "description": "What exactly to do",
      "priority": "High",
      "duration": "2 days",
      "depends_on": [1],
      "tools_or_resources": ["tool 1"],
      "deliverable": "what you will have"
    }}
  ]
}}

Rules:
- depends_on must be a list of task IDs (integers) that must be completed first
- priority must be exactly "High", "Medium", or "Low"
- deliverable must be a concrete thing (a file, a working feature, a document)
- Give 5-7 tasks total
- Do NOT wrap in markdown code blocks"""

        try:
            response = self._call_api([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], max_tokens=2500)

            if response:
                result = self._parse_json_response(response, user_request, intent)
                if result:
                    return result

        except Exception as e:
            print(f"❌ LLM call failed: {e}")

        return self._structured_fallback(user_request, intent)

    # ─────────────────────────────────────────
    # STEP 3: Parse JSON response safely
    # ─────────────────────────────────────────
    def _parse_json_response(self, raw: str, user_request: str, intent: str) -> Optional[Dict[str, Any]]:
        """
        Safely parse the LLM JSON response.
        Handles common issues: markdown fences, trailing text, etc.
        """
        # Strip markdown fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        # Find the JSON object boundaries
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start == -1 or end == -1:
            print("❌ No JSON object found in response")
            return None

        json_str = cleaned[start:end + 1]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            # Try to fix common issues
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                data = json.loads(json_str)
            except Exception:
                print("❌ JSON repair failed")
                return None

        # Validate and normalise
        tasks = data.get("tasks", [])
        if not tasks:
            print("❌ No tasks in response")
            return None

        # Convert to the format app.py expects (subtasks key)
        subtasks = []
        for t in tasks:
            subtasks.append({
                "id": t.get("id", len(subtasks) + 1),
                "title": t.get("title", "Untitled Task"),
                "priority": t.get("priority", "Medium") if t.get("priority") in ["High", "Medium", "Low"] else "Medium",
                "duration": t.get("duration", "3 days"),
                "explanation": f"In this subtask, the user should {t.get('description', 'complete this task')}",
                "description": t.get("description", ""),
                "depends_on": t.get("depends_on", []),
                "tools_or_resources": t.get("tools_or_resources", []),
                "deliverable": t.get("deliverable", ""),
                "resources": [{"name": r, "link": "#"} for r in t.get("tools_or_resources", [])]
            })

        return {
            "user_request": user_request,
            "intent": intent,
            "summary": data.get("summary", ""),
            "estimated_total_time": data.get("estimated_total_time", ""),
            "subtasks": subtasks,
            # Keep chat_response for app.py compatibility
            "chat_response": self._format_chat_response(user_request, intent, subtasks, data.get("summary", ""))
        }

    def _format_chat_response(self, user_request: str, intent: str, subtasks: list, summary: str) -> str:
        """Format a readable chat response from the structured data."""
        intent_labels = {
            "tech_project": "Software Project",
            "devops": "DevOps Roadmap",
            "ml_ai": "ML/AI Project",
            "learning_goal": "Learning Plan",
            "daily_task": "Step-by-Step Guide",
            "business": "Business Plan",
            "general": "Action Plan"
        }
        label = intent_labels.get(intent, "Plan")

        lines = [f"## {label}: {user_request}\n"]
        if summary:
            lines.append(f"{summary}\n")

        for i, task in enumerate(subtasks, 1):
            deps = task.get("depends_on", [])
            dep_str = f" *(after task {', '.join(map(str, deps))})*" if deps else " *(start here)*" if i == 1 else ""
            lines.append(f"**{i}. {task['title']}**{dep_str}")
            lines.append(f"- Priority: {task['priority']} | Duration: {task['duration']}")
            lines.append(f"- {task['description']}")
            if task.get("deliverable"):
                lines.append(f"- ✅ Deliverable: {task['deliverable']}")
            if task.get("tools_or_resources"):
                lines.append(f"- 🔧 Tools: {', '.join(task['tools_or_resources'][:3])}")
            lines.append("")

        return "\n".join(lines)

    # ─────────────────────────────────────────
    # LLM API call (shared method)
    # ─────────────────────────────────────────
    def _call_api(self, messages: list, max_tokens: int = 2500) -> Optional[str]:
        """Single API call method used by both intent detection and decomposition."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://intelligent-agent-bot.app",
            "X-Title": "Intelligent Task Agent"
        }
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": max_tokens
        }
        response = requests.post(self.base_url, headers=headers, json=data, timeout=45)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"❌ API error {response.status_code}: {response.text[:200]}")
            return None

    # ─────────────────────────────────────────
    # Fallback when no API key is set
    # ─────────────────────────────────────────
    def _structured_fallback(self, user_request: str, intent: str) -> Dict[str, Any]:
        """
        Intent-aware fallback. Each intent produces a DIFFERENT structure.
        This is NOT a generic template — it's domain-specific.
        """
        templates = {
            "daily_task": {
                "summary": f"Here is a step-by-step breakdown for: {user_request}",
                "tasks": [
                    {"id": 1, "title": "Gather what you need", "description": f"List and collect all ingredients, tools, or materials required for: {user_request}", "priority": "High", "duration": "5 mins", "depends_on": [], "tools_or_resources": [], "deliverable": "Everything needed is ready"},
                    {"id": 2, "title": "Prepare your workspace", "description": "Set up your space — clean surface, right equipment, correct order", "priority": "Medium", "duration": "5 mins", "depends_on": [1], "tools_or_resources": [], "deliverable": "Ready to begin"},
                    {"id": 3, "title": "Execute the first step", "description": f"Begin the actual process of: {user_request}", "priority": "High", "duration": "10 mins", "depends_on": [2], "tools_or_resources": [], "deliverable": "First step completed"},
                    {"id": 4, "title": "Monitor and adjust", "description": "Check progress, adjust timing or quantities as needed", "priority": "Medium", "duration": "Ongoing", "depends_on": [3], "tools_or_resources": [], "deliverable": "Process is on track"},
                    {"id": 5, "title": "Finish and review", "description": "Complete the final steps, check quality, clean up", "priority": "Low", "duration": "5 mins", "depends_on": [4], "tools_or_resources": [], "deliverable": f"{user_request} — done!"}
                ]
            },
            "tech_project": {
                "summary": f"A structured development roadmap for: {user_request}",
                "tasks": [
                    {"id": 1, "title": "Requirements & scope", "description": "Define what to build, what NOT to build, and success criteria", "priority": "High", "duration": "2 days", "depends_on": [], "tools_or_resources": ["Notion", "GitHub Issues"], "deliverable": "Requirements doc or README"},
                    {"id": 2, "title": "Architecture & tech stack", "description": "Choose technologies, draw system diagram, plan database schema", "priority": "High", "duration": "2 days", "depends_on": [1], "tools_or_resources": ["draw.io", "dbdiagram.io"], "deliverable": "Architecture diagram"},
                    {"id": 3, "title": "Set up project & dev environment", "description": "Initialize repo, install dependencies, configure linting and CI", "priority": "Medium", "duration": "1 day", "depends_on": [2], "tools_or_resources": ["Git", "VS Code", "Docker"], "deliverable": "Running blank project"},
                    {"id": 4, "title": "Build core features (MVP)", "description": "Implement the minimum features needed to demonstrate the idea", "priority": "High", "duration": "7-14 days", "depends_on": [3], "tools_or_resources": ["chosen framework"], "deliverable": "Working MVP"},
                    {"id": 5, "title": "Test and fix bugs", "description": "Write tests, find and fix critical bugs, test edge cases", "priority": "High", "duration": "3 days", "depends_on": [4], "tools_or_resources": ["pytest", "Jest", "Postman"], "deliverable": "Tested application"},
                    {"id": 6, "title": "Deploy and document", "description": "Deploy to a free host, write README, record a demo video", "priority": "Medium", "duration": "2 days", "depends_on": [5], "tools_or_resources": ["Railway", "Vercel", "Render"], "deliverable": "Live URL + documentation"}
                ]
            },
            "learning_goal": {
                "summary": f"A progressive learning plan for: {user_request}",
                "tasks": [
                    {"id": 1, "title": "Map what you need to learn", "description": "Find a roadmap, list prerequisite topics, estimate time needed", "priority": "High", "duration": "1 day", "depends_on": [], "tools_or_resources": ["roadmap.sh", "YouTube"], "deliverable": "Personal study plan"},
                    {"id": 2, "title": "Learn the fundamentals", "description": "Study core concepts — no skipping ahead, foundations matter most", "priority": "High", "duration": "1-2 weeks", "depends_on": [1], "tools_or_resources": ["freeCodeCamp", "Khan Academy", "official docs"], "deliverable": "Can explain basics in own words"},
                    {"id": 3, "title": "Build a small practice project", "description": "Apply what you learned immediately — even a toy project solidifies knowledge", "priority": "High", "duration": "3-5 days", "depends_on": [2], "tools_or_resources": ["GitHub"], "deliverable": "Small working project on GitHub"},
                    {"id": 4, "title": "Study intermediate concepts", "description": "Move to harder topics — only after fundamentals feel comfortable", "priority": "Medium", "duration": "1-2 weeks", "depends_on": [3], "tools_or_resources": ["Udemy", "Coursera", "official docs"], "deliverable": "Can solve intermediate problems"},
                    {"id": 5, "title": "Build a portfolio project", "description": "Create something real that demonstrates full skill — this goes on your resume", "priority": "High", "duration": "1-2 weeks", "depends_on": [4], "tools_or_resources": ["GitHub Pages"], "deliverable": "Completed portfolio project"}
                ]
            }
        }

        # Get intent-specific template or generic fallback
        template = templates.get(intent, {
            "summary": f"A structured plan for: {user_request}",
            "tasks": [
                {"id": 1, "title": "Define the goal clearly", "description": f"Write down exactly what success looks like for: {user_request}", "priority": "High", "duration": "1 day", "depends_on": [], "tools_or_resources": [], "deliverable": "Clear written goal"},
                {"id": 2, "title": "Research existing solutions", "description": "Find how others have solved this. Don't reinvent the wheel.", "priority": "High", "duration": "2 days", "depends_on": [1], "tools_or_resources": ["Google", "YouTube"], "deliverable": "List of approaches"},
                {"id": 3, "title": "Plan your approach", "description": "Choose the best approach based on your research. Break it into steps.", "priority": "Medium", "duration": "1 day", "depends_on": [2], "tools_or_resources": ["Notion", "paper"], "deliverable": "Written action plan"},
                {"id": 4, "title": "Execute and build", "description": "Follow your plan. Document as you go.", "priority": "High", "duration": "Varies", "depends_on": [3], "tools_or_resources": [], "deliverable": "Working result"},
                {"id": 5, "title": "Review and improve", "description": "Does the result meet your goal? Fix gaps. Get feedback.", "priority": "Medium", "duration": "2 days", "depends_on": [4], "tools_or_resources": [], "deliverable": "Final polished result"}
            ]
        })

        subtasks = []
        for t in template["tasks"]:
            subtasks.append({
                "id": t["id"],
                "title": t["title"],
                "priority": t["priority"],
                "duration": t["duration"],
                "explanation": f"In this subtask, the user should {t['description']}",
                "description": t["description"],
                "depends_on": t["depends_on"],
                "tools_or_resources": t.get("tools_or_resources", []),
                "deliverable": t.get("deliverable", ""),
                "resources": [{"name": r, "link": "#"} for r in t.get("tools_or_resources", [])]
            })

        return {
            "user_request": user_request,
            "intent": intent,
            "summary": template["summary"],
            "estimated_total_time": "",
            "subtasks": subtasks,
            "chat_response": self._format_chat_response(user_request, intent, subtasks, template["summary"])
        }

    # ─────────────────────────────────────────
    # Compatibility methods (app.py uses these)
    # ─────────────────────────────────────────
    def chat_decompose_task(self, user_request: str, conversation_history: list = None) -> Dict[str, Any]:
        """Same as decompose_task — kept for app.py compatibility."""
        return self.decompose_task(user_request)

    def validate_decomposition(self, decomposition: Dict[str, Any]) -> List[str]:
        """Basic validation — returns list of error strings."""
        errors = []
        if not decomposition.get("user_request"):
            errors.append("Missing user_request")
        subtasks = decomposition.get("subtasks", [])
        if not subtasks:
            errors.append("No subtasks found")
        elif len(subtasks) < 4:
            errors.append(f"Too few subtasks: {len(subtasks)}")
        return errors

    def format_output(self, decomposition: Dict[str, Any]) -> str:
        """Text format for display — kept for app.py compatibility."""
        lines = [f"User Request: \"{decomposition['user_request']}\"\n"]
        for i, s in enumerate(decomposition.get("subtasks", []), 1):
            deps = s.get("depends_on", [])
            dep_str = f" [depends on: {deps}]" if deps else ""
            lines.append(f"Task {i}: {s['title']}{dep_str}")
            lines.append(f"  Priority: {s['priority']} | Duration: {s['duration']}")
            lines.append(f"  {s.get('description', s.get('explanation', ''))}")
            if s.get("deliverable"):
                lines.append(f"  Deliverable: {s['deliverable']}")
            lines.append("")
        return "\n".join(lines)
