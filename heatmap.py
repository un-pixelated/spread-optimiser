import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap

# ── type palette (copied from plot.py) ───────────────────────────────────────

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

KO_RED     = "#ef4444"
FALLBACK   = "#7dd3fc"
FALLBACK_BG = "#F0F4FF"


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def _blend_hex(c1: str, c2: str, t: float = 0.5) -> str:
    """Linear blend: t=0 → c1, t=1 → c2."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = r1 + (r2 - r1) * t
    g = g1 + (g2 - g1) * t
    b = b1 + (b2 - b1) * t
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'


def _make_cmap(color_hex: str, name: str = 'type_cmap') -> LinearSegmentedColormap:
    """White → type color colormap for the heatmap cells."""
    r, g, b = _hex_to_rgb(color_hex)
    return LinearSegmentedColormap.from_list(name, ['#ffffff', (r, g, b)])


# ── main function ─────────────────────────────────────────────────────────────

def plot_heatmap(
    results:        list[dict],
    def_stat1:      str,          # 'def' or 'spd'
    def_stat2:      str,
    move_type1:     str,
    move_type2:     str,
    attacker1_name: str,
    attacker2_name: str,
    defender_name:  str,
    move1_name:     str,
    move2_name:     str,
    optimal:        dict,
):
    if not results:
        return

    same_stat  = (def_stat1 == def_stat2)
    col1       = TYPE_COLORS.get(move_type1, FALLBACK)
    col2       = TYPE_COLORS.get(move_type2, FALLBACK)
    bg1        = TYPE_BG_COLORS.get(move_type1, FALLBACK_BG)
    bg2        = TYPE_BG_COLORS.get(move_type2, FALLBACK_BG)

    # Chart background: type 1's bg color
    chart_bg   = bg1
    # Axes background: type 2's bg color
    axes_bg    = bg2
    # Heatmap colormap: white → blend(col1, col2)
    blend_col  = _blend_hex(col1, col2, 0.5)
    cmap       = _make_cmap(blend_col)

    if same_stat:
        _plot_two_stat(
            results, def_stat1,
            chart_bg, axes_bg, cmap, blend_col,
            attacker1_name, attacker2_name, defender_name,
            move1_name, move2_name, move_type1, move_type2,
            optimal,
        )
    else:
        _plot_three_stat(
            results, def_stat1, def_stat2,
            chart_bg, axes_bg, cmap, blend_col,
            attacker1_name, attacker2_name, defender_name,
            move1_name, move2_name, move_type1, move_type2,
            optimal,
        )


# ── two-stat heatmap ─────────────────────────────────────────────────────────
# X: DEF (or SPD) SP totals, Y: HP SP totals

def _plot_two_stat(
    results, def_stat,
    chart_bg, axes_bg, cmap, accent,
    atk1, atk2, dfn, mv1, mv2, type1, type2,
    optimal,
):
    # Build lookup: (HP_SP, DEF_SP) → combined %
    lookup = {}
    for r in results:
        lookup[(r['HP_SP'], r[f'{def_stat}_SP'])] = r['total'] * 100

    hp_vals  = sorted(set(r['HP_SP']           for r in results))
    def_vals = sorted(set(r[f'{def_stat}_SP']  for r in results))

    # Grid: rows = HP SP (y), cols = DEF SP (x)
    grid = np.full((len(hp_vals), len(def_vals)), np.nan)
    hp_idx  = {v: i for i, v in enumerate(hp_vals)}
    def_idx = {v: i for i, v in enumerate(def_vals)}

    for (hp, d), pct in lookup.items():
        grid[hp_idx[hp], def_idx[d]] = pct

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(axes_bg)

    # Mask NaN cells
    masked = np.ma.array(grid, mask=np.isnan(grid))
    cmap_copy = plt.cm.get_cmap(cmap) if isinstance(cmap, str) else cmap
    cmap_copy.set_bad(color=axes_bg)

    im = ax.imshow(
        masked,
        aspect='auto',
        origin='lower',
        cmap=cmap_copy,
        interpolation='nearest',
    )

    # KO cells — red border
    for (hp, d), pct in lookup.items():
        if pct >= 100:
            xi = def_idx[d]
            yi = hp_idx[hp]
            ax.add_patch(plt.Rectangle(
                (xi - 0.5, yi - 0.5), 1, 1,
                fill=False, edgecolor=KO_RED, linewidth=1.5, zorder=3,
            ))

    # Optimal cell marker
    opt_x = def_idx.get(optimal[f'{def_stat}_SP'])
    opt_y = hp_idx.get(optimal['HP_SP'])
    if opt_x is not None and opt_y is not None:
        ax.text(opt_x, opt_y, '★', ha='center', va='center',
                fontsize=14, color='white', fontweight='bold', zorder=4)
        ax.add_patch(plt.Rectangle(
            (opt_x - 0.5, opt_y - 0.5), 1, 1,
            fill=False, edgecolor='white', linewidth=2, zorder=4,
        ))

    # Axes
    ax.set_xticks(range(len(def_vals)))
    ax.set_xticklabels(def_vals)
    ax.set_yticks(range(len(hp_vals)))
    ax.set_yticklabels(hp_vals)
    ax.set_xlabel(f'{def_stat.upper()} SP', color=accent)
    ax.set_ylabel('HP SP',                  color=accent)
    ax.tick_params(colors=accent)
    for spine in ax.spines.values():
        spine.set_edgecolor(accent)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label('combined % HP dealt (max roll)', color=accent)
    cbar.ax.yaxis.set_tick_params(color=accent)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=accent)

    # KO tick on colorbar
    vmin = np.nanmin(grid)
    vmax = np.nanmax(grid)
    if vmin < 100 < vmax:
        cbar.ax.axhline(
            (100 - vmin) / (vmax - vmin),
            color=KO_RED, linewidth=1.5, linestyle='--',
        )
        cbar.ax.text(
            1.05, (100 - vmin) / (vmax - vmin), 'KO',
            transform=cbar.ax.transAxes,
            color=KO_RED, va='center', fontsize=8,
        )

    _add_titles_and_save(
        fig, ax, atk1, atk2, dfn, mv1, mv2, type1, type2,
        optimal, accent, chart_bg, filename='heatmap',
        opt_pct=optimal['total'] * 100,
        spread_label=f"{optimal['HP_SP']} HP / {optimal[f'{def_stat}_SP']} {def_stat.upper()}",
    )


# ── three-stat heatmap ───────────────────────────────────────────────────────
# X: stat_a SP, Y: stat_b SP — HP is implicit

def _plot_three_stat(
    results, stat_a, stat_b,
    chart_bg, axes_bg, cmap, accent,
    atk1, atk2, dfn, mv1, mv2, type1, type2,
    optimal,
):
    lookup = {}
    for r in results:
        lookup[(r[f'{stat_a}_SP'], r[f'{stat_b}_SP'])] = r['total'] * 100

    a_vals = sorted(set(r[f'{stat_a}_SP'] for r in results))
    b_vals = sorted(set(r[f'{stat_b}_SP'] for r in results))

    # Grid: rows = stat_b SP (y), cols = stat_a SP (x)
    grid = np.full((len(b_vals), len(a_vals)), np.nan)
    a_idx = {v: i for i, v in enumerate(a_vals)}
    b_idx = {v: i for i, v in enumerate(b_vals)}

    for (a, b), pct in lookup.items():
        grid[b_idx[b], a_idx[a]] = pct

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(chart_bg)
    ax.set_facecolor(axes_bg)

    masked   = np.ma.array(grid, mask=np.isnan(grid))
    cmap_copy = plt.cm.get_cmap(cmap) if isinstance(cmap, str) else cmap
    cmap_copy.set_bad(color=axes_bg)

    im = ax.imshow(
        masked,
        aspect='auto',
        origin='lower',
        cmap=cmap_copy,
        interpolation='nearest',
    )

    # KO borders
    for (a, b), pct in lookup.items():
        if pct >= 100:
            xi = a_idx[a]
            yi = b_idx[b]
            ax.add_patch(plt.Rectangle(
                (xi - 0.5, yi - 0.5), 1, 1,
                fill=False, edgecolor=KO_RED, linewidth=1.5, zorder=3,
            ))

    # Optimal marker
    opt_x = a_idx.get(optimal[f'{stat_a}_SP'])
    opt_y = b_idx.get(optimal[f'{stat_b}_SP'])
    if opt_x is not None and opt_y is not None:
        ax.text(opt_x, opt_y, '★', ha='center', va='center',
                fontsize=14, color='white', fontweight='bold', zorder=4)
        ax.add_patch(plt.Rectangle(
            (opt_x - 0.5, opt_y - 0.5), 1, 1,
            fill=False, edgecolor='white', linewidth=2, zorder=4,
        ))

    # HP annotation on each valid cell — small grey text showing implicit HP SP
    hp_by_cell = {(r[f'{stat_a}_SP'], r[f'{stat_b}_SP']): r['HP_SP'] for r in results}
    for (a, b), hp in hp_by_cell.items():
        ax.text(
            a_idx[a], b_idx[b], f'{hp}',
            ha='center', va='center',
            fontsize=5.5, color='#555555', alpha=0.75, zorder=2,
        )

    # Axes
    ax.set_xticks(range(len(a_vals)))
    ax.set_xticklabels(a_vals)
    ax.set_yticks(range(len(b_vals)))
    ax.set_yticklabels(b_vals)
    ax.set_xlabel(f'{stat_a.upper()} SP  (move 1: {mv1})', color=accent)
    ax.set_ylabel(f'{stat_b.upper()} SP  (move 2: {mv2})', color=accent)
    ax.tick_params(colors=accent)
    for spine in ax.spines.values():
        spine.set_edgecolor(accent)

    # HP SP label reminder
    ax.text(
        0.99, 0.01,
        'cell numbers = HP SP (implicit)',
        transform=ax.transAxes,
        fontsize=7, color=accent, alpha=0.7,
        ha='right', va='bottom',
    )

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label('combined % HP dealt (max roll)', color=accent)
    cbar.ax.yaxis.set_tick_params(color=accent)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=accent)

    vmin = np.nanmin(grid)
    vmax = np.nanmax(grid)
    if vmin < 100 < vmax:
        cbar.ax.axhline(
            (100 - vmin) / (vmax - vmin),
            color=KO_RED, linewidth=1.5, linestyle='--',
        )
        cbar.ax.text(
            1.05, (100 - vmin) / (vmax - vmin), 'KO',
            transform=cbar.ax.transAxes,
            color=KO_RED, va='center', fontsize=8,
        )

    spread_label = (
        f"{optimal['HP_SP']} HP / "
        f"{optimal[f'{stat_a}_SP']} {stat_a.upper()} / "
        f"{optimal[f'{stat_b}_SP']} {stat_b.upper()}"
    )
    _add_titles_and_save(
        fig, ax, atk1, atk2, dfn, mv1, mv2, type1, type2,
        optimal, accent, chart_bg, filename='heatmap',
        opt_pct=optimal['total'] * 100,
        spread_label=spread_label,
    )


# ── shared title + save ───────────────────────────────────────────────────────

def _add_titles_and_save(
    fig, ax,
    atk1, atk2, dfn, mv1, mv2, type1, type2,
    optimal, accent, chart_bg,
    filename, opt_pct, spread_label,
):
    atk_label = atk1 if atk1 == atk2 else f'{atk1} + {atk2}'
    title     = f'{atk_label}  →  {dfn}   ({mv1}  +  {mv2})'
    subtitle  = f'optimal: {spread_label}  —  {opt_pct:.1f}% combined dealt'

    type_tag  = (type1 if type1 == type2 else f'{type1} + {type2}')

    ax.set_title(title,    fontsize=12, fontweight='bold', color=accent, pad=28)
    ax.text(
        0.5, 1.02, subtitle,
        transform=ax.transAxes,
        fontsize=8, color=accent, ha='center', va='bottom',
    )
    ax.text(
        0.5, 1.065, type_tag,
        transform=ax.transAxes,
        fontsize=7.5, color=accent, alpha=0.6, ha='center', va='bottom',
    )

    fig.tight_layout()
    fig.savefig(filename, dpi=150, facecolor=chart_bg)
    plt.close(fig)