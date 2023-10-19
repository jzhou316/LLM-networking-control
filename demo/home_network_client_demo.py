import sys
import re
import time
import streamlit as st
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from random import randint

# Takes a Topology protobuf object, extracts the nodes and links, and draws it using NetworkX
def draw_topology(topology, group_colors, node_shapes):
	NODE_SIZE = 1500
	# Create an empty graph
	G = nx.Graph()

	# Add devices as nodes to the graph
	for node in topology["hosts"]:
		label = node["name"]
		if node["ip_address"] != "":
			label += ("\n" + node["ip_address"])
		if node["type"] == "internet":
			layer = 5
		elif node["type"] == "firewall":
			layer = 4
		elif node["type"] == "router":
			layer = 3
		else:
			layer = -1 * (int(node["ip_address"][-1]) % 2) + 2
		G.add_node(node["name"], ip_addr=node["ip_address"], label=label, groups=node["groups"], type=node["type"], layer=layer)

	# Add edges between existing nodes
	for link in topology["links"]:
		style = 'solid' if link["connection"] == "wired" else "dotted"
		G.add_edge(link["link"][0], link["link"][1], style=style)

	# Visualize the network
	pos = nx.multipartite_layout(G, subset_key="layer", align="horizontal")
	plt.figure(figsize=(8, 6))

	# Draw nodes with labels and edges
	node_labels = nx.get_node_attributes(G, "label")

	node_types = nx.get_node_attributes(G, "type")
	for node_type, shape in node_shapes.items():
		specific_nodes = []
		for host in topology["hosts"]:
			if host["type"] == node_type:
				specific_nodes.append(host["name"])
		nx.draw_networkx_nodes(G, pos=pos, nodelist=specific_nodes, node_color="lightblue", node_size=NODE_SIZE, node_shape=shape, alpha=0.8)
		nx.draw_networkx_labels(G, pos=pos, labels=node_labels, font_size=8, font_color="black")

	edge_styles = nx.get_edge_attributes(G, 'style')
	for (host1, host2, style) in G.edges(data=True):
		nx.draw_networkx_edges(G, pos=pos, edgelist=[(host1, host2)], edge_color='k', style=style['style'], alpha=0.4)

	ax = plt.gca()

	node_groups = nx.get_node_attributes(G, 'groups')
	distance = NODE_SIZE / 50000
	for node, groups in node_groups.items():
		if len(groups) % 2:
			distances = [(i - len(groups) // 2) * distance for i in range(len(groups))]
		else:
			distances = [(-i * distance) if i <= 0 else (i * distance) for i in range(-(len(groups) // 2), (len(groups) // 2) + 1)]
		idx = 0
		for group in group_colors.keys():
			if group in groups:
				ax.plot(pos[node][0] + distances[idx], pos[node][1] - NODE_SIZE / 10000, color=group_colors[group], marker='o', markersize=NODE_SIZE/500)
				idx += 1

	# Show the graph
	plt.axis("off")
	st.pyplot(plt.gcf())

	return

def draw_legend(group_colors):
	plt.figure(figsize=(1, 1))
	legend_elements = []
	for group, color in group_colors.items():
		legend_elements.append(Line2D([0], [0], marker='o', color='w', label=group, markerfacecolor=color, markersize=10))
	plt.legend(handles=legend_elements, loc='upper center')
	plt.axis("off")
	st.pyplot(plt.gcf())

def run():
	# Streamlit application components
	st.set_page_config(page_title="Home Network Simulation", layout="wide")
	st.title("Home Network Simulation")
	st.markdown("""
				<style>
					.block-container {
						padding-top: 2rem;
						padding-bottom: 2rem;
						padding-left: 1rem;
						padding-right: 1rem;
				</style>
				""", unsafe_allow_html=True)
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

	hosts = [{"name": "internet", "ip_address": "", "groups": [], "type": "internet"},
			 {"name": "router", "ip_address": "192.168.1.1", "groups": ["network"], "type": "router"},	
			 {"name": "motion-sensor", "ip_address": "192.168.1.2", "groups": ["network", "home-security-system"], "type": "device"},
			 {"name": "alarm", "ip_address": "192.168.1.3", "groups": ["network", "home-security-system"], "type": "device"},
			 {"name": "smart-lock", "ip_address": "192.168.1.4", "groups": ["network", "home-security-system"], "type": "device"},
			 {"name": "phone", "ip_address": "192.168.1.5", "groups": ["network"], "type": "device"},
			 {"name": "game-console", "ip_address": "192.168.1.6", "groups": ["network", "living-room"], "type": "device"},
			 {"name": "guest-laptop-1", "ip_address": "192.168.1.7", "groups": ["network"], "type": "device"},
			 {"name": "guest-laptop-2", "ip_address": "192.168.1.8", "groups": ["network"], "type": "device"},
			 {"name": "work-laptop", "ip_address": "192.168.1.9", "groups": ["network"], "type": "device"},
			 {"name": "printer", "ip_address": "192.168.1.10", "groups": ["network"], "type": "device"},
	]

	links = [{"link": ('internet', 'router'), "connection": "wired"}, 
			 {"link": ('router', 'motion-sensor'), "connection": "wireless"}, 
			 {"link": ('router', 'alarm'), "connection": "wireless"}, 
			 {"link": ('router', 'smart-lock'), "connection": "wireless"}, 
			 {"link": ('router', 'phone'), "connection": "wireless"}, 
			 {"link": ('router', 'game-console'), "connection": "wireless"}, 
			 {"link": ('router', 'guest-laptop-1'), "connection": "wireless"}, 
			 {"link": ('router', 'guest-laptop-2'), "connection": "wireless"}, 
			 {"link": ('router', 'game-console'), "connection": "wireless"}, 
			 {"link": ('router', 'work-laptop'), "connection": "wireless"}, 
			 {"link": ('router', 'printer'), "connection": "wired"}, 
	]

	groups = ['network', 'home-security-system', 'living-room']
	node_shapes = {"internet": "s", "router": "D", "firewall": "^", "device": "o"}


	user_msg = ""
	ai_msg = ""

	# Check the configuration request and process it
	if config_request:
		print(f"Config request checked: {config_request}")
		user_msg = config_request
		indent = "  "
		if config_request == "I've got a new IoT security camera that I want to connect to my network. It should only interact with my phone and the home security system.":
			ai_msg = "add device('security camera') to group('home security system')\nset policy('camera-traffic') { \n" + indent + "allow traffic(device('security-camera'), [device('phone'), group('home security system')])\n" + indent + "allow traffic([device('phone'), group('home security system')], device('security-camera'))\n}"
		elif config_request == "I want to create a new subnet for my home office devices. This should include my work laptop, printer, and my phone. Also, make sure this subnet has priority access to the bandwidth during office hours.":
			ai_msg = "add device('work laptop') to group('home office')\nadd device('printer') to group('home office')\nadd device('phone') to group('home office')\nset policy('office hours') {\n" + indent + "for group('home office') {\n" + (indent * 2)  + "from hour('09:00') to hour('17:00')\n" + (indent * 2) + "set bandwidth('min', '100', 'mbps')\n" + indent + "}\n}"
		elif config_request == "I want to set up a guest Wi-Fi network that should only provide internet access and nothing more. It should also have limited bandwidth because I don't want it to get in the way of my main network's performance.":
			ai_msg = "add group('guest network')\nset policy('guest bandwidth') {\n" + indent + "for group('guest network') {\n" + (indent * 2) + "set bandwidth('max', '5', 'mbps')\n" + indent + "}\n}"
		elif config_request == "My child does a lot of online gaming and it seems to be slowing down the internet for everyone else. Can you limit the amount of internet he can use?":
			ai_msg = "set policy('gaming bandwidth') {\n" + indent + "for device('gaming console') {\n" + (indent * 2) + "set bandwidth('max', '5', 'mbps')\n" + indent + "}\n}"
		elif config_request == "I've been hearing a lot about cyber threats on the news lately. I want to browse the web safely, but I don't want any strangers connecting to my devices from the internet.":
			ai_msg = "add middlebox('firewall') to group('network')\n" + "set policy('web-browsing-security') {\n" + indent + "for middlebox('firewall') {\n" + (indent * 2) + "allow traffic(group('network'), group('internet'))\n" + (indent * 2) + "block traffic(group('internet'), group('network'))\n" + indent + "}\n}"
		else:
			print(config_request)

		with st.sidebar.chat_message("user"):
			st.markdown(user_msg)

		with st.sidebar.chat_message("assistant"):
			st.code(ai_msg, language="None")

	st.markdown("""
				<style>
					code {
						font-size: smaller !important;
					}
				</style>
			    """, unsafe_allow_html=True)

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

if __name__ == "__main__":
	run()
