import pandas as pd
import matplotlib.pyplot as plt

# 1. Define your experimental results
data = {
    'run': [1, 2, 3, 4, 5, 6],
    'MSE': [1768.02, 611.32, 568.65, 788.38, 566.35, 637.40],
    'R2': [0.7664, 0.9191, 0.9248, 0.8957, 0.9251, 0.9150]
}

# 2. Create a DataFrame
df = pd.DataFrame(data)

# 3. Plot Mean Squared Error
plt.figure()
plt.plot(df['run'], df['MSE'], marker='o')
plt.xlabel('Run Number')
plt.ylabel('Mean Squared Error')
plt.title('MSE Across LightGBM Configurations')
plt.xticks(df['run'])
plt.grid(True)
plt.tight_layout()
plt.show()

# 4. Plot R² Score
plt.figure()
plt.plot(df['run'], df['R2'], marker='o')
plt.xlabel('Run Number')
plt.ylabel('R² Score')
plt.title('R² Across LightGBM Configurations')
plt.xticks(df['run'])
plt.grid(True)
plt.tight_layout()
plt.show()
