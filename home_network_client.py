import grpc
import sys
import re
import streamlit as st
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import home_network_pb2
import home_network_pb2_grpc

# Takes a Topology protobuf object, extracts the nodes and links, and draws it using NetworkX
def draw_topology(topology):
	print("draw_topology() function run!")
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

def parse_add_host(input_string):
	pattern = r"add host with name (\S+) and ip address (\S+)"
	match = re.match(pattern, input_string)

	# If there is a match, proceed with extracting the name and IP address
	if match:
		name = match.group(1)
		ip_address = match.group(2)
		return name, ip_address
	else:
		# If no match, return None for both name and IP address
		return None, None 

def run():
	with grpc.insecure_channel('localhost:50051') as channel:
		# Streamlit application components
		st.title("Home Network Simulation")
		st.sidebar.title("Network Configuration")
		config_request = st.sidebar.text_area("Configure the network in natural language")
		st.sidebar.write("Currently implemented examples")
		st.sidebar.markdown(
		"""
		- add host with name <string> and ip address <10.0.0.X/8>
		- exit 
		"""
		)
		#st.sidebar.write("Example: add host with name <string> and ip address <10.0.0.X/8>")

		# Container for the topology image
		image_container = st.empty()

		# gRPC Client Code
		stub = home_network_pb2_grpc.HomeNetworkStub(channel)
		stub.StartNetwork(home_network_pb2.Empty())

		topology = stub.GetTopology(home_network_pb2.Empty())
		with image_container.container():
			draw_topology(topology)

		# Check the configuration request and process it
		if config_request:
			print(f"Config request checked: {config_request}")
			if config_request == "exit":
				stub.StopNetwork(home_network_pb2.Empty())
				sys.exit(0)
			name, ip_address = parse_add_host(config_request)
			if name and ip_address:
				image_container.empty()
				new_host = stub.AddDevice(home_network_pb2.Host(name=name, ip_address=ip_address))
				print(f"Added host with name {name} and ip address {ip_address} on the client side")
				topology = stub.GetTopology(home_network_pb2.Empty())
				with image_container.container():
					draw_topology(topology)

if __name__ == "__main__":
	run()
