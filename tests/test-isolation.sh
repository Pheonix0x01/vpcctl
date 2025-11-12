#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "VPC Isolation Test"
echo "========================================="

echo -e "\n[1/6] Creating VPC 'vpc1' with CIDR 10.1.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.1.0.0/16

echo -e "\n[2/6] Creating subnet 'subnet1' in vpc1 with CIDR 10.1.1.0/24..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name subnet1 --cidr 10.1.1.0/24 --type public

echo -e "\n[3/6] Creating VPC 'vpc2' with CIDR 10.2.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc2 --cidr 10.2.0.0/16

echo -e "\n[4/6] Creating subnet 'subnet2' in vpc2 with CIDR 10.2.1.0/24..."
sudo uv run vpcctl create-subnet --vpc vpc2 --name subnet2 --cidr 10.2.1.0/24 --type public

echo -e "\n[5/6] Testing isolation: vpc1 should NOT reach vpc2..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet subnet1 ping -c 2 -W 2 10.2.1.2 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} VPCs are NOT isolated (vpc1 can reach vpc2)"
else
    echo -e "${GREEN}✓${NC} VPCs are properly isolated"
fi

echo -e "\n[6/6] Testing isolation: vpc2 should NOT reach vpc1..."
if sudo uv run vpcctl exec --vpc vpc2 --subnet subnet2 ping -c 2 -W 2 10.1.1.2 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} VPCs are NOT isolated (vpc2 can reach vpc1)"
else
    echo -e "${GREEN}✓${NC} VPCs are properly isolated"
fi

echo -e "\n========================================="
echo "Isolation test completed!"
echo "========================================="