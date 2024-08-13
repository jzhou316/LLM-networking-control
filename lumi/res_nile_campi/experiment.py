import re, yaml, json, string, sys
import pandas as pd
from collections import Counter

NILE_OPERATIONS = ['add', 'remove', 'from', 'to', 'set', 'unset', 'allow', 'block', 'start', 'end', 'for']
synonyms_processed = []

# Read and parse synonyms YAML file
with open('synonyms.yml', 'r') as file:
    yaml_data = yaml.safe_load(file)

nlu_data = yaml_data['nlu']
synonyms_processed = {}
for entry in nlu_data:
    key = entry['synonym']
    value = entry['examples']
    value_list = value.strip().split('\n')
    value_list = [str(item).strip('- ') for item in value_list]
    if str(key) not in value_list:
        value_list.append(str(key))
    synonyms_processed[value_list[0]] = list(set(value_list))

def normalize(text):
    return text.lower().strip()

def replace_synonyms(word, synonyms):
    word_lower = word.lower()
    for key, value in synonyms.items():
        if word_lower in value:
            return key
    return word_lower

def parse_intent(intent):
    words = intent.lower().split()
    if len(words) <= 3:
        return []
    
    remaining_intent = ' '.join(words[3:])
    
    # Find and normalize entities within parentheses
    entity_pattern = re.compile(r"\('([^']+)'\)")
    entities = entity_pattern.findall(remaining_intent)
    normalized_entities = [replace_synonyms(normalize(entity), synonyms_processed) for entity in entities]
    
    # Replace original entities with normalized entities in the intent
    for original, normalized in zip(entities, normalized_entities):
        remaining_intent = remaining_intent.replace(original, normalized)
    
    # Replace every (' and ') with a space
    remaining_intent = remaining_intent.replace("('", " ").replace("')", " ")
    
    # Remove punctuation except colons and spaces
    remaining_intent = remaining_intent.translate(str.maketrans('', '', string.punctuation.replace("'", "").replace(":", ""))).replace("'", "")
    
    # Split the cleaned remaining intent into words
    remaining_words = remaining_intent.split()
    return remaining_words

def calculate_fine_grained_accuracy(intent1, intent2):
    words1 = parse_intent(intent1.lower())
    words2 = parse_intent(intent2.lower())
    print(words1)
    print(words2)
    new_list = []
    for word in words1:
        if word not in words2:
            new_list.append(word)
    for word in words2:
        if word not in words1:
            new_list.append(word)
    print(new_list)
    print()
    if not words1 or not words2:
        return 0
    
    matching_words = list((Counter(words1) & Counter(words2)).elements())

    # Calculate the percentage of matching words
    match_count = len(matching_words)
    total_count = len(words2)

    return ((match_count / total_count) * 100, match_count == total_count)

if __name__ == "__main__":
    intents = []
    if len(sys.argv) != 2:
        print("Usage: python evaluate_results.py llm | python evaluate_results.py lumi")
        sys.exit(1)
    
    if sys.argv[1] == "llm":
        with open('results_campi_llm_ee.json', 'r') as file:
            # Load json as dict
            data = json.load(file)
        for item in data:
            intents.append(item['nile_statement'])
    elif sys.argv[1] == "lumi":
        with open('results_campi_lumi_ee.json', 'r') as file:
            # Load json as dict
            data = json.load(file)
        for item in data:
            intents.append(item['nile_statement'])

    answers = []
    with open('extraction_campi.json', 'r') as file:
        # Load json as dict
        data = json.load(file)

    for intent in data['intents']:
        answers.append(intent['nile'])

    truth_vals = []
    exact_match = []
    for intent, answer in zip(intents, answers):
        soln = calculate_fine_grained_accuracy(intent, answer)
        truth_vals.append(soln[0])
        exact_match.append(soln[1])
    
    print(sum(truth_vals) / len(truth_vals))
    print(sum(exact_match) / len(exact_match))