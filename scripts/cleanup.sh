#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "========================================="
echo "VPCctl Cleanup Script"
echo "========================================="

echo -e "\n${YELLOW}WARNING: This will delete ALL vpcctl resources!${NC}"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo -e "\n[1/6] Deleting network namespaces..."
for ns in $(ip netns list 2>/dev/null | awk '{print $1}'); do
    if [[ "$ns" == vpc* ]]; then
        ip netns del "$ns" 2>/dev/null && echo "  Deleted namespace: $ns" || true
    fi
done

echo -e "\n[2/6] Deleting bridges..."
for bridge in $(ip link show type bridge 2>/dev/null | grep -oP 'br-\S+'); do
    ip link del "$bridge" 2>/dev/null && echo "  Deleted bridge: $bridge" || true
done

echo -e "\n[3/6] Deleting veth pairs..."
for veth in $(ip link show 2>/dev/null | grep -oP 'v[bn]-\S+'); do
    ip link del "$veth" 2>/dev/null && echo "  Deleted veth: $veth" || true
done

echo -e "\n[4/6] Flushing iptables NAT rules..."
iptables -t nat -F 2>/dev/null && echo "  NAT rules flushed" || true

echo -e "\n[5/6] Flushing iptables FORWARD rules..."
iptables -F FORWARD 2>/dev/null && echo "  FORWARD rules flushed" || true

echo -e "\n[6/6] Clearing state file..."
rm -f ~/.vpcctl/vpcs.json 2>/dev/null && echo "  State file deleted" || true

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}Cleanup completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"