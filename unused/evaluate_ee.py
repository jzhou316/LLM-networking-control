import json, sys
from sklearn.metrics import precision_score, recall_score, f1_score

if len(sys.argv) != 2:
    print("Usage: python evaluate_results.py llm | python evaluate_results.py lumi")
    sys.exit(1)

if sys.argv[1] == "llm":
    # Load the JSON data from the files
    with open("results_alpha_llm_ee.json") as results_file:
        results_data = json.load(results_file)
    
    # Extract entities from the new results
    results_entities = []
    for item in results_data:
        for entity_type, entity_value in item.get("entities", {}).items():
            results_entities.append((item["intent_statement"], entity_type, entity_value))

elif sys.argv[1] == "lumi":
    # Load the JSON data from the files
    with open("results_alpha_lumi_ee.json") as results_file:
        results_data = json.load(results_file)

    results_entities = []
    for item in results_data:
        for entity in item.get("extracted_entities", []):
            results_entities.append((item["text"], entity["type"], entity["value"]))

with open("extraction_alpha.json") as extraction_file:
    extraction_data = json.load(extraction_file)

# Extract expected entities from the extraction
expected_entities = []
for intent in extraction_data["intents"]:
    for part in intent["parts"]:
        if "entity_type" in part and "text" in part and part["entity_type"] != "@sys.ignore":
            expected_entities.append((intent["text"], part["entity_type"], part["text"]))

# Prepare data for evaluation
results_flat = [entity[1] for entity in results_entities]
expected_flat = [entity[1][1:] for entity in expected_entities]

# print("Results entities:", sorted(set(results_flat)))
# print()
# print("Expected entities:", sorted(set(expected_flat)))

# Convert to binary format for precision/recall calculation
all_entities = results_flat + expected_flat
results_binary = [1 if entity in results_flat else 0 for entity in all_entities]
expected_binary = [1 if entity in expected_flat else 0 for entity in all_entities]

# Calculate precision, recall, and F1 score
precision = precision_score(expected_binary, results_binary)
recall = recall_score(expected_binary, results_binary)
f1 = f1_score(expected_binary, results_binary)

print("Precision:", precision)
print("Recall:", recall)
print("F1 Score:", f1)
