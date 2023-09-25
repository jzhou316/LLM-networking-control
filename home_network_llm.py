import json
import sys
import re
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate, LLMChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.callbacks import get_openai_callback

class Chat:
    def __init__(self):
        self.chat = ChatOpenAI(temperature=0,
                               openai_api_key="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"
                               )
        self.message_chain = []

        # system message is the instruction
        with open('instr.txt', 'r') as f:
            instr = f.read()

        system_message_prompt = SystemMessagePromptTemplate.from_template(instr)
        self.message_chain.append(system_message_prompt)

        # import examples and break them into human-ai pairs
        with open('examples.json', 'r') as f:
            examples = json.load(f)

        for example in examples:
            example_human = "Natural language request: {}".format(example['query'])
            example_human = HumanMessagePromptTemplate.from_template(example_human)
            example_ai = example['answer']
            example_ai = AIMessagePromptTemplate.from_template(example_ai)
            self.message_chain.append(example_human)
            self.message_chain.append(example_ai)

    def query(self, input: str):
        # human prompt is the suffix
        prompt_template = PromptTemplate(
            input_variables=["query"],
            output_parser=None,
            partial_variables={},
            template="Natural language request: {query}",
            template_format='f-string',
            validate_template=True
        )

        human_message_prompt = HumanMessagePromptTemplate(prompt=prompt_template)
        self.message_chain.append(human_message_prompt)

        # build chat completion from the formatted messages
        chat_prompt = ChatPromptTemplate.from_messages(self.message_chain)
        chain = LLMChain(llm=self.chat, prompt=chat_prompt)

        # run the chain and return the answer
        ai_answer = chain.run({
            'query': input
        })

        print(ai_answer)
        return ai_answer

    def print_message_chain(self):
        chat_prompt = ChatPromptTemplate.from_messages(self.message_chain)
        chain = LLMChain(llm=self.chat, prompt=chat_prompt)
        for message in chat_prompt.messages:
            if isinstance(message, SystemMessagePromptTemplate):
                system_message = message.prompt.template
                print("\033[31m\033[1mSystem:\033[0m")
                print(system_message)
            elif isinstance(message, HumanMessagePromptTemplate):
                human_message = message.prompt.template
                print("\033[34m\033[1mHuman:\033[0m")
                try:
                    print(human_message.format(query=input))
                except:
                    print(human_message)
            elif isinstance(message, AIMessagePromptTemplate):
                ai_message = message.prompt.template
                print("\033[32m\033[1mAI:\033[0m")
                print(ai_message)

    def parse_intent(self, intent: str):
        # Define entities and operations
        entities = ['endpoint', 'link', 'group', 'bandwidth']
        operations = ['add', 'remove', 'for', 'set', 'from', 'to']

        # Split the intent into expressions
        expressions = intent.split('\n')

        # For each expression, split into operation and entity
        parsed_intent = {}
        for expr in expressions:
            op, rest = expr.strip().split(' ', 1)
            if op not in operations: 
                continue
            # Further split the rest into entity and arguments
            entity_args = re.findall(r"(\w+)\(\'(.*?)\'\)", rest)
            print(rest)
            print(entity_args)
            entity_list = []
            for entity, args in entity_args:
                if entity in entities:
                    args = args.split(', ')
                    entity_list.append((entity, args))
            parsed_intent[op] = entity_list

        return parsed_intent
