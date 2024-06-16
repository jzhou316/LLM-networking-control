import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the JSON files
file_path_campi = 'results_campi_llm_ee.json'
file_path_alpha = 'results_alpha_llm_ee.json'

with open(file_path_campi, 'r') as file:
    json_data_campi = json.load(file)
with open(file_path_alpha, 'r') as file:
    json_data_alpha = json.load(file)

# Convert the JSON data into pandas dataframes
df_json_campi = pd.json_normalize(json_data_campi)
df_json_alpha = pd.json_normalize(json_data_alpha)

# Add a new column to distinguish the datasets
df_json_campi['source'] = 'Campi'
df_json_alpha['source'] = 'Alpha'

# Combine the dataframes
df_combined = pd.concat([df_json_campi, df_json_alpha], ignore_index=True)

# Set up the figure and axes
fig, axes = plt.subplots(2, 2, figsize=(20, 14))

# Define a color palette suitable for scientific research
palette = sns.color_palette("Set2")

# Scatter plot for iterations vs processing time
sns.scatterplot(ax=axes[0, 0], x='iterations', y='time', hue='source', style='source', palette=palette, data=df_combined, alpha=0.6, s=100)
axes[0, 0].set_title('Iterations vs Processing Time', fontsize=16)
axes[0, 0].set_xlabel('Iterations', fontsize=14)
axes[0, 0].set_ylabel('Time (seconds)', fontsize=14)
axes[0, 0].legend(title='Source', loc='upper left')
axes[0, 0].grid(True)

# Box plot for processing times per iteration
sns.boxplot(ax=axes[0, 1], x='iterations', y='time', hue='source', palette=palette, data=df_combined)
axes[0, 1].set_title('Processing Times vs. Iteration with Distribution', fontsize=16)
axes[0, 1].set_xlabel('Iterations', fontsize=14)
axes[0, 1].set_ylabel('Time (seconds)', fontsize=14)
axes[0, 1].legend(title='Source', loc='upper left')
axes[0, 1].grid(True)

# Histogram for processing times with separate bars
sns.histplot(ax=axes[1, 0], data=df_combined, x='time', hue='source', multiple='dodge', bins=20, shrink=0.8, palette=palette, alpha=0.7)
axes[1, 0].set_title('Distribution of Processing Times', fontsize=16)
axes[1, 0].set_xlabel('Time (seconds)', fontsize=14)
axes[1, 0].set_ylabel('Frequency', fontsize=14)
axes[1, 0].grid(True)

# Distribution of output length
sns.histplot(ax=axes[1, 1], data=df_combined, x='nile_length', hue='source', multiple='dodge', bins=20, shrink=0.8, palette=palette, alpha=0.7)
axes[1, 1].set_title('Distribution of NILE Output Lengths', fontsize=16)
axes[1, 1].set_xlabel('NILE Length', fontsize=14)
axes[1, 1].set_ylabel('Frequency', fontsize=14)
axes[1, 1].grid(True)

# Adjust layout and aesthetics
plt.tight_layout()
sns.set_style("whitegrid")

# Save the combined plot
fig.savefig('combined_iterations_vs_time_distribution_pretty_v2.png')

# Show plot
plt.show()
