import ipaddress
from fastapi import HTTPException

class NetworkState:
    def __init__(self, subnet_mask: str = "255.255.255.0", base_ip: str = "10.0.0.0"):
        self.subnet_mask = subnet_mask
        self.base_ip = base_ip
        self.total_ips, self.pool_range = self.calculate_pool(subnet_mask)

    def calculate_pool(self, subnet_mask: str):
        try:
            net = ipaddress.IPv4Network(f"{self.base_ip}/{subnet_mask}", strict=False)

            total_hosts = net.num_addresses - 2  # remove network + broadcast

            first_ip = net.network_address + 1
            last_ip = net.broadcast_address - 1

            return total_hosts, f"{first_ip} - {last_ip}"

        except Exception:
            return 254, f"{self.base_ip}.1 - {self.base_ip}.254"

    def update_subnet(self, device_ip: str, subnet_mask: str):
        net = ipaddress.IPv4Network(f"{device_ip}/{subnet_mask}", strict=False)

        self.base_ip = str(net.network_address)
        self.subnet_mask = subnet_mask
        self.total_ips, self.pool_range = self.calculate_pool(subnet_mask)
        

    def validate_subnet_mask(self, mask: str) -> bool:
        try:
            # Convert to network using 0.0.0.0 as base (just for validation)
            ipaddress.IPv4Network(f"0.0.0.0/{mask}", strict=False)
            return True
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid subnet mask: {mask}")
        
network_state = NetworkState()