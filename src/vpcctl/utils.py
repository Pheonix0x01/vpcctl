import os
import sys
import subprocess
import json
import re
import logging
from pathlib import Path

STATE_DIR = Path.home() / ".vpcctl"
STATE_FILE = STATE_DIR / "vpcs.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger = logging.getLogger()
logger.handlers = [handler]

def check_root():
    if os.geteuid() != 0:
        logger.error("This script must be run as root (use sudo)")
        sys.exit(1)

def run_command(cmd, check=True):
    logger.debug(f"Executing: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if check and result.returncode != 0:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Error: {result.stderr}")
        raise RuntimeError(f"Command failed: {result.stderr}")
    
    return result

def validate_cidr(cidr):
    pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
    if not re.match(pattern, cidr):
        return False
    
    ip_part, prefix = cidr.split('/')
    octets = ip_part.split('.')
    
    for octet in octets:
        if int(octet) > 255:
            return False
    
    if int(prefix) > 32:
        return False
    
    return True

def get_default_interface():
    result = run_command("ip route show default", check=True)
    output = result.stdout.strip()
    
    if not output:
        logger.error("No default route found")
        return None
    
    parts = output.split()
    if 'dev' in parts:
        dev_index = parts.index('dev')
        if dev_index + 1 < len(parts):
            return parts[dev_index + 1]
    
    return None

def load_state():
    if not STATE_FILE.exists():
        return {"vpcs": []}
    
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def save_state(data):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    temp_file = STATE_FILE.with_suffix('.tmp')
    with open(temp_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    temp_file.replace(STATE_FILE)

def get_vpc(name):
    state = load_state()
    for vpc in state['vpcs']:
        if vpc['name'] == name:
            return vpc
    return None

def get_subnet(vpc_name, subnet_name):
    vpc = get_vpc(vpc_name)
    if not vpc:
        return None
    
    for subnet in vpc.get('subnets', []):
        if subnet['name'] == subnet_name:
            return subnet
    
    return None