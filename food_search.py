import re
import sqlite3
from pathlib import Path


SIMPLE_FOOD_WORDS = {
    "raw",
    "fresh",
    "plain",
    "whole",
    "boiled",
    "baked",
    "broiled",
    "roasted",
    "grilled"
}


PROCESSED_FOOD_WORDS = {
    "fried",
    "coated",
    "breaded",
    "battered",
    "candied",
    "sweetened",
    "juice",
    "beverage",
    "pie",
    "crisp",
    "cake",
    "candy",
    "dessert",
    "sauce",
    "syrup",
    "jam",
    "jelly",
    "smoothie",
    "cookie",
    "pudding",
    "marinade",
    "marinated"
}

SEARCH_MODIFIER_WORDS = {
    "raw",
    "fresh",
    "plain",
    "whole",
    "skinless",
    "skin",
    "eaten",
    "not",
    "with",
    "without",
    "boneless",
    "baked",
    "broiled",
    "roasted",
    "grilled",
    "fried",
    "coated",
    "breaded",
    "battered",
    "boiled",
    "poached",
    "cooked",
    "prepared",
    "dried",
    "candied",
    "sweetened",
    "unsweetened",
    "skim",
    "nonfat",
    "low",
    "reduced",
    "fat",
    "from"
}


COOKING_METHODS = {
    "raw",
    "baked",
    "broiled",
    "roasted",
    "grilled",
    "fried",
    "boiled",
    "poached",
    "dried"
}


