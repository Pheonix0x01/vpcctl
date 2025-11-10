#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "VPC Isolation Test"
echo "========================================="

echo -e "\n[1/5] Creating VPC 'vpc1' with CIDR 10.0.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.0.0.0/16

echo -e "\n[2/5] Creating subnet in vpc1..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name subnet1 --cidr 10.0.1.0/24 --type public

echo -e "\n[3/5] Creating VPC 'vpc2' with CIDR 10.1.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc2 --cidr 10.1.0.0/16

echo -e "\n[4/5] Creating subnet in vpc2..."
sudo uv run vpcctl create-subnet --vpc vpc2 --name subnet1 --cidr 10.1.1.0/24 --type public

echo -e "\n[5/5] Testing isolation - vpc1 should NOT reach vpc2..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet subnet1 -- ping -c 2 -W 2 10.1.1.1 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} VPCs are NOT isolated (should be isolated!)"
else
    echo -e "${GREEN}✓${NC} VPCs are properly isolated"
fi

echo -e "\n========================================="
echo "Test completed!"
echo "========================================="