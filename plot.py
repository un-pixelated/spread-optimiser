# plot.py

import matplotlib.pyplot as plt

def plot(xs: list[tuple[int, int]], ys: list[float]):
    plt.plot([str(x) for x in xs], [y * 100 for y in ys])
    plt.xlabel("(HP SP, DEF SP)")
    plt.ylabel("% HP dealt")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.show()