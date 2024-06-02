# Notes
Run OpenAI LLM with prompt composed of instructions + examples and write results to outputs
`python experiment.py [instructions.txt] [examples.json] [outputs.csv]`

Produces heatmap comparison of accuracies of different prompt settings by question number
`python compare.py` 

Produces a comparison of the answers of the different prompt settings for a specific intent (by number)
`python error_analysis.py [intent number (1-50)]`