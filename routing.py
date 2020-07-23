from netmiko import ConnectHandler
import time
import itertools
import re
import ipaddress
import socket



def connection(ip):
	return {
	'device_type':'cisco_ios',
	'ip':ip,
	'username':'bala',
	'password':'cisco',
	'secret':'cisco',
	}

ip_addresses = []
visited_list = [] #router ids
ip_list = ['10.0.0.1'] #router ips
subnet_mask = []
advertised_address = []
neighbors= []
eigrp_commands = ["router eigrp 1"]
static_commands = []
gateways = []
visited_routers = []
net_connect = None


def find_ip_masks(ip_address):
	global net_connect
	advertized_address = []
	iosv = connection(ip_address)
	print("connecting to "+str(iosv))
	net_connect = ConnectHandler(**iosv)
	net_connect.enable()
	commands=['exit','sh run | include interface|ip address']
	output = net_connect.send_config_set(commands, delay_factor=5)
	addresses = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",output)
	commands = ['exit','sh run']
	output = net_connect.send_config_set(commands, delay_factor=6)
	hostname = re.findall(r'hostname\s+(\S*)',output)[0].encode()
	visited_list.append(hostname)
	for a in addresses:
		address = a.encode('ascii', 'ignore')
		advertized_address.append(address)
	return advertized_address

def find_network_ids(advertized_address):
	#print(advertized_address)
	global net_connect
	subnet_mask = []
	for i in range(len(advertized_address)/2):
		x = ipaddress.IPv4Interface(unicode(advertized_address[(2)*i])+"/"+unicode(advertized_address[(2)*i+1]))
		subnet_mask.append(str(x.network.network_address))
	gateways= advertized_address[0::2]
	del advertized_address[0::2]
	return advertized_address,subnet_mask

def enable_routing(advertised_address,subnet_mask):
	global net_connect
	for ip, mask in zip(subnet_mask,advertised_address):
		command = "network "+ip+" "+mask
		eigrp_commands.append(command)
	output = net_connect.send_config_set(eigrp_commands)
	print(output+"\nRouting Enabled")
	del advertised_address[:], subnet_mask[:]

def find_neighbors():
	global net_connect
	global ip_list
	neighbors = []	
	output = net_connect.send_command("sh cdp neighbor detail",delay_factor=3)
	addresses = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",output)
	for a in addresses:
		address = a.encode('ascii', 'ignore')
		neighbors.append(address)
		ip_list.append(address)
	print(neighbors)
	return neighbors

def routing(neighbors):
	global net_connect
	global visited_list
	for ip in neighbors:
		ssh_entry = "ssh -l bala "+ip
		commands = ["exit",ssh_entry,"cisco","en","cisco","sh run","        exit"]
		output = net_connect.send_config_set(commands, delay_factor=5)
		hostname = re.findall(r'hostname\s+(\S*)',output)[0].encode()		
		if hostname not in visited_list:
			print(visited_list)
			visited_list.append(hostname)
			commands = ["exit",ssh_entry,"cisco","en","cisco","sh run | include interface |ip address","exit"]
			output = net_connect.send_config_set(commands, delay_factor=5)
			addresses = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",output)
			eigrp_ids=[]
			network_ids=[]
			command = ["exit",ssh_entry,"cisco","en","cisco","conf t","router eigrp 1"]		
			for a in addresses:
				address = a.encode('ascii', 'ignore')
				eigrp_ids.append(address)
			eigrp_ids = eigrp_ids[1:-1]
			for i in range(len(eigrp_ids)/2):
				x = ipaddress.IPv4Interface(unicode(eigrp_ids[(2)*i])+"/"+unicode(eigrp_ids[(2)*i+1]))
				network_ids.append(str(x.network.network_address))
			del eigrp_ids[0::2]
			for ip, mask in zip(network_ids,eigrp_ids):
				commands = "network "+ip+" "+mask
				command.append(commands)
			command.append("exit") #to exit from routing mode
			command.append("exit") # to exit from global conf mode
			command.append("exit")	#to exit from the router
			output = net_connect.send_config_set(command,delay_factor=5)
			commands = ["exit",ssh_entry,"cisco","sh cdp neighbors detail ","  exit"]
			output = net_connect.send_config_set(commands,delay_factor=5)
			addresses = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",output)
			commands = ["exit",ssh_entry,"cisco","en","cisco","sh run","            exit"]
			output = net_connect.send_config_set(commands,delay_factor = 4)
			hostname = re.findall(r'hostname\s+(\S*)',output)[0].encode()
			visited_list.append(hostname)			
			print(ip_list)


def static_implementation(ip_address):
	global net_connect
	advertized_address = []
	iosv = connection(ip_address)
	print("connecting to "+str(iosv))
	net_connect = ConnectHandler(**iosv)
	net_connect.enable()
	commands=['exit','sh ip route eigrp']
	output = net_connect.send_config_set(commands, delay_factor=4)
	output = output.split("\n")
	output = [a.encode() for a in output]
	output1 = []	
	for i in output:
		if i.startswith("D"):
			output1.append(i)
		else:
			output.remove(i)
	addresses = []
	for i in output1:
		a = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/\d{1,2}",i)
		b = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",i)
		
	print(addresses)

for ip_address in ip_list:
	advertised_address=find_ip_masks(ip_address)	
#	print(advertised_address)
	advertised_address,subnet_mask = find_network_ids(advertised_address)
	enable_routing(advertised_address,subnet_mask)
	neighbors = find_neighbors()
	routing(neighbors)
	static_implementation(ip_address)
