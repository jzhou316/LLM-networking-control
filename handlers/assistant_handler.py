import time, os, asyncio
from openai import OpenAI
from dotenv import load_dotenv

# Initialize OpenAI client
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Paths to SONiC network configuration files
CONFIG_FILE_PATHS = [
    "configs/sonic_configs/LEAF0/config_db.json",
    "configs/sonic_configs/LEAF0/frr.txt", 
    "configs/sonic_configs/LEAF1/config_db.json", 
    "configs/sonic_configs/LEAF1/frr.txt", 
    "configs/sonic_configs/SPINE0/config_db.json", 
    "configs/sonic_configs/SPINE0/frr.txt", 
    "configs/sonic_configs/SPINE1/config_db.json", 
    "configs/sonic_configs/SPINE1/frr.txt"
]

class AssistantHandler:
    def __init__(self, state_assistant_id=None, fdb_assistant_id=None):
        # Create or retrieve the state assistant
        self.state_assistant = (
            self.create_state_assistant() if state_assistant_id is None else client.beta.assistants.retrieve(state_assistant_id)
        )
        # Create or retrieve the fdb assistant
        self.fdb_assistant = (
            self.create_fdb_assistant() if fdb_assistant_id is None else client.beta.assistants.retrieve(fdb_assistant_id)
        )
        # Create the vector store for the network configuration files
        # self.delete_all_vector_stores()
        # self.delete_all_files()
        self.state_vector_store = client.beta.vector_stores.create(name="SONIC CLOS Network Vector Store")
        self.yang_vector_store = client.beta.vector_stores.create(name="YANG Model Vector Store")
        self.upload_files_to_state_vs()
        self.upload_files_to_yang_vs()
    
    def create_state_assistant(self):
        with open("../prompt_templates/fdb_assistant.txt", "r") as f:
            instructions = f.read()
        return client.beta.assistants.create(
            instructions=instructions,
            name="Network Config",
            tools=[{"type": "file_search"}, {"type": "code_interpreter"}], 
            temperature=0.1,
            model="gpt-4o",
        )

    def create_fdb_assistant(self):
        with open("../prompt_templates/fdb_assistant.txt", "r") as f:
            instructions = f.read()
        return client.beta.assistants.create(
            instructions=instructions,
            name="YANG Grammar Corrector",
            tools=[{"type": "file_search"}, {"type": "code_interpreter"}], 
            temperature=0.1,
            model="gpt-4o",
        )
    
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
        folder_path = "yang_txts/"
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
    
    async def run_state_assistant(self, message):
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

    async def run_fdb_assistant(self, message):
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
