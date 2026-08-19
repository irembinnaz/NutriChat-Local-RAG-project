import re
import sqlite3
from datetime import datetime
from pathlib import Path

from food_selector import select_best_food


NUMBER_WORDS = {
    "a": 1.0,
    "an": 1.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "half": 0.5
}


UNIT_NAMES = {
    "g": "gram",
    "gram": "gram",
    "grams": "gram",

    "piece": "piece",
    "pieces": "piece",

    "slice": "slice",
    "slices": "slice",

    "cup": "cup",
    "cups": "cup",

    "bowl": "bowl",
    "bowls": "bowl",

    "plate": "plate",
    "plates": "plate",

    "tablespoon": "tablespoon",
    "tablespoons": "tablespoon",
    "tbsp": "tablespoon",

    "teaspoon": "teaspoon",
    "teaspoons": "teaspoon",
    "tsp": "teaspoon",

    "serving": "serving",
    "servings": "serving",

    "ounce": "ounce",
    "ounces": "ounce",
    "oz": "ounce"
}

GENERAL_PORTION_ESTIMATES = {
    "piece": 100.0,
    "slice": 30.0,
    "cup": 240.0,
    "bowl": 250.0,
    "plate": 250.0,
    "tablespoon": 15.0,
    "teaspoon": 5.0,
    "serving": 100.0,
    "ounce": 28.35
}

FOOD_PORTION_ESTIMATES = {
    "egg": {
        "piece": 50.0
    },
    "apple": {
        "piece": 182.0,
        "slice": 15.0
    },
    "banana": {
        "piece": 118.0,
        "slice": 8.0
    },
    "orange": {
        "piece": 131.0
    },
    "bread": {
        "slice": 28.0,
        "piece": 28.0
    },
    "rice": {
        "cup": 158.0,
        "bowl": 180.0,
        "plate": 200.0,
        "tablespoon": 15.0,
        "serving": 150.0
    },
    "pasta": {
        "cup": 140.0,
        "bowl": 180.0,
        "plate": 200.0,
        "serving": 150.0
    },
    "yogurt": {
        "cup": 245.0,
        "bowl": 200.0,
        "tablespoon": 15.0,
        "serving": 200.0
    },
    "milk": {
        "cup": 244.0
    },
    "chicken breast": {
        "piece": 170.0,
        "serving": 100.0
    }
}


