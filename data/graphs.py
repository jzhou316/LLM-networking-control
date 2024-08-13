import matplotlib.pyplot as plt
import numpy as np
import json
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MultipleLocator
from tueplots import figsizes, fonts

# Load the new JSON data
file_path = 'results.json'
with open(file_path, 'r') as file:
    data = json.load(file)
    data = data  # Adjust data length if needed

# Intent names in order
intent_names = ['ip-config-1', 'ip-config-2', 'bgp-1', 'bgp-2', 'port-channels-1', 'port-channels-2', 
                'vxlan-1', 'vxlan-2', 'acl-1', 'acl-2', 'qos-1', 'qos-2', 'ospf-1']

# Extract latencies and group them by intent statements
trials_per_intent = 3

entries = []
latencies = []

for i, entry in enumerate(data):
    latencies.append(entry["latencies"])
    intent_num = (i // trials_per_intent)
    entries.append(f"{intent_names[intent_num]}")

# Limit verification iterations to 5 for qos intents
for i, entry in enumerate(entries):
    if 'qos' in entry:
        latencies[i] = latencies[i][:7]  # Keep the first 7 components (2 mandatory + 5 verification)

# Determine the maximum number of latencies in any entry
max_latencies = max(len(lat) for lat in latencies)

# Convert to numpy array for easier manipulation
latencies = np.array([np.pad(lat, (0, max_latencies - len(lat)), 'constant') for lat in latencies])

# Calculate the mean latency
mean_latency = np.mean([sum(lat) for lat in latencies])

# Define the width of the bars
width = 0.6

# Define a divergent heat map color palette
base_colors = ['#377eb8', '#C0C0C0']  # Blue for first component, silver for second
gradient_colors = plt.cm.Reds(np.linspace(0.3, 1, max_latencies - 2)).tolist()  # Gradient from light to dark red for verification iterations
colors = base_colors + gradient_colors

# Define labels for each component
component_labels = ['Context Retrieval', 'Config Generation + Initial Verification'] + [f'Correction + Re-verification {i+1}' for i in range(max_latencies - 2)]

# Create new entries list with unique intent names
unique_entries = list(dict.fromkeys(entries))

plt.rcParams['font.family'] = "serif"
plt.rcParams['font.serif'] = "Computer Modern"

# Plotting the stacked bar chart
fig, ax = plt.subplots(figsize=(18, 12))  # Adjusted figure size

# Initialize the bottom array to zero
bottom = np.zeros(len(latencies))

# Create a stacked bar plot
for i in range(max_latencies):
    heights = latencies[:, i]
    p = ax.bar(np.arange(len(entries)), heights, width, label=component_labels[i], bottom=bottom, color=colors[i])
    bottom += heights

# Add labels and title
ax.set_xlabel('Intent Statements', fontsize=24)
ax.set_ylabel('Time (seconds)', fontsize=24)
ax.legend(loc="upper left", title='Components', fontsize=18, title_fontsize=20)

# Replace x-axis labels with unique intent names and add space for separation
ax.set_xticks(np.arange(0, len(entries), trials_per_intent) + trials_per_intent / 2 - 0.5)
ax.set_xticklabels(unique_entries, rotation=45, ha='right', fontsize=18)

# Make y-axis numbers larger
ax.tick_params(axis='y', labelsize=18)

# Add horizontal grid lines at 25, 50, 75, etc.
ax.yaxis.set_major_locator(MultipleLocator(25))
ax.yaxis.grid(True, which='major', linestyle='--', linewidth=0.5, color='grey')

# Remove default vertical grid lines
ax.grid(False, axis='x')

# Group bars for each intent statement together by using vertical grid lines
for i in range(trials_per_intent, len(entries), trials_per_intent):
    plt.axvline(x=i - 0.5, color='grey', linestyle='--', linewidth=1.5)

# Adjust x-axis limits to remove extra space
ax.set_xlim(-0.5, len(entries) - 0.5)

# Add mean latency line
mean_line = ax.axhline(mean_latency, color='green', linestyle='--', linewidth=2)
ax.text(-0.45, mean_latency + 5, f'Mean Latency: {mean_latency:.2f}s', color='green', fontsize=15, verticalalignment='center', weight='bold')

# Add annotation for qos-2
for i, entry in enumerate(entries):
    if entry == 'qos-2':
        ax.text(i + 0.25, sum(latencies[i]) + 2, 'Failed', ha='center', fontsize=15, color='red', weight='bold')

plt.tight_layout()

# Save the figure
plt.savefig('clos_final.png', format='png', dpi=1000)

plt.show()
