import grpc
import sys
import re
import time
import streamlit as st
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import home_network_pb2
import home_network_pb2_grpc
from home_network_llm import Chat

# Takes a Topology protobuf object, extracts the nodes and links, and draws it using NetworkX
def draw_topology(topology):
	# Create an empty graph
	G = nx.Graph()

	# Add devices as nodes to the graph
	for node in topology.hosts:
		label = node.name + "\n" + node.ip_address
		G.add_node(node.name, ip_addr=node.ip_address, label=label)

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
	nx.draw_networkx_nodes(G, pos=pos, node_color="lightblue", node_size=3000)
	nx.draw_networkx_labels(G, pos=pos, labels=node_labels, font_size=10, font_color="black")
	nx.draw_networkx_edges(G, pos=pos)

	# Show the graph
	plt.axis("off")
	st.pyplot(plt.gcf())

	return

def run():
	chat = Chat()
	with grpc.insecure_channel('localhost:50051') as channel:
		# Streamlit application components
		st.title("Home Network Simulation")
		st.markdown("This simulation interface is designed to help you configure a home network using natural language. Enter your configuration commands in the left side panel and see the network topology changes in real-time.")
		st.sidebar.title("Network Configuration")
		config_request = st.sidebar.text_area("Enter your request here. For example, you can say \"hi, can you please connect a new printer to my home?\"")
		st.sidebar.write('')
		st.sidebar.write('')
		st.sidebar.write('')
		st.sidebar.write('')
		st.sidebar.divider()

		# Container for the topology image
		image_container = st.empty()

		# Panel to show network status
		with st.expander("Network status", expanded=True):
			st.write("Not implemented yet")

		# gRPC Client Code
		stub = home_network_pb2_grpc.HomeNetworkStub(channel)
		st.sidebar.header("Groups")

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
							new_host = stub.AddDevice(home_network_pb2.Host(name=args[0]))
						elif entity == 'group':
							new_group = stub.AddGroup(home_network_pb2.Group(name=args[0]))
				elif 'remove' in parsed_intent.keys():
					image_container.empty()
					for entity, args in parsed_intent['remove']:
						if entity == 'endpoint':
							new_host = stub.RemoveDevice(home_network_pb2.Host(name=args[0]))
				elif 'set' in parsed_intent.keys():
					print("not implemented")
				else:
					print("Unable to parse Nile")
				print(parsed_intent)

		groups = [group.name for group in stub.GetGroups(home_network_pb2.Empty()).groups]
		assert len(groups) <= 3
		colors = ['blue', 'red', 'orange']
		s = ''
		for i in range(len(groups)):
			s += (f"- {groups[i]}: :{colors[i]}[{colors[i]}]\n")
		st.sidebar.markdown(s)
		stub.StartNetwork(home_network_pb2.Empty())

		topology = stub.GetTopology(home_network_pb2.Empty())
		with image_container.container():
			draw_topology(topology)

if __name__ == "__main__":
	run()
