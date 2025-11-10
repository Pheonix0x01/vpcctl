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
    
    if not vpc1:
        logger.error(f"VPC '{vpc1_name}' not found")
        return False
    
    if not vpc2:
        logger.error(f"VPC '{vpc2_name}' not found")
        return False
    
    if vpc1_name == vpc2_name:
        logger.error("Cannot peer a VPC with itself")
        return False
    
    for peering in vpc1.get('peerings', []):
        if peering['peer_vpc'] == vpc2_name:
            logger.error(f"Peering already exists between '{vpc1_name}' and '{vpc2_name}'")
            return False
    
    peer1_name = f"peer-{vpc1_name}-{vpc2_name}-1"
    peer2_name = f"peer-{vpc1_name}-{vpc2_name}-2"
    bridge1 = vpc1['bridge']
    bridge2 = vpc2['bridge']
    vpc1_cidr = vpc1['cidr']
    vpc2_cidr = vpc2['cidr']
    
    try:
        run_command(f"ip link add {peer1_name} type veth peer name {peer2_name}")
        logger.info(f"Created veth pair {peer1_name} <-> {peer2_name}")
        
        run_command(f"ip link set {peer1_name} master {bridge1}")
        logger.info(f"Attached {peer1_name} to bridge {bridge1}")
        
        run_command(f"ip link set {peer2_name} master {bridge2}")
        logger.info(f"Attached {peer2_name} to bridge {bridge2}")
        
        run_command(f"ip link set {peer1_name} up")
        logger.info(f"Brought up {peer1_name}")
        
        run_command(f"ip link set {peer2_name} up")
        logger.info(f"Brought up {peer2_name}")
        
        run_command(f"ip route add {vpc2_cidr} dev {bridge1}", check=False)
        logger.info(f"Added route to {vpc2_cidr} via {bridge1}")
        
        run_command(f"ip route add {vpc1_cidr} dev {bridge2}", check=False)
        logger.info(f"Added route to {vpc1_cidr} via {bridge2}")
        
        bridge1_ip = vpc1['bridge_ip']
        bridge2_ip = vpc2['bridge_ip']
        
        for subnet1 in vpc1.get('subnets', []):
            ns1 = subnet1['namespace']
            run_command(f"ip netns exec {ns1} ip route add {vpc2_cidr} via {bridge1_ip}", check=False)
            logger.info(f"Added route in {ns1}: {vpc2_cidr} via {bridge1_ip}")
            
            for subnet2 in vpc2.get('subnets', []):
                cidr2 = subnet2['cidr']
                run_command(f"ip netns exec {ns1} ip route add {cidr2} via {bridge1_ip}", check=False)
        
        for subnet2 in vpc2.get('subnets', []):
            ns2 = subnet2['namespace']
            run_command(f"ip netns exec {ns2} ip route add {vpc1_cidr} via {bridge2_ip}", check=False)
            logger.info(f"Added route in {ns2}: {vpc1_cidr} via {bridge2_ip}")
            
            for subnet1 in vpc1.get('subnets', []):
                cidr1 = subnet1['cidr']
                run_command(f"ip netns exec {ns2} ip route add {cidr1} via {bridge2_ip}", check=False)
        
        peering_data_vpc1 = {
            "peer_vpc": vpc2_name,
            "veth_local": peer1_name,
            "veth_peer": peer2_name
        }
        
        peering_data_vpc2 = {
            "peer_vpc": vpc1_name,
            "veth_local": peer2_name,
            "veth_peer": peer1_name
        }
        
        state = load_state()
        for v in state['vpcs']:
            if v['name'] == vpc1_name:
                v['peerings'].append(peering_data_vpc1)
            elif v['name'] == vpc2_name:
                v['peerings'].append(peering_data_vpc2)
        save_state(state)
        
        logger.info(f"Peering created successfully between '{vpc1_name}' and '{vpc2_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create peering: {e}")
        run_command(f"ip link del {peer1_name}", check=False)
        return False

def delete_peering(vpc1_name, vpc2_name):
    vpc1 = get_vpc(vpc1_name)
    vpc2 = get_vpc(vpc2_name)
    
    if not vpc1:
        logger.error(f"VPC '{vpc1_name}' not found")
        return False
    
    if not vpc2:
        logger.error(f"VPC '{vpc2_name}' not found")
        return False
    
    peering1 = None
    for p in vpc1.get('peerings', []):
        if p['peer_vpc'] == vpc2_name:
            peering1 = p
            break
    
    if not peering1:
        logger.error(f"No peering found between '{vpc1_name}' and '{vpc2_name}'")
        return False
    
    veth_local = peering1['veth_local']
    bridge1 = vpc1['bridge']
    bridge2 = vpc2['bridge']
    vpc1_cidr = vpc1['cidr']
    vpc2_cidr = vpc2['cidr']
    bridge1_ip = vpc1['bridge_ip']
    bridge2_ip = vpc2['bridge_ip']
    
    try:
        run_command(f"ip link del {veth_local}", check=False)
        logger.info(f"Deleted veth {veth_local}")
        
        run_command(f"ip route del {vpc2_cidr} dev {bridge1}", check=False)
        logger.info(f"Deleted route to {vpc2_cidr} via {bridge1}")
        
        run_command(f"ip route del {vpc1_cidr} dev {bridge2}", check=False)
        logger.info(f"Deleted route to {vpc1_cidr} via {bridge2}")
        
        for subnet1 in vpc1.get('subnets', []):
            ns1 = subnet1['namespace']
            run_command(f"ip netns exec {ns1} ip route del {vpc2_cidr} via {bridge1_ip}", check=False)
            
            for subnet2 in vpc2.get('subnets', []):
                cidr2 = subnet2['cidr']
                run_command(f"ip netns exec {ns1} ip route del {cidr2} via {bridge1_ip}", check=False)
        
        for subnet2 in vpc2.get('subnets', []):
            ns2 = subnet2['namespace']
            run_command(f"ip netns exec {ns2} ip route del {vpc1_cidr} via {bridge2_ip}", check=False)
            
            for subnet1 in vpc1.get('subnets', []):
                cidr1 = subnet1['cidr']
                run_command(f"ip netns exec {ns2} ip route del {cidr1} via {bridge2_ip}", check=False)
        
        state = load_state()
        for v in state['vpcs']:
            if v['name'] == vpc1_name:
                v['peerings'] = [p for p in v['peerings'] if p['peer_vpc'] != vpc2_name]
            elif v['name'] == vpc2_name:
                v['peerings'] = [p for p in v['peerings'] if p['peer_vpc'] != vpc1_name]
        save_state(state)
        
        logger.info(f"Peering deleted successfully between '{vpc1_name}' and '{vpc2_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete peering: {e}")
        return False