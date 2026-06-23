import matplotlib.pyplot as plt

plt.style.use("dark_background")

ACCENT = "#7dd3fc"   # line colour
HILITE = "#facc15"   # best-spread highlight
KO_RED = "#ef4444"   # 100% HP / KO reference line


def plot(
    xs: list[tuple[int, int]],
    ys: list[float],
    def_stat: str = "def",
    *,
    attacker_name: str = "",
    defender_name: str = "",
    move_name: str = "",
    best_index: int | None = None,
):
    labels = [str(x) for x in xs]
    pcts = [y * 100 for y in ys]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.plot(labels, pcts, color=ACCENT, linewidth=2, marker="o", markersize=3.5)

    # KO reference line at 100% HP dealt
    ax.axhline(100, color=KO_RED, linestyle="--", linewidth=1, alpha=0.7)
    ax.text(len(labels) - 1, 100, " KO line", color=KO_RED, fontsize=8,
             va="bottom", ha="right")

    # Highlight the best (lowest-damage-taken) spread
    if best_index is not None:
        ax.scatter([labels[best_index]], [pcts[best_index]],
                    color=HILITE, s=120, zorder=5,
                    edgecolor="black", linewidth=0.8)
        ax.annotate(
            f"best: {labels[best_index]}\n{pcts[best_index]:.1f}% HP",
            xy=(best_index, pcts[best_index]),
            xytext=(0, 18), textcoords="offset points",
            ha="center", fontsize=9, fontweight="bold", color=HILITE,
        )

    title = f"{move_name or 'Attack'} → {defender_name or 'Defender'}"
    if attacker_name:
        title += f"  (atk: {attacker_name})"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)

    ax.set_xlabel(f"(HP SP, {def_stat.upper()} SP)")
    ax.set_ylabel("% HP dealt (max roll)")
    ax.grid(True, alpha=0.2)
    ax.tick_params(axis="x", rotation=90)

    fig.tight_layout()
    fig.savefig("plot", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)