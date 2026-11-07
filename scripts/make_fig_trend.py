"""Included studies by publication year and category (Figure 1). The counts by year and category match data/included_studies.csv."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams.update({"pdf.fonttype": 42, "font.family": "serif",
    "font.serif": ["Palatino Linotype", "Palatino", "TeX Gyre Pagella", "DejaVu Serif"], "font.size": 8.5})
years = ["2023", "2024", "2025", "2026\n(to Sep)"]
cats = [("3 Channel denoising", [1, 5, 17, 24], "#2a78d6"),
        ("4 Interference, multi-user", [0, 1, 1, 9], "#eb6834"),
        ("5 Generative decoding", [1, 10, 24, 39], "#1baf7a"),
        ("6 Security, adversarial", [1, 2, 1, 8], "#eda100"),
        ("7 Flow, bridge, one step", [0, 0, 0, 7], "#e87ba4")]
fig, ax = plt.subplots(figsize=(5.2, 2.7), dpi=300)
bottom = [0] * 4
for name, v, c in cats:
    bars = ax.bar(years, v, 0.62, bottom=bottom, color=c, edgecolor="#fcfcfb", linewidth=1.0, label=name)
    for i, (b, n) in enumerate(zip(bottom, v)):
        if n >= 4:
            ax.text(i, b + n / 2, str(n), ha="center", va="center", fontsize=7, color="#0b0b0b")
    bottom = [b + n for b, n in zip(bottom, v)]
for i, t in enumerate(bottom):
    ax.text(i, t + 1.2, str(t), ha="center", va="bottom", fontsize=8, color="#0b0b0b", fontweight="bold")
ax.set_ylabel("Included studies", color="#52514e")
ax.set_ylim(0, 92)
for s in ("top", "right"): ax.spines[s].set_visible(False)
for s in ("left", "bottom"): ax.spines[s].set_color("#9a9994")
ax.tick_params(colors="#52514e", length=2)
ax.yaxis.grid(True, color="#e6e5e1", lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=7, loc="upper left", handlelength=1.1, handleheight=0.9)
fig.tight_layout()
fig.savefig("fig_trend.pdf")
