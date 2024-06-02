import time, os
from openai import OpenAI
client = OpenAI(api_key="sk-proj-ZLIBoCIOaLxVhbWHen32T3BlbkFJyU3Pg2ecLEuUdBCrxZSf")

CONFIG_FILE_PATHS = ["configs/sonic_configs/LEAF0/config_db.json", "configs/sonic_configs/LEAF0/frr.txt", "configs/sonic_configs/LEAF1/config_db.json", "configs/sonic_configs/LEAF1/frr.txt", "configs/sonic_configs/SPINE0/config_db.json", "configs/sonic_configs/SPINE0/frr.txt", "configs/sonic_configs/SPINE1/config_db.json", "configs/sonic_configs/SPINE1/frr.txt"]

class AssistantHandler:
    def __init__(self, state_assistant_id=None, fdb_assistant_id=None):
        # Create the state assistant
        if state_assistant_id == None:
            self.state_assistant = client.beta.assistants.create(
              instructions="You are an assistant whose job is to understand network configuration files. You are provided these network configuration files from a SONiC clos network. For your information, the configuration files describe a network with four devices, Spine0, Spine1, Leaf0, and Leaf1. The user is trying to perform a configuration objective, but they do not know what the current state of the network is. Based on the provided network configuration files, you will help the user understand the current state of the network, providing any details that will aid in their configuration. For example, you may need to provide the current IP address of a device, the active interfaces on each device, the current VLAN configuration, or the current BGP neighbors. It will help you to know that each device has an IP address, but each interface might also have its own IP address. You should describe the network state for every device, so that the user at least knows which devices are in the network. You should not explain how to perform the configuration. Your primary task is to provide information about the current state of the network. At the end, you should also describe how you would perform the configuration. \n\n IT IS IMPERATIVE THAT YOUR RESPONSE IS ENTIRELY ACCURATE BASED ON THE INFORMATION ABOUT THE NETWORK STATE FROM THE VECTOR STORE. Please explicitly use the vector store as evidence for your decisions.",
              name="Network Config",
              tools=[{"type": "file_search"}, {"type": "code_interpreter"}], 
              temperature=0.1,
              model="gpt-4o",
            )
        else:
            self.state_assistant = client.beta.assistants.retrieve(state_assistant_id)
        if fdb_assistant_id == None:
            self.fdb_assistant = client.beta.assistants.create(
              instructions="You are an assistant to a network operator. The network operator wants to perform a configuration on a SONIC clos network, and their configuration code will be given to you in a YANG ABNF data format. However, the configuration does not pass the YANG validator tests. The compile error logs are given to you. You can use file retrieval and the code interpreter to look into a vector store containing all of the YANG modules, which specify the grammar that the YANG configuration must adhere to. Please correct the YANG configuration that is given to you, and return the correct version delineated clearly as a standalone list within a single, complete Python snippet (see below). For automatic extraction purposes, the solution should be the only Python block in your output. \n\n```python\n[\n\t<configuration>\n]\n```",
              name="YANG Grammar Corrector",
              tools=[{"type": "file_search"}, {"type": "code_interpreter"}], 
              temperature=0.1,
              model="gpt-4o",
            )
        else:
            # Create the fdb assistant
            self.fdb_assistant = client.beta.assistants.retrieve(fdb_assistant_id)
        # Create the vector store for the network configuration files
        self.delete_all_vector_stores()
        # self.delete_all_files()
        self.state_vector_store = client.beta.vector_stores.create(name="SONIC CLOS Network Vector Store")
        self.yang_vector_store = client.beta.vector_stores.create(name="YANG Model Vector Store")
        self.upload_files_to_state_vs()
        self.upload_files_to_yang_vs()
    
    def upload_files_to_state_vs(self):
        file_streams = [open(path, "rb") for path in CONFIG_FILE_PATHS]
        client.beta.vector_stores.file_batches.upload_and_poll(
          vector_store_id=self.state_vector_store.id, files=file_streams
        )
        self.state_assistant = client.beta.assistants.update(
          assistant_id=self.state_assistant.id,
          tool_resources={"file_search": {"vector_store_ids": [self.state_vector_store.id]}},
        )

    def upload_files_to_yang_vs(self):
        # Get all file paths in the specified folder
        folder_path = "yang_txts/libyang-python-tests/sample-yang-models/"
        file_paths = [os.path.join(folder_path, file_name) for file_name in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file_name))]
        
        # Open each file in binary read mode
        file_streams = [open(path, "rb") for path in file_paths]
        
        try:
            # Upload the files to the vector store
            client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=self.yang_vector_store.id, files=file_streams
            )
            
            # Update the state assistant with the new vector store
            self.fdb_assistant = client.beta.assistants.update(
                assistant_id=self.fdb_assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [self.yang_vector_store.id]}},
            )
        finally:
            # Ensure all file streams are closed after uploading
            for file_stream in file_streams:
                file_stream.close()
    
    def run_state_assistant(self, message):
        run = client.beta.threads.create_and_run(
          assistant_id=self.state_assistant.id,
          thread={"messages": [{"role": "user", "content": message}]}
        )
        while True:
            run_steps = client.beta.threads.runs.steps.list(
              thread_id=run.thread_id,
              run_id=run.id
            )
            if run_steps.data != [] and run_steps.data[0].status == 'completed': 
                messages = client.beta.threads.messages.list(run.thread_id)
                result = messages.data[0].content[0].text.value
                return result
            else:
                time.sleep(1)

    def run_fdb_assistant(self, message):
        run = client.beta.threads.create_and_run(
          assistant_id=self.fdb_assistant.id,
          thread={"messages": [{"role": "user", "content": message}]}
        )
        while True:
            run_steps = client.beta.threads.runs.steps.list(
              thread_id=run.thread_id,
              run_id=run.id
            )
            if run_steps.data != [] and run_steps.data[0].status == 'completed': 
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