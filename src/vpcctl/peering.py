from .utils import (
    logger,
    run_command,
    load_state,
    save_state,
    get_vpc
)

def create_peering(vpc1_name, vpc2_name):
    vpc1 = get_vpc(vpc1_name)
    vpc2 = get_vpc(vpc2_name)
    
    if not vpc1 or not vpc2:
        logger.error(f"One or both VPCs not found")
        return False
    
    if vpc1_name == vpc2_name:
        logger.error(f"Cannot peer VPC with itself")
        return False
    
    bridge1 = vpc1['bridge']
    bridge2 = vpc2['bridge']
    cidr1 = vpc1['cidr']
    cidr2 = vpc2['cidr']
    
    veth1 = f"vp-{vpc1_name[:4]}-{vpc2_name[:4]}"
    veth2 = f"vp-{vpc2_name[:4]}-{vpc1_name[:4]}"
    
    try:
        run_command(f"ip link add {veth1} type veth peer name {veth2}")
        logger.info(f"Created veth pair {veth1} <-> {veth2}")
        
        run_command(f"ip link set {veth1} master {bridge1}")
        run_command(f"ip link set {veth2} master {bridge2}")
        logger.info(f"Attached veth pair to bridges")
        
        run_command(f"ip link set {veth1} up")
        run_command(f"ip link set {veth2} up")
        logger.info(f"Brought up veth pair")
        
        for subnet1 in vpc1.get('subnets', []):
            ns1 = subnet1['namespace']
            gw1 = subnet1['gateway']
            run_command(f"ip netns exec {ns1} ip route add {cidr2} via {gw1}", check=False)
            logger.info(f"Added route to {cidr2} in {ns1}")
        
        for subnet2 in vpc2.get('subnets', []):
            ns2 = subnet2['namespace']
            gw2 = subnet2['gateway']
            run_command(f"ip netns exec {ns2} ip route add {cidr1} via {gw2}", check=False)
            logger.info(f"Added route to {cidr1} in {ns2}")
        
        run_command(f"iptables -D FORWARD -i {bridge1} -o {bridge2} -j DROP", check=False)
        run_command(f"iptables -D FORWARD -i {bridge2} -o {bridge1} -j DROP", check=False)
        run_command(f"iptables -I FORWARD -i {bridge1} -o {bridge2} -j ACCEPT", check=False)
        run_command(f"iptables -I FORWARD -i {bridge2} -o {bridge1} -j ACCEPT", check=False)
        logger.info(f"Removed isolation rules between {bridge1} and {bridge2}")
        
        peering_data = {
            "vpc1": vpc1_name,
            "vpc2": vpc2_name,
            "veth1": veth1,
            "veth2": veth2
        }
        
        state = load_state()
        for v in state['vpcs']:
            if v['name'] == vpc1_name:
                v.setdefault('peerings', []).append(peering_data)
            elif v['name'] == vpc2_name:
                v.setdefault('peerings', []).append(peering_data)
        save_state(state)
        
        logger.info(f"Peering created between '{vpc1_name}' and '{vpc2_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create peering: {e}")
        run_command(f"ip link del {veth1}", check=False)
        return False

def delete_peering(vpc1_name, vpc2_name):
    vpc1 = get_vpc(vpc1_name)
    vpc2 = get_vpc(vpc2_name)
    
    if not vpc1 or not vpc2:
        logger.error(f"One or both VPCs not found")
        return False
    
    bridge1 = vpc1['bridge']
    bridge2 = vpc2['bridge']
    cidr1 = vpc1['cidr']
    cidr2 = vpc2['cidr']
    
    veth1 = f"vp-{vpc1_name[:4]}-{vpc2_name[:4]}"
    
    try:
        run_command(f"ip link del {veth1}", check=False)
        logger.info(f"Deleted veth pair")
        
        for subnet1 in vpc1.get('subnets', []):
            ns1 = subnet1['namespace']
            run_command(f"ip netns exec {ns1} ip route del {cidr2}", check=False)
        
        for subnet2 in vpc2.get('subnets', []):
            ns2 = subnet2['namespace']
            run_command(f"ip netns exec {ns2} ip route del {cidr1}", check=False)
        
        run_command(f"iptables -D FORWARD -i {bridge1} -o {bridge2} -j ACCEPT", check=False)
        run_command(f"iptables -D FORWARD -i {bridge2} -o {bridge1} -j ACCEPT", check=False)
        run_command(f"iptables -I FORWARD -i {bridge1} -o {bridge2} -j DROP", check=False)
        run_command(f"iptables -I FORWARD -i {bridge2} -o {bridge1} -j DROP", check=False)
        logger.info(f"Re-added isolation rules between {bridge1} and {bridge2}")
        
        state = load_state()
        for v in state['vpcs']:
            if v['name'] in [vpc1_name, vpc2_name]:
                v['peerings'] = [p for p in v.get('peerings', []) 
                               if not (p['vpc1'] in [vpc1_name, vpc2_name] and 
                                      p['vpc2'] in [vpc1_name, vpc2_name])]
        save_state(state)
        
        logger.info(f"Peering deleted between '{vpc1_name}' and '{vpc2_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete peering: {e}")
        return False