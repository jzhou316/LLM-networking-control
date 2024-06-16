import time
import os
import re
import json
import ast
from openai import OpenAI

OPENAI_API_KEY = "sk-proj-qJ1qUAx4jc1ltuUsYjl4T3BlbkFJKKwhXNSCV6Nc4Kf5iSTI"
client = OpenAI(api_key=OPENAI_API_KEY)

class AssistantHandler:
    def __init__(self, assistant_id=None):
        if assistant_id is None:
            self.assistant = client.beta.assistants.create(
                instructions="""You are an AI named Lumi. The user will type a statement related to network management. Use the vector store, which has training data, to identify the task-relevant entities in the given statement. The entities are defined in the files attached.\n
                Please format the output as a JSON, where the key-value pairs are such that the key is the entity and value is the value. Specifically, please be sure the keys are one of the following: middlebox, group, traffic, protocol, service, qos_constraint, qos_metric, qos_unit, qos_value, date, datetime, hour, origin, destination, target, start, end, operation.\n
                Next, in a separate JSON, please take the statement and your extracted entities and form a 'network intent'. Please perform retrieval on the synonyms file whenever you are unsure what to use for a name. You may use the code interpreter to ensure that the intent adheres strictly to the following EBNF grammar:\n
                <intent> ::= 'define intent' <term>':' <operations>
                <operations> ::= <path> <operation> { ' ' <operation> }
                <path> ::= [<from_to> | <targets>]
                <from_to> ::= 'from' <endpoint> 'to' <endpoint>
                <operation> ::= (<mboxes> | <qos> | <rules>)+ [ <interval> ]
                <mboxes> ::= ['add' | 'remove'] <middlebox> { (',' | ',\n') <middlebox> }
                <middlebox> ::= 'middlebox('<term>')'
                <qos> ::= ['set' | 'unset'] <metrics>
                <metrics> ::= <metric> { (',' | ',\n') <metric> }
                <metric> ::= [ <bandwidth> | <quota> ]
                <rules> ::= ['allow' | 'block'] <matches> [ <matches> ]
                <targets> ::= 'for' <target> { (',' | ',\n') <target> }
                <target> ::= [ <group> | <service> | <endpoint> | <traffic> ]
                <matches> ::= [ <service> | <traffic> | <protocol> ]
                <endpoint> ::= 'endpoint('<term>')'
                <group> ::= 'group('<term>')'
                <service> ::= 'service('<term>')'
                <traffic> ::= 'traffic('<term>')'
                <protocol> ::= 'bandwidth('<term>')'
                <bandwidth> ::= 'bandwidth('['max' | 'min' ]', '<term>', <bw_unit>)'
                <bw_unit> ::= [ 'bps' | 'kbps' | 'mbps' | 'gbps' ]
                <quota> ::= 'quota('['download' | 'upload' | 'any' ]', '<term>', <q_unit>)'
                <q_unit> ::= [ 'mb/d' | 'mb/wk' | 'gb/d' | 'gb/wk' | 'gb/mth' ]
                <interval> ::= 'start' <datetime> 'end' <datetime>
                <datetime> ::= 'datetime('<term>')' | 'date('<term>')' | 'hour('<term>')'
                <term> ::= [a-z0-9]+

                Example request: "Add firewall and intrusion detection from the gateway to the backend for client B with at least 100mbps of bandwidth, and allow HTTPS only"

                Example response:
                Entities:
                {
                    "endpoint": "gateway",
                    "endpoint": "database",
                    "group": "B",
                    "middlebox": "firewall",
                    "middlebox": "ids",
                    "bandwidth": "min 100mbps",
                    "traffic": "HTTPS"
                }
                Intent:
                "define intent qosIntent: from endpoint('gateway') to endpoint('database') add middlebox('firewall'), middlebox('ids') set bandwidth('min', '100', 'mbps') for group('B') allow traffic('HTTPS')"
                """,
                name="Network Config",
                tools=[{"type": "file_search"}, {"type": "code_interpreter"}],
                temperature=0.2,
                model="gpt-4o",
            )
        else:
            self.assistant = client.beta.assistants.retrieve(assistant_id)

        self.vector_store = client.beta.vector_stores.create(name="Entity Recognition Rules and Examples")
        self.upload_files_to_vs()

    def upload_files_to_vs(self):
        folder_path = "data/"
        file_paths = [os.path.join(folder_path, file_name) for file_name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file_name))]

        file_streams = [open(path, "rb") for path in file_paths]

        try:
            client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=self.vector_store.id, files=file_streams
            )

            self.assistant = client.beta.assistants.update(
                assistant_id=self.assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [self.vector_store.id]}},
            )
        except Exception as e:
            print("Error uploading files to vector store:", e)
        finally:
            for file_stream in file_streams:
                file_stream.close()

    def run_assistant(self, message):
        run = client.beta.threads.create_and_run(
            assistant_id=self.assistant.id,
            thread={"messages": [{"role": "user", "content": message}]}
        )
        while True:
            run_steps = client.beta.threads.runs.steps.list(
                thread_id=run.thread_id,
                run_id=run.id
            )
            if run_steps.data and run_steps.data[0].status == 'completed':
                messages = client.beta.threads.messages.list(run.thread_id)
                result = messages.data[0].content[0].text.value
                return result
            else:
                time.sleep(1)

    def delete_all_vector_stores(self):
        vector_stores = client.beta.vector_stores.list()
        for vector_store in vector_stores.data:
            client.beta.vector_stores.delete(vector_store_id=vector_store.id)

    def delete_all_files(self):
        files = client.files.list()
        for file in files.data:
            client.files.delete(file.id)
            time.sleep(0.5)

    def extract_json(self, content: str):
        pattern = r"```json(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        entities = json.loads(matches[0].strip()) if matches else {}
        return json.dumps(entities, indent=4)
    
    def extract_python(self, content: str):
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        return ast.literal_eval(matches[0].strip())
