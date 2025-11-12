#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "Firewall Policy Test"
echo "========================================="

echo -e "\n[1/7] Creating VPC 'vpc1' with CIDR 10.0.0.0/16..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.0.0.0/16

echo -e "\n[2/7] Creating public subnet..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name public1 --cidr 10.0.1.0/24 --type public

echo -e "\n[3/7] Creating private subnet..."
sudo uv run vpcctl create-subnet --vpc vpc1 --name private1 --cidr 10.0.2.0/24 --type private

echo -e "\n[4/7] Starting simple HTTP server in private subnet..."
sudo uv run vpcctl exec --vpc vpc1 --subnet private1 python3 -m http.server 8080 > /dev/null 2>&1 &
HTTP_PID=$!
sleep 2

echo -e "\n[5/7] Testing HTTP access before firewall (should work)..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet public1 curl -s -m 2 http://10.0.2.2:8080 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} HTTP accessible before firewall"
else
    echo -e "${RED}✗${NC} HTTP not accessible before firewall"
fi

echo -e "\n[6/7] Applying restrictive firewall policy..."
cat > /tmp/test-policy.yaml << EOF
rules:
  - action: drop
    protocol: tcp
    port: 8080
    direction: ingress
EOF

sudo uv run vpcctl apply-policy --vpc vpc1 --subnet private1 --file /tmp/test-policy.yaml

echo -e "\n[7/7] Testing HTTP access after firewall (should fail)..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet public1 curl -s -m 2 http://10.0.2.2:8080 > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} HTTP still accessible after firewall (firewall not working)"
else
    echo -e "${GREEN}✓${NC} HTTP blocked by firewall"
fi

sudo kill $HTTP_PID 2>/dev/null || true
rm -f /tmp/test-policy.yaml

echo -e "\n========================================="
echo "Firewall test completed!"
echo "========================================="