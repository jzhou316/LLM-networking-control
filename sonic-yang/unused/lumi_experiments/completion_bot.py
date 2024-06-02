import json
from langchain import PromptTemplate, FewShotPromptTemplate
from langchain.llms import OpenAI

# initialize the models
openai = OpenAI(
    model_name="text-davinci-003",
    openai_api_key="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"
)

# create our examples
with open('examples.json', 'r') as file:
    examples = json.load(file)

# create a example template
example_template = """
Natural language request: {query}\n
Nile: {answer}
"""

# create a prompt example from above template
example_prompt = PromptTemplate(
    input_variables=["query", "answer"],
    template=example_template
)

# now break our previous prompt into a prefix and suffix
# the prefix is our instructions
with open('prefix.txt', 'r') as file:
    prefix = file.read()

# and the suffix our user input and output indicator
suffix = """
\"\"\"
Natural language request: {query}\n
Nile: """

# now create the few shot prompt template
few_shot_prompt_template = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix=prefix,
    suffix=suffix,
    input_variables=["query"],
    example_separator="\n\n"
)

with open('input.txt', 'r') as file:
    queries = file.readlines()

# with open("output.txt", "w") as file:
#     for query in queries:
#         output = openai(few_shot_prompt_template.format(query=query.strip()))
#         file.writelines(output)

query = queries[7]
final_prompt = few_shot_prompt_template.format(query=query.strip())
#print(final_prompt)
print(openai(final_prompt))

