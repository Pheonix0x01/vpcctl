from .utils import (
    logger,
    run_command,
    load_state,
    get_vpc,
    get_subnet
)

def setup_nat(vpc_name, subnet_cidr, internet_interface):
    try:
        result = run_command("cat /proc/sys/net/ipv4/ip_forward", check=True)
        if result.stdout.strip() != "1":
            run_command("echo 1 > /proc/sys/net/ipv4/ip_forward")
            logger.info("IP forwarding enabled")
        
        run_command(f"iptables -t nat -A POSTROUTING -s {subnet_cidr} -o {internet_interface} -j MASQUERADE")
        logger.info(f"Added MASQUERADE rule for {subnet_cidr} on {internet_interface}")
        
        run_command(f"iptables -A FORWARD -i br-* -o {internet_interface} -j ACCEPT")
        logger.info(f"Added FORWARD rule for bridge to {internet_interface}")
        
        run_command(f"iptables -A FORWARD -i {internet_interface} -o br-* -m state --state RELATED,ESTABLISHED -j ACCEPT")
        logger.info(f"Added FORWARD rule for {internet_interface} to bridge")
        
        logger.info(f"NAT setup completed for {subnet_cidr}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup NAT: {e}")
        return False

def add_inter_subnet_routes(vpc_name):
    vpc = get_vpc(vpc_name)
    if not vpc:
        logger.error(f"VPC '{vpc_name}' not found")
        return False
    
    subnets = vpc.get('subnets', [])
    bridge = vpc['bridge']
    
    if len(subnets) < 2:
        logger.info(f"VPC '{vpc_name}' has less than 2 subnets, no inter-subnet routes needed")
        return True
    
    try:
        run_command(f"iptables -A FORWARD -i {bridge} -o {bridge} -j ACCEPT", check=False)
        logger.info(f"Added iptables rule for inter-bridge forwarding on {bridge}")
        
        for subnet1 in subnets:
            ns1 = subnet1['namespace']
            gateway1 = subnet1['gateway']
            
            for subnet2 in subnets:
                if subnet1['name'] == subnet2['name']:
                    continue
                
                cidr2 = subnet2['cidr']
                
                run_command(f"ip netns exec {ns1} ip route add {cidr2} via {gateway1}", check=False)
                logger.info(f"Added route in {ns1}: {cidr2} via {gateway1}")
        
        logger.info(f"Inter-subnet routes configured for VPC '{vpc_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add inter-subnet routes: {e}")
        return False

def setup_private_subnet_routing(vpc_name, subnet_name):
    subnet = get_subnet(vpc_name, subnet_name)
    if not subnet:
        logger.error(f"Subnet '{subnet_name}' not found in VPC '{vpc_name}'")
        return False
    
    namespace = subnet['namespace']
    gateway = subnet['gateway']
    
    try:
        vpc = get_vpc(vpc_name)
        all_subnets = vpc.get('subnets', [])
        
        run_command(f"ip netns exec {namespace} ip route del default", check=False)
        logger.info(f"Removed default route from private subnet {namespace}")
        
        for other_subnet in all_subnets:
            if other_subnet['name'] != subnet_name:
                other_cidr = other_subnet['cidr']
                run_command(f"ip netns exec {namespace} ip route add {other_cidr} via {gateway}", check=False)
                logger.info(f"Re-added route to {other_cidr} via {gateway} in private subnet {namespace}")
        
        logger.info(f"Private subnet routing configured for {subnet_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup private subnet routing: {e}")
        return False