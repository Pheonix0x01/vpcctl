import json
from pathlib import Path
from .utils import (
    logger,
    run_command,
    get_subnet
)

def parse_policy(policy_file):
    policy_path = Path(policy_file)
    
    if not policy_path.exists():
        logger.error(f"Policy file not found: {policy_file}")
        return None
    
    try:
        with open(policy_path, 'r') as f:
            policy = json.load(f)
        
        if 'subnet' not in policy:
            logger.error("Policy must contain 'subnet' field")
            return None
        
        if 'ingress' not in policy:
            logger.error("Policy must contain 'ingress' field")
            return None
        
        for rule in policy['ingress']:
            if 'port' not in rule or 'protocol' not in rule or 'action' not in rule:
                logger.error("Each ingress rule must have 'port', 'protocol', and 'action' fields")
                return None
            
            if rule['action'] not in ['allow', 'deny']:
                logger.error(f"Invalid action '{rule['action']}'. Must be 'allow' or 'deny'")
                return None
        
        logger.info(f"Policy parsed successfully from {policy_file}")
        return policy
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in policy file: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to parse policy: {e}")
        return None

def apply_policy(vpc_name, subnet_name, policy_file):
    policy = parse_policy(policy_file)
    if not policy:
        return False
    
    subnet = get_subnet(vpc_name, subnet_name)
    if not subnet:
        logger.error(f"Subnet '{subnet_name}' not found in VPC '{vpc_name}'")
        return False
    
    namespace = subnet['namespace']
    
    try:
        run_command(f"ip netns exec {namespace} iptables -F INPUT")
        logger.info(f"Flushed existing INPUT rules in {namespace}")
        
        run_command(f"ip netns exec {namespace} iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT")
        logger.info("Added rule to allow established/related connections")
        
        run_command(f"ip netns exec {namespace} iptables -A INPUT -i lo -j ACCEPT")
        logger.info("Added rule to allow loopback traffic")
        
        for rule in policy['ingress']:
            port = rule['port']
            protocol = rule['protocol']
            action = rule['action']
            
            if action == 'allow':
                iptables_action = 'ACCEPT'
            else:
                iptables_action = 'DROP'
            
            run_command(f"ip netns exec {namespace} iptables -A INPUT -p {protocol} --dport {port} -j {iptables_action}")
            logger.info(f"Added rule: {action} {protocol}/{port} in {namespace}")
        
        run_command(f"ip netns exec {namespace} iptables -A INPUT -j DROP")
        logger.info(f"Added default DROP rule in {namespace}")
        
        logger.info(f"Policy applied successfully to subnet '{subnet_name}' in VPC '{vpc_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply policy: {e}")
        return False

def clear_policy(vpc_name, subnet_name):
    subnet = get_subnet(vpc_name, subnet_name)
    if not subnet:
        logger.error(f"Subnet '{subnet_name}' not found in VPC '{vpc_name}'")
        return False
    
    namespace = subnet['namespace']
    
    try:
        run_command(f"ip netns exec {namespace} iptables -F")
        logger.info(f"Flushed all iptables rules in {namespace}")
        
        run_command(f"ip netns exec {namespace} iptables -X")
        logger.info(f"Deleted all custom chains in {namespace}")
        
        run_command(f"ip netns exec {namespace} iptables -P INPUT ACCEPT")
        run_command(f"ip netns exec {namespace} iptables -P FORWARD ACCEPT")
        run_command(f"ip netns exec {namespace} iptables -P OUTPUT ACCEPT")
        logger.info(f"Set default policies to ACCEPT in {namespace}")
        
        logger.info(f"Policy cleared successfully from subnet '{subnet_name}' in VPC '{vpc_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear policy: {e}")
        return False