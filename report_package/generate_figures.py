"""Create the small, data-backed figures used by the LaTeX report.

Run from the report_package directory with: python generate_figures.py
"""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
navy, teal, orange, grey = "#17324D", "#167D8D", "#E8893A", "#667085"

# Measured ten-seed benchmark summary, benchmark_run_004_summary.csv.
methods = ["Greedy\ncost", "Random\nfeasible", "NSGA-II"]
runtime = [0.0363, 0.5834, 7.4304]
cost = [75.714, 78.898, 78.898]
feasible = [1.0, 40.0, 40.1]

fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), constrained_layout=True)
bars = axes[0].bar(methods, runtime, color=[orange, teal, navy], width=0.58)
axes[0].set_ylabel("Mean runtime (seconds, log scale)")
axes[0].set_yscale("log")
axes[0].set_title("Time used per benchmark run")
axes[0].grid(axis="y", alpha=.22)
for bar, value in zip(bars, runtime):
    axes[0].text(bar.get_x()+bar.get_width()/2, value*1.35, f"{value:.3g}", ha="center", fontsize=9)
bars = axes[1].bar(methods, feasible, color=[orange, teal, navy], width=0.58)
axes[1].set_ylabel("Mean feasible candidates")
axes[1].set_title("Feasible candidates returned")
axes[1].grid(axis="y", alpha=.22)
for bar, value in zip(bars, feasible):
    axes[1].text(bar.get_x()+bar.get_width()/2, value+1.2, f"{value:.1f}", ha="center", fontsize=9)
fig.savefig(OUT / "benchmark_comparison.png", dpi=220, bbox_inches="tight")
plt.close(fig)

# Four-week scheduler output, monthly_smoke.json.
pairs = ["W1--W2", "W1--W3", "W1--W4", "W2--W3", "W2--W4", "W3--W4"]
differences = [21, 17, 17, 20, 21, 18]
fig, ax = plt.subplots(figsize=(8.3, 3.7), constrained_layout=True)
bar_colors = [navy if d >= 18 else teal for d in differences]
ax.bar(pairs, differences, color=bar_colors, width=.6)
ax.axhline(7, color=orange, linewidth=2, linestyle="--", label="Required minimum: 7")
ax.set_ylim(0, 23)
ax.set_ylabel("Different meal slots (out of 21)")
ax.set_title("Diversity between selected monthly weeks")
ax.grid(axis="y", alpha=.22)
ax.legend(frameon=False, loc="lower right")
for i, value in enumerate(differences):
    ax.text(i, value+.55, str(value), ha="center")
fig.savefig(OUT / "monthly_diversity.png", dpi=220, bbox_inches="tight")
plt.close(fig)

# Clear workflow as a vector-like raster graphic, made for the report.
fig, ax = plt.subplots(figsize=(11, 3.4))
ax.axis("off")
steps = [
    ("Meal data", "200 vegetarian dishes\nprice, nutrition, rating"),
    ("Valid menu builder", "21 slots + hard rules\nonly eligible dishes"),
    ("NSGA-II search", "evolve alternatives\nwithout one fixed priority"),
    ("Pareto menus", "cost / nutrition /\nsatisfaction trade-offs"),
    ("Monthly selector", "four distinct weeks\nminimum slot difference"),
    ("Web application", "view and export\nweekly meal plans"),
]
xs = np.linspace(.09, .91, len(steps))
for i, (title, detail) in enumerate(steps):
    ax.text(xs[i], .61, title, ha="center", va="center", weight="bold", color="white",
            bbox=dict(boxstyle="round,pad=.55", fc=navy if i in (2, 3) else teal, ec="none"),
            transform=ax.transAxes)
    ax.text(xs[i], .25, detail, ha="center", va="center", color=grey, transform=ax.transAxes)
    if i < len(steps)-1:
        ax.annotate("", xy=(xs[i+1]-.057,.61), xytext=(xs[i]+.057,.61), xycoords=ax.transAxes,
                    arrowprops=dict(arrowstyle="->", lw=1.8, color=orange))
ax.set_title("System workflow", loc="left", weight="bold", color=navy, pad=12)
fig.savefig(OUT / "system_workflow.png", dpi=220, bbox_inches="tight", facecolor="white")
plt.close(fig)
