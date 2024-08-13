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
df_json_campi['source'] = 'Campi (Time)'
df_json_alpha['source'] = 'Alpha (Time)'

# Combine the dataframes
df_combined = pd.concat([df_json_campi, df_json_alpha], ignore_index=True)

# Calculate means and standard deviations
df_grouped = df_combined.groupby(['iterations', 'source'])['time'].agg(['mean', 'std']).reset_index()

# Calculate the quantity
df_combined['quantity'] = 1
df_quantity = df_combined.groupby(['iterations', 'source'])['quantity'].sum().reset_index()
df_quantity['source'] = df_quantity['source'].replace({'Campi (Time)': 'Campi (Quantity)', 'Alpha (Time)': 'Alpha (Quantity)'})

# Set up the figure and axes with a more rectangular aspect ratio
fig, ax1 = plt.subplots(figsize=(14, 6))

# Define custom colors
palette = {'Campi (Time)': 'red', 'Alpha (Time)': '#377eb8'}

# Line plot with error bars for processing times per iteration
sns.lineplot(ax=ax1, x='iterations', y='mean', hue='source', palette=palette, data=df_grouped, marker='o', markersize=10, ci=None, linewidth=3, style='source', markers=['o', 's'])

# Add error bars with horizontal lines at the ends
for name, group in df_grouped.groupby('source'):
    ax1.errorbar(group['iterations'], group['mean'], yerr=group['std'], fmt='o', color=palette[name], capsize=5, capthick=1, elinewidth=1)

ax1.set_xlabel('Number of Correction Iterations', fontsize=20)
ax1.set_ylabel('Time (seconds)', fontsize=20)
ax1.tick_params(axis='both', which='major', labelsize=16)
ax1.grid(True, which='major', axis='both', linestyle='-', linewidth='0.5')
ax1.grid(True, which='minor', axis='both', linestyle=':', linewidth='0.5')
ax1.set_xticks(range(0, df_combined['iterations'].max() + 1))
ax1.set_yticks(range(0, int(df_grouped['mean'].max()) + 5, 5))  # Adjust spacing as needed

# Create a second y-axis for the quantity
ax2 = ax1.twinx()

bar_width = 0.35
iterations = df_quantity['iterations'].unique()

# Ensure that the quantities align properly with the iterations
campi_quantities = df_quantity[df_quantity['source'] == 'Campi (Quantity)'].set_index('iterations').reindex(iterations, fill_value=0)['quantity']
alpha_quantities = df_quantity[df_quantity['source'] == 'Alpha (Quantity)'].set_index('iterations').reindex(iterations, fill_value=0)['quantity']

bars_campi = ax2.bar(iterations - bar_width/2, campi_quantities, bar_width, alpha=0.3, label='Campi (Count)', color='red')
bars_alpha = ax2.bar(iterations + bar_width/2, alpha_quantities, bar_width, alpha=0.3, label='Alpha (Count)', color='#377eb8')

ax2.set_ylabel('Count', fontsize=20)
ax2.tick_params(axis='both', which='major', labelsize=16)
ax2.grid(True, which='major', axis='y', linestyle='--', linewidth='0.5', dashes=(5, 10))
ax2.set_yticks(range(0, int(df_quantity['quantity'].max()) + 10, 10))  # Adjust spacing as needed

# Annotate the bar at iteration 8 with "Failed"
for bar in bars_campi:
    if bar.get_x() + bar.get_width() / 2 > 7:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), 'Failed', ha='center', va='bottom', fontsize=14, color='red', weight='bold')

# Combine legends
handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()

# Ensure ordering of legend is Alpha (Time), Campi (Time), Alpha (Quantity), Campi (Quantity)
ordered_handles = [handles1[0], handles1[1], handles2[1], handles2[0]]
ordered_labels = [labels1[0], labels1[1], labels2[1], labels2[0]]

ax1.legend(ordered_handles, ordered_labels, loc='lower right', fontsize=16, title_fontsize=18, bbox_to_anchor=(1, 0.2))

# Adjust layout and aesthetics
sns.set_style("whitegrid")
plt.tight_layout()

# Save the plot
plt.savefig('lumi_latency.png')

# Show plot
plt.show()
