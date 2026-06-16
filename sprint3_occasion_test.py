import requests
from datetime import datetime

API_URL = "http://localhost:8000/api"

TEST_CASES = [
    {
        "name": "S3-O1 | Yeni Ev Hediyesi",
        "answers": ["Arkadaş", "Kadın", "25 - 34", "Yeni Ev Hediyesi", "1.000 - 2.500 TL", "Ev Dekorasyonu", "Toprak", "Boğa"],
        "expected": ["ev", "dekor", "vazo", "mum", "tablo", "battaniye", "mutfak"],
        "bad": ["makyaj", "ruj", "kulaklık", "powerbank", "oyuncak"],
    },
    {
        "name": "S3-O2 | Mezuniyet",
        "answers": ["Kardeş", "Erkek", "18 - 24", "Mezuniyet", "1.000 - 2.500 TL", "Teknoloji & Elektronik", "Siyah", "Oğlak"],
        "expected": ["saat", "kalem", "çanta", "bilgisayar", "aksesuar", "teknoloji", "cüzdan"],
        "bad": ["bebek", "oyuncak", "makyaj", "ruj"],
    },
    {
        "name": "S3-O3 | Sevgililer Günü",
        "answers": ["Sevgili", "Kadın", "25 - 34", "Sevgililer Günü", "2.500 - 5.000 TL", "Kozmetik & Kişisel Bakım", "Pastel", "Terazi"],
        "expected": ["parfüm", "takı", "çanta", "romantik", "kadın", "kozmetik"],
        "bad": ["bebek", "oyuncak", "matkap", "ofis"],
    },
    {
        "name": "S3-O4 | Babalar Günü",
        "answers": ["Baba", "Erkek", "45 - 54", "Babalar Günü", "1.000 - 2.500 TL", "Moda & Giyim", "Siyah", "Oğlak"],
        "expected": ["erkek", "cüzdan", "kemer", "saat", "ayakkabı", "gömlek"],
        "bad": ["kadın", "makyaj", "ruj", "bebek"],
    },
    {
        "name": "S3-O5 | Anneler Günü",
        "answers": ["Anne", "Kadın", "45 - 54", "Anneler Günü", "1.000 - 2.500 TL", "Ev Dekorasyonu", "Pastel", "Boğa"],
        "expected": ["kadın", "ev", "dekor", "kahve", "kupa", "parfüm", "bakım", "vazo", "mum"],
        "bad": ["erkek", "oyuncak", "gaming", "bebek"],
    },
    {
        "name": "S3-O6 | Geçmiş Olsun / Moral",
        "answers": ["Arkadaş", "Kadın", "25 - 34", "Geçmiş Olsun", "500 - 1.000 TL", "Kahve & Çay Kültürü", "Pastel", "Balık"],
        "expected": ["kupa", "kahve", "çay", "mum", "peluş", "battaniye", "rahat"],
        "bad": ["matkap", "gaming", "erkek ayakkabı", "bebek"],
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

    report.append("# Sprint 3 - Occasion Automated Test Report\n\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    for i, case in enumerate(TEST_CASES, 1):
        answers = build_answers(questions, case["answers"])

        response = requests.post(
            f"{API_URL}/recommend?limit=5",
            json={"answers": answers},
        )
        response.raise_for_status()

        data = response.json()
        recs = data.get("recommendations", [])

        status, expected_hits, bad_hits, rows = evaluate(recs, case["expected"], case["bad"])
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

    with open("sprint3_occasion_report.md", "w", encoding="utf-8") as f:
        f.writelines(report)

    print("Done.")
    print(summary)
    print("Report created: sprint3_occasion_report.md")


if __name__ == "__main__":
    run_tests()