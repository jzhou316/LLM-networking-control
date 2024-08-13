from json import dump, loads
import requests, os

class NetworkHandler:
    def __init__(self):
        pass

    def get_config_db_network_state(self, device):
        response = requests.get(f'http://10.10.20.22:6000/get_config_db_network_state/{device}')
        if response.status_code == 200:
            hostname = response.json()["DEVICE_METADATA"]["localhost"]["hostname"]
            local_path = f'configs/sonic_configs/{hostname}/config_db.json'
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=128):
                    f.write(chunk)
            return True, f'{local_path}'
        else:
            error_message = response.json().get("error", "Unknown error")
            return False, f'Error: {response.status_code} - {error_message}' 
    
    def get_frr_network_state(self, device, hostname):
        response = requests.get(f'http://10.10.20.22:6000/get_frr_network_state/{device}')
        if response.status_code == 200:
            local_path = f'configs/sonic_configs/{hostname}/frr.txt'
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=128):
                    f.write(chunk)
            return True, f'{local_path}'
        else:
            error_message = response.json().get("error", "Unknown error")
            return False, f'Error: {response.status_code} - {error_message}'
    
    def update_network_state(self, device, config):
        config_path = f'sonic_configs/{device}_config_db.json'
        with open(config_path, 'w') as f:
            dump(loads(config), f, indent=4)
        send_endpoint = f'http://10.10.20.22:5000/update_network_state/{device}'
        with open(config_path, 'rb') as f:
            response = requests.post(send_endpoint, files={'file': f})
        if response.status_code == 200:
            return f'Successfully updated {device} config'
        else:
            error_message = response.json().get("error")
            return f'Error: {response.status_code} - {error_message}'