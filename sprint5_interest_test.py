import requests
from datetime import datetime

API_URL = "http://localhost:8000/api"

BASE_ANSWERS = [
    "Yakın Arkadaş",
    "Belirtmek İstemiyorum / Unisex",
    "25 - 34",
    "Doğum Günü",
    "1.000 - 2.500 TL",
    "Siyah / Gri / Antrasit",
    "Akrep",
]

TEST_CASES = [
    {
        "name": "S5-I1 | Teknoloji & Elektronik",
        "interest": "Teknoloji & Elektronik",
        "expected": ["kulaklık", "powerbank", "akıllı saat", "telefon", "elektronik", "bilgisayar", "tablet"],
        "bad": ["ruj", "makyaj", "battaniye", "nevresim", "vazo"],
    },
    {
        "name": "S5-I2 | Moda & Giyim",
        "interest": "Moda & Giyim",
        "expected": ["çanta", "ayakkabı", "cüzdan", "kemer", "giyim", "takı", "aksesuar"],
        "bad": ["powerbank", "kulaklık", "kahve", "french press", "bebek"],
    },
    {
        "name": "S5-I3 | Kozmetik & Kişisel Bakım",
        "interest": "Kozmetik & Kişisel Bakım",
        "expected": ["parfüm", "kozmetik", "makyaj", "ruj", "allık", "maskara", "cilt bakım", "bakım"],
        "bad": ["powerbank", "kulaklık", "ayakkabı", "kamp", "matkap"],
    },
    {
        "name": "S5-I4 | Ev Dekorasyonu & Yaşam",
        "interest": "Ev Dekorasyonu & Yaşam",
        "expected": ["ev", "dekor", "tablo", "mum", "vazo", "battaniye", "nevresim", "ev tekstili"],
        "bad": ["powerbank", "kulaklık", "ruj", "maskara", "oyuncak"],
    },
    {
        "name": "S5-I5 | Kahve & Çay Kültürü",
        "interest": "Kahve & Çay Kültürü",
        "expected": ["kahve", "çay", "espresso", "french press", "filtre kahve", "kupa"],
        "bad": ["ayakkabı", "ruj", "maskara", "powerbank", "bebek"],
    },
    {
        "name": "S5-I6 | Oyun & Eğlence",
        "interest": "Oyun & Eğlence",
        "expected": ["oyun", "puzzle", "konsol", "joystick", "eğlence", "gaming", "kutu oyunu"],
        "bad": ["ruj", "parfüm", "battaniye", "nevresim", "bebek"],
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
            option_lower = option.lower()
            if any(k.lower() in option_lower for k in keywords):
                answers[q["id"]] = option
                break

    return answers


def contains_any(text, keywords):
    return any(k.lower() in text for k in keywords)


def evaluate(recommendations, expected, bad):
    expected_hits = 0
    bad_hits = 0
    rows = []

    for p in recommendations:
        text = f"{p.get('title','')} {p.get('category','')} {p.get('brand','')}".lower()

        expected_hit = contains_any(text, expected)
        bad_hit = contains_any(text, bad)

        expected_hits += int(expected_hit)
        bad_hits += int(bad_hit)

        rows.append({
            "title": p.get("title", ""),
            "price": p.get("price", ""),
            "brand": p.get("brand", ""),
            "category": p.get("category", ""),
            "score": p.get("score", ""),
            "confidence": p.get("confidence", ""),
            "expected": expected_hit,
            "bad": bad_hit,
        })

    if bad_hits > 0:
        status = "FAIL"
    elif expected_hits >= 3:
        status = "PASS"
    elif expected_hits >= 1:
        status = "WARNING"
    else:
        status = "FAIL"

    return status, expected_hits, bad_hits, rows


def run_tests():
    questions = get_questions()
    summary = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    report = []

    report.append("# Sprint 5 - Interest Matching Automated Test Report\n\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    for i, case in enumerate(TEST_CASES, 1):
        keywords = BASE_ANSWERS + [case["interest"]]
        answers = build_answers(questions, keywords)

        response = requests.post(
            f"{API_URL}/recommend?limit=5",
            json={"answers": answers},
        )
        response.raise_for_status()

        data = response.json()
        recs = data.get("recommendations", [])

        status, expected_hits, bad_hits, rows = evaluate(
            recs,
            case["expected"],
            case["bad"],
        )

        summary[status] += 1

        report.append(f"## Test #{i}: {case['name']}\n\n")
        report.append(f"**Status:** {status}\n\n")
        report.append(f"Expected hits: {expected_hits}/5  \n")
        report.append(f"Bad hits: {bad_hits}/5\n\n")

        report.append("### Selected Answers\n")
        for k, v in answers.items():
            report.append(f"- **{k}:** {v}\n")

        report.append("\n### Recommendations\n")
        report.append("| # | Product | Price | Brand | Category | Score | Confidence | Expected | Bad |\n")
        report.append("|---|---------|-------|-------|----------|-------|------------|----------|-----|\n")

        for idx, row in enumerate(rows, 1):
            report.append(
                f"| {idx} | {row['title']} | {row['price']} | {row['brand']} | "
                f"{row['category']} | {row['score']} | {row['confidence']} | "
                f"{row['expected']} | {row['bad']} |\n"
            )

        report.append("\n---\n\n")

    report.insert(2, "## Summary\n\n")
    report.insert(3, f"- PASS: {summary['PASS']}\n")
    report.insert(4, f"- WARNING: {summary['WARNING']}\n")
    report.insert(5, f"- FAIL: {summary['FAIL']}\n\n")

    with open("sprint5_interest_report.md", "w", encoding="utf-8") as f:
        f.writelines(report)

    print("Done.")
    print(summary)
    print("Report created: sprint5_interest_report.md")


if __name__ == "__main__":
    run_tests()