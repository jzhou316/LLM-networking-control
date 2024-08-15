import sys
import os
import copy
import time
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), 'handlers'))

from network_handler import NetworkHandler
from openai_chat_handler import OpenAIChatHandler
from yang_model_handler import YangModelHandler
from assistant_handler import AssistantHandler
from dataset_handler import DatasetHandler
from json import dumps, loads, load
import streamlit as st

st.set_page_config(layout="wide")
st.title('Network Configuration Interface')

st.sidebar.subheader("User Inputs")
config_request = st.sidebar.text_area("Natural Language Query:", height=150)

# Load handlers
yang_dir = "yang_modules"
nh = NetworkHandler()
ymh = YangModelHandler(yang_dir=yang_dir)
ch = OpenAIChatHandler()
ah = AssistantHandler(state_assistant_id="asst_M0rQl9cTPOJSZ7Usw82PXNDa", fdb_assistant_id="asst_SYbJwMTjG2iwxCXjB4IEYMOC")
dh = DatasetHandler()

# Get config_db and frrouting network state for all devices
devices = ['S0', 'S1', 'L0', 'L1']
names = {'S0': '', 'S1': '', 'L0': '', 'L1': ''}

async def get_modules(config_request, truncated_network_states, module_list):
    filter_ir = await ch.invoke(system_template="prompt_templates/filter_ir_system.txt",
                                human_template="prompt_templates/filter_ir_human.txt",
                                system_input_variables=['network_state', 'yang_modules'],
                                human_input_variables=['request'],
                                system_input_values=[str(truncated_network_states), str(module_list)],
                                human_input_values=[config_request],
                                session_id="filter_ir")
    return ch.extract_code_list(content=filter_ir)

async def get_network_state(config_request):
    return await ah.run_state_assistant(config_request)

async def main():
    network_states = {}
    truncated_network_states = {}
    modified_network_states = {}
    pre_verifier_expander = st.expander("Run Verifier on Default Network States")
    for device in devices:
        # status_config_db, path_config_db = nh.get_config_db_network_state(device)
        mapping = {'S0': 'SPINE0', 'S1': 'SPINE1', 'L0': 'LEAF0', 'L1': 'LEAF1'}
        path_config_db = f"configs/sonic_configs/{mapping[device]}/config_db.json"
        with open(path_config_db, 'r') as f:
            content = load(f)
            names[device] = content["DEVICE_METADATA"]["localhost"]["hostname"]
            network_states[device] = dumps(content)
        network_states[device] = loads(ymh.configdb_to_yang(network_states[device]))
        network_states[device] = ymh.fix_yang_mismatches(network_states[device])

        # Uncomment this line to update FRR file (for BGP and OSPF configurations)
        # status_frr, path_frr = nh.get_frr_network_state(device, names[device])

        # Automatically verify the starting network state (sanity check)
        status, msg = ymh.load_data_file(network_states[device])
        pre_verifier_expander.write(f"({device}): {status}")
        truncated_network_states[device] = ymh.truncate_lists_in_dict(network_states[device])

    # Get all modules
    module_names = ymh.get_all_module_names()
    module_list = [ymh.get_yang_module_simplified(module) for module in module_names]

    # Generate configuration based on user query
    if config_request:
        # Show the natural language query
        st.write("Natural Language Query:", config_request)
        st.subheader("LLM: Chain of thought and feedback reasoning")
        times = []

        with st.container(height=600):
            t0 = time.time()
            with st.chat_message("user"):
                st.write("Find the relevant modules for the given query:")

            # Run API calls concurrently
            relevant_modules, state_assistant_info = await asyncio.gather(
                get_modules(config_request, truncated_network_states, module_list),
                get_network_state(config_request)
            )

            times.append(time.time() - t0)
            t0 = time.time()

            with st.chat_message("assistant"):
                st.write(relevant_modules)

            with st.chat_message("user"):
                st.write("Give relevant network state information based on vector store:")

            with st.chat_message("assistant"):
                st.write(state_assistant_info)

            with st.chat_message("user"):
                st.write("Generate the configuration based on the query and selected modules:")

            relevant_modules_full = [ymh.get_yang_module_full(module) for module in relevant_modules if module in module_names]
            generate_config = await ch.invoke(system_template="prompt_templates/gen_cfg_system.txt",
                                              human_template="prompt_templates/gen_cfg_human.txt",
                                              system_input_variables=['state', 'yang_modules'],
                                              human_input_variables=['request'],
                                              system_input_values=[state_assistant_info, str(relevant_modules_full)],
                                              human_input_values=[config_request],
                                              session_id="cfg")

            with st.chat_message("assistant"):
                st.write(generate_config)

            times.append(time.time() - t0)
            t0 = time.time()

            iterations = 0
            success = False

            all_statuses = []
            while iterations < 7:
                network_states_changed = {'S0': False, 'S1': False, 'L0': False, 'L1': False}
                modified_network_states = copy.deepcopy(network_states)

                for config in ch.extract_python_literal(generate_config):
                    device = config["device"]
                    network_states_changed[device] = True
                    for change in config["config"]:
                        target_list = modified_network_states[device]
                        for segment in change["path"][:-1]:
                            if segment not in target_list:
                                target_list[segment] = {}
                            target_list = target_list[segment]

                        target_key = change["path"][-1]

                        if change["action"] == "remove":
                            if target_key in target_list and change["value"] in target_list[target_key]:
                                target_list[target_key].remove(change["value"])
                        elif change["action"] == "append":
                            if target_key not in target_list:
                                target_list[target_key] = []
                            target_list[target_key].append(change["value"])
                        else:
                            st.write(f"Invalid action {change['action']} specified in generated configuration!")

                statuses = []
                error = False
                for device in devices:
                    if network_states_changed[device]:
                        if not ymh.load_data_file(modified_network_states[device])[0]:
                            error = True
                        statuses.append((device, ymh.load_data_file(modified_network_states[device])[1]))
                st.subheader("YANG Verifier Output")
                st.write(statuses)
                all_statuses.append(statuses)

                if error:
                    generate_config = await ah.run_fdb_assistant("Error logs: " + str(statuses) + "\n Here are the configurations to correct: " + ch.extract_python_config(generate_config))
                    with st.chat_message("user"):
                        st.write("Failed YANG verifier. Feedback from FDB assistant:")
                    with st.chat_message("assistant"):
                        st.write(generate_config)
                else:
                    st.write("Passed YANG verifier")
                    success = True
                    network_states = copy.deepcopy(modified_network_states)
                    break
                
                times.append(time.time() - t0)
                t0 = time.time()

                iterations += 1

        if success:
            st.subheader("Final configuration:")
            result = ch.extract_python_literal(generate_config)
            with st.container(height=600):
                st.write(result)
            dh.insert_configuration(nl_request=config_request.strip(), json_config=result, yang_status=True, modules=relevant_modules, latencies=times, iterations=iterations, comments=None)
            st.subheader("Translated into SONiC")
            with st.container(height=600):
                for device in devices:
                    st.write(f"({device}) {names[device]}")
                    st.write(ymh.yang_to_configdb(dumps(network_states[device], indent=4)))
        else:
            st.subheader(f"Failed after {iterations} iterations of feedback. Most recent configuration:")
            try:
                result = ch.extract_python_literal(generate_config)
                st.write(result)
            except:
                result = ""
                st.write("Unable to fetch")
            dh.insert_configuration(nl_request=config_request.strip(), json_config=result, yang_status=False, modules=relevant_modules, latencies=times, iterations=iterations, comments=all_statuses)

if __name__ == "__main__":
    asyncio.run(main())
