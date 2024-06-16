from lark import Lark, UnexpectedInput

class GrammarCheck:
    def __init__(self):
        # Load the grammar from the file
        self.grammar = """
            start: intent

            intent: "define intent " term ": " operations

            operations: path " " operation (" " operation)*

            path: from_to | targets

            from_to: "from " endpoint " to " endpoint

            operation: (mboxes | qos | rules)+ [" " interval ]

            mboxes: ("add " | "remove ") middlebox (", " middlebox)*

            middlebox: "middlebox('" term "')"

            qos: ("set " | "unset ") metrics

            metrics: metric (", " metric)*

            metric: bandwidth | quota

            rules: ("allow " | "block ") matches (", " matches)*

            targets: "for " target (", " target)*

            target: group | service | endpoint | traffic

            matches: service | traffic | protocol

            endpoint: "endpoint('" term "')"

            group: "group('" term "')"

            service: "service('" term "')"

            traffic: "traffic('" term "')"

            protocol: "protocol('" term "')"

            bandwidth: "bandwidth(" (max_min) ", '" number "', " bw_unit ")"

            max_min: "'max'" | "'min'"

            bw_unit: "'bps'" | "'kbps'" | "'mbps'" | "'gbps'"

            quota: "quota(" direction ", '" number "', " q_unit ")"

            direction: "'download'" | "'upload'" | "'any'"

            q_unit: "'mb/d'" | "'mb/wk'" | "'gb/d'" | "'gb/wk'" | "'gb/mth'"

            interval: "start " datetime " end " datetime

            datetime: "datetime('" term "')" | "date('" term "')" | "hour('" time "')"

            term: /[A-Za-z0-9]+/

            number: /[0-9]+/

            time: /\d{2}:\d{2}/
        """

        # Create the Lark parser
        self.parser = Lark(self.grammar, start='start')

    def check_grammar(self, input_string):
        input_string = input_string.strip()
        if input_string[0] == '"':
            input_string = input_string[1:-1]
        try:
            self.parser.parse(input_string)
            return (True, None)
        except UnexpectedInput as e:
            return (False, e.column)