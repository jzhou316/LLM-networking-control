import json
import os

class DatasetHandler:
    def __init__(self, file_path='data/results.json'):
        self.file_path = file_path

    # Function to load configurations from the file
    def load_configurations(self):
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, 'r') as file:
            return json.load(file)

    # Function to save configurations to the file
    def save_configurations(self, configurations):
        with open(self.file_path, 'w') as file:
            json.dump(configurations, file, indent=4)

    # Function to insert a new configuration
    def insert_configuration(self, nl_request, json_config, yang_status, modules, latency, iterations, comments=None):
        # Iterations records number of times an error log prompt was sent to the API
        configurations = self.load_configurations()
        configurations.append({"nl_request": nl_request, "yang_config": json_config, "yang_modules": modules, "yang_status": yang_status, "latency": latency, "iterations": iterations, "comments": comments})
        self.save_configurations(configurations)

    # Function to convert string to dict
    def str_to_dict(self, str):
        return json.loads(str)