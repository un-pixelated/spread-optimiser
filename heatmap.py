import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ── type palette ──────────────────────────────────────────────────────────────

TYPE_COLORS = {
    "Normal":   "#A8A878", "Fire":     "#F08030", "Water":    "#6890F0",
    "Electric": "#F8D030", "Grass":    "#78C850", "Ice":      "#98D8D8",
    "Fighting": "#C03028", "Poison":   "#A040A0", "Ground":   "#E0C068",
    "Flying":   "#A890F0", "Psychic":  "#F85888", "Bug":      "#A8B820",
    "Rock":     "#B8A038", "Ghost":    "#705898", "Dragon":   "#7038F8",
    "Dark":     "#705848", "Steel":    "#B8B8D0", "Fairy":    "#EE99AC",
    "Stellar":  "#40B5A5",
}

TYPE_BG_COLORS = {
    "Normal":   "#EEEEDD", "Fire":     "#FDECD8", "Water":    "#DDE8FD",
    "Electric": "#FDF7D0", "Grass":    "#E5F5DA", "Ice":      "#E5F6F6",
    "Fighting": "#F5DFDE", "Poison":   "#EDD8ED", "Ground":   "#FAF3DF",
    "Flying":   "#EBE8FD", "Psychic":  "#FEE2EC", "Bug":      "#F0F2D8",
    "Rock":     "#EEE8D8", "Ghost":    "#DED8EC", "Dragon":   "#E0D8FE",
    "Dark":     "#E0DCD8", "Steel":    "#EBEBF2", "Fairy":    "#FCEEF2",
    "Stellar":  "#D8F2EE",
}

KO_RED      = "#ef4444"
FALLBACK    = "#5B8DB8"
FALLBACK_BG = "#E8EFF5"
TEXT_DARK   = "#1a1a2e"   # near-black for all labels/titles


def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def _darken(hex_color, factor=0.55):
    """Darken a hex color by mixing with black."""
    r, g, b = _hex_to_rgb(hex_color)
    return f'#{int(r*factor*255):02x}{int(g*factor*255):02x}{int(b*factor*255):02x}'


def _make_cmap(color_hex):
    """type color (dark/saturated) → near-white: dark = optimal (low damage)."""
    r, g, b = _hex_to_rgb(color_hex)
    return LinearSegmentedColormap.from_list('type_cmap', [
        (r, g, b),             # low damage  → darkest (good)
        (0.97, 0.97, 0.97),   # high damage → near-white (bad)
    ])


# ── main entry point ──────────────────────────────────────────────────────────

def plot_heatmap(
    results, def_stat1, def_stat2,
    move_type1, move_type2,
    attacker1_name, attacker2_name,
    defender_name, move1_name, move2_name,
    optimal,
):
    if not results:
        return

    accent   = TYPE_COLORS.get(move_type1, FALLBACK)
    dark_acc = _darken(accent, 0.6)    # darker shade for text on light bg
    bg_color = TYPE_BG_COLORS.get(move_type1, FALLBACK_BG)
    cmap     = _make_cmap(accent)

    same_stat = (def_stat1 == def_stat2)
    if same_stat:
        _plot_two_stat(
            results, def_stat1, cmap, accent, dark_acc, bg_color,
            attacker1_name, attacker2_name, defender_name,
            move1_name, move2_name, move_type1, move_type2, optimal,
        )
    else:
        _plot_three_stat(
            results, def_stat1, def_stat2, cmap, accent, dark_acc, bg_color,
            attacker1_name, attacker2_name, defender_name,
            move1_name, move2_name, move_type1, move_type2, optimal,
        )


# ── grid builder ──────────────────────────────────────────────────────────────

def _build_grid(results, x_key, y_key):
    x_vals = sorted(set(r[x_key] for r in results))
    y_vals = sorted(set(r[y_key] for r in results))
    x_idx  = {v: i for i, v in enumerate(x_vals)}
    y_idx  = {v: i for i, v in enumerate(y_vals)}
    grid   = np.full((len(y_vals), len(x_vals)), np.nan)
    for r in results:
        grid[y_idx[r[y_key]], x_idx[r[x_key]]] = r['total'] * 100
    return grid, x_vals, y_vals, x_idx, y_idx


# ── figure + imshow ───────────────────────────────────────────────────────────

