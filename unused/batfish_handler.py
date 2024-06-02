import subprocess, os, sys, json, re
from pybatfish.client.session import Session
from pybatfish.datamodel import *
from pybatfish.datamodel.answer import *
from pybatfish.datamodel.flow import *

sys.path.append(os.path.join(os.path.dirname(__file__), 'handlers/'))
import openai_chat_handler as ch

class BatfishHandler:
    def __init__(self):
        with open("prompt_templates/batfish_boilerplate.txt", 'r') as f:
            self.batfish_boilerplate = f.read()
            self.chat_handler = ch.OpenAIChatHandler()
        with open("documentation/commands.json", 'r') as f:
            self.commands = json.load(f)
            self.commands = {key.lower(): value for key, value in self.commands.items()}
        with open("documentation/types.json", 'r') as f:
            self.types = json.load(f)
            self.types = {key.lower(): value for key, value in self.types.items()}

    def get_boilerplate(self):
        return self.batfish_boilerplate

    def run_gpt_generated_code(self, filepath: str):
        try:
            output = subprocess.run(["python", filepath], capture_output=True, text=True, timeout=6)
        except subprocess.TimeoutExpired:
            return {'status': False, 'content': 'Execution timed out'}
        if output.returncode == 0:
            return {'status': True, 'content': output.stdout}
        else:
            return {'status': False, 'content': output.stderr}
    
    def get_parsed_nodes(self):
        bf = Session(host="localhost")

        # Assign a friendly name to your network and snapshot
        NETWORK_NAME = "sonic_clos_network"
        SNAPSHOT_NAME = "sonic_clos_snapshot"

        SNAPSHOT_PATH = "configs/"

        # Now create the network and initialize the snapshot
        bf.set_network(NETWORK_NAME)
        bf.init_snapshot(SNAPSHOT_PATH, name=SNAPSHOT_NAME, overwrite=True)

        # Get parsing status
        parse_status = bf.q.fileParseStatus().answer()
        nodes = dict(parse_status.frame())["Nodes"]
        list_nodes = set([item for sublist in nodes for item in sublist])
        return list_nodes
    
    def extract_error_info(self, error_message):
        type_error_pattern = r'Expected type: \'(\w+)\' for parameter: \'(\w+)\'.'
        match = re.search(type_error_pattern, error_message)
        
        if match:
            expected_type = match.group(1)
            parameter = match.group(2)
            return {"error_type": "type", "expected_type": expected_type, "parameter": parameter}
        
        return {"error_type": "Unknown"}
    
    def generate_config_full(self, config_request: str):
        topics_list = [{"topic": topic, "description": self.commands[topic]["description"]} for topic in self.commands.keys()]
        relevant_topics = self.chat_handler.invoke(system_template="prompt_templates/bf_choose_system.txt",
                                human_template="prompt_templates/bf_choose_human.txt",
                                system_input_variables=['topics_list'],
                                human_input_variables=['request'],
                                system_input_values=[topics_list],
                                human_input_values=[config_request],
                                session_id="topics_session")
        relevant_topics = self.chat_handler.extract_code_list(relevant_topics)
        print(relevant_topics)
        documentation = [{topic: self.commands[topic]} for topic in relevant_topics]
        types_set = {input["type"] for topic in relevant_topics for input in self.commands[topic]["inputs"]}
        print(types_set)
        types_spec = {type: self.types[type] for type in types_set if type in self.types.keys()}
        types_spec["enumsetspec"] = self.types["enumsetspec"]
        batfish_code = self.chat_handler.invoke(system_template="prompt_templates/bf_system.txt",
                                human_template="prompt_templates/bf_human.txt",
                                system_input_variables=['documentation', 'types', 'nodes'],
                                human_input_variables=['request'],
                                system_input_values=[documentation, types_spec, self.get_parsed_nodes()],
                                human_input_values=[config_request],
                                session_id="batfish_session")
        code = self.chat_handler.extract_python_config(batfish_code)
        with open("gpt_generated_code.py", "w") as f:
            f.write(self.get_boilerplate())
            f.write(code)
        output = self.run_gpt_generated_code("gpt_generated_code.py")
        while not output['status']:
            print(output)
            if output["content"] == "Execution timed out":
                error_msg = "Execution timed out."
                types_spec = "From experience, this usually happens when one of the following is true: \
                1. You included 'Interface' in the 'interfacePropertySpec'. You don't need to include 'Interface'. \
                2. You specified a HeaderConstraints incorrectly. Make sure that the applications field is a list of \
                Layer 4 application names. IP, for example, is not a valid application name."
            else:
                error_msg = output['content']
                error_info = self.extract_error_info(error_msg)
                if error_info["error_type"] == "type":
                    types_spec = {error_info["expected_type"]: self.types[error_info["expected_type"].lower()]}
                else:
                    types_spec = {}
            batfish_code = self.chat_handler.invoke(system_template="prompt_templates/bf_fdb_system.txt",
                                    human_template="prompt_templates/bf_fdb_human.txt",
                                    system_input_variables=['nodes', 'documentation'],
                                    human_input_variables=["error_msg", "request"],
                                    system_input_values=[self.get_parsed_nodes(), types_spec],
                                    human_input_values=[error_msg, config_request],
                                    session_id="batfish_session")
            code = self.chat_handler.extract_python_config(batfish_code)
            with open("gpt_generated_code.py", "w") as f:
                f.write(self.get_boilerplate())
                f.write(code)
            output = self.run_gpt_generated_code("gpt_generated_code.py")
        shorter = self.chat_handler.invoke(system_template="prompt_templates/bf_summarize_system.txt",
                                human_template="prompt_templates/bf_summarize_human.txt",
                                system_input_variables=[],
                                human_input_variables=["request", "output"],
                                system_input_values=[],
                                human_input_values=[config_request, output['content']],
                                session_id="batfish_session")
        return shorter
