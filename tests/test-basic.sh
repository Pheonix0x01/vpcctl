#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "Basic Connectivity Test"
echo "========================================="

echo -e "\n[1/7] Creating VPC 'vpc1' with CIDR 10.0.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.0.0.0/16

echo -e "\n[2/7] Creating public subnet 'public1' with CIDR 10.0.1.0/24..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name public1 --cidr 10.0.1.0/24 --type public

echo -e "\n[3/7] Creating private subnet 'private1' with CIDR 10.0.2.0/24..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name private1 --cidr 10.0.2.0/24 --type private

echo -e "\n[4/7] Testing subnet-to-subnet communication..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet public1 -- ping -c 2 -W 2 10.0.2.1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Public subnet can reach private subnet"
else
    echo -e "${RED}✗${NC} Public subnet cannot reach private subnet"
fi

echo -e "\n[5/7] Testing private-to-public communication..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet private1 -- ping -c 2 -W 2 10.0.1.1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Private subnet can reach public subnet"
else
    echo -e "${RED}✗${NC} Private subnet cannot reach public subnet"
fi

echo -e "\n[6/7] Testing public subnet internet access..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet public1 -- ping -c 2 -W 2 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Public subnet has internet access"
else
    echo -e "${RED}✗${NC} Public subnet does not have internet access"
fi

echo -e "\n[7/7] Testing private subnet NO internet access..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet private1 -- ping -c 2 -W 2 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Private subnet has internet access (should not!)"
else
    echo -e "${GREEN}✓${NC} Private subnet correctly has no internet access"
fi

echo -e "\n========================================="
echo "Test completed!"
echo "========================================="