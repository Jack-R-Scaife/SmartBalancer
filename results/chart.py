import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Updated dataset with clean labels and units
data = {
    ("Low Scenario", "Standard"): {
        "RR": [6.99, 7.67, 7.52, 2.51],
        "WRR": [10.95, 6.96, 9.25, 2.32],
        "LRT": [9.07, 6.77, 5.47, 2.67],
        "LC": [12.63, 7.30, 6.63, 1.42],
        "RB": [8.60, 7.10, 7.58, 1.85],
    },
    ("Low Scenario", "Enhanced"): {
        "RR": [5.86, 8.46, 5.67, 1.13],
        "WRR": [5.62, 8.56, 3.76, 1.15],
        "LRT": [5.82, 9.17, 4.91, 1.14],
        "LC": [6.12, 7.80, 3.48, 1.17],
        "RB": [8.34, 8.34, 1.66, 1.13],
    },
    ("Medium Scenario", "Standard"): {
        "RR": [8.19, 6.67, 7.54, 2.46],
        "WRR": [17.36, 5.74, 6.82, 2.87],
        "LRT": [10.47, 15.88, 3.70, 1.87],
        "LC": [6.98, 7.51, 14.04, 1.38],
        "RB": [14.83, 5.42, 2.23, 2.11],
    },
    ("Medium Scenario", "Enhanced"): {
        "RR": [8.68, 8.62, 4.99, 1.86],
        "WRR": [5.53, 8.38, 3.83, 1.12],
        "LRT": [5.76, 8.70, 4.85, 1.19],
        "LC": [5.80, 7.97, 2.20, 1.16],
        "RB": [5.58, 7.70, 1.67, 1.12],
    },
    ("High Scenario", "Standard"): {
        "RR": [7.05, 5.53, 5.24, 2.23],
        "WRR": [11.44, 6.98, 5.40, 2.39],
        "LRT": [10.31, 6.71, 4.81, 2.01],
        "LC": [7.13, 8.10, 8.50, 1.22],
        "RB": [19.48, 5.50, 2.40, 2.54],
    },
    ("High Scenario", "Enhanced"): {
        "RR": [5.93, 8.35, 5.10, 1.13],
        "WRR": [5.73, 8.66, 3.81, 1.14],
        "LRT": [5.81, 9.90, 5.23, 1.18],
        "LC": [5.94, 8.97, 6.10, 1.15],
        "RB": [5.48, 8.21, 1.72, 1.14],
    },
}

# Flatten data into DataFrame
records = []
for (scenario, strategy_type), values in data.items():
    for strategy, metrics in values.items():
        records.append([
            scenario, strategy_type, strategy,
            metrics[0], metrics[1], metrics[2], metrics[3]
        ])

df = pd.DataFrame(records, columns=[
    "Scenario", "Type", "Strategy",
    "Avg Response Time (ms)", "Avg CPU (%)", "Avg Memory (MB)", "Avg Connections"
])

# Plotting
sns.set(style="whitegrid")
metrics = {
    "Avg Response Time (ms)": "ms",
    "Avg CPU (%)": "%",
    "Avg Memory (MB)": "MB",
    "Avg Connections": ""
}
scenarios = df["Scenario"].unique()

import matplotlib.ticker as mtick

# Generate charts with proper labels
for metric, unit in metrics.items():
    for scenario in scenarios:
        plt.figure(figsize=(10, 6))
        chart_data = df[df["Scenario"] == scenario]
        barplot = sns.barplot(data=chart_data, x="Strategy", y=metric, hue="Type")

        plt.title(f"{metric} - {scenario}")
        plt.xlabel("Load Balancing Strategy")
        plt.ylabel(f"{metric}" if unit == "" else f"{metric}")
        plt.xticks(rotation=45)
        plt.legend(title="Strategy Type")

        for p in barplot.patches:
            if p.get_height() > 0:  # Avoid printing "0.0" for invisible bars
                height = p.get_height()
                barplot.annotate(f'{height:.2f}', 
                                 (p.get_x() + p.get_width() / 2., height),
                                 ha='center', va='bottom', fontsize=9, color='black', xytext=(0, 3),
                                 textcoords='offset points')

        plt.tight_layout()
        plt.show()
