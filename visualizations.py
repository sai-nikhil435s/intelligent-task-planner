import re
import math
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any


class Visualizer:

    @staticmethod
    def create_dependency_graph(subtasks: List[Dict[str, Any]]):
        """
        Creates a real Directed Acyclic Graph (DAG) showing task dependencies.
        Nodes = tasks, Edges = 'must be done before' relationships.
        """
        if not subtasks:
            return go.Figure()

        priority_colors = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}

        levels = _compute_levels(subtasks)
        max_level = max(levels.values()) if levels else 0

        positions = {}
        level_counts = {}
        for tid, lv in levels.items():
            level_counts[lv] = level_counts.get(lv, 0) + 1

        level_cursors = {}
        for tid in sorted(levels.keys()):
            lv = levels[tid]
            idx = level_cursors.get(lv, 0)
            count = level_counts[lv]
            x = (idx + 0.5) / count
            y = 1.0 - (lv / max(max_level, 1))
            positions[tid] = (x, y)
            level_cursors[lv] = idx + 1

        edge_x, edge_y = [], []
        arrow_annotations = []

        for task in subtasks:
            tid = task.get("id", 0)
            for dep_id in task.get("depends_on", []):
                if dep_id in positions and tid in positions:
                    x0, y0 = positions[dep_id]
                    x1, y1 = positions[tid]
                    edge_x += [x0, x1, None]
                    edge_y += [y0, y1, None]
                    arrow_annotations.append(dict(
                        ax=x0, ay=y0,
                        x=x1, y=y1,
                        xref="x", yref="y",
                        axref="x", ayref="y",
                        showarrow=True,
                        arrowhead=3,
                        arrowsize=1.2,
                        arrowwidth=1.5,
                        arrowcolor="#94a3b8"
                    ))

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode="lines",
            line=dict(width=1.5, color="#475569"),
            hoverinfo="none"
        )

        node_x, node_y, node_text, node_color, node_hover = [], [], [], [], []

        for task in subtasks:
            tid = task.get("id", task.get("ID", 0))
            title = task.get("title", f"Task {tid}")
            priority = task.get("priority", "Medium")
            duration = task.get("duration", "")
            deliverable = task.get("deliverable", "")
            deps = task.get("depends_on", [])

            x, y = positions.get(tid, (0.5, 0.5))
            node_x.append(x)
            node_y.append(y)

            label = title if len(title) <= 20 else title[:18] + "…"
            node_text.append(label)
            node_color.append(priority_colors.get(priority, "#6366f1"))

            dep_str = f"Depends on: Task {deps}" if deps else "No dependencies (start here)"
            hover = (
                f"<b>{title}</b><br>"
                f"Priority: {priority}<br>"
                f"Duration: {duration}<br>"
                f"{dep_str}<br>"
                f"{'Deliverable: ' + deliverable if deliverable else ''}"
            )
            node_hover.append(hover)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            marker=dict(
                size=28,
                color=node_color,
                line=dict(width=2, color="#1e293b"),
                symbol="circle"
            ),
            text=node_text,
            textposition="top center",
            textfont=dict(size=11, color="#e2e8f0"),
            hovertext=node_hover,
            hoverinfo="text"
        )

        id_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="text",
            text=[str(t.get("id", i + 1)) for i, t in enumerate(subtasks)],
            textfont=dict(size=12, color="white", family="Arial Black"),
            hoverinfo="none"
        )

        fig = go.Figure(
            data=[edge_trace, node_trace, id_trace],
            layout=go.Layout(
                title=dict(text="Task Dependency Graph", font=dict(color="white", size=16)),
                showlegend=False,
                hovermode="closest",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                annotations=arrow_annotations,
                margin=dict(l=20, r=20, t=50, b=20),
                height=420
            )
        )

        for priority, color in priority_colors.items():
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=color),
                name=f"{priority} priority",
                showlegend=True
            ))
        fig.update_layout(
            legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", font=dict(color="white"))
        )

        return fig

    @staticmethod
    def create_workflow_graph(subtasks: List[Dict[str, Any]]):
        """Returns (dependency_graph, effort_chart) — kept for backward compatibility."""
        fig_dep = Visualizer.create_dependency_graph(subtasks)
        fig_bar = Visualizer.create_effort_chart(subtasks)
        return fig_dep, fig_bar

    @staticmethod
    def create_effort_chart(subtasks: List[Dict[str, Any]]):
        """Horizontal bar chart showing estimated effort per task."""
        if not subtasks:
            return go.Figure()

        rows = []
        for i, task in enumerate(subtasks, 1):
            title = task.get("title", f"Task {i}")
            duration_str = str(task.get("duration", "1 day")).lower()
            hours = _duration_to_hours(duration_str)
            priority = task.get("priority", "Medium")
            rows.append({"Task": f"{i}. {title[:30]}", "Hours": hours, "Priority": priority})

        df = pd.DataFrame(rows)
        color_map = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}

        fig = px.bar(
            df, x="Hours", y="Task",
            orientation="h",
            color="Priority",
            color_discrete_map=color_map,
            title="Estimated Effort per Task",
            labels={"Hours": "Estimated Hours", "Task": ""}
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=350,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig

    @staticmethod
    def create_priority_chart(subtasks: List[Dict[str, Any]]):
        """Pie chart of priority distribution."""
        if not subtasks:
            return go.Figure()

        counts = {"High": 0, "Medium": 0, "Low": 0}
        for t in subtasks:
            p = t.get("priority", "Medium")
            if p in counts:
                counts[p] += 1

        fig = go.Figure(go.Pie(
            labels=list(counts.keys()),
            values=list(counts.values()),
            marker=dict(colors=["#ef4444", "#f97316", "#22c55e"]),
            textinfo="label+percent",
            hole=0.4
        ))
        fig.update_layout(
            title="Priority Distribution",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=300
        )
        return fig

    @staticmethod
    def create_timeline(subtasks: List[Dict[str, Any]]):
        """Gantt-style timeline respecting dependencies."""
        if not subtasks:
            return go.Figure()

        start_days: Dict[int, float] = {}
        durations: Dict[int, float] = {}

        for task in subtasks:
            tid = task.get("id", 0)
            durations[tid] = _duration_to_days(str(task.get("duration", "3 days")).lower())

        for task in subtasks:
            tid = task.get("id", 0)
            deps = task.get("depends_on", [])
            if not deps:
                start_days[tid] = 0
            else:
                start_days[tid] = max(
                    start_days.get(d, 0) + durations.get(d, 1)
                    for d in deps
                    if d in start_days
                ) if any(d in start_days for d in deps) else 0

        color_map = {"High": "#ef4444", "Medium": "#f97316", "Low": "#22c55e"}
        fig = go.Figure()

        for i, task in enumerate(subtasks):
            tid = task.get("id", i + 1)
            title = task.get("title", f"Task {tid}")
            priority = task.get("priority", "Medium")
            start = start_days.get(tid, i * 3)
            dur = durations.get(tid, 3)

            fig.add_trace(go.Bar(
                x=[dur],
                y=[f"{tid}. {title[:25]}"],
                base=[start],
                orientation="h",
                marker_color=color_map.get(priority, "#6366f1"),
                name=title,
                hovertemplate=f"<b>{title}</b><br>Start: Day {start:.0f}<br>Duration: {dur:.0f} days<extra></extra>",
                showlegend=False
            ))

        fig.update_layout(
            title="Project Timeline (days)",
            barmode="overlay",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(title="Days from start", color="white"),
            yaxis=dict(color="white", autorange="reversed"),
            height=max(250, len(subtasks) * 45),
            margin=dict(l=20, r=20, t=50, b=40)
        )
        return fig


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def _compute_levels(subtasks: List[Dict[str, Any]]) -> Dict[int, int]:
    """Topological level assignment for DAG layout."""
    id_map = {t.get("id", i + 1): t for i, t in enumerate(subtasks)}
    levels = {}

    def get_level(tid, visited=None):
        if visited is None:
            visited = set()
        if tid in levels:
            return levels[tid]
        if tid in visited:
            return 0
        visited.add(tid)
        task = id_map.get(tid)
        if not task:
            return 0
        deps = task.get("depends_on", [])
        if not deps:
            levels[tid] = 0
        else:
            levels[tid] = max(get_level(d, visited.copy()) + 1 for d in deps if d in id_map)
        return levels[tid]

    for task in subtasks:
        tid = task.get("id", 0)
        get_level(tid)

    return levels


def _duration_to_hours(duration_str: str) -> float:
    """Convert duration string to hours for charts."""
    d = duration_str.lower()
    num_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*\d+(?:\.\d+)?)?", d)
    num = float(num_match.group(1)) if num_match else 1.0
    if "week" in d:
        return num * 40
    if "month" in d:
        return num * 160
    if "day" in d:
        return num * 8
    if "hour" in d or "hr" in d:
        return num
    if "min" in d:
        return num / 60
    return num * 8


def _duration_to_days(duration_str: str) -> float:
    """Convert duration string to days for timeline."""
    d = duration_str.lower()
    num_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?", d)
    if num_match:
        low = float(num_match.group(1))
        high = float(num_match.group(2)) if num_match.group(2) else low
        num = (low + high) / 2
    else:
        num = 1.0
    if "week" in d:
        return num * 5
    if "month" in d:
        return num * 20
    if "hour" in d or "hr" in d or "min" in d:
        return 0.5
    return num
