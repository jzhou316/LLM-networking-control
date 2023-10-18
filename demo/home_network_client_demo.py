import sys
import re
import time
import streamlit as st
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D

# Takes a Topology protobuf object, extracts the nodes and links, and draws it using NetworkX
def draw_topology(topology, group_colors, node_shapes):
	NODE_SIZE = 3100
	# Create an empty graph
	G = nx.Graph()

	# Add devices as nodes to the graph
	for node in topology["hosts"]:
		label = node["name"] + "\n" + node["ip_address"]
		G.add_node(node["name"], ip_addr=node["ip_address"], label=label, groups=node["groups"], type=node["type"])

	# Add edges between existing nodes
	for link in topology["links"]:
		style = 'solid' if link["connection"] == "wired" else "dotted"
		G.add_edge(link["link"][0], link["link"][1], style=style)

	# Visualize the network
	pos = nx.spring_layout(G, seed=42)
	plt.figure(figsize=(8, 6))

	# Draw nodes with labels and edges
	node_labels = nx.get_node_attributes(G, "label")
	node_types = nx.get_node_attributes(G, "type")
	for node_type, shape in node_shapes:
		specific_nodes = []
		for host in topology["hosts"]:
			if host["type"] == node_type:
				specific_nodes.append(host["name"])
		nx.draw_networkx_nodes(G, pos=pos, nodelist=specific_nodes, node_color="lightblue", node_size=NODE_SIZE, node_shape=shape)
		nx.draw_networkx_labels(G, pos=pos, labels=node_labels, font_size=10, font_color="black")

	edge_styles = nx.get_edge_attributes(G, 'style')
	for (host1, host2, style) in G.edges(data=True):
		nx.draw_networkx_edges(G, pos=pos, edgelist=[(host1, host2)], edge_color='k', style=style['style'])

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
	st.markdown("This simulation interface is designed to help you configure a home network using natural language. Talk to your network in the left side panel and see the changes in real-time.")
	col1, col2 = st.columns([6, 1])

	st.sidebar.title("Configuration")
	config_request = st.sidebar.text_area("Configure your network here. For example, you can say \"hi, can you please connect a new printer to my home?\"")
	st.sidebar.write('')
	st.sidebar.write('')
	st.sidebar.write('')
	st.sidebar.write('')
	st.sidebar.divider()

	with col1:
		# Container for the topology image
		image_container = st.empty()

	# gRPC Client Code
	st.sidebar.header("Chat History")

	with col2:
		st.write("")
		st.write("")
		st.markdown("**Groups**")
		# Container for the key
		key_container = st.empty()


	#--------------------------------------- NETWORK CONFIG ---------------------------------------#

	hosts = [{"name": "internet", "ip_address": "", "groups": ["network"], "type": "internet"},
			 {"name": "router", "ip_address": "", "groups": ["network"], "type": "router"},	
			 {"name": "motion-sensor", "ip_address": "", "groups": ["network", "home-security-system"], "type": "device"},
			 {"name": "alarm", "ip_address": "", "groups": ["network", "home-security-system"], "type": "device"},
			 {"name": "smart-lock", "ip_address": "", "groups": ["network", "home-security-system"], "type": "device"},
			 {"name": "phone", "ip_address": "", "groups": ["network"], "type": "device"},
			 {"name": "game-console", "ip_address": "", "groups": ["network", "living-room"], "type": "device"},
			 {"name": "guest-laptop-1", "ip_address": "", "groups": ["network"], "type": "device"},
			 {"name": "guest-laptop-2", "ip_address": "", "groups": ["network"], "type": "device"},
			 {"name": "game-console", "ip_address": "", "groups": ["network"], "type": "device"},
			 {"name": "work-laptop", "ip_address": "", "groups": ["network"], "type": "device"},
			 {"name": "printer", "ip_address": "", "groups": ["network"], "type": "device"},
	]

	links = [{"link": ('internet', 'router'), "connection": ""}, 
			 {"link": ('router', 'motion-sensor'), "connection": ""}, 
			 {"link": ('router', 'alarm'), "connection": ""}, 
			 {"link": ('router', 'smart-lock'), "connection": ""}, 
			 {"link": ('router', 'phone'), "connection": ""}, 
			 {"link": ('router', 'game-console'), "connection": ""}, 
			 {"link": ('router', 'guest-laptop-1'), "connection": ""}, 
			 {"link": ('router', 'guest-laptop-2'), "connection": ""}, 
			 {"link": ('router', 'game-console'), "connection": ""}, 
			 {"link": ('router', 'work-laptop'), "connection": ""}, 
			 {"link": ('router', 'printer'), "connection": ""}, 
	]

	groups = ['network', 'home-security-system', 'living-room']
	node_shapes = [{"type": "internet", "shape": "s"},
				   {"type": "router", "shape": "D"},
				   {"type": "firewall", "shape": "^"},
				   {"type": "device", "shape": "o"}
	]

	# Check the configuration request and process it
	if config_request:
		print(f"Config request checked: {config_request}")
		if config_request == "I've got a new IoT security camera that I want to connect to my network. It should only interact with my phone and the home security system.":
			pass
		elif config_request == "I want to create a new subnet for my home office devices. This should include my work laptop, printer, and my phone. Also, make sure this subnet has priority access to the bandwidth during office hours.":
			pass
		elif config_request == "I want to set up a guest Wi-Fi network that should only provide internet access and nothing more. It should also have limited bandwidth because I don't want it to get in the way of my main network's performance.":
			pass
		elif config_request == "My child does a lot of online gaming and it seems to be slowing down the internet for everyone else. Can you limit the amount of internet he can use?":
			pass
		elif config_request == "I've been hearing a lot about cyber threats on the news lately. Can you do something to make sure my personal information is safe when I'm online?":
			pass

	colors = list(mcolors.TABLEAU_COLORS.values())
	group_colors = {}
	for i in range(len(groups)):
		group_colors[groups[i]] = colors[i]

	with key_container.container():
		draw_legend(group_colors)

	topology = {"hosts": hosts, "links": links}
	with image_container.container():
		draw_topology(topology, group_colors, node_shapes)

	st.subheader("Network Status")
	st.write("Not implemented")

	for user_msg, ai_msg in chat_history.items():
		st.sidebar.chat_message("user").write("placeholder")
		st.sidebar.chat_message("assistant").write("placeholder")

if __name__ == "__main__":
	run()
