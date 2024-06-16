#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <input_file> <output_file>"
  exit 1
fi

# Assign command line arguments to variables
input_file="$1"
output_file="$2"

# Endpoint URL
url="http://localhost:5005/model/parse"

output_json="["

# Read each line from the input file and process it as a JSON payload
while IFS= read -r line; do
  echo "Processing: $line"
  payload="{ \"text\": \"$line\" }"
  response=$(curl -s -XPOST $url -d "$payload" -H "Content-Type: application/json")
  # echo "$response"
  
  # Extract entity types and values
  entities=$(echo "$response" | jq -r '[.entities[] | {type: .entity, value: .value}]')
  echo "$entities"

  # Format as JSON object and append to the output
  output_json="${output_json}{\"text\": \"$line\", \"extracted_entities\": ${entities}},"
done < "$input_file"

# Remove the trailing comma and close the JSON array
output_json="${output_json%,}]"

# Print the final JSON output to the specified output file
echo "$output_json" | jq . > "$output_file"

# Notify the user that the process is complete
echo "Output written to $output_file"
