import requests
from datetime import datetime

API_URL = "http://localhost:8000/api"


TEST_CASES = [
    {
        "name": "S1-G1 | Kadın + Kozmetik",
        "target_gender": "kadın",
        "answers": [
            "Yakın Arkadaş (Kadın)",
            "Kadın",
            "18 - 24",
            "Doğum Günü",
            "1.000 - 2.500 TL",
            "Kozmetik & Kişisel Bakım",
            "Pastel",
            "Üstüme başıma",
            "Terazi",
        ],
        "expected": ["kadın", "parfüm", "makyaj", "kozmetik", "ruj", "maskara", "bakım", "cilt"],
        "bad": ["erkek", "tıraş", "traş"],
    },
    {
        "name": "S1-G2 | Kadın + Moda",
        "target_gender": "kadın",
        "answers": [
            "Sevgili (Kadın)",
            "Kadın",
            "25 - 34",
            "Yıl Dönümü",
            "2.500 - 5.000 TL",
            "Moda & Giyim",
            "Pastel",
            "Üstüme başıma",
            "Aslan",
        ],
        "expected": ["kadın", "çanta", "takı", "aksesuar", "ayakkabı", "giyim", "parfüm"],
        "bad": ["erkek", "tıraş", "traş"],
    },
    {
        "name": "S1-G3 | Erkek + Teknoloji",
        "target_gender": "erkek",
        "answers": [
            "Sevgili (Erkek)",
            "Erkek",
            "25 - 34",
            "Doğum Günü",
            "1.000 - 2.500 TL",
            "Teknoloji & Elektronik",
            "Siyah",
            "Telefon şarjının sürekli %5",
            "Kova",
        ],
        "expected": ["erkek", "powerbank", "şarj", "kulaklık", "teknoloji", "akıllı", "elektronik"],
        "bad": ["kadın", "makyaj", "ruj", "maskara", "sütyen", "elbise"],
    },
    {
        "name": "S1-G4 | Erkek + Moda",
        "target_gender": "erkek",
        "answers": [
            "Baba",
            "Erkek",
            "45 - 54",
            "Babalar Günü",
            "1.000 - 2.500 TL",
            "Moda & Giyim",
            "Siyah",
            "Hiçbir şeyim yok",
            "Oğlak",
        ],
        "expected": ["erkek", "cüzdan", "kemer", "saat", "ayakkabı", "giyim", "çanta"],
        "bad": ["kadın", "ruj", "maskara", "makyaj", "sütyen", "elbise"],
    },
    {
        "name": "S1-G5 | Unisex + Teknoloji",
        "target_gender": "unisex",
        "answers": [
            "Kendime",
            "Belirtmek İstemiyorum / Unisex",
            "18 - 24",
            "İçimden Geldi",
            "500 - 1.000 TL",
            "Teknoloji & Elektronik",
            "Siyah",
            "Telefon şarjının sürekli %5",
            "Kova",
        ],
        "expected": ["powerbank", "şarj", "kulaklık", "teknoloji", "akıllı", "elektronik", "unisex"],
        "bad": ["kadın", "erkek", "sütyen", "elbise", "bebek"],
    },
    {
        "name": "S1-G6 | Unisex + Oyun/Eğlence",
        "target_gender": "unisex",
        "answers": [
            "Kardeş",
            "Belirtmek İstemiyorum / Unisex",
            "18 - 24",
            "Doğum Günü",
            "500 - 1.000 TL",
            "Oyun & Eğlence",
            "Canlı",
            "Puzzle",
            "İkizler",
        ],
        "expected": ["oyun", "puzzle", "konsol", "eğlence", "gaming", "unisex"],
        "bad": ["kadın", "erkek", "sütyen", "elbise", "bebek"],
    },
]


def get_questions():
    response = requests.get(f"{API_URL}/questions")
    response.raise_for_status()
    return response.json()


def build_answers(questions, keywords):
    answers = {}

    for question in questions:
        for option in question["options"]:
            option_lower = option.lower()
            if any(keyword.lower() in option_lower for keyword in keywords):
                answers[question["id"]] = option
                break

    return answers


def contains_any(text, keywords):
    return any(keyword.lower() in text for keyword in keywords)