def normalize_text(text):

    text = str(text).casefold()
    text = text.replace("-", " ")

    text = re.sub(
        r"[^\w\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_words(text):

    normalized_text = normalize_text(text)

    return [
        word
        for word in normalized_text.split()
        if word
    ]


def get_core_search_words(search_text):
    words = get_words(search_text)

    core_words = [
        word
        for word in words
        if word not in SEARCH_MODIFIER_WORDS
    ]

    if core_words:
        return core_words

    return words


def contains_any(text, phrases):
    normalized_text = normalize_text(text)

    return any(
        normalize_text(phrase) in normalized_text
        for phrase in phrases
    )


def calculate_match_score(
    food_name,
    search_text,
    table_name
):
    normalized_name = normalize_text(food_name)
    normalized_search = normalize_text(search_text)

    name_words = set(get_words(food_name))
    search_words = set(get_words(search_text))
    core_words = get_core_search_words(search_text)

    score = 0.0

    if normalized_name == normalized_search:
        score += 500

    if normalized_name.startswith(
        normalized_search
    ):
        score += 140

    if normalized_search in normalized_name:
        score += 80


    for word in core_words:
        if word in name_words:
            score += 50

        elif word in normalized_name:
            score += 15

        else:
            score -= 80


    if table_name == "foods":
        score += 40

    skinless_requested = (
        "skinless" in search_words
        or "skin not eaten" in normalized_search
        or "without skin" in normalized_search
    )

    with_skin_requested = (
        "with skin" in normalized_search
        or "skin eaten" in normalized_search
    )

    name_is_skinless = (
        "skin not eaten" in normalized_name
        or "skinless" in normalized_name
        or "without skin" in normalized_name
    )

    name_has_skin = (
        "skin eaten" in normalized_name
        and "skin not eaten" not in normalized_name
    )

    if skinless_requested:
        if name_is_skinless:
            score += 220

        if name_has_skin:
            score -= 240

    elif with_skin_requested:
        if name_has_skin:
            score += 220

        if name_is_skinless:
            score -= 180

    requested_methods = {
        method
        for method in COOKING_METHODS
        if method in search_words
    }

    for method in requested_methods:
        if method in name_words:
            score += 110
        else:
            score -= 30

    if "raw" in requested_methods:
        if "raw" in name_words:
            score += 80

        if contains_any(
            normalized_name,
            [
                "baked",
                "fried",
                "boiled",
                "roasted",
                "grilled"
            ]
        ):
            score -= 100

    for processed_word in PROCESSED_FOOD_WORDS:
        name_has_processed_word = (
            processed_word in name_words
            or processed_word in normalized_name
        )

        user_requested_processed_word = (
            processed_word in search_words
        )

        if (
            name_has_processed_word
            and user_requested_processed_word
        ):
            score += 90

        elif name_has_processed_word:
            score -= 65

    if (
        "chicken" in core_words
        and "breast" in core_words
        and not requested_methods
    ):
        if contains_any(
            normalized_name,
            [
                "baked",
                "broiled",
                "roasted",
                "grilled"
            ]
        ):
            score += 35

        if contains_any(
            normalized_name,
            [
                "fried",
                "coated",
                "breaded",
                "battered",
                "marinade",
                "marinated"
            ]
        ):
            score -= 130

    for simple_word in SIMPLE_FOOD_WORDS:
        if (
            simple_word in name_words
            and simple_word not in search_words
        ):
            score += 12

    extra_word_count = max(
        0,
        len(name_words) - len(search_words)
    )

    score -= extra_word_count * 1.2
    score -= len(normalized_name) * 0.01

    return score


def build_search_condition(search_words):

    return " AND ".join(
        "LOWER(name) LIKE ?"
        for _ in search_words
    )


def build_search_parameters(search_words):

    return [
        f"%{word}%"
        for word in search_words
    ]


def search_custom_foods(
    cursor,
    search_text
):
    search_words = get_core_search_words(
        search_text
    )

    if not search_words:
        return []

    conditions = build_search_condition(
        search_words
    )

    parameters = build_search_parameters(
        search_words
    )

    query = f"""
        SELECT
            id,
            name,
            calories_per_100g,
            COALESCE(protein_per_100g, 0),
            COALESCE(carbohydrates_per_100g, 0),
            COALESCE(fat_per_100g, 0),
            COALESCE(fiber_per_100g, 0),
            source
        FROM foods
        WHERE {conditions}
        LIMIT 100
    """

    cursor.execute(
        query,
        parameters
    )

    results = []

    for record in cursor.fetchall():
        (
            food_id,
            name,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber,
            source
        ) = record

        results.append(
            {
                "table": "foods",
                "food_id": food_id,
                "fdc_id": None,
                "name": name,
                "calories_per_100g": calories,
                "protein_per_100g": protein,
                "carbohydrates_per_100g": carbohydrates,
                "fat_per_100g": fat,
                "fiber_per_100g": fiber,
                "source": source,
                "score": calculate_match_score(
                    name,
                    search_text,
                    "foods"
                )
            }
        )

    return results


def search_fndds_foods(
    cursor,
    search_text
):
    search_words = get_core_search_words(
        search_text
    )

    if not search_words:
        return []

    conditions = build_search_condition(
        search_words
    )

    parameters = build_search_parameters(
        search_words
    )

    query = f"""
        SELECT
            fdc_id,
            name,
            calories_per_100g,
            COALESCE(protein_per_100g, 0),
            COALESCE(carbohydrates_per_100g, 0),
            COALESCE(fat_per_100g, 0),
            COALESCE(fiber_per_100g, 0),
            source
        FROM fndds_foods
        WHERE {conditions}
        LIMIT 700
    """

    cursor.execute(
        query,
        parameters
    )

    results = []

    for record in cursor.fetchall():
        (
            fdc_id,
            name,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber,
            source
        ) = record

        results.append(
            {
                "table": "fndds_foods",
                "food_id": None,
                "fdc_id": fdc_id,
                "name": name,
                "calories_per_100g": calories,
                "protein_per_100g": protein,
                "carbohydrates_per_100g": carbohydrates,
                "fat_per_100g": fat,
                "fiber_per_100g": fiber,
                "source": source,
                "score": calculate_match_score(
                    name,
                    search_text,
                    "fndds_foods"
                )
            }
        )

    return results


def remove_duplicate_results(results):

    unique_results = []
    used_names = set()

    for result in results:
        normalized_name = normalize_text(
            result["name"]
        )

        if normalized_name in used_names:
            continue

        used_names.add(normalized_name)
        unique_results.append(result)

    return unique_results


def search_all_foods(
    cursor,
    search_text,
    limit=15
):
    results = []

    results.extend(
        search_custom_foods(
            cursor,
            search_text
        )
    )

    results.extend(
        search_fndds_foods(
            cursor,
            search_text
        )
    )

    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    unique_results = remove_duplicate_results(
        results
    )

    return unique_results[:limit]


def display_search_results(results):


    if not results:
        print("\nNo matching foods were found.")
        return

    print("\nBest matching foods:")

    for index, result in enumerate(
        results,
        start=1
    ):
        print("-" * 70)
        print(f"{index}. {result['name']}")

        print(
            "Calories:",
            result["calories_per_100g"],
            "kcal / 100 g"
        )

        print(
            "Protein:",
            result["protein_per_100g"],
            "g"
        )

        print(
            "Carbohydrates:",
            result["carbohydrates_per_100g"],
            "g"
        )

        print(
            "Fat:",
            result["fat_per_100g"],
            "g"
        )

        print("Source:", result["source"])

        print(
            "Match score:",
            round(result["score"], 2)
        )


def main():
    project_directory = (
        Path(__file__).resolve().parent
    )

    database_path = (
        project_directory / "nutrition.db"
    )

    if not database_path.exists():
        print(
            "The nutrition.db file could not be found."
        )
        return

    search_text = input(
        "Enter a food name: "
    ).strip()

    if not search_text:
        print("The food name cannot be empty.")
        return

    connection = sqlite3.connect(
        database_path
    )

    cursor = connection.cursor()

    try:
        results = search_all_foods(
            cursor,
            search_text
        )

        display_search_results(results)

    except sqlite3.Error as error:
        print("\nA database error occurred:")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    main()