import argparse
import json
from collections import defaultdict

def load_data():
    with open("all_results.json", "r", encoding="utf-8") as f:
        return json.load(f)

def process_data(data, analyze_subjects=True):
    if not analyze_subjects:
        return {
            "data": data,
            "subject_code_map": {},
            "passed_counts": defaultdict(lambda: defaultdict(int)),
            "failed_counts": defaultdict(int),
            "total_counts": defaultdict(int),
            "overall_passed": 0,
            "overall_failed": 0
        }

    subject_code_map = {}
    passed_counts = defaultdict(lambda: defaultdict(int))
    failed_counts = defaultdict(int)
    total_counts = defaultdict(int)
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

    return {
        "data": data,
        "subject_code_map": subject_code_map,
        "passed_counts": passed_counts,
        "failed_counts": failed_counts,
        "total_counts": total_counts,
        "overall_passed": overall_passed,
        "overall_failed": overall_failed
    }

def calculate_fail_percentages(total_counts, failed_counts):
    return {
        code: (failed_counts.get(code, 0) / total * 100) if total > 0 else 0
        for code, total in total_counts.items()
    }

def print_subject_stats(code, stats):
    subj = stats["subject_code_map"].get(code, ("UNKNOWN POSITION", "UNKNOWN SUBJECT"))[1]
    total = stats["total_counts"].get(code, 0)
    failed = stats["failed_counts"].get(code, 0)
    fail_percentage = (failed / total * 100) if total > 0 else 0

    print(f"Subject: {subj} ({code}) | Total candidates: {total}")
    if code in stats["passed_counts"]:
        for position, count in stats["passed_counts"][code].items():
            print(f"         Passed {position}: {count}")
    print(f"         Failed Count: {failed} | Fail Percentage: {fail_percentage:.2f}%")
    print("-"*70)

def search_candidate_by_roll(data, roll_number):
    results = [c for c in data if c.get("roll", "") == roll_number]
    if not results:
        print(f"No candidate found with roll number: {roll_number}")
        return False
    
    print(f"\n{'='*50}")
    print(f"Candidate Result for Roll: {roll_number}")
    print(f"{'='*50}")
    for candidate in results:
        personal_details = candidate.get("personal_details", {})
        print(f"Name: {personal_details.get('Name', 'N/A')}")
        print(f"Father's Name: {personal_details.get('Father', 'N/A')}")
        print(f"Mother's Name: {personal_details.get('Mother', 'N/A')}")
        print(f"Subject: {candidate.get('subject', 'N/A')}")
        print(f"Position: {candidate.get('position', 'N/A')}")
        print(f"Status: {candidate.get('status', 'N/A')}")
        print("-"*50)
    return True

def main():
    parser = argparse.ArgumentParser(description="Analyze subject results or search candidate records.")
    parser.add_argument("-s", "--subject_code", help="Subject code to filter the analysis")
    parser.add_argument("-f", "--fail_rate", action="store_true", help="Show top 10 subjects sorted by fail percentage")
    parser.add_argument("-a", "--all", action="store_true", help="Show statistics for all subject codes")
    parser.add_argument("-r", "--roll", help="Search for candidate by roll number")
    args = parser.parse_args()

    data = load_data()
    
    stats = process_data(data, analyze_subjects=True)

    if args.roll:
        found = search_candidate_by_roll(data, args.roll)
        if not found:
            return

        if not any([args.subject_code, args.fail_rate, args.all]):
            response = input("\nShow subject analysis for this candidate's subject code? (y/n): ").strip().lower()
            if response == 'y':
                subject_code = args.roll[:3]
                print("\n" + "="*70)
                if subject_code in stats["total_counts"]:
                    print_subject_stats(subject_code, stats)
                else:
                    print(f"No subject analysis available for code: {subject_code}")

    if any([args.subject_code, args.fail_rate, args.all]):
        print(f"{'='*70}\nTotal Candidates: {len(data)}, Passed = {stats['overall_passed']}, Failed = {stats['overall_failed']}")
        fail_percentages = calculate_fail_percentages(stats["total_counts"], stats["failed_counts"])

        if args.subject_code:
            print("="*70)
            if args.subject_code in stats["total_counts"]:
                print_subject_stats(args.subject_code, stats)
            else:
                print(f"No data found for subject code: {args.subject_code}")

        if args.all:
            print("\nStatistics for all subject codes:")
            for code in sorted(stats["total_counts"].keys()):
                print_subject_stats(code, stats)
            print("="*70)

        if args.fail_rate:
            if fail_percentages:
                fail_list = [
                    (code, stats["subject_code_map"].get(code, ("UNKNOWN POSITION", "UNKNOWN SUBJECT"))[1], fail)
                    for code, fail in fail_percentages.items()
                ]
                fail_list.sort(key=lambda x: x[2], reverse=True)

                print("\nTop 10 subjects sorted by fail percentage (desc):")
                for code, subj, fail_pct in fail_list[:10]:
                    total = stats["total_counts"].get(code, 0)
                    failed = stats["failed_counts"].get(code, 0)
                    print(f" - {subj} ({code}) - {fail_pct:.2f}% | Total: {total}, Failed: {failed}")
            else:
                print("No data to calculate fail percentages.")

    if not any([args.subject_code, args.fail_rate, args.all, args.roll]):
        parser.print_help()

if __name__ == "__main__":
    main()