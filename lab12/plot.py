import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("results.csv")
med = df.groupby(["mode", "workers"], as_index=False)[["rps", "p95"]].median()

for metric, title, ylabel, filename in [
    ("p95", "Зависимость P95 Latency от числа клиентов", "P95 Latency (мс)", "charts/p95_chart.png"),
    ("rps", "Зависимость Throughput (RPS) от числа клиентов", "RPS (запросов/сек)", "charts/rps_chart.png"),
]:
    plt.figure(figsize=(8, 5))
    for mode, label in [("no_index", "Без индекса"), ("with_index", "С составным индексом")]:
        sub = med[med["mode"] == mode]
        plt.plot(sub["workers"], sub[metric], marker="o", label=label)
    plt.title(title)
    plt.xlabel("Количество параллельных клиентов (workers)")
    plt.ylabel(ylabel)
    plt.xticks([1, 4, 8])
    plt.grid(True)
    plt.legend()
    plt.savefig(filename, dpi=150)
    plt.close()
print("Графики сохранены в папку charts/")
