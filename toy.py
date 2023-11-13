import re

def parse_intent(intent: str):
    # Define entities and operations
    entities = ['endpoint', 'link', 'group', 'policy']
    operations = ['add', 'remove', 'for', 'set', 'from', 'to']

    # Split the intent into expressions
    expressions = intent.split('\n')

    # Regex pattern to match operation, entity, and arguments while respecting spaces within parentheses
    pattern = r"(" + '|'.join(op for op in operations) + r")\s+(\w+)\('([^']+)'\)"

    # Find all matches
    matches = re.findall(pattern, intent)

    # For each match, create the appropriate dictionary entry
    parsed_intents = []
    for match in matches:
        operation, entity, argument = match
        print(operation, entity, argument)
        parsed_intent = {operation: [(entity, argument)]}
        parsed_intents.append(parsed_intent)

    return parsed_intents

def main():
    print(parse_intent("remove endpoint('smart phone') from group('living room')"))

if __name__ == "__main__":
    main()