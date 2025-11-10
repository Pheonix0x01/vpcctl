#!/bin/bash

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "Firewall Policy Test"
echo "========================================="

echo -e "\n[1/6] Creating VPC and subnet..."
sudo uv run vpcctl create-vpc --name vpc1 --cidr 10.0.0.0/16
sudo uv run vpcctl create-subnet --vpc vpc1 --name public1 --cidr 10.0.1.0/24 --type public

echo -e "\n[2/6] Starting HTTP server on port 8080..."
sudo uv run vpcctl exec --vpc vpc1 --subnet public1 -- python3 -m http.server 8080 > /dev/null 2>&1 &
SERVER_PID=$!
sleep 2

echo -e "\n[3/6] Testing port 8080 before firewall (should work)..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet public1 -- timeout 2 bash -c "echo > /dev/tcp/10.0.1.1/8080" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Port 8080 accessible before firewall"
else
    echo -e "${RED}✗${NC} Port 8080 not accessible before firewall"
fi

echo -e "\n[4/6] Applying firewall policy..."
cat > /tmp/test-policy.json << 'EOF'
{
  "subnet": "10.0.1.0/24",
  "ingress": [
    {"port": 22, "protocol": "tcp", "action": "deny"}
  ]
}
EOF

sudo uv run vpcctl apply-policy --vpc vpc1 --subnet public1 --file /tmp/test-policy.json

echo -e "\n[5/6] Testing port 22 after firewall (should be blocked)..."
if sudo uv run vpcctl exec --vpc vpc1 --subnet public1 -- timeout 2 bash -c "echo > /dev/tcp/10.0.1.1/22" 2>/dev/null; then
    echo -e "${RED}✗${NC} Port 22 not blocked by firewall"
else
    echo -e "${GREEN}✓${NC} Port 22 correctly blocked by firewall"
fi

echo -e "\n[6/6] Cleaning up..."
sudo kill $SERVER_PID 2>/dev/null || true
rm /tmp/test-policy.json

echo -e "\n========================================="
echo "Test completed!"
echo "========================================="