import argparse
import sys
from . import utils
from . import vpc
from . import subnet
from . import peering
from . import firewall

def main():
    utils.check_root()
    
    if 'exec' in sys.argv:
        exec_index = sys.argv.index('exec')
        
        parser = argparse.ArgumentParser()
        parser.add_argument('--verbose', '-v', action='store_true')
        parser.add_argument('command', nargs='?')
        parser.add_argument('--vpc', required=True)
        parser.add_argument('--subnet', required=True)
        
        args, unknown = parser.parse_known_args(sys.argv[1:])
        
        command_parts = []
        for i in range(exec_index + 1, len(sys.argv)):
            arg = sys.argv[i]
            if arg not in ['--vpc', '--subnet'] and not (i > 0 and sys.argv[i-1] in ['--vpc', '--subnet']):
                command_parts.append(arg)
        
        subnet_obj = utils.get_subnet(args.vpc, args.subnet)
        if not subnet_obj:
            utils.logger.error(f"Subnet '{args.subnet}' not found in VPC '{args.vpc}'")
            sys.exit(1)
        
        namespace = subnet_obj['namespace']
        cmd = ' '.join(command_parts)
        
        if not cmd:
            utils.logger.error("No command specified for exec")
            sys.exit(1)
        
        result = utils.run_command(f"ip netns exec {namespace} {cmd}", check=False)
        print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        sys.exit(result.returncode)
    
    parser = argparse.ArgumentParser(
        description='VPCctl - Linux VPC management using network primitives',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    vpc_create = subparsers.add_parser('create-vpc', help='Create a new VPC')
    vpc_create.add_argument('--name', required=True, help='VPC name')
    vpc_create.add_argument('--cidr', required=True, help='VPC CIDR block (e.g., 10.0.0.0/16)')
    
    vpc_delete = subparsers.add_parser('delete-vpc', help='Delete a VPC')
    vpc_delete.add_argument('--name', required=True, help='VPC name')
    
    subparsers.add_parser('list-vpcs', help='List all VPCs')
    
    subnet_create = subparsers.add_parser('create-subnet', help='Create a subnet')
    subnet_create.add_argument('--vpc', required=True, help='VPC name')
    subnet_create.add_argument('--name', required=True, help='Subnet name')
    subnet_create.add_argument('--cidr', required=True, help='Subnet CIDR block')
    subnet_create.add_argument('--type', required=True, choices=['public', 'private'], help='Subnet type')
    
    subnet_delete = subparsers.add_parser('delete-subnet', help='Delete a subnet')
    subnet_delete.add_argument('--vpc', required=True, help='VPC name')
    subnet_delete.add_argument('--name', required=True, help='Subnet name')
    
    subnet_list = subparsers.add_parser('list-subnets', help='List subnets in a VPC')
    subnet_list.add_argument('--vpc', required=True, help='VPC name')
    
    peering_create = subparsers.add_parser('create-peering', help='Create VPC peering')
    peering_create.add_argument('--vpc1', required=True, help='First VPC name')
    peering_create.add_argument('--vpc2', required=True, help='Second VPC name')
    
    peering_delete = subparsers.add_parser('delete-peering', help='Delete VPC peering')
    peering_delete.add_argument('--vpc1', required=True, help='First VPC name')
    peering_delete.add_argument('--vpc2', required=True, help='Second VPC name')
    
    policy_apply = subparsers.add_parser('apply-policy', help='Apply firewall policy to subnet')
    policy_apply.add_argument('--vpc', required=True, help='VPC name')
    policy_apply.add_argument('--subnet', required=True, help='Subnet name')
    policy_apply.add_argument('--file', required=True, help='Policy file path')
    
    policy_clear = subparsers.add_parser('clear-policy', help='Clear firewall policy from subnet')
    policy_clear.add_argument('--vpc', required=True, help='VPC name')
    policy_clear.add_argument('--subnet', required=True, help='Subnet name')
    
    args = parser.parse_args()
    
    if args.verbose:
        utils.logger.setLevel('DEBUG')
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'create-vpc':
            success = vpc.create_vpc(args.name, args.cidr)
            sys.exit(0 if success else 1)
            
        elif args.command == 'delete-vpc':
            success = vpc.delete_vpc(args.name)
            sys.exit(0 if success else 1)
            
        elif args.command == 'list-vpcs':
            vpc.list_vpcs()
            sys.exit(0)
            
        elif args.command == 'create-subnet':
            success = subnet.create_subnet(args.vpc, args.name, args.cidr, args.type)
            sys.exit(0 if success else 1)
            
        elif args.command == 'delete-subnet':
            success = subnet.delete_subnet(args.vpc, args.name)
            sys.exit(0 if success else 1)
            
        elif args.command == 'list-subnets':
            subnet.list_subnets(args.vpc)
            sys.exit(0)
            
        elif args.command == 'create-peering':
            success = peering.create_peering(args.vpc1, args.vpc2)
            sys.exit(0 if success else 1)
            
        elif args.command == 'delete-peering':
            success = peering.delete_peering(args.vpc1, args.vpc2)
            sys.exit(0 if success else 1)
            
        elif args.command == 'apply-policy':
            success = firewall.apply_policy(args.vpc, args.subnet, args.file)
            sys.exit(0 if success else 1)
            
        elif args.command == 'clear-policy':
            success = firewall.clear_policy(args.vpc, args.subnet)
            sys.exit(0 if success else 1)
            
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        utils.logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        utils.logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()