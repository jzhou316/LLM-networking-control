import grpc
import sys
import re
import time
import streamlit as st
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import home_network_pb2
import home_network_pb2_grpc
from home_network_llm import Chat

# Takes a Topology protobuf object, extracts the nodes and links, and draws it using NetworkX
def draw_topology(topology, group_colors):
	NODE_SIZE = 3100
	# Create an empty graph
	G = nx.Graph()

	# Add devices as nodes to the graph
	for node in topology.hosts:
		label = node.name + "\n" + node.ip_address
		G.add_node(node.name, ip_addr=node.ip_address, label=label, groups=node.groups)

	# Add edges between existing nodes
	connections = []

	for link in topology.links:
		host1 = link.host1.name
		host2 = link.host2.name
		connections.append((host1, host2))

	G.add_edges_from(connections)

	# Visualize the network
	pos = nx.spring_layout(G, seed=42)
	plt.figure(figsize=(8, 6))

	# Draw nodes with labels and edges
	node_labels = nx.get_node_attributes(G, "label")
	nx.draw_networkx_nodes(G, pos=pos, node_color="lightblue", node_size=NODE_SIZE)
	nx.draw_networkx_labels(G, pos=pos, labels=node_labels, font_size=10, font_color="black")
	nx.draw_networkx_edges(G, pos=pos)

	ax = plt.gca()

	node_groups = nx.get_node_attributes(G, 'groups')
	distance = NODE_SIZE / 100000
	for node, groups in node_groups.items():
		if len(groups) % 2:
			distances = [(i - len(groups) // 2) * distance for i in range(len(groups))]
		else:
			distances = [(-i * distance) if i <= 0 else (i * distance) for i in range(-(len(groups) // 2), (len(groups) // 2) + 1)]
		groups = [group.name for group in groups]
		idx = 0
		for group in group_colors.keys():
			if group in groups:
				ax.plot(pos[node][0] + distances[idx], pos[node][1] - NODE_SIZE / 10000, color=group_colors[group], marker='o', markersize=NODE_SIZE/1000)
				idx += 1

	# Show the graph
	plt.axis("off")
	st.pyplot(plt.gcf())

	return

def draw_legend(group_colors):
	plt.figure(figsize=(1, 3))
	legend_elements = []
	for group, color in group_colors.items():
		legend_elements.append(Line2D([0], [0], marker='o', color='w', label=group, markerfacecolor=color, markersize=10))
	plt.legend(handles=legend_elements, loc='upper center')
	plt.axis("off")
	st.pyplot(plt.gcf())

def run():
	chat = Chat()
	with grpc.insecure_channel('localhost:50051') as channel:
		# Streamlit application components
		st.markdown("""
					<style>
						.block-container {
							padding-top: 0.2rem;
							padding-bottom: 0rem;
							padding-left: 0.2rem;
							padding-right: 0.2rem;
						}
					</style>
					""", unsafe_allow_html=True)
		st.title("Home Network Simulation")
		st.markdown("This simulation interface is designed to help you configure a home network using natural language. Enter your configuration commands in the left side panel and see the network topology changes in real-time.")
		col1, col2 = st.columns([6, 1])

		st.sidebar.title("Network Configuration")
		config_request = st.sidebar.text_area("Enter your request here. For example, you can say \"hi, can you please connect a new printer to my home?\"")
		st.sidebar.write('')
		st.sidebar.write('')
		st.sidebar.write('')
		st.sidebar.write('')
		st.sidebar.divider()

		with col1:
			# Container for the topology image
			image_container = st.empty()

		# gRPC Client Code
		stub = home_network_pb2_grpc.HomeNetworkStub(channel)
		st.sidebar.header("Chat History")

		with col2:
			st.write("")
			st.write("")
			st.markdown("**Groups**")
			# Container for the key
			key_container = st.empty()

		# Check the configuration request and process it
		if config_request:
			print(f"Config request checked: {config_request}")
			if config_request == "exit":
				stub.StopNetwork(home_network_pb2.Empty())
				sys.exit(0)
			else:
				nile = chat.query(config_request)
				parsed_intent = chat.parse_intent(nile)
				if 'add' in parsed_intent.keys():
					image_container.empty()
					for entity, args in parsed_intent['add']:
						if entity == 'endpoint':
							if 'for' not in parsed_intent:
								print("Incorrect Nile")
								break
							f_entity, f_args = parsed_intent['for'][0]
							groups = [home_network_pb2.Group(name=f_args[0])]
							new_host = stub.AddDevice(home_network_pb2.Host(name=args[0], groups=groups))
						elif entity == 'group':
							new_group = stub.AddGroup(home_network_pb2.Group(name=args[0]))
				elif 'remove' in parsed_intent.keys():
					image_container.empty()
					for entity, args in parsed_intent['remove']:
						if entity == 'endpoint':
							if 'for' not in parsed_intent:
								print("Incorrect Nile")
								break
							f_entity, f_args = parsed_intent['for'][0]
							groups = [home_network_pb2.Group(name=f_args[0])]
							new_host = stub.RemoveDevice(home_network_pb2.Host(name=args[0], groups=groups))
						elif entity == 'group':
							new_group = stub.AddGroup(home_network_pb2.Group(name=args[0]))
				elif 'set' in parsed_intent.keys():
					print("not implemented")
				else:
					print("Unable to parse Nile")
				print(parsed_intent)

		stub.StartNetwork(home_network_pb2.Empty())

		groups = [group.name for group in stub.GetGroups(home_network_pb2.Empty()).groups]
		colors = list(mcolors.TABLEAU_COLORS.values())
		group_colors = {}
		for i in range(len(groups)):
			group_colors[groups[i]] = colors[i]

		with key_container.container():
			draw_legend(group_colors)
		topology = stub.GetTopology(home_network_pb2.Empty())
		with image_container.container():
			draw_topology(topology, group_colors)

		st.subheader("Network Status")
		st.write("Not implemented")

		chat_history = chat.get_chat_history()
		for user_msg, ai_msg in chat_history.items():
			st.sidebar.chat_message("user").write(user_msg)
			st.sidebar.chat_message("assistant").write(ai_msg)

if __name__ == "__main__":
	run()
