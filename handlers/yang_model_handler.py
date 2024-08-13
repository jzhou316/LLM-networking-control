from sonic_yang import SonicYang
from json import dumps, loads, dump
from contextlib import redirect_stdout, redirect_stderr
import tempfile, os, io

class YangModelHandler:
    def __init__(self, yang_dir):
        self.yang_dir = yang_dir
        self.sy = SonicYang(self.yang_dir)
        self.sy.loadYangModel()

    def get_yang_module_full(self, module_name: str):
        mod = self.sy._get_module(module_name)
        return self.sy._get_module_tree(mod, format="JSON")
    
    def get_yang_module_simplified(self, module_name: str, depth: int = 6):
        mod = self.sy._get_module(module_name)
        return dumps(self.sy.get_simplified_schema(mod, depth), indent=2)
    
    def get_all_module_names(self):
        return [module.name() for module in self.sy.ctx.__iter__()]
    
    def truncate_lists_in_dict(self, data, truncate_lists: bool = True):
        if not truncate_lists:
            return data
        if isinstance(data, dict):
            return {key: self.truncate_lists_in_dict(value) for key, value in data.items()}
        elif isinstance(data, list) and len(data) >= 10:
            return data[:5] + ["..."]
        else:
            return data
    
    def yang_to_configdb(self, json_str: str):
        translation = self.sy.XlateYangToConfigDB(loads(json_str))
        return dumps(translation, indent=4)

    def configdb_to_yang(self, json_str: str):
        translation = self.sy.loadData(loads(json_str), print=True)
        return dumps(translation, indent=4)
    
    def load_data_file(self, datadict: dict):
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.json') as tmpfile:
            dump(datadict, tmpfile)
            tmpfile_path = tmpfile.name

        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.sy._load_data_file(tmpfile_path)
        except:
            output_stdout = stdout.getvalue()
            output_stderr = stderr.getvalue()
            if output_stdout.strip() != "":
                print(output_stdout)
                newline_index = output_stdout.find("\n")
                error_msg = output_stdout[newline_index+1:] if newline_index != -1 else output_stdout
                return (False, error_msg)
            if output_stderr.strip() != "":
                print(output_stderr)
                newline_index = output_stderr.find("\n")
                error_msg = output_stderr[newline_index+1:] if newline_index != -1 else output_stderr
                return (False, error_msg)

        os.remove(tmpfile_path)
        return (True, "Data file loaded successfully.")
        
    def fix_yang_mismatches(self, data):
        crm_config_fields = [
            "acl_counter_high_threshold", "acl_counter_low_threshold",
            "acl_entry_high_threshold", "acl_entry_low_threshold",
            "acl_group_high_threshold", "acl_group_low_threshold",
            "acl_table_high_threshold", "acl_table_low_threshold",
            "dnat_entry_high_threshold", "dnat_entry_low_threshold",
            "fdb_entry_high_threshold", "fdb_entry_low_threshold",
            "ipmc_entry_high_threshold", "ipmc_entry_low_threshold",
            "ipv4_neighbor_high_threshold", "ipv4_neighbor_low_threshold",
            "ipv4_nexthop_high_threshold", "ipv4_nexthop_low_threshold",
            "ipv4_route_high_threshold", "ipv4_route_low_threshold",
            "ipv6_neighbor_high_threshold", "ipv6_neighbor_low_threshold",
            "ipv6_nexthop_high_threshold", "ipv6_nexthop_low_threshold",
            "ipv6_route_high_threshold", "ipv6_route_low_threshold",
            "nexthop_group_high_threshold", "nexthop_group_low_threshold",
            "nexthop_group_member_high_threshold", "nexthop_group_member_low_threshold",
            "polling_interval", "snat_entry_high_threshold", "snat_entry_low_threshold"
        ]

        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                if key in crm_config_fields or key == "port":
                    # Convert string numbers to integers
                    if isinstance(value, str) and value.isdigit():
                        new_dict[key] = int(value)
                    else:
                        new_dict[key] = value
                else:
                    # Recurse into nested dictionaries
                    new_dict[key] = self.fix_yang_mismatches(value)
            return new_dict
        elif isinstance(data, list):
            # Process each item in the list
            return [self.fix_yang_mismatches(item) for item in data]
        else:
            # If it's not a dictionary or list, return it as is
            return data

    def reverse_fix_yang_mismatches(self, data):
        crm_config_fields = [
            "acl_counter_high_threshold", "acl_counter_low_threshold",
            "acl_entry_high_threshold", "acl_entry_low_threshold",
            "acl_group_high_threshold", "acl_group_low_threshold",
            "acl_table_high_threshold", "acl_table_low_threshold",
            "dnat_entry_high_threshold", "dnat_entry_low_threshold",
            "fdb_entry_high_threshold", "fdb_entry_low_threshold",
            "ipmc_entry_high_threshold", "ipmc_entry_low_threshold",
            "ipv4_neighbor_high_threshold", "ipv4_neighbor_low_threshold",
            "ipv4_nexthop_high_threshold", "ipv4_nexthop_low_threshold",
            "ipv4_route_high_threshold", "ipv4_route_low_threshold",
            "ipv6_neighbor_high_threshold", "ipv6_neighbor_low_threshold",
            "ipv6_nexthop_high_threshold", "ipv6_nexthop_low_threshold",
            "ipv6_route_high_threshold", "ipv6_route_low_threshold",
            "nexthop_group_high_threshold", "nexthop_group_low_threshold",
            "nexthop_group_member_high_threshold", "nexthop_group_member_low_threshold",
            "polling_interval", "snat_entry_high_threshold", "snat_entry_low_threshold"
        ]

        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                if key in crm_config_fields or key == "port":
                    # Convert integers back into strings
                    if isinstance(value, int):
                        new_dict[key] = str(value)
                    else:
                        new_dict[key] = value
                else:
                    # Recurse into nested dictionaries
                    new_dict[key] = self.reverse_fix_yang_mismatches(value)
            return new_dict
        elif isinstance(data, list):
            # Process each item in the list
            return [self.reverse_fix_yang_mismatches(item) for item in data]
        else:
            # If it's not a dictionary or list, return it as is
            return data
  