import pandas as pd
import yaml
import re
import sys
from chatbot import openai_bot, print_prompt
from langchain.callbacks import get_openai_callback

NILE_OPERATIONS = ['add', 'remove', 'from', 'to', 'set', 'unset', 'allow', 'block', 'start', 'end', 'for']

# Read and parse synonyms YAML file
with open('synonyms.yml', 'r') as file:
    yaml_data = yaml.safe_load(file)

nlu_data = yaml_data['nlu']
synonyms_processed = []
for entry in nlu_data:
    key = entry['synonym']
    value = entry['examples']
    value_list = value.strip().split('\n')
    value_list = [str(item).strip('- ') for item in value_list]
    if str(key) not in value_list:
        value_list.append(str(key))
    synonyms_processed.append(set(value_list))

# Parses a NILE intent into a dictionary format
def parse_intent(intent):
    # Removes header
    intent_match = re.match(r"define intent uniIntent: ((?:{})(?: [^:]+)*)".format('|'.join(NILE_OPERATIONS)), intent)
    if intent_match is None:
        return {}
    intent = intent_match.group(1).strip()
    # Finds indices of NILE keywords
    indexes = []
    for operation in NILE_OPERATIONS:
        index = intent.find(operation)
        while (index == 0) or (index != -1 and intent[index-1] == ' ' and intent[index+len(operation)] == ' '):
            indexes.append((index, index+len(operation)))
            index = intent.find(operation, index + 1)
    indexes = sorted(indexes, key=lambda x: x[0])
    # Uses indices of NILE keywords to separate entities
    entities = {}
    for index_ind in range(len(indexes)):
        if indexes[index_ind] != indexes[-1]:
            cur_index = indexes[index_ind]
            next_index = indexes[index_ind + 1]
            entities[intent[cur_index[0]:cur_index[1]]] = intent[cur_index[1]+1:next_index[0]-1] 
        else:
            cur_index = indexes[index_ind]
            entities[intent[cur_index[0]:cur_index[1]]] = intent[cur_index[1]+1:len(intent)]
    # Parses the argument(s) of each NILE entity
    for entity in entities:
        pattern = r"(\w+)\((.*?)\)"
        matches = re.findall(pattern, entities[entity])
        keywords = {}
        for match in matches:
            keyword, parameter = match
            if keyword in keywords:
                keywords[keyword].append(parameter.strip("'"))
            else:
                keywords[keyword] = [parameter.strip("'")]
        entities[entity] = keywords
    return entities

def compare_dictionaries(intent1, intent2):
    # Check if dictionaries are exactly the same
    if intent1 == intent2:
        return True

    # Check if the dictionaries have the same NILE operations
    if set(intent1.keys()) != set(intent2.keys()):
        return False
    
    # Iterate over the NILE operations and compare the tags
    for op in intent1.keys():
        entry1 = intent1[op]
        entry2 = intent2[op]

        # If the tagged entries are exactly the same, continue to the next key
        if entry1 == entry2:
            continue

        # If tag keywords not the same, return False
        if set(entry1.keys()) != set(entry2.keys()):
            return False

        for tag in entry1.keys():
            inner1 = entry1[tag]
            inner2 = entry2[tag]

            # Synonyms checking
            for word1 in inner1:
                found = False
                if word1.lower() in [w.lower() for w in inner2]:
                    found = True
                    break
                for synonym_entry in synonyms_processed:
                    synonym_entry_lower = [w.lower() for w in synonym_entry]
                    if word1.lower() in synonym_entry_lower:
                        for synonym in synonym_entry_lower:
                            if synonym.lower() in [w.lower() for w in inner2]:
                                found = True
                                break
                    if found:
                        break
    
    # All key-value pairs are either the same or synonyms
    return True

# Takes the LLM output and extracts the translation answer
def extract_translation(string):
    substring = "Nile translation: "
    if substring in string:
        index = string.index(substring)
        return string[index + len(substring):]
    else:
        return string

# Takes the LLM output and extracts the CoT as a list of steps
def extract_cot(string):
    substring = "Reasoning: "
    if substring in string:
        index = string.index(substring)
        steps_string = string[index + len(substring):]
        # Regular expression pattern to match the steps
        pattern = r"\b((?<!Rule\s)\d\.\s[A-Za-z].*?)(?=\b(?<!Rule\s)\d\.\s[A-Za-z]|$)"
        # Extract the steps using regex
        steps = re.findall(pattern, steps_string, re.DOTALL)
        if len(steps) < 5:
            for i in range(5 - len(steps)):
                steps.append([""])
        if len(steps) != 5:
            print(steps)
            print("Number of steps is not 5.")
        return steps
    else:
        return [""] * 5


def main():
    # Translates campi intents into NILE 
    with open('data/input.txt') as file:
        intents = [(line.rstrip()).lstrip() for line in file]
    
    # Reads correct NILE intents from dataset
    with open('data/niles_campi.txt') as file:
        niles = [(line.rstrip()).lstrip() for line in file]
    
    intents = intents
    niles = niles

    niles_ser = pd.Series(niles)
    outputs = []

    # print_prompt(intents[0])
    # return

    with get_openai_callback() as cb:
        for intent in intents:
            # different processing of NL intents
            output = openai_bot(intent)
            output = output.replace('\n', '').replace('\t', '')
            # record steps and translation
            parsed_output = {}
            parsed_output["translation"] = extract_translation(output)
            parsed_output["steps"] = extract_cot(output)
            #print(parsed_output["steps"])
            outputs.append(parsed_output)
        print(cb)

    translations = []
    step_1s = []
    step_2s = []
    step_3s = []
    step_4s = []
    step_5s = []
    
    for output in outputs:
        translations.append(output["translation"])
        step_1s.append(output["steps"][0])
        step_2s.append(output["steps"][1])
        step_3s.append(output["steps"][2])
        step_4s.append(output["steps"][3])
        step_5s.append(output["steps"][4])
    translations_ser = pd.Series(translations)
    step_1_ser = pd.Series(step_1s)
    step_2_ser = pd.Series(step_2s)
    step_3_ser = pd.Series(step_3s)
    step_4_ser = pd.Series(step_4s)
    step_5_ser = pd.Series(step_5s)

    exact_matches = []
    relaxed_matches = []
    for i in range(len(intents)):
        exact_matches.append(outputs[i]["translation"] == niles[i])
        relaxed_matches.append(compare_dictionaries(parse_intent(outputs[i]["translation"]), parse_intent(niles[i])))
    exact_matches_ser = pd.Series(exact_matches)
    relaxed_matches_ser = pd.Series(relaxed_matches)
  
    # reading the csv file
    df = pd.read_csv("results/results.csv")
    # Extract the desired part of the filename
    col_name = sys.argv[3][sys.argv[3].find('_') + 1 : sys.argv[3].rfind('.')]
    # updating the column value/data
    df.loc[0, col_name] = str(exact_matches.count(True) / len(exact_matches))
    df.loc[1, col_name] = str(relaxed_matches.count(True) / len(relaxed_matches))
    # writing into the file
    df.to_csv("results/results.csv", index=False)

    data = {
        "Intents": intents,
        "LLM Output": translations_ser,
        "Correct Output": niles_ser,
        "Step 1": step_1_ser,
        "Step 2": step_2_ser,
        "Step 3": step_3_ser,
        "Step 4": step_4_ser,
        "Step 5": step_5_ser,
        "Exact Match": exact_matches_ser,
        "Relaxed Match": relaxed_matches_ser
    }
    df = pd.DataFrame(data=data)
    df.to_csv(sys.argv[3])

if __name__ == "__main__":
    main()