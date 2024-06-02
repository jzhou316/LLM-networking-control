# LLM for Network Configuration Project

In this project, we develop a system that leverages LLMs to automatically configure network switch devices based on natural language requests. 

## Description

Our goal is to leverage LLMs to perform network configuration. Specifically, this implementation translates natural language requests into configurations in SONiC. To ensure structure and precision in the LLM outputs,  the system first converts the natural language query into a YANG data file. We use YANG modules to define a grammar for the LLM output. The end-to-end process is as follows:

1. A user describes a configuration objective in *natural language* (NL). 
2. **LLM Agent 1** determines which YANG modules are relevant for this query.
3. **LLM Agent 2**, given a vector store of the configuration files that describe the current state of the network, describes the parts of the network state that are relevant to this query.
4. Given the outputs from LLM Agents 1 and 2, **LLM Agent 3** performs the configuration. It outputs a YANG configuration that satisfies the user query.
5. We run ```pyang``` (a YANG verifier) to check that the LLM output satisfies the syntax and constraints described in the YANG grammar. If there is an error, **LLM Agent 4** (which also has all the YANG modules in a vector store) attempts to correct the configuration based on the error log. This is repeated until the configuration passes the pyang tests, or until a specified number of iterations have failed.

We use OpenAI's off-the-shelf GPT-4 model for all LLM agents. Instructions are provided to the agents via prompting. 

We evaluate this system on a dataset of 13 NL utterances collected from Cisco SONiC engineers. The LLM generations are evaluated for the following criteria: 
- were the correct YANG modules selected?
- does it correctly identify the parts of the config files that need to be changed? (to-do)
- does the final configuration file compile? (when loaded onto the switch devices)
- does it adhere to the YANG grammar? (i.e., passes the verifier step)
- if the verifier step took place, how many iterations did it take for the LLM to correct its own generation?
- how long did the generation take?

## Getting Started


### Installing

* to-do
* some dependencies must be installed
* also OpenAI api must be set up

### Executing program

This implementation is designed to configure SONiC devices running in the Cisco sandbox environment. The files from ```/server``` should be loaded into the sandbox environment. A REST API is used to communicate between the server-side network devices and the client-side LLM system. First, run the following on the server side:
```
python3 -m pip install flask
python3 server.py
```
This loads the configuration files to the client side and also allows configurations to be pushed back to the network devices. On the client side, run the following:
```
streamlit run main.py
```
In the web interface that pops up, the user can submit a natural language query. The interface will display the reasoning steps taken by the LLM. If the configuration is successful, the result is automatically appended to ```data/results.json```


## License

See the LICENSE.md file for details
