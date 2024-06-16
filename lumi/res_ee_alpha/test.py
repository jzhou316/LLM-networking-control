import csv, ast, json, sys
from collections import Counter

# open and read a csv to dict
with open('final_alpha_entity_extraction.csv', 'r') as file:
    reader = csv.DictReader(file)
    data = list(reader)
    total_tp_llm = 0
    total_fp_llm = 0
    total_fn_llm = 0
    total_tp_lumi = 0
    total_fp_lumi = 0
    total_fn_lumi = 0
    for item in data[:-2]:
        llm_output = ast.literal_eval(item['llm_output'])
        lumi_output = ast.literal_eval(item['lumi_output'])
        expected_output = ast.literal_eval(item['expected_output'])
        # Find the intersection of the two lists
        matching_words_llm = list((Counter(llm_output) & Counter(expected_output)).elements())
        matching_words_lumi = list((Counter(lumi_output) & Counter(expected_output)).elements())
        item['tp_llm'] = len(matching_words_llm) 
        item['tp_lumi'] = len(matching_words_lumi)
        item['fp_llm'] = len(llm_output) - len(matching_words_llm) if len(llm_output) - len(matching_words_llm) > 0 else 0
        item['fp_lumi'] = len(lumi_output) - len(matching_words_lumi) if len(lumi_output) - len(matching_words_lumi) > 0 else 0
        item['fn_llm'] = len(expected_output) - len(matching_words_llm) if len(expected_output) - len(matching_words_llm) > 0 else 0
        item['fn_lumi'] = len(expected_output) - len(matching_words_lumi) if len(expected_output) - len(matching_words_lumi) > 0 else 0
        item['precision_llm'] = item['tp_llm'] / (item['tp_llm'] + item['fp_llm']) if item['tp_llm'] + item['fp_llm'] > 0 else 0
        item['precision_lumi'] = item['tp_lumi'] / (item['tp_lumi'] + item['fp_lumi']) if item['tp_lumi'] + item['fp_lumi'] > 0 else 0
        item['recall_llm'] = item['tp_llm'] / (item['tp_llm'] + item['fn_llm']) if item['tp_llm'] + item['fn_llm'] > 0 else 0
        item['recall_lumi'] = item['tp_lumi'] / (item['tp_lumi'] + item['fn_lumi']) if item['tp_lumi'] + item['fn_lumi'] > 0 else 0
        item['f1_score_llm'] = 2 * (item['precision_llm'] * item['recall_llm']) / (item['precision_llm'] + item['recall_llm']) if item['precision_llm'] + item['recall_llm'] > 0 else 0
        item['f1_score_lumi'] = 2 * (item['precision_lumi'] * item['recall_lumi']) / (item['precision_lumi'] + item['recall_lumi']) if item['precision_lumi'] + item['recall_lumi'] > 0 else 0
        total_tp_llm += item['tp_llm']
        total_fp_llm += item['fp_llm']
        total_fn_llm += item['fn_llm']
        total_tp_lumi += item['tp_lumi']
        total_fp_lumi += item['fp_lumi']
        total_fn_lumi += item['fn_lumi']
        # Write to a new CSV
        with open('final_alpha_entity_extraction_eval.csv', 'w') as file:
            writer = csv.DictWriter(file, fieldnames=item.keys())
            writer.writeheader()
            writer.writerows(data[:-2])
    print(f"Total True Positives LLM: {total_tp_llm}")
    print(f"Total False Positives LLM: {total_fp_llm}")
    print(f"Total False Negatives LLM: {total_fn_llm}")
    print(f"Total True Positives Lumi: {total_tp_lumi}")
    print(f"Total False Positives Lumi: {total_fp_lumi}")
    print(f"Total False Negatives Lumi: {total_fn_lumi}")
    precision_llm = total_tp_llm / (total_tp_llm + total_fp_llm) if total_tp_llm + total_fp_llm > 0 else 0
    precision_lumi = total_tp_lumi / (total_tp_lumi + total_fp_lumi) if total_tp_lumi + total_fp_lumi > 0 else 0
    recall_llm = total_tp_llm / (total_tp_llm + total_fn_llm) if total_tp_llm + total_fn_llm > 0 else 0
    recall_lumi = total_tp_lumi / (total_tp_lumi + total_fn_lumi) if total_tp_lumi + total_fn_lumi > 0 else 0
    print(f"Precision LLM: {precision_llm}")
    print(f"Precision Lumi: {precision_lumi}")
    print(f"Recall LLM: {recall_llm}")
    print(f"Recall Lumi: {recall_lumi}")
    f1_score_llm = 2 * (precision_llm * recall_llm) / (precision_llm + recall_llm) if precision_llm + recall_llm > 0 else 0
    f1_score_lumi = 2 * (precision_lumi * recall_lumi) / (precision_lumi + recall_lumi) if precision_lumi + recall_lumi > 0 else 0
    print(f"F1 Score LLM: {f1_score_llm}")
    print(f"F1 Score Lumi: {f1_score_lumi}")