import os
import json
import sys
import random
import string
import re
import time

from assistant_handler import AssistantHandler
from grammar_handler import GrammarCheck
from openai_handler import OpenAIChatHandler

if len(sys.argv) != 2:
    print("Usage: python evaluate_results.py alpha | python evaluate_results.py campi | python evaluate_results.py cisco")
    sys.exit(1)


ah = AssistantHandler(assistant_id="asst_Gcl9yHz5NuGJ0xCmPgywyL8C")
gh = GrammarCheck()
ch = OpenAIChatHandler()

if sys.argv[1] == "alpha":
    with open('inputs_alpha.txt', 'r') as file:
        lines = file.readlines()
    file_path = "results_alpha_llm_ee.json"
elif sys.argv[1] == "campi":
    with open('inputs_campi.txt', 'r') as file:
        lines = file.readlines()
    file_path = "results_campi_llm_ee.json"
elif sys.argv[1] == "cisco":
    with open('inputs_cisco.txt', 'r') as file:
        lines = file.readlines()
    file_path = "results_cisco_llm_ee.json"

results = []

# print(gh.check_grammar("define intent parentalControlIntent: for service('PlayStation') add middlebox('parental_control')"))
# sys.exit(0)

# Process each line and append results
for line in lines:
    # Read existing results if the file exists
    if os.path.exists(file_path):
        with open(file_path, 'r') as infile:
            try:
                results = json.load(infile)
            except json.JSONDecodeError:
                results = []
    escape_pattern = r'^[\x00-\x1f\x7f-\x9f"]+|[\x00-\x1f\x7f-\x9f"]+$'
    # Use re.sub to replace escape characters with an empty string
    line = line.strip()
    if line:
        t0 = time.time()
        result = ah.run_assistant(line)
        extracted_json = ah.extract_json(result)
        extracted_python = ah.extract_python(result)
        grammar_check = gh.check_grammar(extracted_python)
        count = 0
        while not grammar_check[0] and count < 8:
            session_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
            generate_config = ch.invoke(system_template="prompt_templates/system.txt",
                                        human_template="prompt_templates/human.txt",
                                        system_input_variables=[],
                                        human_input_variables=['intent', 'request', 'column'],
                                        system_input_values=[],
                                        human_input_values=[line, extracted_python, grammar_check[1]],
                                        session_id=session_id)
            extracted_python = ch.extract_python_config(generate_config)
            grammar_check = gh.check_grammar(re.sub(escape_pattern, '', extracted_python))
            count += 1
        t1 = time.time()
        results.append({
            "text": line,
            "extracted_entities": json.loads(extracted_json),
            "nile_statement": re.sub(escape_pattern, '', extracted_python),
            "grammar_check": grammar_check[0],
            "iterations": count,
            "time": t1 - t0,
            "intent_length": len(line),
            "nile_length": len(re.sub(escape_pattern, '', extracted_python))
        })

    with open(file_path, 'w') as outfile:
        json.dump(results, outfile, indent=4)