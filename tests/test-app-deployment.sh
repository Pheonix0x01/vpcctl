#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "Application Deployment Test"
echo "========================================="

echo -e "\n[1/8] Creating VPC 'app-vpc' with CIDR 10.0.0.0/16..."
sudo uv run vpcctl create-vpc --name app-vpc --cidr 10.0.0.0/16

echo -e "\n[2/8] Creating web tier (public subnet)..."
sudo uv run vpcctl create-subnet --vpc app-vpc --name web-tier --cidr 10.0.1.0/24 --type public

echo -e "\n[3/8] Creating app tier (private subnet)..."
sudo uv run vpcctl create-subnet --vpc app-vpc --name app-tier --cidr 10.0.2.0/24 --type private

echo -e "\n[4/8] Creating database tier (private subnet)..."
sudo uv run vpcctl create-subnet --vpc app-vpc --name db-tier --cidr 10.0.3.0/24 --type private

echo -e "\n[5/8] Verifying web tier has internet access..."
if sudo uv run vpcctl exec --vpc app-vpc --subnet web-tier ping -c 2 -W 2 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Web tier has internet access"
else
    echo -e "${RED}✗${NC} Web tier has no internet access"
fi

echo -e "\n[6/8] Verifying app tier has no internet access..."
if sudo uv run vpcctl exec --vpc app-vpc --subnet app-tier ping -c 2 -W 2 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} App tier should not have internet access"
else
    echo -e "${GREEN}✓${NC} App tier correctly has no internet access"
fi

echo -e "\n[7/8] Testing web tier can reach app tier..."
if sudo uv run vpcctl exec --vpc app-vpc --subnet web-tier ping -c 2 -W 2 10.0.2.2 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Web tier can communicate with app tier"
else
    echo -e "${RED}✗${NC} Web tier cannot reach app tier"
fi

echo -e "\n[8/8] Testing app tier can reach db tier..."
if sudo uv run vpcctl exec --vpc app-vpc --subnet app-tier ping -c 2 -W 2 10.0.3.2 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} App tier can communicate with db tier"
else
    echo -e "${RED}✗${NC} App tier cannot reach db tier"
fi

echo -e "\n========================================="
echo "Application deployment test completed!"
echo "========================================="