import csv

def evaluate_response(expected, actual):
    return expected.lower() in actual.lower()

def run_evaluation(log_file="tests/qa_log.csv"):
    results = []

    with open(log_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            expected = row["expected_answer"]
            actual = row["actual_answer"]

            passed = evaluate_response(expected, actual)

            results.append({
                "question": row["question"],
                "pass": passed
            })

    total = len(results)
    passed_count = sum(1 for r in results if r["pass"])

    print(f"Passed {passed_count}/{total} tests")

    return results