def gender_violation(product, target_gender):
    title = str(product.get("title", "")).lower()
    category = str(product.get("category", "")).lower()
    text = f"{title} {category}"

    has_female = "kadın" in text
    has_male = "erkek" in text
    has_unisex = "unisex" in text

    if target_gender == "kadın":
        return has_male and not has_unisex

    if target_gender == "erkek":
        return has_female and not has_unisex

    if target_gender == "unisex":
        return has_female or has_male

    return False


def evaluate_recommendations(recommendations, expected_keywords, bad_keywords, target_gender):
    expected_hits = 0
    bad_hits = 0
    gender_bad_hits = 0
    rows = []

    for product in recommendations:
        title = str(product.get("title", ""))
        category = str(product.get("category", ""))
        brand = str(product.get("brand", ""))
        text = f"{title} {category} {brand}".lower()

        expected_hit = contains_any(text, expected_keywords)
        keyword_bad_hit = contains_any(text, bad_keywords)
        gender_bad_hit = gender_violation(product, target_gender)

        if expected_hit:
            expected_hits += 1

        if keyword_bad_hit:
            bad_hits += 1

        if gender_bad_hit:
            gender_bad_hits += 1

        rows.append({
            "title": title,
            "price": product.get("price", ""),
            "brand": brand,
            "category": category,
            "score": product.get("score", ""),
            "confidence": product.get("confidence", ""),
            "expected_hit": expected_hit,
            "keyword_bad_hit": keyword_bad_hit,
            "gender_bad_hit": gender_bad_hit,
            "rationale": product.get("rationale", ""),
        })

    total_bad = bad_hits + gender_bad_hits

    if total_bad > 0:
        status = "FAIL"
    elif expected_hits >= 3:
        status = "PASS"
    elif expected_hits >= 1:
        status = "WARNING"
    else:
        status = "FAIL"

    return status, expected_hits, bad_hits, gender_bad_hits, rows


def run_tests():
    questions = get_questions()
    summary = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    report = []

    report.append("# Sprint 1 - Gender Automated Test Report\n\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    for index, test_case in enumerate(TEST_CASES, start=1):
        answers = build_answers(questions, test_case["answers"])

        response = requests.post(
            f"{API_URL}/recommend?limit=5",
            json={"answers": answers},
        )
        response.raise_for_status()

        data = response.json()
        recommendations = data.get("recommendations", [])

        status, expected_hits, keyword_bad_hits, gender_bad_hits, rows = evaluate_recommendations(
            recommendations,
            test_case["expected"],
            test_case["bad"],
            test_case["target_gender"],
        )

        summary[status] += 1

        report.append(f"## Test #{index}: {test_case['name']}\n\n")
        report.append(f"**Status:** {status}\n\n")
        report.append(f"Expected hits: {expected_hits}/5  \n")
        report.append(f"Keyword bad hits: {keyword_bad_hits}/5  \n")
        report.append(f"Gender bad hits: {gender_bad_hits}/5\n\n")

        report.append("### Selected Answers\n")
        for key, value in answers.items():
            report.append(f"- **{key}:** {value}\n")

        report.append("\n### Recommendations\n")
        report.append("| # | Product | Price | Brand | Category | Score | Confidence | Expected | Keyword Bad | Gender Bad |\n")
        report.append("|---|---------|-------|-------|----------|-------|------------|----------|-------------|------------|\n")

        for idx, row in enumerate(rows, start=1):
            report.append(
                f"| {idx} | {row['title']} | {row['price']} | {row['brand']} | "
                f"{row['category']} | {row['score']} | {row['confidence']} | "
                f"{row['expected_hit']} | {row['keyword_bad_hit']} | {row['gender_bad_hit']} |\n"
            )

        report.append("\n---\n\n")

    report.insert(2, "## Summary\n\n")
    report.insert(3, f"- PASS: {summary['PASS']}\n")
    report.insert(4, f"- WARNING: {summary['WARNING']}\n")
    report.insert(5, f"- FAIL: {summary['FAIL']}\n\n")

    with open("sprint1_gender_report.md", "w", encoding="utf-8") as file:
        file.writelines(report)

    print("Done.")
    print(summary)
    print("Report created: sprint1_gender_report.md")


if __name__ == "__main__":
    run_tests()