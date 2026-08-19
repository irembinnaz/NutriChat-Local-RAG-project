from food_search import (
    normalize_text,
    search_all_foods
)


AMBIGUOUS_FOOD_QUERIES = {
    "chicken breast",
    "chicken",
    "bread",
    "yogurt",
    "milk",
    "rice",
    "cheese",
    "beef",
    "fish"
}


EXPLICIT_QUALIFIERS = {
    "raw",
    "baked",
    "dried",
    "fried",
    "boiled",
    "poached",
    "roasted",
    "broiled",
    "grilled",
    "skinless",
    "sweetened",
    "unsweetened",
    "skim",
    "nonfat"
}


def get_words(text):
    return set(
        normalize_text(text).split()
    )


def needs_clarification(
    food_query,
    results
):
    if len(results) < 2:
        return False

    normalized_query = normalize_text(
        food_query
    )

    query_words = get_words(
        food_query
    )

    first_score = results[0]["score"]
    second_score = results[1]["score"]

    score_difference = (
        first_score - second_score
    )

    if normalized_query in AMBIGUOUS_FOOD_QUERIES:
        return True

    has_explicit_qualifier = any(
        qualifier in query_words
        for qualifier in EXPLICIT_QUALIFIERS
    )

    if has_explicit_qualifier:
        return score_difference < 10

    return score_difference < 12


def shorten_food_options(
    results,
    limit=5
):
    selected_results = []
    used_names = set()

    for result in results:
        normalized_name = normalize_text(
            result["name"]
        )

        if normalized_name in used_names:
            continue

        used_names.add(normalized_name)
        selected_results.append(result)

        if len(selected_results) >= limit:
            break

    return selected_results


def ask_user_to_select_food(
    food_query,
    results
):
    options = shorten_food_options(
        results
    )

    print(
        f"\nAssistant: I found several possible "
        f"matches for '{food_query}'."
    )

    print("Which one did you mean?")

    for index, option in enumerate(
        options,
        start=1
    ):
        print(
            f"{index}. {option['name']} "
            f"({option['calories_per_100g']:.1f} "
            f"kcal / 100 g)"
        )

    print("0. None of these")

    try:
        selection_text = input(
            "\nEnter the option number: "
        ).strip()

        selection = int(selection_text)

    except ValueError:
        print(
            "Assistant: Please enter a valid "
            "option number."
        )
        return None

    if selection == 0:
        print(
            "Assistant: Please describe the food "
            "in more detail."
        )
        return None

    if (
        selection < 1
        or selection > len(options)
    ):
        print("Assistant: Invalid option.")
        return None

    return options[selection - 1]


def select_best_food(
    cursor,
    food_query
):
    results = search_all_foods(
        cursor,
        food_query,
        limit=10
    )

    if not results:
        return None, []

    if needs_clarification(
        food_query,
        results
    ):
        selected_food = ask_user_to_select_food(
            food_query,
            results
        )

        return selected_food, results

    return results[0], results