import argparse
import json
from collections import defaultdict

parser = argparse.ArgumentParser(description="Analyze subject results by subject code or show top failure rates.")
parser.add_argument("-s", "--subject_code", help="Subject code to filter the analysis")
parser.add_argument("-f", "--fail_rate", action="store_true", help="Show top 10 subjects sorted by fail percentage")
args = parser.parse_args()

filter_code = args.subject_code
show_failures = args.fail_rate

with open("all_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

subject_code_map = {}

overall_passed = 0
overall_failed = 0
for candidate in data:
    roll = candidate.get("roll", "")
    status = candidate.get("status", "").upper()
    position = candidate.get("position")
    subject = candidate.get("subject")

    if len(roll) >= 3:
        code = roll[:3]
        if status == "PASSED" and position and subject:
            if code not in subject_code_map:
                subject_code_map[code] = (position, subject)

passed_counts = defaultdict(lambda: defaultdict(int))
failed_counts = defaultdict(int)
total_counts = defaultdict(int)

for candidate in data:
    roll = candidate.get("roll", "")
    status = candidate.get("status", "").upper()
    position = candidate.get("position")
    subject = candidate.get("subject")

    if len(roll) < 3:
        continue
    code = roll[:3]

    if not position or not subject:
        if code in subject_code_map:
            position, subject = subject_code_map[code]
        else:
            position = position or "UNKNOWN POSITION"
            subject = subject or "UNKNOWN SUBJECT"

    total_counts[code] += 1
    if status == "PASSED":
        passed_counts[code][position] += 1
        overall_passed += 1
    elif status == "FAILED":
        failed_counts[code] += 1
        overall_failed += 1

print(f"{'='*70}\nTotal Candidates: Passed = {overall_passed}, Failed = {overall_failed}")
fail_percentages = {}

if filter_code:
    print("="*70)
    if filter_code in total_counts:
        subj = subject_code_map.get(filter_code, ("UNKNOWN POSITION", "UNKNOWN SUBJECT"))[1]
        total = total_counts.get(filter_code, 0)
        failed = failed_counts.get(filter_code, 0)
        fail_percentage = (failed / total * 100) if total > 0 else 0
        fail_percentages[filter_code] = fail_percentage

        print(f"Subject: {subj} ({filter_code}) | Total candidates: {total}")
        if filter_code in passed_counts:
            for position, count in passed_counts[filter_code].items():
                print(f"         Passed {position}: {count}")
        else:
            print("    None")
        print(f"         Failed Count: {failed} | Fail Percentage: {fail_percentage:.2f}%")
        print("-"*70)
    else:
        print(f"No data found for subject code: {filter_code}")

if show_failures:
    for code in total_counts:
        total = total_counts[code]
        failed = failed_counts.get(code, 0)
        fail_percentage = (failed / total * 100) if total > 0 else 0
        fail_percentages[code] = fail_percentage

    if fail_percentages:
        fail_list = [
            (code, subject_code_map.get(code, ("UNKNOWN POSITION", "UNKNOWN SUBJECT"))[1], fail)
            for code, fail in fail_percentages.items()
        ]
        fail_list.sort(key=lambda x: x[2], reverse=True)

        print("\nTop 10 subjects sorted by fail percentage (desc):")
        for code, subj, fail_pct in fail_list[:10]:
            total = total_counts.get(code, 0)
            failed = failed_counts.get(code, 0)
            print(f" - {subj} ({code}) - {fail_pct:.2f}% | Total: {total}, Failed {failed}")
    else:
        print("No data to calculate fail percentages.")

if not filter_code and not show_failures:
    parser.print_help()
