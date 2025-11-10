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

echo -e "\n[1/5] Deleting network namespaces..."
for ns in $(ip netns list | grep -E '^vpc' | awk '{print $1}'); do
    ip netns del "$ns" 2>/dev/null && echo "  Deleted namespace: $ns" || true
done

echo -e "\n[2/5] Deleting bridges..."
for bridge in $(ip link show type bridge | grep -E '^[0-9]+: br-' | cut -d: -f2 | awk '{print $1}'); do
    ip link del "$bridge" 2>/dev/null && echo "  Deleted bridge: $bridge" || true
done

echo -e "\n[3/5] Flushing iptables NAT rules..."
iptables -t nat -F 2>/dev/null && echo "  NAT rules flushed" || true

echo -e "\n[4/5] Flushing iptables FORWARD rules..."
iptables -F FORWARD 2>/dev/null && echo "  FORWARD rules flushed" || true

echo -e "\n[5/5] Clearing state file..."
mkdir -p state
echo '{"vpcs": []}' > state/vpcs.json && echo "  State file cleared" || true

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}Cleanup completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"