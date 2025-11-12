#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "VPC Peering Test"
echo "========================================="

echo -e "\n[1/8] Creating VPC 'vpc1' with CIDR 10.1.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.1.0.0/16

echo -e "\n[2/8] Creating subnet 'subnet1' in vpc1 with CIDR 10.1.1.0/24..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name subnet1 --cidr 10.1.1.0/24 --type public

echo -e "\n[3/8] Creating VPC 'vpc2' with CIDR 10.2.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc2 --cidr 10.2.0.0/16

echo -e "\n[4/8] Creating subnet 'subnet2' in vpc2 with CIDR 10.2.1.0/24..."
sudo uv run vpcctl create-subnet --vpc vpc2 --name subnet2 --cidr 10.2.1.0/24 --type public

echo -e "\n[5/8] Verifying VPCs are isolated before peering..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet subnet1 ping -c 2 -W 2 10.2.1.2 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} VPCs should be isolated before peering"
else
    echo -e "${GREEN}✓${NC} VPCs are isolated before peering"
fi

echo -e "\n[6/8] Creating peering between vpc1 and vpc2..."
sudo uv run vpcctl create-peering --vpc1 vpc1 --vpc2 vpc2

echo -e "\n[7/8] Testing connectivity: vpc1 should reach vpc2..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet subnet1 ping -c 2 -W 2 10.2.1.2 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} vpc1 can reach vpc2 after peering"
else
    echo -e "${RED}✗${NC} vpc1 cannot reach vpc2 after peering"
fi

echo -e "\n[8/8] Testing connectivity: vpc2 should reach vpc1..."
if sudo uv run vpcctl exec --vpc vpc2 --subnet subnet2 ping -c 2 -W 2 10.1.1.2 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} vpc2 can reach vpc1 after peering"
else
    echo -e "${RED}✗${NC} vpc2 cannot reach vpc1 after peering"
fi

echo -e "\n========================================="
echo "Peering test completed!"
echo "========================================="