def normalize_text(text):
    text = text.casefold()
    text = text.replace("-", " ")

    text = re.sub(
        r"[^\w\s.]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def parse_number(value):
    cleaned_value = value.casefold().strip()

    if cleaned_value in NUMBER_WORDS:
        return NUMBER_WORDS[cleaned_value]

    return float(cleaned_value)


def singular_unit(unit):
    if unit is None:
        return None

    cleaned_unit = unit.casefold().strip()

    return UNIT_NAMES.get(
        cleaned_unit,
        cleaned_unit
    )


def display_unit(unit, quantity):
    if quantity == 1:
        return unit

    plural_units = {
        "gram": "grams",
        "piece": "pieces",
        "slice": "slices",
        "cup": "cups",
        "bowl": "bowls",
        "plate": "plates",
        "tablespoon": "tablespoons",
        "teaspoon": "teaspoons",
        "serving": "servings",
        "ounce": "ounces"
    }

    return plural_units.get(unit, unit)


def clean_meal_message(user_text):

    text = user_text.strip()

    introductory_patterns = [
        r"^\s*today\s+i\s+ate\s+",
        r"^\s*today\s+i\s+had\s+",
        r"^\s*i\s+have\s+eaten\s+",
        r"^\s*i\s+ate\s+",
        r"^\s*i\s+had\s+",
        r"^\s*for\s+breakfast\s+i\s+ate\s+",
        r"^\s*for\s+lunch\s+i\s+ate\s+",
        r"^\s*for\s+dinner\s+i\s+ate\s+"
    ]

    for pattern in introductory_patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

    return text.strip()


def split_meal_into_parts(user_text):
    cleaned_text = clean_meal_message(user_text)

    parts = re.split(
        r"\s*,\s*|\s+\band\b\s+",
        cleaned_text,
        flags=re.IGNORECASE
    )

    return [
        part.strip(" .")
        for part in parts
        if part.strip(" .")
    ]


def singularize_food_query(food_query):
    words = normalize_text(food_query).split()

    special_words = {
        "eggs": "egg",
        "apples": "apple",
        "bananas": "banana",
        "oranges": "orange",
        "breads": "bread",
        "potatoes": "potato",
        "tomatoes": "tomato",
        "berries": "berry",
        "strawberries": "strawberry",
        "blueberries": "blueberry",
        "cherries": "cherry"
    }

    normalized_words = []

    for word in words:
        normalized_words.append(
            special_words.get(word, word)
        )

    return " ".join(normalized_words)


def infer_default_unit(food_query):

    normalized_query = normalize_text(food_query)

    if any(
        word in normalized_query
        for word in [
            "bread",
            "toast"
        ]
    ):
        return "slice"

    if any(
        word in normalized_query
        for word in [
            "rice",
            "pasta",
            "bulgur",
            "couscous"
        ]
    ):
        return "plate"

    if any(
        word in normalized_query
        for word in [
            "yogurt",
            "soup",
            "oatmeal",
            "cereal"
        ]
    ):
        return "bowl"

    if any(
        word in normalized_query
        for word in [
            "milk",
            "juice",
            "coffee",
            "tea"
        ]
    ):
        return "cup"

    if any(
        word in normalized_query
        for word in [
            "egg",
            "apple",
            "banana",
            "orange",
            "pear",
            "potato",
            "tomato"
        ]
    ):
        return "piece"

    return "serving"


def parse_food_part(food_part):

    normalized_part = normalize_text(food_part)

    half_pattern = re.fullmatch(
        r"half\s+"
        r"(?:a\s+|an\s+)?"
        r"(?P<unit>"
        r"plates?|bowls?|cups?|slices?|pieces?|"
        r"servings?|tablespoons?|teaspoons?"
        r")"
        r"(?:\s+of)?\s+"
        r"(?P<food>.+)",
        normalized_part
    )

    if half_pattern:
        food_query = singularize_food_query(
            half_pattern.group("food")
        )

        return {
            "quantity": 0.5,
            "unit": singular_unit(
                half_pattern.group("unit")
            ),
            "food_query": food_query
        }

    quantity_unit_pattern = re.fullmatch(
        r"(?P<quantity>"
        r"\d+(?:\.\d+)?|"
        r"a|an|one|two|three|four|five|"
        r"six|seven|eight|nine|ten"
        r")\s*"
        r"(?P<unit>"
        r"g|grams?|pieces?|slices?|cups?|bowls?|"
        r"plates?|servings?|tablespoons?|teaspoons?|"
        r"tbsp|tsp|ounces?|oz"
        r")"
        r"(?:\s+of)?\s+"
        r"(?P<food>.+)",
        normalized_part
    )

    if quantity_unit_pattern:
        food_query = singularize_food_query(
            quantity_unit_pattern.group("food")
        )

        return {
            "quantity": parse_number(
                quantity_unit_pattern.group("quantity")
            ),
            "unit": singular_unit(
                quantity_unit_pattern.group("unit")
            ),
            "food_query": food_query
        }

    quantity_food_pattern = re.fullmatch(
        r"(?P<quantity>"
        r"\d+(?:\.\d+)?|"
        r"a|an|one|two|three|four|five|"
        r"six|seven|eight|nine|ten"
        r")\s+"
        r"(?P<food>.+)",
        normalized_part
    )

    if quantity_food_pattern:
        food_query = singularize_food_query(
            quantity_food_pattern.group("food")
        )

        return {
            "quantity": parse_number(
                quantity_food_pattern.group("quantity")
            ),
            "unit": infer_default_unit(food_query),
            "food_query": food_query
        }

    food_query = singularize_food_query(
        normalized_part
    )

    return {
        "quantity": 1.0,
        "unit": infer_default_unit(food_query),
        "food_query": food_query
    }


def choose_best_food(cursor, food_query):
    return select_best_food(
        cursor,
        food_query
    )


def get_custom_portion_grams(
    cursor,
    food_result,
    unit
):

    if food_result["table"] != "foods":
        return None

    cursor.execute(
        """
        SELECT
            portion_name,
            portion_grams
        FROM foods
        WHERE id = ?
        """,
        (food_result["food_id"],)
    )

    record = cursor.fetchone()

    if record is None:
        return None

    portion_name, portion_grams = record

    if (
        portion_name
        and portion_grams
        and unit in normalize_text(portion_name)
    ):
        return float(portion_grams)

    return None


def get_fndds_portion_grams(
    cursor,
    food_result,
    unit
):

    if (
        food_result["table"] != "fndds_foods"
        or food_result["fdc_id"] is None
    ):
        return None

    cursor.execute(
        """
        SELECT
            description,
            grams
        FROM fndds_portions
        WHERE fdc_id = ?
          AND grams > 0
        ORDER BY grams
        """,
        (food_result["fdc_id"],)
    )

    portions = cursor.fetchall()

    unit_keywords = {
        "piece": [
            "piece",
            "item",
            "medium",
            "small",
            "large",
            "whole",
            "each"
        ],
        "slice": [
            "slice"
        ],
        "cup": [
            "cup"
        ],
        "bowl": [
            "bowl"
        ],
        "plate": [
            "plate"
        ],
        "tablespoon": [
            "tablespoon",
            "tbsp"
        ],
        "teaspoon": [
            "teaspoon",
            "tsp"
        ],
        "serving": [
            "serving"
        ],
        "ounce": [
            "ounce",
            "oz"
        ]
    }

    keywords = unit_keywords.get(unit, [])

    matching_portions = []

    for description, grams in portions:
        normalized_description = normalize_text(
            description or ""
        )

        score = sum(
            1
            for keyword in keywords
            if keyword in normalized_description
        )

        if score > 0:
            matching_portions.append(
                (
                    score,
                    len(normalized_description),
                    float(grams)
                )
            )

    if not matching_portions:
        return None

    matching_portions.sort(
        key=lambda item: (
            -item[0],
            item[1]
        )
    )

    return matching_portions[0][2]


def get_fallback_portion_grams(
    food_query,
    unit
):

    normalized_query = normalize_text(food_query)

    for food_keyword, unit_values in (
        FOOD_PORTION_ESTIMATES.items()
    ):
        if food_keyword in normalized_query:
            if unit in unit_values:
                return unit_values[unit]

    return GENERAL_PORTION_ESTIMATES.get(unit)


def calculate_total_grams(
    cursor,
    food_result,
    food_query,
    quantity,
    unit
):

    if unit == "gram":
        return quantity, "exact grams"

    if unit == "ounce":
        return (
            quantity * 28.35,
            "ounce conversion"
        )

    portion_grams = get_custom_portion_grams(
        cursor,
        food_result,
        unit
    )

    portion_source = "custom food portion"

    if portion_grams is None:
        portion_grams = get_fndds_portion_grams(
            cursor,
            food_result,
            unit
        )

        portion_source = "FNDDS portion"

    if portion_grams is None:
        portion_grams = get_fallback_portion_grams(
            food_query,
            unit
        )

        portion_source = "estimated portion"

    if portion_grams is None:
        raise ValueError(
            f"No gram value could be found for "
            f"'{unit}' of {food_query}."
        )

    return (
        quantity * portion_grams,
        portion_source
    )


def calculate_food_nutrition(
    cursor,
    parsed_food
):

    food_query = parsed_food["food_query"]
    quantity = parsed_food["quantity"]
    unit = parsed_food["unit"]

    food_result, alternatives = choose_best_food(
        cursor,
        food_query
    )

    if food_result is None:
        raise LookupError(
            f"No food record was selected for "
            f"'{food_query}'."
        )

    total_grams, portion_source = (
        calculate_total_grams(
            cursor,
            food_result,
            food_query,
            quantity,
            unit
        )
    )

    ratio = total_grams / 100

    return {
        "food_query": food_query,
        "database_name": food_result["name"],
        "quantity": quantity,
        "unit": unit,
        "grams": total_grams,

        "calories": (
            food_result["calories_per_100g"]
            * ratio
        ),

        "protein": (
            food_result["protein_per_100g"]
            * ratio
        ),

        "carbohydrates": (
            food_result["carbohydrates_per_100g"]
            * ratio
        ),

        "fat": (
            food_result["fat_per_100g"]
            * ratio
        ),

        "fiber": (
            food_result["fiber_per_100g"]
            * ratio
        ),

        "source": food_result["source"],
        "portion_source": portion_source,
        "alternatives": alternatives
    }


def calculate_totals(results):
    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "carbohydrates": 0.0,
        "fat": 0.0,
        "fiber": 0.0
    }

    for result in results:
        totals["calories"] += result["calories"]
        totals["protein"] += result["protein"]

        totals["carbohydrates"] += (
            result["carbohydrates"]
        )

        totals["fat"] += result["fat"]
        totals["fiber"] += result["fiber"]

    return totals


