import matplotlib.pyplot as plt

def plot(xs: list[tuple[int, int]], ys: list[float], def_stat: str = "def"):
    plt.plot([str(x) for x in xs], [y * 100 for y in ys])
    plt.xlabel(f"(HP SP, {def_stat.upper()} SP)")
    plt.ylabel("% HP dealt (max roll)")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig("plot")
