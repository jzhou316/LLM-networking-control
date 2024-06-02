from flask import Flask, send_file, request, jsonify
from lib.leaf_spine import *
import yaml

app = Flask(__name__)
UPLOAD_FOLDER = 'sonic_configs'

# Open and load YAML file
# Equivalent to ssh -l cisco <ip> -p <port>
yaml_path = 'lib/leaf_spine.yaml'
with open(yaml_path, 'r') as file:
    devices_data = yaml.safe_load(file)
    devices_data = devices_data['devices']

# Represents the state of each network node
devices = {'S0': '', 'S1': '', 'L0': '', 'L1': ''}

@app.route('/get_config_db_network_state/<device>', methods=['GET'])
def get_config_db_network_state(device):
    if device in devices:
        directory_path = f"configs/sonic_configs/{device}/"
        os.makedirs(directory_path, exist_ok=True)
        file_path = os.path.join(directory_path, "config_db.json")
        config_info = devices_data[device]['connections']['cli']
        save_cfg_locally(config_info['ip'], config_info['port'], file_path)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404

@app.route('/get_frr_network_state/<device>', methods=['GET'])
def get_frr_network_state(device):
    if device in devices:
        directory_path = f"configs/sonic_configs/{device}/"
        os.makedirs(directory_path, exist_ok=True)
        file_path = os.path.join(directory_path, "frr.conf")
        config_info = devices_data[device]['connections']['cli']
        config_data = fetch_frr_config_via_ssh(config_info['ip'], config_info['port'])
        with open(file_path, 'w') as file:
            file.write(config_data)
            print(f"Configuration written to {file_path}")
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404

@app.route('/update_network_state/<device>', methods=['POST'])
def update_network_state(device):
    config_info = devices_data[device]['connections']['cli']
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = file.filename
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        devices[device].execute('sudo rm ../../etc/sonic/config_db.json')
        copy_file_to_rtr(config_info['ip'], config_info['port'], save_path, 'config_db.json')
        out = devices[device].execute(f'echo y | sudo config load config_db.json; echo y | sudo config save')
        return jsonify({'message': f'File {filename} uploaded successfully'}), 200

if __name__ == "__main__":
    tb = access_device_consoles(yaml_path, devices)
    devices['S0'].execute('sudo config hostname SPINE0')
    devices['S0'].execute('sudo config save -y')
    devices['S1'].execute('sudo config hostname SPINE1')
    devices['S1'].execute('sudo config save -y')
    devices['L0'].execute('sudo config hostname LEAF0')
    devices['L0'].execute('sudo config save -y')
    devices['L1'].execute('sudo config hostname LEAF1')
    devices['L1'].execute('sudo config save -y')
    app.run(host='0.0.0.0', port=6000)
