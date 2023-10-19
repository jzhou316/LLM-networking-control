import grpc
import itertools
import home_network_pb2
import home_network_pb2_grpc
from concurrent import futures
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Controller
from mininet.util import dumpNodeConnections

class HomeNetworkServicer(home_network_pb2_grpc.HomeNetworkServicer):
	def __init__(self):
		self.net = None
		self.host_counter = 1
		self.user_to_mininet = {}
		self.mininet_to_user = {}
		self.group_to_host = {'network': []}
		self.host_to_group = {}
		print("Server initiated")

	def _CreateHostName(self):
		new_name = "h" + str(self.host_counter)
		self.host_counter += 1
		return new_name

	def _GetNode(self, name):
		return self.net.get(self.user_to_mininet[name])

	def _BuildBasicTopo(self):
		self.net.addController('c0')
		self.user_to_mininet['switch'] = 's1'
		self.mininet_to_user['s1'] = 'switch'
		s1 = self.net.addSwitch('s1')
		self.group_to_host['network'].append('switch')
		self.host_to_group['switch'] = ['network']

		map = ['home router', 'laptop', 'camera', 'lights']
		for device in map:
			host_name = self._CreateHostName()
			self.user_to_mininet[device] = host_name
			self.mininet_to_user[host_name] = device
			self.group_to_host['network'].append(device)
			self.host_to_group[device] = ['network']
			new_device = self.net.addHost(host_name)
			self.net.addLink(new_device, s1)
		return

	def StartNetwork(self, request, context):
		if self.net == None:
			self.net = Mininet(controller=Controller)
			self._BuildBasicTopo()
			self.net.start()
			h1 = self.net.get('h1')
			h2 = self.net.get('h2')
			self.net.iperf((h1, h2), l4Type='TCP', seconds=3)
			self.net.pingAll()
		return home_network_pb2.Empty()

	def GetTopology(self, request, context):
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

		links_list = []
		for link in self.net.links:
			node1, intf1 = link.intf1.name.split('-')
			node2, intf2 = link.intf2.name.split('-')
			node_obj1 = home_network_pb2.Host(name=self.mininet_to_user[node1], ip_address=nodes_lookup[node1])
			node_obj2 = home_network_pb2.Host(name=self.mininet_to_user[node2], ip_address=nodes_lookup[node2])
			links_list.append(home_network_pb2.Link(host1=node_obj1, host2=node_obj2))
		return home_network_pb2.Topology(hosts=nodes_list, links=links_list)

	def AddDevice(self, request, context):
		if request.name not in self.user_to_mininet.keys():
			new_host = self._CreateHostName()
			self.mininet_to_user[new_host] = request.name
			self.user_to_mininet[request.name] = new_host
			new_device = self.net.addHost('h5')
			switch = self.net.get('s1')
			print(new_device)
			print(switch)
			self.net.addLink(new_device, switch)
			print(f"Added host {request.name} on server side")
			self.group_to_host["network"].append(request.name)
			self.host_to_group[request.name] = ["network"]

		if request.groups[0].name != "network":
			self.group_to_host[request.groups[0].name].append(request.name)
			self.host_to_group[request.name].append(request.groups[0].name)

		added_device = self._GetNode(request.name)
		h1 = self.net.get('h1')
		h5 = self.net.get('h5')
		h5.cmd('ifconfig h5-eth0 inet 192.168.1.19 netmask 255.255.255.0')
		CLI(self.net)
		dumpNodeConnections(self.net.hosts)
		dumpNodeConnections(self.net.switches)
		#self.net.iperf((h5, h1), l4Type='TCP', seconds=3)
		self.net.pingAll()
		return home_network_pb2.Host(name=request.name)

	def GetGroups(self, request, context):
		groups_list = [home_network_pb2.Group(name=group) for group in self.group_to_host.keys()]
		return home_network_pb2.Groups(groups=groups_list)

def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	home_network_pb2_grpc.add_HomeNetworkServicer_to_server(HomeNetworkServicer(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	server.wait_for_termination()

if __name__ == "__main__":
	serve()