def _make_fig(bg_color, cmap, grid, figsize=(12, 7.5)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    cmap.set_bad(color=bg_color)
    masked = np.ma.array(grid, mask=np.isnan(grid))
    vmin   = float(np.nanmin(grid))
    vmax   = float(np.nanmax(grid))

    im = ax.imshow(
        masked, aspect='auto', origin='lower',
        cmap=cmap, interpolation='bilinear',
        vmin=vmin, vmax=vmax,
    )
    return fig, ax, im, vmin, vmax


# ── axes + colorbar styling ───────────────────────────────────────────────────

def _style_axes(ax, cbar, dark_acc, bg_color, vmin, vmax):
    ax.tick_params(colors=dark_acc, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(dark_acc)

    cbar.set_label('combined % HP dealt (max roll)', color=dark_acc, fontsize=9)
    cbar.ax.yaxis.set_tick_params(color=dark_acc)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=dark_acc)
    cbar.outline.set_edgecolor(dark_acc)

    if vmin < 100 < vmax:
        frac = (100 - vmin) / (vmax - vmin)
        cbar.ax.axhline(frac, color=KO_RED, linewidth=1.5, linestyle='--')
        cbar.ax.text(1.1, frac, 'KO', transform=cbar.ax.transAxes,
                     color=KO_RED, va='center', fontsize=8, fontweight='bold')


# ── KO contour ────────────────────────────────────────────────────────────────

def _draw_ko_contour(ax, grid, x_vals, y_vals, vmin, vmax):
    if vmin < 100 < vmax:
        safe = np.where(np.isnan(grid), vmax, grid)
        ax.contour(
            np.arange(len(x_vals)), np.arange(len(y_vals)), safe,
            levels=[100], colors=[KO_RED], linewidths=2.0, linestyles='--',
        )


# ── optimal marker ────────────────────────────────────────────────────────────

def _draw_optimal(ax, opt_x, opt_y):
    ax.scatter(opt_x, opt_y, s=300, marker='*',
               color='white', edgecolors=TEXT_DARK, linewidths=1.4, zorder=5)


# ── info box (bottom-left) ────────────────────────────────────────────────────

def _draw_info_box(ax, optimal, def_stat1, def_stat2, dark_acc, bg_color):
    same_stat = (def_stat1 == def_stat2)

    if same_stat:
        spread = (f"{optimal['HP_SP']} HP / "
                  f"{optimal[f'{def_stat1}_SP']} {def_stat1.upper()}")
    else:
        spread = (f"{optimal['HP_SP']} HP / "
                  f"{optimal[f'{def_stat1}_SP']} {def_stat1.upper()} / "
                  f"{optimal[f'{def_stat2}_SP']} {def_stat2.upper()}")

    pct1    = optimal['pct1']
    pct2    = optimal['pct2']
    total   = optimal['total'] * 100
    box_txt = (
        f"optimal spread\n"
        f"{spread}\n"
        f"move 1: {optimal['dmg1']}/{optimal['HP']} HP  ({pct1:.1f}%)\n"
        f"move 2: {optimal['dmg2']}/{optimal['HP']} HP  ({pct2:.1f}%)\n"
        f"combined: {total:.1f}%"
    )
    ax.text(
        0.02, 0.03, box_txt,
        transform=ax.transAxes,
        fontsize=8.5, color=dark_acc,
        va='bottom', ha='left', linespacing=1.5,
        bbox=dict(
            boxstyle='round,pad=0.5',
            facecolor='white', edgecolor=dark_acc,
            linewidth=1.4, alpha=0.88,
        ),
        zorder=6,
    )


# ── title block ───────────────────────────────────────────────────────────────

def _draw_titles(fig, ax, atk1, atk2, dfn, mv1, mv2, type1, type2,
                 dark_acc, bg_color, optimal):
    atk_label = atk1 if atk1 == atk2 else f'{atk1} + {atk2}'

    # Main title — no type tag, ASCII arrow
    title = f'{atk_label}  ->  {dfn}   ({mv1}  +  {mv2})'
    ax.set_title(title, fontsize=13, fontweight='bold', color=dark_acc, pad=68)

    # Desc lines — directly below title, clear gap above the axes
    desc1 = optimal.get('desc1', '')
    desc2 = optimal.get('desc2', '')
    if desc2:
        ax.text(0.5, 1.01, desc2,
                transform=ax.transAxes, fontsize=7.5, color=dark_acc,
                alpha=0.72, ha='center', va='bottom')
    if desc1:
        ax.text(0.5, 1.055, desc1,
                transform=ax.transAxes, fontsize=7.5, color=dark_acc,
                alpha=0.72, ha='center', va='bottom')


# ── tick helper ───────────────────────────────────────────────────────────────

def _set_ticks(ax, x_vals, y_vals, xlabel, ylabel, dark_acc):
    step_x = max(1, len(x_vals) // 20)
    step_y = max(1, len(y_vals) // 20)
    ax.set_xticks(range(0, len(x_vals), step_x))
    ax.set_xticklabels([x_vals[i] for i in range(0, len(x_vals), step_x)])
    ax.set_yticks(range(0, len(y_vals), step_y))
    ax.set_yticklabels([y_vals[i] for i in range(0, len(y_vals), step_y)])
    ax.set_xlabel(xlabel, color=dark_acc, fontsize=10)
    ax.set_ylabel(ylabel, color=dark_acc, fontsize=10)


# ── save ──────────────────────────────────────────────────────────────────────

def _save(fig, bg_color):
    fig.tight_layout()
    fig.savefig('heatmap', dpi=150, facecolor=bg_color, bbox_inches='tight')
    plt.close(fig)
    print("  Saved heatmap.png")


# ── two-stat ──────────────────────────────────────────────────────────────────

def _plot_two_stat(
    results, def_stat, cmap, accent, dark_acc, bg_color,
    atk1, atk2, dfn, mv1, mv2, type1, type2, optimal,
):
    grid, x_vals, y_vals, x_idx, y_idx = _build_grid(
        results, x_key=f'{def_stat}_SP', y_key='HP_SP')

    fig, ax, im, vmin, vmax = _make_fig(bg_color, cmap, grid)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    _style_axes(ax, cbar, dark_acc, bg_color, vmin, vmax)
    _draw_ko_contour(ax, grid, x_vals, y_vals, vmin, vmax)

    opt_x = x_idx.get(optimal[f'{def_stat}_SP'])
    opt_y = y_idx.get(optimal['HP_SP'])
    if opt_x is not None and opt_y is not None:
        _draw_optimal(ax, opt_x, opt_y)

    _set_ticks(ax, x_vals, y_vals,
               xlabel=f'{def_stat.upper()} SP',
               ylabel='HP SP',
               dark_acc=dark_acc)
    _draw_info_box(ax, optimal, def_stat, def_stat, dark_acc, bg_color)
    _draw_titles(fig, ax, atk1, atk2, dfn, mv1, mv2, type1, type2,
                 dark_acc, bg_color, optimal)
    _save(fig, bg_color)


# ── three-stat ────────────────────────────────────────────────────────────────

def _plot_three_stat(
    results, stat_a, stat_b, cmap, accent, dark_acc, bg_color,
    atk1, atk2, dfn, mv1, mv2, type1, type2, optimal,
):
    grid, x_vals, y_vals, x_idx, y_idx = _build_grid(
        results, x_key=f'{stat_a}_SP', y_key=f'{stat_b}_SP')

    fig, ax, im, vmin, vmax = _make_fig(bg_color, cmap, grid)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    _style_axes(ax, cbar, dark_acc, bg_color, vmin, vmax)
    _draw_ko_contour(ax, grid, x_vals, y_vals, vmin, vmax)

    opt_x = x_idx.get(optimal[f'{stat_a}_SP'])
    opt_y = y_idx.get(optimal[f'{stat_b}_SP'])
    if opt_x is not None and opt_y is not None:
        _draw_optimal(ax, opt_x, opt_y)

    _set_ticks(ax, x_vals, y_vals,
               xlabel=f'{stat_a.upper()} SP  (move 1: {mv1})',
               ylabel=f'{stat_b.upper()} SP  (move 2: {mv2})',
               dark_acc=dark_acc)

    ax.text(0.99, 0.01, f'HP SP = budget − {stat_a.upper()} SP − {stat_b.upper()} SP',
            transform=ax.transAxes, fontsize=7, color=dark_acc,
            alpha=0.55, ha='right', va='bottom')

    _draw_info_box(ax, optimal, stat_a, stat_b, dark_acc, bg_color)
    _draw_titles(fig, ax, atk1, atk2, dfn, mv1, mv2, type1, type2,
                 dark_acc, bg_color, optimal)
    _save(fig, bg_color)