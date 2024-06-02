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
        self.chat_history = {}

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

        self.chat_history[input] = ai_answer
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
        # Split the intent into individual operations or policies
        statements = re.split(r';\n', intent)
        intents = []

        for statement in statements:
            if statement.startswith('add') or statement.startswith('remove'):
                intents.append(self.parse_operation(statement))
            elif statement.startswith('set') or statement.startswith('allow') or statement.startswith('block'):
                intents.append(self.parse_policy(statement))
            else:
                intents.append({})
        return intents

    def parse_operation(self, operation_statement: str):
        add_endpoint = re.match(r"add endpoint\('([^']+)'\) to group\('([^']+)'\)", operation_statement)
        remove_endpoint = re.match(r"remove endpoint\('([^']+)'\) from group\('([^']+)'\)", operation_statement)
        add_link = re.match(r"add link\('endpoint\('([^']+)'\)'\, 'endpoint\('([^']+)'\)'\)", operation_statement)
        remove_link = re.match(r"remove link\('endpoint\('([^']+)'\)'\, 'endpoint\('([^']+)'\)'\)", operation_statement)
        add_group = re.match(r"add group\('([^']+)'\)", operation_statement)
        remove_group = re.match(r"remove group\('([^']+)'\)", operation_statement)

        result_dict = {}
        # Create dictionary to represent the intent
        if add_endpoint:
            result_dict['operation'] = "add_endpoint"
            result_dict['endpoint'] = add_endpoint.group(1)
            result_dict['group'] = add_endpoint.group(2)
        elif remove_endpoint:
            result_dict['operation'] = "remove_endpoint"
            result_dict['endpoint'] = remove_endpoint.group(1)
            result_dict['group'] = remove_endpoint.group(2)
        elif add_link:
            result_dict['operation'] = "add_link"
            result_dict['source'] = add_link.group(1)
            result_dict['destination'] = add_link.group(2)
        elif remove_link:
            result_dict['operation'] = "remove_link"
            result_dict['source'] = remove_link.group(1)
            result_dict['destination'] = remove_link.group(2)
        elif add_group:
            result_dict['operation'] = "add_group"
            result_dict['group'] = add_group.group(1)
        elif remove_group:
            result_dict['operation'] = "remove_group"
            result_dict['group'] = remove_group.group(1)
        else:
            result_dict['operation'] = "unparsable"
            result_dict['statement'] = operation_statement

        return result_dict

    def parse_policy(self, policy_statement: str):
        time_interval = re.search(r"start hour\('(\d{2}:\d{2})'\) end hour\('(\d{2}:\d{2})'\)", policy_statement)
        set_bandwidth_link = re.match(r"set bandwidth\(('max'|'min'), (\d+), ('gbps'|'mbps')\) for link\(endpoint\('([^']+)'\), endpoint\('([^']+)'\)\)(?: ?)", policy_statement)
        set_bandwidth_endpoint = re.match(r"set bandwidth\(('max'|'min'), (\d+), ('gbps'|'mbps')\) for endpoint\('([^']+)'\)(?: ?)", policy_statement)
        set_bandwidth_group = re.match(r"set bandwidth\(('max'|'min'), (\d+), ('gbps'|'mbps')\) for group\('([^']+)'\)(?: ?)", policy_statement)
        allow_traffic = re.match(r"allow traffic\('([^']+)'\) from (endpoint|group)\('([^']+)'\) to (endpoint|group)\('([^']+)'\)(?: ?)", policy_statement)
        block_traffic = re.match(r"block traffic\('([^']+)'\) from (endpoint|group)\('([^']+)'\) to (endpoint|group)\('([^']+)'\)(?: ?)", policy_statement)

        result_dict = {}
        
        if set_bandwidth_link:
            result_dict['policy_type'] = 'set_bandwidth'
            result_dict['max_min'] = set_bandwidth_link.group(1)
            result_dict['bw_amt'] = set_bandwidth_link.group(2)
            result_dict['units'] = set_bandwidth_link.group(3)
            result_dict['link_source'] = set_bandwidth_link.group(4)
            result_dict['link_destination'] = set_bandwidth_link.group(5)
            if time_interval != None:
                result_dict['start_hour'] = time_interval.group(1)
                result_dict['end_hour'] = time_interval.group(2)
        elif set_bandwidth_endpoint:
            result_dict['policy_type'] = 'set_bandwidth'
            result_dict['max_min'] = set_bandwidth_endpoint.group(1)
            result_dict['bw_amt'] = set_bandwidth_endpoint.group(2)
            result_dict['units'] = set_bandwidth_endpoint.group(3)
            result_dict['endpoint'] = set_bandwidth_endpoint.group(4)
            if time_interval != None:
                result_dict['start_hour'] = time_interval.group(1)
                result_dict['end_hour'] = time_interval.group(2)
        elif set_bandwidth_group:
            result_dict['policy_type'] = 'set_bandwidth'
            result_dict['max_min'] = set_bandwidth_group.group(1)
            result_dict['bw_amt'] = set_bandwidth_group.group(2)
            result_dict['units'] = set_bandwidth_group.group(3)
            result_dict['group'] = set_bandwidth_group.group(4)
            if time_interval != None:
                result_dict['start_hour'] = time_interval.group(1)
                result_dict['end_hour'] = time_interval.group(2)
        elif allow_traffic:
            result_dict['policy_type'] = 'allow_traffic'
            result_dict['traffic_type'] = allow_traffic.group(1)
            result_dict['source_type'] = allow_traffic.group(2)
            result_dict['source'] = allow_traffic.group(3)
            result_dict['destination_type'] = allow_traffic.group(4)
            result_dict['destination'] = allow_traffic.group(5)
            if time_interval != None:
                result_dict['start_hour'] = time_interval.group(1)
                result_dict['end_hour'] = time_interval.group(2)
        elif block_traffic:
            result_dict['policy_type'] = 'block_traffic'
            result_dict['traffic_type'] = block_traffic.group(1)
            result_dict['source_type'] = block_traffic.group(2)
            result_dict['source'] = block_traffic.group(3)
            result_dict['destination_type'] = block_traffic.group(4)
            result_dict['destination'] = block_traffic.group(5)
            if time_interval != None:
                result_dict['start_hour'] = time_interval.group(1)
                result_dict['end_hour'] = time_interval.group(2)
        
        return result_dict

    def get_chat_history(self):
        return self.chat_history
