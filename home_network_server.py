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

class BasicHomeTopo(Topo):
	"""
	Simple home topology example.
	A router is linked to three home devices: lamp, phone, pc.

	"""

	def build(self):
		# Add hosts and switches
		home_router = self.addHost('HomeRouter', ip='10.0.0.1/8')
		lamp = self.addHost('Lamp', ip='10.0.0.2/8')
		phone = self.addHost('Phone', ip='10.0.0.3/8')
		pc = self.addHost('PC', ip='10.0.0.4/8')

		# Add links
		self.addLink(home_router, lamp)
		self.addLink(home_router, phone)
		self.addLink(home_router, pc)

class HomeNetworkServicer(home_network_pb2_grpc.HomeNetworkServicer):
	def __init__(self):
		self.net = None
		self.home_router = None
		print("Server servicer initiated")

	def StartNetwork(self, request, context):
		if self.net == None:
			topo = BasicHomeTopo()
			self.net = Mininet(topo=topo, link=TCLink)
			self.net.start()
			self.home_router = self.net.getNodeByName("HomeRouter")
			print("Network started")
		return home_network_pb2.Empty()

	def StopNetwork(self, request, context):
		if self.net:
			self.net.stop()
			print("Network stopped")
		return home_network_pb2.Empty()

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
			nodes_list.append(home_network_pb2.Host(name=key, ip_address=nodes_lookup[key]))
		# Get the links
		links_list = []
		for link in self.net.links:
			node1, intf1 = link.intf1.name.split('-')
			node2, intf2 = link.intf2.name.split('-')
			node_obj1 = home_network_pb2.Host(name=node1, ip_address=nodes_lookup[node1])
			node_obj2 = home_network_pb2.Host(name=node2, ip_address=nodes_lookup[node2])
			links_list.append(home_network_pb2.Link(host1=node_obj1, host2=node_obj2))
		return home_network_pb2.Topology(hosts=nodes_list, links=links_list)

	def AddDevice(self, request, context):
		added_host = self.net.addHost(request.name)

		# Connect the new device to the last switch
		self.net.addLink(added_host, self.home_router)
		added_host.setIP(request.ip_address)
		print(f"Added host {request.name} with ip address {request.ip_address} on server side")
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
