# LLMs for Network Configuration

We develop a system that leverages LLMs to automatically configure network switch devices based on natural language requests. 

## Description

We use LLMs to translate natural language requests into configurations in [SONiC](https://sonicfoundation.dev/). To enforce a structure in the LLM outputs, first we convert the natural language query into a YANG data file. This YANG output follows an explicit grammar that is defined by a set of provided YANG modules. 

The user begins by describing a configuration objective in *natural language* (NL). There are three key stages:

**Retrieval Stage**: *LLM Agent 1* performs dense retrieval on a vector database of the configuration files and identifies the parts of the network state that are relevant to this query. Asynchronously, *LLM Agent 2* identifies the YANG modules that are relevant to this specific query.

**Configuration Stage**: Given the outputs from LLM Agents 1 and 2, *LLM Agent 3* performs the configuration. It outputs a YANG configuration that satisfies the user query.

**Verification Stage**: We run the verifier pyang to check that the LLM output satisfies the syntax and constraints described in the YANG grammar. If there is an error, *LLM Agent 4* attempts to correct the configuration based on the error log. The verification stage is repeated until the configuration passes the pyang tests, or until a specified number of iterations have failed.

After the YANG configuration has been verified, a compiler translates it into SONiC code via a deterministic mapping.

![llm_components](data/images/llm_components.png)

We use GPT-4 for all LLM agents. Instructions are provided to the agents via prompting. 

### Requirements and Installation

First, clone the repository and install the required dependencies:
```
git clone git@github.com:jzhou316/LLM-networking-control.git
pip install -r requirements.txt
```

Next, you will need to supply API keys for OpenAI and LangChain. Replace the empty values for the fields `OPENAI_API_KEY` and `LANGCHAIN_API_KEY` in `handlers/.env`. 

Static SONiC configuration files have been provided in `configs/sonic_configs`. We also support real-time configurations by providing a script in `handlers/network_handler.py` to interact with the Cisco 8000 Emulator Sandbox for SONiC. You will need to set up a [Cisco 8000 SONiC Notebook sandbox environment](https://devnetsandbox.cisco.com/DevNet). Once you have set up your SONiC environment, upload the script `server/server.py` to the environment. This will set up a RESTAPI to communicate between the sandbox environment and the local repository.



### Executing program

We configure SONiC devices running in a sandbox environment. The files from ```/server``` are first loaded into the sandbox environment. A REST API is used to communicate between the server-side network devices and the client-side LLM system. 

Next, the server code loads the configuration files to the client side and allows new configurations to be pushed back to the network devices. 

On the client side, a Streamlit web interface allows the user to submit a natural language query. The interface will display the reasoning steps taken by the LLM. If the configuration is successful, the result is automatically appended to ```data/results.json```


## License

See the LICENSE.md file for details
