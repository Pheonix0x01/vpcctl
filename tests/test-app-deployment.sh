#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "Application Deployment Test"
echo "========================================="

echo -e "\n[1/5] Creating VPC with public and private subnets..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.0.0.0/16
sudo uv run vpcctl create-subnet --vpc vpc1 --name public1 --cidr 10.0.1.0/24 --type public
sudo uv run vpcctl create-subnet --vpc vpc1 --name private1 --cidr 10.0.2.0/24 --type private

echo -e "\n[2/5] Deploying HTTP server in public subnet..."
sudo uv run vpcctl exec --vpc vpc1 --subnet public1 -- python3 -m http.server 8080 > /dev/null 2>&1 &
PUBLIC_PID=$!
sleep 2

echo -e "\n[3/5] Deploying HTTP server in private subnet..."
sudo uv run vpcctl exec --vpc vpc1 --subnet private1 -- python3 -m http.server 8081 > /dev/null 2>&1 &
PRIVATE_PID=$!
sleep 2

echo -e "\n[4/5] Testing access to public subnet from host..."
if curl -s --connect-timeout 2 http://10.0.1.1:8080 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Public subnet accessible from host"
else
    echo -e "${RED}✗${NC} Public subnet not accessible from host"
fi

echo -e "\n[5/5] Testing access to private subnet from host (should fail)..."
if curl -s --connect-timeout 2 http://10.0.2.1:8081 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Private subnet accessible from host (should not be!)"
else
    echo -e "${GREEN}✓${NC} Private subnet correctly not accessible from host"
fi

echo -e "\nCleaning up..."
sudo kill $PUBLIC_PID $PRIVATE_PID 2>/dev/null || true

echo -e "\n========================================="
echo "Test completed!"
echo "========================================="