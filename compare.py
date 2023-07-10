import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

df1 = pd.read_csv("outputs/res_base_base.csv")
df2 = pd.read_csv("outputs/res_base_cot.csv")
df3 = pd.read_csv("outputs/res_rules_base.csv")
df4= pd.read_csv("outputs/res_rules_cot.csv")
df1_acc = df1["Relaxed Match"].values.tolist()
df2_acc = df2["Relaxed Match"].values.tolist()
df3_acc = df3["Relaxed Match"].values.tolist()
df4_acc = df4["Relaxed Match"].values.tolist()

# Combine results into a 2D array
results = np.array([df1_acc, df2_acc, df3_acc, df4_acc])

# Set up labels for LLMs and input sentences
llm_labels = ['Base-Base', 'Base-CoT', 'Rules-Base', 'Rules-CoT']
sentence_labels = [str(i) for i in range(results.shape[1])]

# Create a heatmap
fig, ax = plt.subplots()
sns.heatmap(results, annot=True, fmt=".0f", cmap='Blues', cbar=True, ax=ax, linewidths=1, linecolor='black')

ax.set_yticks(np.arange(len(llm_labels)) + 0.5)  # Set the tick positions
ax.set_yticklabels(llm_labels, rotation='vertical')
ax.set_xticks(np.arange(len(sentence_labels)) + 0.5)  # Set the tick positions
ax.set_xticklabels(sentence_labels)

ax.set_xlabel('Intent Inputs')
ax.set_ylabel('Prompt Configuration')
ax.set_title('Nile Intent Parsing Results for Different Prompt Configurations')

plt.show()
