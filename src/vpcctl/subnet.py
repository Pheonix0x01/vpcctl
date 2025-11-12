import ipaddress
from .utils import (
    logger,
    run_command,
    validate_cidr,
    load_state,
    save_state,
    get_vpc,
    get_subnet
)

def create_subnet(vpc_name, subnet_name, cidr, subnet_type):
    if not validate_cidr(cidr):
        logger.error(f"Invalid CIDR format: {cidr}")
        return False
    
    vpc = get_vpc(vpc_name)
    if not vpc:
        logger.error(f"VPC '{vpc_name}' not found")
        return False
    
    vpc_network = ipaddress.ip_network(vpc['cidr'], strict=False)
    subnet_network = ipaddress.ip_network(cidr, strict=False)
    
    if not subnet_network.subnet_of(vpc_network):
        logger.error(f"Subnet CIDR {cidr} is not within VPC CIDR {vpc['cidr']}")
        return False
    
    if get_subnet(vpc_name, subnet_name):
        logger.error(f"Subnet '{subnet_name}' already exists in VPC '{vpc_name}'")
        return False
    
    namespace = f"{vpc_name}-{subnet_name}"
    veth_br = f"vb-{vpc_name[:4]}-{subnet_name[:4]}"
    veth_ns = f"vn-{vpc_name[:4]}-{subnet_name[:4]}"
    bridge = vpc['bridge']
    
    subnet_hosts = list(subnet_network.hosts())
    gateway_ip = str(subnet_hosts[0])
    subnet_ip = str(subnet_hosts[1])
    prefix = cidr.split('/')[1]
    
    try:
        run_command(f"ip netns add {namespace}")
        logger.info(f"Created namespace {namespace}")
        
        run_command(f"ip link add {veth_br} type veth peer name {veth_ns}")
        logger.info(f"Created veth pair {veth_br} <-> {veth_ns}")
        
        run_command(f"ip link set {veth_br} master {bridge}")
        logger.info(f"Attached {veth_br} to bridge {bridge}")
        
        run_command(f"ip addr add {gateway_ip}/{prefix} dev {bridge}")
        logger.info(f"Added IP {gateway_ip}/{prefix} to bridge {bridge}")
        
        run_command(f"echo 0 > /proc/sys/net/ipv4/conf/{veth_br}/rp_filter")
        logger.info(f"Disabled rp_filter on {veth_br}")
        
        run_command(f"ip link set {veth_br} up")
        logger.info(f"Brought up {veth_br}")
        
        run_command(f"ip link set {veth_ns} netns {namespace}")
        logger.info(f"Moved {veth_ns} to namespace {namespace}")
        
        run_command(f"ip netns exec {namespace} ip addr add {subnet_ip}/{prefix} dev {veth_ns}")
        logger.info(f"Assigned IP {subnet_ip}/{prefix} to {veth_ns}")
        
        run_command(f"ip netns exec {namespace} ip link set {veth_ns} up")
        logger.info(f"Brought up {veth_ns} in namespace")
        
        run_command(f"ip netns exec {namespace} ip link set lo up")
        logger.info(f"Brought up loopback in namespace")
        
        run_command(f"ip netns exec {namespace} ip route add default via {gateway_ip}")
        logger.info(f"Added default route via {gateway_ip}")
        
        subnet_data = {
            "name": subnet_name,
            "cidr": cidr,
            "type": subnet_type,
            "namespace": namespace,
            "ip": subnet_ip,
            "gateway": gateway_ip,
            "veth_br": veth_br,
            "veth_ns": veth_ns
        }
        
        state = load_state()
        for v in state['vpcs']:
            if v['name'] == vpc_name:
                v['subnets'].append(subnet_data)
                break
        save_state(state)
        
        if subnet_type == "public":
            from . import routing as routing_module
            from .utils import get_default_interface
            internet_interface = get_default_interface()
            if internet_interface:
                routing_module.setup_nat(vpc_name, cidr, internet_interface)
                routing_module.add_inter_subnet_routes(vpc_name)
        elif subnet_type == "private":
            from . import routing as routing_module
            routing_module.setup_private_subnet_routing(vpc_name, subnet_name)
            routing_module.add_inter_subnet_routes(vpc_name)
        
        logger.info(f"Subnet '{subnet_name}' created successfully in VPC '{vpc_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create subnet: {e}")
        run_command(f"ip netns del {namespace}", check=False)
        run_command(f"ip link del {veth_br}", check=False)
        return False

def delete_subnet(vpc_name, subnet_name):
    subnet = get_subnet(vpc_name, subnet_name)
    if not subnet:
        logger.error(f"Subnet '{subnet_name}' not found in VPC '{vpc_name}'")
        return False
    
    vpc = get_vpc(vpc_name)
    bridge = vpc['bridge']
    namespace = subnet['namespace']
    veth_br = subnet['veth_br']
    cidr = subnet['cidr']
    gateway = subnet.get('gateway')
    prefix = cidr.split('/')[1]
    
    try:
        run_command(f"ip netns del {namespace}", check=False)
        logger.info(f"Deleted namespace {namespace}")
        
        run_command(f"ip link del {veth_br}", check=False)
        logger.info(f"Deleted veth {veth_br}")
        
        if gateway:
            run_command(f"ip addr del {gateway}/{prefix} dev {bridge}", check=False)
            logger.info(f"Removed IP {gateway}/{prefix} from bridge {bridge}")
        
        from .utils import get_default_interface
        internet_interface = get_default_interface()
        if internet_interface:
            run_command(f"iptables -t nat -D POSTROUTING -s {cidr} -o {internet_interface} -j MASQUERADE", check=False)
            run_command(f"iptables -D FORWARD -s {cidr} -j ACCEPT", check=False)
        
        state = load_state()
        for v in state['vpcs']:
            if v['name'] == vpc_name:
                v['subnets'] = [s for s in v['subnets'] if s['name'] != subnet_name]
                break
        save_state(state)
        
        logger.info(f"Subnet '{subnet_name}' deleted successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete subnet: {e}")
        return False

def list_subnets(vpc_name):
    vpc = get_vpc(vpc_name)
    if not vpc:
        logger.error(f"VPC '{vpc_name}' not found")
        return
    
    subnets = vpc.get('subnets', [])
    
    if not subnets:
        logger.info(f"No subnets found in VPC '{vpc_name}'")
        return
    
    print(f"\n{'Subnet Name':<20} {'CIDR':<18} {'Type':<10} {'Namespace':<30} {'IP':<15}")
    print("-" * 100)
    
    for subnet in subnets:
        name = subnet['name']
        cidr = subnet['cidr']
        subnet_type = subnet['type']
        namespace = subnet['namespace']
        ip = subnet['ip']
        
        print(f"{name:<20} {cidr:<18} {subnet_type:<10} {namespace:<30} {ip:<15}")
    
    print()