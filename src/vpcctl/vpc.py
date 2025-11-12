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
    
    if get_vpc(name):
        logger.error(f"VPC '{name}' already exists")
        return False
    
    bridge = f"br-{name}"
    bridge_ip = cidr.split('/')[0].rsplit('.', 1)[0] + '.1'
    prefix = cidr.split('/')[1]
    
    try:
        run_command(f"ip link add {bridge} type bridge")
        logger.info(f"Created bridge {bridge}")
        
        run_command(f"ip addr add {bridge_ip}/{prefix} dev {bridge}")
        logger.info(f"Assigned IP {bridge_ip}/{prefix} to {bridge}")
        
        run_command(f"ip link set {bridge} up")
        logger.info(f"Bridge {bridge} is up")
        
        run_command("echo 1 > /proc/sys/net/ipv4/ip_forward")
        logger.info("IP forwarding enabled")
        
        run_command(f"echo 0 > /proc/sys/net/ipv4/conf/{bridge}/send_redirects")
        logger.info(f"Disabled ICMP redirects on {bridge}")
        
        run_command(f"echo 0 > /proc/sys/net/ipv4/conf/{bridge}/rp_filter")
        logger.info(f"Disabled reverse path filtering on {bridge}")
        
        run_command(f"echo 1 > /proc/sys/net/ipv4/conf/{bridge}/forwarding")
        logger.info(f"Enabled forwarding on {bridge}")
        
        vpc_data = {
            "name": name,
            "cidr": cidr,
            "bridge": bridge,
            "bridge_ip": bridge_ip,
            "subnets": [],
            "peerings": []
        }
        
        state = load_state()
        state['vpcs'].append(vpc_data)
        save_state(state)
        
        logger.info(f"VPC '{name}' created successfully with CIDR {cidr}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create VPC: {e}")
        run_command(f"ip link del {bridge}", check=False)
        return False

def delete_vpc(name):
    vpc = get_vpc(name)
    if not vpc:
        logger.error(f"VPC '{name}' not found")
        return False
    
    if vpc.get('subnets'):
        logger.error(f"Cannot delete VPC '{name}': it has active subnets")
        return False
    
    bridge = vpc['bridge']
    
    try:
        run_command(f"ip link del {bridge}", check=False)
        logger.info(f"Deleted bridge {bridge}")
        
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