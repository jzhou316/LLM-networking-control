import grpc
import time
import itertools
import ipaddress
import home_network_pb2
import home_network_pb2_grpc
from concurrent import futures
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink, Intf
from mininet.cli import CLI
from mininet.node import CPULimitedHost, DefaultController
from mininet.util import dumpNodeConnections

class HomeNetworkServicer(home_network_pb2_grpc.HomeNetworkServicer):
	def __init__(self):
		self.net = None
		self.base_ip = "192.0.2.0"
		self.subnet_mask = 24
		self.host_counter = 1
		self.available_ips = set()
		# keep track of user-given name and mininet name pairs
		self.user_to_mininet = {}
		self.mininet_to_user = {}
		# group names and members
		self.group_to_host = {'network': []}
		self.host_to_group = {}
		print("Server initiated")

	# Creates a host name with format "h[number]"
	def _CreateHostName(self):
		new_name = "h" + str(self.host_counter)
		self.host_counter += 1
		return new_name

	# Takes in a name like "h1" and returns the host/switch Mininet object
	def _GetNode(self, name):
		return self.net.get(self.user_to_mininet[name])

	def _GenerateIPAddresses(self):
		ips = list(ipaddress.ip_network(f'{self.base_ip}/{self.subnet_mask}').hosts())
		self.available_ips = set(str(ip) for ip in ips)

	def _ReleaseIP(self, ip):
		if ip not in self.available_ips:
			self.available_ips.add(ip)

	def _BuildBasicTopo(self):
		# Add hosts in basic home network
		map = ['home router','laptop', 'camera', 'lights']
		self.user_to_mininet['switch'] = 's1'
		self.mininet_to_user['s1'] = 'switch'
		self.net.addSwitch('s1')
		self.group_to_host['network'].append('switch')
		self.host_to_group['switch'] = ['network']
		switch = self._GetNode('switch')

		for device in map:
			host_name = self._CreateHostName()
			self.user_to_mininet[device] = host_name
			self.mininet_to_user[host_name] = device
			self.group_to_host['network'].append(device)
			self.host_to_group[device] = ['network']
			self.net.addHost(host_name, ip=self.available_ips.pop())

			new_device = self._GetNode(device)
			self.net.addLink(switch, new_device)

		return

	# Starts the network with the basic topology
	def StartNetwork(self, request, context):
		if self.net == None:
			self.net = Mininet(host=CPULimitedHost, link=TCLink, controller=DefaultController)
			self._GenerateIPAddresses()
			self._BuildBasicTopo()

			# Start the network
			self.net.start()
			print("Network started")
		return home_network_pb2.Empty()

	# Stops the network if the network is active
	def StopNetwork(self, request, context):
		if self.net:
			self.net.stop()
			print("Network stopped")
		return home_network_pb2.Empty()

	# Get the topology of the network and return it
	def GetTopology(self, request, context):
		# Get the hosts
		nodes_lookup = {}
		for node in itertools.chain(self.net.hosts, self.net.switches):
			nodename = node.name
			try:
				ip_addr = node.IP()
			except:
				ip_addr = "No IP Address"
			nodes_lookup[nodename] = ip_addr
		nodes_list = []
		for key in nodes_lookup.keys():
			groups_list = [home_network_pb2.Group(name=group) for group in self.host_to_group[self.mininet_to_user[key]]]
			nodes_list.append(home_network_pb2.Host(name=self.mininet_to_user[key], ip_address=nodes_lookup[key], groups=groups_list))

		# Get the links
		links_list = []
		for link in self.net.links:
			node1, intf1 = link.intf1.name.split('-')
			node2, intf2 = link.intf2.name.split('-')
			node_obj1 = home_network_pb2.Host(name=self.mininet_to_user[node1], ip_address=nodes_lookup[node1])
			node_obj2 = home_network_pb2.Host(name=self.mininet_to_user[node2], ip_address=nodes_lookup[node2])
			links_list.append(home_network_pb2.Link(host1=node_obj1, host2=node_obj2))
		return home_network_pb2.Topology(hosts=nodes_list, links=links_list)

	# Add new device to network
	def AddDevice(self, request, context):
		if request.name not in self.user_to_mininet.keys():
			# Add a new device to the network
			new_host = self._CreateHostName()
			self.mininet_to_user[new_host] = request.name
			self.user_to_mininet[request.name] = new_host
			self.net.addHost(new_host)
			added_host = self._GetNode(request.name)
			# Connect the new device to the switch
			self.net.addLink(added_host, self._GetNode('switch'))
			added_host.setIP(self.available_ips.pop())
			print(f"Added host {request.name} on server side")
			# All devices should be added to the group "network"
			self.group_to_host["network"].append(request.name)
			self.host_to_group[request.name] = ["network"]

		# Add to another group if specified by user (assumes group alr exists)
		if request.groups[0].name != "network":
			self.group_to_host[request.groups[0].name].append(request.name)
			self.host_to_group[request.name].append(request.groups[0].name)

		print(self.net.hosts)
		print(self.group_to_host)
		print(self.host_to_group)
		return home_network_pb2.Host(name=request.name, ip_address=request.ip_address)

	# Remove a device from the network
	def RemoveDevice(self, request, context):
		if request.groups[0].name != "network":
			group_name = request.groups[0].name
			self.group_to_host[group_name].remove(request.name)
			self.host_to_group[request.name].remove(group_name)
		else:
			# Restore IP address and remove device from all groups
			removed_host = self._GetNode(request.name)
			for _, hosts in self.group_to_host.items():
				if request.name in hosts:
					hosts.remove(request.name)
			self.available_ips.add(removed_host.IP())
			print(f"Added back {removed_host.IP} to available IPs!")
			# Remove all links with the node
			for link in self.net.links:
				node1, intf1 = link.intf1.name.split('-')
				node2, intf2 = link.intf2.name.split('-')
				removed_mn = self.user_to_mininet[request.name]
				if node1 == removed_mn or node2 == removed_mn:
					self.net.delLink(link)

			# Remove the device from the network
			self.net.delHost(removed_host)
			print(f"Removed host {request.name} on server side")
			print(self.net.hosts)
			print(self.net.links)

		return home_network_pb2.Empty()

	# Get a list of all groups in the network
	def GetGroups(self, request, context):
		groups_list = [home_network_pb2.Group(name=group) for group in self.group_to_host.keys()]
		return home_network_pb2.Groups(groups=groups_list)

	# Add a new group to the network
	def AddGroup(self, request, context):
		self.group_to_host[request.name] = []
		return home_network_pb2.Empty()

def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	home_network_pb2_grpc.add_HomeNetworkServicer_to_server(HomeNetworkServicer(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	print("gRPC server started")
	server.wait_for_termination()

if __name__ == "__main__":
	serve()
