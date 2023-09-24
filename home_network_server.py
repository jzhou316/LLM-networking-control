import grpc
import time
import itertools
import home_network_pb2
import home_network_pb2_grpc
from concurrent import futures
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink, Intf
from mininet.cli import CLI
from mininet.clean import cleanup

class HomeNetworkServicer(home_network_pb2_grpc.HomeNetworkServicer):
	def __init__(self):
		self.net = None
		self.host_counter = 1
		# keys are user-given names ("Laptop", "Camera") and values are mininet names ("h1", "h2")
		self.name_to_node = {}
		# keys are mininet names ("h1", "h3") and values are user-given names ("Laptop", "Camera") 
		self.node_to_name = {}
		# keys are group names and values are user-given names
		self.groups = {"network": []}
		print("Server initiated")

	# Creates a host name with format "h[number]"
	def _CreateHostName(self):
		new_name = "h" + str(self.host_counter)
		self.host_counter += 1
		return new_name

	# Takes in a name like "h1" and returns the host/switch Mininet object
	def _GetNode(self, name):
		return self.net.get(self.name_to_node[name])

	def _BuildBasicTopo(self):
		# Add hosts in basic home network
		map = {'Home Router': '10.0.0.1/8',
			   'Laptop': '10.0.0.2/8',
			   'Camera': '10.0.0.3/8',
			   'Lights': '10.0.0.4/8'}
		for device in map.keys():
			host_name = self._CreateHostName()
			self.name_to_node[device] = host_name
			self.node_to_name[host_name] = device
			self.groups["network"].append(device)
			self.net.addHost(host_name, ip=map[device])

		self.name_to_node['Switch'] = 's1'
		self.node_to_name['s1'] = 'Switch'
		self.net.addSwitch('s1')
		self.groups["network"].append('Switch')

		home_router = self._GetNode('Home Router')
		laptop = self._GetNode('Laptop')
		camera = self._GetNode('Camera')
		lights = self._GetNode('Lights')
		switch = self._GetNode('Switch')

		# Add links from switch to every other device
		self.net.addLink(home_router, switch)
		self.net.addLink(switch, laptop)
		self.net.addLink(switch, camera)
		self.net.addLink(switch, lights)
		return

	# Starts the network with the basic topology
	def StartNetwork(self, request, context):
		if self.net == None:
			self.net = Mininet(link=TCLink)
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
			print(key)
			print(self.node_to_name[key])
			print(nodes_lookup[key])
			nodes_list.append(home_network_pb2.Host(name=self.node_to_name[key], ip_address=nodes_lookup[key]))
		# Get the links
		links_list = []
		for link in self.net.links:
			node1, intf1 = link.intf1.name.split('-')
			node2, intf2 = link.intf2.name.split('-')
			node_obj1 = home_network_pb2.Host(name=self.node_to_name[node1], ip_address=nodes_lookup[node1])
			node_obj2 = home_network_pb2.Host(name=self.node_to_name[node2], ip_address=nodes_lookup[node2])
			links_list.append(home_network_pb2.Link(host1=node_obj1, host2=node_obj2))
		return home_network_pb2.Topology(hosts=nodes_list, links=links_list)

	# Add new device to network 
	def AddDevice(self, request, context):
		new_host = self._CreateHostName()
		self.node_to_name[new_host] = request.name
		self.name_to_node[request.name] = new_host
		added_host = self.net.addHost(new_host)
		self.groups["network"].append(request.name)

		# Connect the new device to the switch
		self.net.addLink(added_host, self._GetNode('Switch'))
		added_host.setIP(request.ip_address)
		print(f"Added host {request.name} on server side")
		print(self.net.hosts)
		return home_network_pb2.Host(name=request.name, ip_address=request.ip_address)

def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	home_network_pb2_grpc.add_HomeNetworkServicer_to_server(HomeNetworkServicer(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	print("gRPC server started")
	server.wait_for_termination()

if __name__ == "__main__":
	serve()
