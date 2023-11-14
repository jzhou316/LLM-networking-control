import re

def parse_intent(intent: str):
    # Split the intent into individual operations or policies
    statements = re.split(r';\n', intent)

    for statement in statements:
        if statement.startswith('add') or statement.startswith('remove'):
            return parse_operation(statement)
        elif statement.startswith('set') or statement.startswith('allow') or statement.startswith('block'):
            return parse_policy(statement)
        else:
            print(f"Invalid Nile: {intent}")

def parse_operation(operation_statement: str):
    add_endpoint = re.match(r"add endpoint\('([^']+)'\) to group\('([^']+)'\)", operation_statement)
    remove_endpoint = re.match(r"remove endpoint\('([^']+)'\) from group\('([^']+)'\)", operation_statement)
    add_link = re.match(r"add link\('endpoint\('([^']+)'\)'\, 'endpoint\('([^']+)'\)'\)", operation_statement)
    remove_link = re.match(r"remove link\('endpoint\('([^']+)'\)'\, 'endpoint\('([^']+)'\)'\)", operation_statement)
    add_group = re.match(r"add group\('([^']+)'\)", operation_statement)
    remove_group = re.match(r"remove group\('([^']+)'\)", operation_statement)

    result_dict = {}
    # Create dictionary to represent the intent
    if add_endpoint:
        result_dict['operation'] = "add_endpoint"
        result_dict['endpoint'] = add_endpoint.group(1)
        result_dict['group'] = add_endpoint.group(2)
    elif remove_endpoint:
        result_dict['operation'] = "remove_endpoint"
        result_dict['endpoint'] = remove_endpoint.group(1)
        result_dict['group'] = remove_endpoint.group(2)
    elif add_link:
        result_dict['operation'] = "add_link"
        result_dict['source'] = add_link.group(1)
        result_dict['destination'] = add_link.group(2)
    elif remove_link:
        result_dict['operation'] = "remove_link"
        result_dict['source'] = remove_link.group(1)
        result_dict['destination'] = remove_link.group(2)
    elif add_group:
        result_dict['operation'] = "add_group"
        result_dict['group'] = add_group.group(1)
    elif remove_group:
        result_dict['operation'] = "remove_group"
        result_dict['group'] = remove_group.group(1)
    else:
        result_dict['operation'] = "unparsable"
        result_dict['statement'] = operation_statement

    return result_dict

def parse_policy(policy_statement: str):
    # for link\('endpoint\('([^']+)'\)'\, 'endpoint\('([^']+)'\)'\)({from hour\((\d{2}:\d{2})\) to hour\((\d{2}:\d{2})\)})?
    time_interval = re.search(r"start hour\('(\d{2}:\d{2})'\) end hour\('(\d{2}:\d{2})'\)", policy_statement)
    set_bandwidth_link = re.match(r"set bandwidth\(('max'|'min'), (\d+), ('gbps'|'mbps')\) for link\(endpoint\('([^']+)'\), endpoint\('([^']+)'\)\)(?: ?)", policy_statement)
    set_bandwidth_endpoint = re.match(r"set bandwidth\(('max'|'min'), (\d+), ('gbps'|'mbps')\) for endpoint\('([^']+)'\)(?: ?)", policy_statement)
    set_bandwidth_group = re.match(r"set bandwidth\(('max'|'min'), (\d+), ('gbps'|'mbps')\) for group\('([^']+)'\)(?: ?)", policy_statement)
    allow_traffic = re.match(r"allow traffic\('([^']+)'\) from (endpoint|group)\('([^']+)'\) to (endpoint|group)\('([^']+)'\)(?: ?)", policy_statement)
    block_traffic = re.match(r"block traffic\('([^']+)'\) from (endpoint|group)\('([^']+)'\) to (endpoint|group)\('([^']+)'\)(?: ?)", policy_statement)

    result_dict = {}
    
    if set_bandwidth_link:
        result_dict['policy_type'] = 'set_bandwidth'
        result_dict['max_min'] = set_bandwidth_link.group(1)
        result_dict['bw_amt'] = set_bandwidth_link.group(2)
        result_dict['units'] = set_bandwidth_link.group(3)
        result_dict['link_source'] = set_bandwidth_link.group(4)
        result_dict['link_destination'] = set_bandwidth_link.group(5)
        if time_interval != None:
            result_dict['start_hour'] = time_interval.group(1)
            result_dict['end_hour'] = time_interval.group(2)
    elif set_bandwidth_endpoint:
        result_dict['policy_type'] = 'set_bandwidth'
        result_dict['max_min'] = set_bandwidth_endpoint.group(1)
        result_dict['bw_amt'] = set_bandwidth_endpoint.group(2)
        result_dict['units'] = set_bandwidth_endpoint.group(3)
        result_dict['endpoint'] = set_bandwidth_endpoint.group(4)
        if time_interval != None:
            result_dict['start_hour'] = time_interval.group(1)
            result_dict['end_hour'] = time_interval.group(2)
    elif set_bandwidth_group:
        result_dict['policy_type'] = 'set_bandwidth'
        result_dict['max_min'] = set_bandwidth_group.group(1)
        result_dict['bw_amt'] = set_bandwidth_group.group(2)
        result_dict['units'] = set_bandwidth_group.group(3)
        result_dict['group'] = set_bandwidth_group.group(4)
        if time_interval != None:
            result_dict['start_hour'] = time_interval.group(1)
            result_dict['end_hour'] = time_interval.group(2)
    elif allow_traffic:
        result_dict['policy_type'] = 'allow_traffic'
        result_dict['traffic_type'] = allow_traffic.group(1)
        result_dict['source_type'] = allow_traffic.group(2)
        result_dict['source'] = allow_traffic.group(3)
        result_dict['destination_type'] = allow_traffic.group(4)
        result_dict['destination'] = allow_traffic.group(5)
        if time_interval != None:
            result_dict['start_hour'] = time_interval.group(1)
            result_dict['end_hour'] = time_interval.group(2)
    elif block_traffic:
        result_dict['policy_type'] = 'block_traffic'
        result_dict['traffic_type'] = block_traffic.group(1)
        result_dict['source_type'] = block_traffic.group(2)
        result_dict['source'] = block_traffic.group(3)
        result_dict['destination_type'] = block_traffic.group(4)
        result_dict['destination'] = block_traffic.group(5)
        if time_interval != None:
            result_dict['start_hour'] = time_interval.group(1)
            result_dict['end_hour'] = time_interval.group(2)
    
    return result_dict


def main():
    ans = parse_intent("set bandwidth('max', 4, 'mbps') for endpoint('hi') start hour('15:00') end hour('20:00')")
    print(ans)

if __name__ == "__main__":
    main()