import pandas as pd
import sys

# Intent Statement
input_file = open('data/input.txt')
input_content = input_file.readlines()
print("\033[32m\033[1mnl intent:\033[0m")
print(input_content[int(sys.argv[1]) - 1])

# Output from Different Prompt Configurations
for output_file in ['outputs/res_base_base.csv', 'outputs/res_base_cot.csv', 'outputs/res_rules_base.csv', 'outputs/res_rules_cot.csv', 'outputs/res_rules_cot_rn.csv']:
    df = pd.read_csv(output_file)
    print("\033[34m\033[1m" + output_file[output_file.find('_') + 1 : output_file.rfind('.')] + ":\033[0m")
    print(df.loc[int(sys.argv[1]) - 1, "LLM Output"])
print()

# Correct Answer
ans_file = open('data/niles_campi.txt')
ans_content = ans_file.readlines()
print("\033[32m\033[1mcorrect answer:\033[0m")
print(ans_content[int(sys.argv[1]) - 1])
