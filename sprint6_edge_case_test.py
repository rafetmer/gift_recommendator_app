import requests
from datetime import datetime

API_URL = "http://localhost:8000/api"

TEST_CASES = [
    {
        "name": "S6-E1 | Empty answers should not crash",
        "answers": [],
        "budget": None,
        "expect_min_results": 1,
        "expect_status": "success",
    },
    {
        "name": "S6-E2 | Only gender selected",
        "answers": ["Kadın"],
        "budget": None,
        "expect_min_results": 1,
        "expect_status": "success",
    },
    {
        "name": "S6-E3 | Only budget selected",
        "answers": ["500 - 1.000 TL"],
        "budget": None,
        "expect_min_results": 1,
        "expect_status": "success",
    },
    {
        "name": "S6-E4 | Conflicting signals: erkek + kozmetik",
        "answers": ["Erkek", "25 - 34", "Doğum Günü", "1.000 - 2.500 TL", "Kozmetik & Kişisel Bakım"],
        "budget": None,
        "expect_min_results": 1,
        "expect_status": "success",
    },
    {
        "name": "S6-E5 | Very strict low slider budget",
        "answers": ["Yakın Arkadaş", "Unisex", "18 - 24", "Doğum Günü", "Teknoloji & Elektronik"],
        "budget": 300,
        "expect_min_results": 0,
        "expect_status": "success",
    },
    {
        "name": "S6-E6 | High limit request",
        "answers": ["Yakın Arkadaş", "Unisex", "25 - 34", "Doğum Günü", "Teknoloji & Elektronik", "1.000 - 2.500 TL"],
        "budget": None,
        "limit": 20,
        "expect_min_results": 1,
        "expect_status": "success",
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


def run_tests():
    questions = get_questions()
    summary = {"PASS": 0, "FAIL": 0}
    report = []

    report.append("# Sprint 6 - Edge Case & Stability Test Report\n\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    for i, case in enumerate(TEST_CASES, 1):
        answers = build_answers(questions, case["answers"])
        payload = {"answers": answers}

        if case.get("budget") is not None:
            payload["budget"] = case["budget"]

        limit = case.get("limit", 5)

        error = None
        data = {}
        try:
            response = requests.post(
                f"{API_URL}/recommend?limit={limit}",
                json=payload,
                timeout=30,
            )
            status_code = response.status_code
            data = response.json()
        except Exception as e:
            status_code = "EXCEPTION"
            error = str(e)

        recommendations = data.get("recommendations", []) if isinstance(data, dict) else []
        api_status = data.get("status", "") if isinstance(data, dict) else ""

        pass_condition = (
            status_code == 200
            and api_status == case["expect_status"]
            and len(recommendations) >= case["expect_min_results"]
        )

        status = "PASS" if pass_condition else "FAIL"
        summary[status] += 1

        report.append(f"## Test #{i}: {case['name']}\n\n")
        report.append(f"**Status:** {status}\n\n")
        report.append(f"HTTP status: {status_code}  \n")
        report.append(f"API status: {api_status}  \n")
        report.append(f"Result count: {len(recommendations)}  \n")
        report.append(f"Expected minimum results: {case['expect_min_results']}\n\n")

        if error:
            report.append(f"Error: `{error}`\n\n")

        report.append("### Selected Answers\n")
        if answers:
            for k, v in answers.items():
                report.append(f"- **{k}:** {v}\n")
        else:
            report.append("- Empty or unmatched answers\n")

        report.append("\n### Recommendations\n")
        report.append("| # | Product | Price | Brand | Category | Score | Confidence |\n")
        report.append("|---|---------|-------|-------|----------|-------|------------|\n")

        for idx, p in enumerate(recommendations[:10], 1):
            report.append(
                f"| {idx} | {p.get('title', '')} | {p.get('price', '')} | "
                f"{p.get('brand', '')} | {p.get('category', '')} | "
                f"{p.get('score', '')} | {p.get('confidence', '')} |\n"
            )

        report.append("\n---\n\n")

    report.insert(2, "## Summary\n\n")
    report.insert(3, f"- PASS: {summary['PASS']}\n")
    report.insert(4, f"- FAIL: {summary['FAIL']}\n\n")

    with open("sprint6_edge_case_report.md", "w", encoding="utf-8") as f:
        f.writelines(report)

    print("Done.")
    print(summary)
    print("Report created: sprint6_edge_case_report.md")


if __name__ == "__main__":
    run_tests()