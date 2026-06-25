import matplotlib.pyplot as plt
import matplotx

TYPE_COLORS = {
    "Normal":   "#A8A878",
    "Fire":     "#F08030",
    "Water":    "#6890F0",
    "Electric": "#F8D030",
    "Grass":    "#78C850",
    "Ice":      "#98D8D8",
    "Fighting": "#C03028",
    "Poison":   "#A040A0",
    "Ground":   "#E0C068",
    "Flying":   "#A890F0",
    "Psychic":  "#F85888",
    "Bug":      "#A8B820",
    "Rock":     "#B8A038",
    "Ghost":    "#705898",
    "Dragon":   "#7038F8",
    "Dark":     "#705848",
    "Steel":    "#B8B8D0",
    "Fairy":    "#EE99AC",
    "Stellar":  "#40B5A5",
}

TYPE_BG_COLORS = {
    "Normal":   "#EEEEDD",
    "Fire":     "#FDECD8",
    "Water":    "#DDE8FD",
    "Electric": "#FDF7D0",
    "Grass":    "#E5F5DA",
    "Ice":      "#E5F6F6",
    "Fighting": "#F5DFDE",
    "Poison":   "#EDD8ED",
    "Ground":   "#FAF3DF",
    "Flying":   "#EBE8FD",
    "Psychic":  "#FEE2EC",
    "Bug":      "#F0F2D8",
    "Rock":     "#EEE8D8",
    "Ghost":    "#DED8EC",
    "Dragon":   "#E0D8FE",
    "Dark":     "#E0DCD8",
    "Steel":    "#EBEBF2",
    "Fairy":    "#FCEEF2",
    "Stellar":  "#D8F2EE",
}

KO_RED = "#ef4444"

def plot(
    xs: list[tuple[int, int]],
    ys: list[float],
    def_stat: str = "def",
    *,
    attacker_name: str = "",
    defender_name: str = "",
    move_name: str = "",
    move_type: str = "",
    best_index: int | None = None,
    best_dmg: int = 0,
    best_hp: int = 0,
    best_desc: str = "",
):
    labels = [str(x) for x in xs]
    pcts = [y * 100 for y in ys]
    line_color = TYPE_COLORS.get(move_type, "#7dd3fc")
    bg_color   = TYPE_BG_COLORS.get(move_type, "#F0F4FF")

    with plt.style.context(matplotx.styles.pacoty):
        fig, ax = plt.subplots(figsize=(10, 5.5))

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        ax.plot(labels, pcts, color=line_color, linewidth=2, marker="o", markersize=3.5)
        ax.grid(True, color=line_color, linewidth=0.6, alpha=0.35)
        ax.set_axisbelow(True)

        # KO line — solid red, full width
        ax.axhline(100, color=KO_RED, linestyle="-", linewidth=1.2, alpha=1.0)
        ax.text(len(labels) - 1, 100, " KO line", color=KO_RED, fontsize=8,
                va="bottom", ha="right")

        if best_index is not None:
            bx = best_index
            by = pcts[bx]

            # Render axes so limits are finalised
            fig.canvas.draw()
            xlim = ax.get_xlim()   # e.g. (-0.5, 29.5) for categorical axis
            ylim = ax.get_ylim()

            # Convert point position to axes fractions (0‥1)
            bx_frac = (bx - xlim[0]) / (xlim[1] - xlim[0])
            by_frac = (by - ylim[0]) / (ylim[1] - ylim[0])

            # Horizontal: from y-axis (xmin=0) to the point (xmax=bx_frac)
            ax.axhline(by, xmin=0, xmax=bx_frac,
                       color=line_color, linestyle=(0, (8, 4)),
                       linewidth=0.9, alpha=0.7)

            # Vertical: from x-axis (ymin=0) to the point (ymax=by_frac)
            ax.axvline(labels[bx], ymin=0, ymax=by_frac,
                       color=line_color, linestyle=(0, (8, 4)),
                       linewidth=0.9, alpha=0.7)

            # Corner info box
            box_text = (
                f"best: {labels[bx]}\n"
                f"{by:.1f}% HP dealt\n"
                f"{best_dmg} / {best_hp} HP"
            )
            ax.text(
                0.02, 0.97, box_text,
                transform=ax.transAxes,
                fontsize=9, fontweight="bold",
                color=line_color, va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor=line_color, linewidth=1.2, alpha=0.85),
            )

        title = f"{attacker_name or 'Attacker'} -> {defender_name or 'Defender'}  ({move_name or 'Move'})"
        ax.set_title(title, fontsize=13, fontweight="bold", pad=30)

        if best_desc:
            ax.text(0.5, 1.015, best_desc,
                    transform=ax.transAxes,
                    fontsize=7.5, color=line_color,
                    ha="center", va="bottom")

        ax.set_xlabel(f"(HP SP, {def_stat.upper()} SP)")
        ax.set_ylabel("% HP dealt (max roll)")
        ax.tick_params(axis="x", rotation=90)

        fig.tight_layout()
        fig.savefig("plot", dpi=150, facecolor=bg_color)
        plt.close(fig)