def display_meal_result(results):
    print("\nI understood the following meal:")

    for result in results:
        unit_text = display_unit(
            result["unit"],
            result["quantity"]
        )

        print(
            f"- {result['quantity']:g} "
            f"{unit_text} of "
            f"{result['food_query']}"
        )

        print(
            "  Matched food:",
            result["database_name"]
        )

        print(
            "  Estimated weight:",
            f'{result["grams"]:.1f} g'
        )

        print(
            "  Portion source:",
            result["portion_source"]
        )

    totals = calculate_totals(results)

    print("\n" + "=" * 60)
    print("Estimated meal total")
    print("=" * 60)

    print(
        f"Calories: {totals['calories']:.1f} kcal"
    )

    print(
        f"Protein: {totals['protein']:.2f} g"
    )

    print(
        "Carbohydrates: "
        f"{totals['carbohydrates']:.2f} g"
    )

    print(
        f"Fat: {totals['fat']:.2f} g"
    )

    print(
        f"Fiber: {totals['fiber']:.2f} g"
    )

    print(
        "\nPortions marked as estimates may vary "
        "depending on serving size."
    )


def create_meal_tables(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            meal_log_id INTEGER NOT NULL,

            food_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            grams REAL NOT NULL,

            calories REAL NOT NULL,
            protein REAL NOT NULL,
            carbohydrates REAL NOT NULL,
            fat REAL NOT NULL,
            fiber REAL NOT NULL,

            source TEXT,

            FOREIGN KEY (meal_log_id)
                REFERENCES meal_logs(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()


def save_meal(
    connection,
    user_message,
    results
):
    cursor = connection.cursor()

    created_at = datetime.now().isoformat(
        timespec="seconds"
    )

    try:
        cursor.execute(
            """
            INSERT INTO meal_logs (
                user_message,
                created_at
            )
            VALUES (?, ?)
            """,
            (
                user_message,
                created_at
            )
        )

        meal_log_id = cursor.lastrowid

        for result in results:
            cursor.execute(
                """
                INSERT INTO meal_items (
                    meal_log_id,
                    food_name,
                    quantity,
                    unit,
                    grams,
                    calories,
                    protein,
                    carbohydrates,
                    fat,
                    fiber,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_log_id,
                    result["database_name"],
                    result["quantity"],
                    result["unit"],
                    result["grams"],
                    result["calories"],
                    result["protein"],
                    result["carbohydrates"],
                    result["fat"],
                    result["fiber"],
                    result["source"]
                )
            )

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        raise


def is_greeting(text):

    normalized_text = normalize_text(text)

    greetings = {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
    }

    return normalized_text in greetings


def is_today_summary_question(text):

    normalized_text = normalize_text(text)

    phrases = [
        "what did i eat today",
        "what have i eaten today",
        "how many calories did i eat today",
        "how many calories have i consumed today",
        "how many calories today",
        "calories today",
        "daily total",
        "my total today",
        "show todays total",
        "show today s total"
    ]

    return any(
        phrase in normalized_text
        for phrase in phrases
    )


def display_today_summary(cursor):


    today = datetime.now().date().isoformat()

    cursor.execute(
        """
        SELECT
            meal_items.food_name,
            meal_items.quantity,
            meal_items.unit,
            meal_items.grams,
            meal_items.calories,
            meal_items.protein,
            meal_items.carbohydrates,
            meal_items.fat,
            meal_items.fiber,
            meal_logs.created_at
        FROM meal_items
        INNER JOIN meal_logs
            ON meal_items.meal_log_id = meal_logs.id
        WHERE SUBSTR(meal_logs.created_at, 1, 10) = ?
        ORDER BY
            meal_logs.created_at,
            meal_items.id
        """,
        (today,)
    )

    records = cursor.fetchall()

    if not records:
        print(
            "Assistant: You have not recorded "
            "any meals today."
        )
        return

    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "carbohydrates": 0.0,
        "fat": 0.0,
        "fiber": 0.0
    }

    print("Assistant:")
    print("\nFoods recorded today:")

    for record in records:
        (
            food_name,
            quantity,
            unit,
            grams,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber,
            created_at
        ) = record

        unit_text = display_unit(
            unit,
            quantity
        )

        time_text = created_at[11:16]

        print(
            f"- {quantity:g} {unit_text} of "
            f"{food_name} "
            f"({grams:.1f} g, "
            f"{calories:.1f} kcal, "
            f"{time_text})"
        )

        totals["calories"] += calories
        totals["protein"] += protein
        totals["carbohydrates"] += carbohydrates
        totals["fat"] += fat
        totals["fiber"] += fiber

    print("\n" + "=" * 60)
    print("Today's nutritional total")
    print("=" * 60)

    print(
        f"Calories: {totals['calories']:.1f} kcal"
    )

    print(
        f"Protein: {totals['protein']:.2f} g"
    )

    print(
        "Carbohydrates: "
        f"{totals['carbohydrates']:.2f} g"
    )

    print(
        f"Fat: {totals['fat']:.2f} g"
    )

    print(
        f"Fiber: {totals['fiber']:.2f} g"
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

    print("Nutrition Assistant")

    print(
        "Describe a meal or ask for today's total. "
        "Type 'exit' to close the program."
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    create_meal_tables(connection)

    cursor = connection.cursor()

    try:
        while True:
            user_text = input("\nYou: ").strip()

            if not user_text:
                continue

            if user_text.casefold() in {
                "exit",
                "quit",
                "bye"
            }:
                print(
                    "Assistant: Goodbye! "
                    "Have a healthy day."
                )
                break

            if is_greeting(user_text):
                print(
                    "Assistant: Hello! "
                    "Tell me what you ate today."
                )
                continue

            if is_today_summary_question(user_text):
                display_today_summary(cursor)
                continue

            meal_parts = split_meal_into_parts(
                user_text
            )

            parsed_foods = [
                parse_food_part(part)
                for part in meal_parts
            ]

            results = []
            errors = []

            for parsed_food in parsed_foods:
                try:
                    result = calculate_food_nutrition(
                        cursor,
                        parsed_food
                    )

                    results.append(result)

                except (
                    ValueError,
                    LookupError
                ) as error:
                    errors.append(str(error))

            if errors:
                print("Assistant:")

                for error in errors:
                    print("-", error)

            if not results:
                print(
                    "Assistant: I could not calculate "
                    "this meal."
                )
                continue

            print("Assistant:")
            display_meal_result(results)

            save_meal(
                connection,
                user_text,
                results
            )

            print(
                "\nAssistant: This meal was saved "
                "to today's food log."
            )

    except sqlite3.Error as error:
        print("\nA database error occurred:")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    main()