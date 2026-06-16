import requests
from datetime import datetime

API_URL = "http://localhost:8000/api"

TEST_CASES = [
    {
        "name": "S4-B1 | 500 - 1.000 TL",
        "answers": ["Arkadaş", "Unisex", "18 - 24", "Doğum Günü", "500 - 1.000 TL", "Teknoloji & Elektronik", "Siyah"],
        "min_budget": 500,
        "max_budget": 1000,
        "request_budget": None,
    },
    {
        "name": "S4-B2 | 1.000 - 2.500 TL",
        "answers": ["Baba", "Erkek", "45 - 54", "Babalar Günü", "1.000 - 2.500 TL", "Moda & Giyim", "Siyah"],
        "min_budget": 1000,
        "max_budget": 2500,
        "request_budget": None,
    },
    {
        "name": "S4-B3 | 2.500 - 5.000 TL",
        "answers": ["Sevgili", "Kadın", "25 - 34", "Yıl Dönümü", "2.500 - 5.000 TL", "Kozmetik & Kişisel Bakım", "Pastel"],
        "min_budget": 2500,
        "max_budget": 5000,
        "request_budget": None,
    },
    {
        "name": "S4-B4 | 5.000 TL ve üzeri",
        "answers": ["Kendime", "Unisex", "25 - 34", "İçimden Geldi", "5.000 TL ve üzeri", "Teknoloji & Elektronik", "Siyah"],
        "min_budget": 5000,
        "max_budget": 50000,
        "request_budget": None,
    },
    {
        "name": "S4-B5 | Slider Override 1500 TL",
        "answers": ["Arkadaş", "Unisex", "18 - 24", "Doğum Günü", "2.500 - 5.000 TL", "Oyun & Eğlence", "Canlı"],
        "min_budget": 0,
        "max_budget": 1500,
        "request_budget": 1500,
    },
    {
        "name": "S4-B6 | Empty answers should not crash",
        "answers": [],
        "min_budget": 0,
        "max_budget": 50000,
        "request_budget": None,
    },
]


def get_questions():
    r = requests.get(f"{API_URL}/questions")
    r.raise_for_status()
    return r.json()


def build_answers(questions, keywords):
    answers = {}
    for q in questions:
        for option in q["options"]:
            if any(k.lower() in option.lower() for k in keywords):
                answers[q["id"]] = option
                break
    return answers


def evaluate_budget(recommendations, min_budget, max_budget):
    rows = []
    violations = 0

    for p in recommendations:
        price = float(p.get("price", 0))

        too_low = price < min_budget
        too_high = price > max_budget
        violation = too_low or too_high

        if violation:
            violations += 1

        rows.append({
            "title": p.get("title", ""),
            "price": price,
            "brand": p.get("brand", ""),
            "category": p.get("category", ""),
            "score": p.get("score", ""),
            "confidence": p.get("confidence", ""),
            "too_low": too_low,
            "too_high": too_high,
            "violation": violation,
        })

    status = "PASS" if violations == 0 else "FAIL"
    return status, violations, rows


def run_tests():
    questions = get_questions()
    summary = {"PASS": 0, "FAIL": 0}
    report = []

    report.append("# Sprint 4 - Budget Automated Test Report\n\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    for i, case in enumerate(TEST_CASES, 1):
        answers = build_answers(questions, case["answers"])

        payload = {"answers": answers}
        if case["request_budget"] is not None:
            payload["budget"] = case["request_budget"]

        response = requests.post(
            f"{API_URL}/recommend?limit=5",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        recs = data.get("recommendations", [])

        status, violations, rows = evaluate_budget(
            recs,
            case["min_budget"],
            case["max_budget"],
        )

        summary[status] += 1

        report.append(f"## Test #{i}: {case['name']}\n\n")
        report.append(f"**Status:** {status}\n\n")
        report.append(f"Budget range: {case['min_budget']} - {case['max_budget']} TL  \n")
        report.append(f"Violations: {violations}/5\n\n")

        report.append("### Selected Answers\n")
        if answers:
            for k, v in answers.items():
                report.append(f"- **{k}:** {v}\n")
        else:
            report.append("- Empty answers\n")

        report.append("\n### Recommendations\n")
        report.append("| # | Product | Price | Brand | Category | Too Low | Too High | Violation |\n")
        report.append("|---|---------|-------|-------|----------|---------|----------|-----------|\n")

        for idx, row in enumerate(rows, 1):
            report.append(
                f"| {idx} | {row['title']} | {row['price']} | {row['brand']} | "
                f"{row['category']} | {row['too_low']} | {row['too_high']} | {row['violation']} |\n"
            )

        report.append("\n---\n\n")

    report.insert(2, "## Summary\n\n")
    report.insert(3, f"- PASS: {summary['PASS']}\n")
    report.insert(4, f"- FAIL: {summary['FAIL']}\n\n")

    with open("sprint4_budget_report.md", "w", encoding="utf-8") as f:
        f.writelines(report)

    print("Done.")
    print(summary)
    print("Report created: sprint4_budget_report.md")


if __name__ == "__main__":
    run_tests()