import ipaddress
from .utils import (
    logger,
    run_command,
    validate_cidr,
    load_state,
    save_state,
    get_vpc
)

def create_vpc(name, cidr):
    if not validate_cidr(cidr):
        logger.error(f"Invalid CIDR format: {cidr}")
        return False
    
    state = load_state()
    
    if get_vpc(name):
        logger.error(f"VPC '{name}' already exists")
        return False
    
    bridge_name = f"br-{name}"
    
    try:
        run_command(f"ip link add {bridge_name} type bridge")
        logger.info(f"Created bridge {bridge_name}")
        
        network = ipaddress.ip_network(cidr, strict=False)
        bridge_ip = str(list(network.hosts())[0])
        prefix = cidr.split('/')[1]
        
        run_command(f"ip addr add {bridge_ip}/{prefix} dev {bridge_name}")
        logger.info(f"Assigned IP {bridge_ip}/{prefix} to {bridge_name}")
        
        run_command(f"ip link set {bridge_name} up")
        logger.info(f"Bridge {bridge_name} is up")
        
        run_command("echo 1 > /proc/sys/net/ipv4/ip_forward")
        logger.info("IP forwarding enabled")
        
        vpc_data = {
            "name": name,
            "cidr": cidr,
            "bridge": bridge_name,
            "bridge_ip": bridge_ip,
            "subnets": [],
            "peerings": []
        }
        
        state['vpcs'].append(vpc_data)
        save_state(state)
        
        logger.info(f"VPC '{name}' created successfully with CIDR {cidr}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create VPC: {e}")
        run_command(f"ip link del {bridge_name}", check=False)
        return False

def delete_vpc(name):
    vpc = get_vpc(name)
    if not vpc:
        logger.error(f"VPC '{name}' not found")
        return False
    
    try:
        from . import subnet as subnet_module
        from . import peering as peering_module
        
        for sn in list(vpc.get('subnets', [])):
            subnet_module.delete_subnet(name, sn['name'])
        
        for peer in list(vpc.get('peerings', [])):
            peering_module.delete_peering(name, peer['peer_vpc'])
        
        bridge_name = vpc['bridge']
        run_command(f"ip link del {bridge_name}", check=False)
        logger.info(f"Deleted bridge {bridge_name}")
        
        state = load_state()
        state['vpcs'] = [v for v in state['vpcs'] if v['name'] != name]
        save_state(state)
        
        logger.info(f"VPC '{name}' deleted successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete VPC: {e}")
        return False

def list_vpcs():
    state = load_state()
    vpcs = state.get('vpcs', [])
    
    if not vpcs:
        logger.info("No VPCs found")
        return
    
    print(f"\n{'VPC Name':<20} {'CIDR':<18} {'Bridge':<15} {'Subnets':<10}")
    print("-" * 70)
    
    for vpc in vpcs:
        name = vpc['name']
        cidr = vpc['cidr']
        bridge = vpc['bridge']
        subnet_count = len(vpc.get('subnets', []))
        
        print(f"{name:<20} {cidr:<18} {bridge:<15} {subnet_count:<10}")
    
    print()