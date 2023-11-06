import re

def parse_intent(intent: str):
    # Define entities and operations
    entities = ['endpoint', 'link', 'group', 'policy']
    operations = ['add', 'remove', 'for', 'set', 'from', 'to']

    # Split the intent into expressions
    expressions = intent.split('\n')

    # For each expression, split into operation and entity
    parsed_intents = []
    for expr in expressions:
        parsed_intent = {}
        words = expr.split(' ')
        current_key = ''
        entity_args = []
        for word in words:
            if word in operations:
                current_key = word
                continue
            else:
                entity_args = re.findall(r"(\w+)\(\'(.*?)\'\)", word)
            if current_key != '' and len(entity_args) > 0:
                parsed_intent[current_key] = [entity_args[0]]
                current_key = ''
        parsed_intents.append(parsed_intent)
    return parsed_intents

def main():
    print(parse_intent("add group('living-room')"))

if __name__ == "__main__":
    main()