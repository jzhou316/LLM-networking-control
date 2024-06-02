import langchain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import re, ast, os

langchain.verbose = False

class OpenAIChatHandler:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.1,  openai_api_key="sk-proj-ZLIBoCIOaLxVhbWHen32T3BlbkFJyU3Pg2ecLEuUdBCrxZSf", model="gpt-4o")
        self.store = {}
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "LLM for network config"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = "ls__00910ef8094d47719d8412b32fa933cc"

    def get_session_history(self, session_id: str):
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]
    
    def invoke(self, system_template: str, human_template: str, 
               system_input_variables: list, human_input_variables: list,
               system_input_values: list, human_input_values: list, session_id: str):
        assert len(system_input_variables) == len(system_input_values)
        assert len(human_input_variables) == len(human_input_values)
        with open(system_template, 'r') as f:
            system_template_str = f.read()
        with open(human_template, 'r') as f:
            human_template_str = f.read()
        input_variables = system_input_variables + human_input_variables
        input_values = system_input_values + human_input_values
        input_value_dict = dict(zip(input_variables, input_values))
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    system_template_str,
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", human_template_str),
            ]
        )
        prompt = prompt | self.llm

        with_message_history = RunnableWithMessageHistory(
            prompt,
            self.get_session_history,
            input_messages_key=human_input_variables[0],
            history_messages_key="history",
        )

        answer = with_message_history.invoke(
            input_value_dict,
            config={"configurable": {"session_id": session_id}},
        )

        return answer.content
    
    def extract_text(self, content: str):
        pattern = r"```(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        return matches
    
    def extract_code_list(self, content: str):
        relevant_modules = []
        list_pattern = r"\[\s*['\"].*?['\"]\s*\]"
        matches = re.search(list_pattern, content, re.DOTALL)

        if matches:
        # Extract the string representation of the list
            list_str = matches.group(0)
            try:
                # Convert string representation of list to an actual list
                relevant_modules += ast.literal_eval(list_str)
            except (ValueError, SyntaxError):
                # Handle the exception if the string is not a valid Python literal
                return relevant_modules
        return relevant_modules

    def extract_python_literal(self, content: str):
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        # Each match is a Python code block
        return ast.literal_eval(matches[0])
    
    def extract_python_config(self, content: str):
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        # Each match is a Python code block
        return matches[0]