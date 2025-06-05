import argparse
import json
from collections import defaultdict

def load_and_process_data():
    with open("all_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

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

def main():
    parser = argparse.ArgumentParser(description="Analyze subject results by subject code or show top failure rates.")
    parser.add_argument("-s", "--subject_code", help="Subject code to filter the analysis")
    parser.add_argument("-f", "--fail_rate", action="store_true", help="Show top 10 subjects sorted by fail percentage")
    parser.add_argument("-a", "--all", action="store_true", help="Show statistics for all subject codes")
    args = parser.parse_args()

    stats = load_and_process_data()
    fail_percentages = calculate_fail_percentages(stats["total_counts"], stats["failed_counts"])

    print(f"{'='*70}\nTotal Candidates: {len(stats['data'])}, Passed = {stats['overall_passed']}, Failed = {stats['overall_failed']}")

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
                print(f" - {subj} ({code}) - {fail_pct:.2f}% | Total: {total}, Failed {failed}")
            print("="*70)
        else:
            print("No data to calculate fail percentages.")

    if not args.subject_code and not args.fail_rate and not args.all:
        parser.print_help()

if __name__ == "__main__":
    main()