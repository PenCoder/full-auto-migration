"""Generates docs/presentation/assets/gantt_chart.png — a real Gantt chart
matching the timeline in docs/FULL_AUTOMATION_EXPOSE.md §5, for embedding in
the presentation instead of describing the work breakdown as text.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "presentation" / "assets" / "gantt_chart.png"

BLUE = "#063D79"
GREEN = "#008439"
AMBER = "#B97000"
GREY = "#9A9A9A"

TASKS = [
    ("Architecture and MVC", date(2026, 4, 1), date(2026, 4, 17), BLUE),
    ("Recommendation engine", date(2026, 4, 17), date(2026, 5, 14), BLUE),
    ("UI automation", date(2026, 5, 14), date(2026, 5, 22), BLUE),
    ("Backup and restore", date(2026, 5, 22), date(2026, 5, 28), BLUE),
    ("Packaging and distribution", date(2026, 5, 28), date(2026, 5, 29), BLUE),
    ("Risk buffer and fixes", date(2026, 5, 29), date(2026, 6, 4), AMBER),
    ("Supervisor presentation", date(2026, 6, 4), date(2026, 6, 5), GREEN),
    ("Final documentation", date(2026, 6, 5), date(2026, 6, 8), GREEN),
]

fig, ax = plt.subplots(figsize=(12.0, 3.5), dpi=200)

for i, (name, start, end, color) in enumerate(TASKS):
    y = len(TASKS) - i - 1
    ax.barh(y, (end - start).days, left=start, height=0.6, color=color, edgecolor="none")
    ax.text(mdates.date2num(start) - 0.4, y, name, ha="right", va="center", fontsize=12, color="#1A1A1A")

ax.set_yticks([])
ax.set_xlim(date(2026, 3, 30), date(2026, 6, 9))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.tick_params(axis="x", labelsize=11, colors="#3F3F3F")
for spine in ("top", "right", "left"):
    ax.spines[spine].set_visible(False)
ax.spines["bottom"].set_color("#D8DADC")
ax.grid(axis="x", color="#D8DADC", linewidth=0.6)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(OUT_PATH, transparent=True)
print(f"Saved {OUT_PATH}")
