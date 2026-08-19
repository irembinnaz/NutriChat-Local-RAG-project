import sqlite3
from pathlib import Path


def search_fndds_foods(cursor, search_text):

    search_words = [
        word.strip()
        for word in search_text.casefold().replace(",", " ").split()
        if word.strip()
    ]

    if not search_words:
        return []

    conditions = " AND ".join(
        "LOWER(name) LIKE ?"
        for _ in search_words
    )

    parameters = [
        f"%{word}%"
        for word in search_words
    ]

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
        ORDER BY
            LENGTH(name),
            name
        LIMIT 15
    """

    cursor.execute(query, parameters)
    return cursor.fetchall()


def get_portions(cursor, fdc_id):

    cursor.execute(
        """
        SELECT
            id,
            description,
            grams
        FROM fndds_portions
        WHERE fdc_id = ?
        ORDER BY grams
        """,
        (fdc_id,)
    )

    return cursor.fetchall()


def choose_food(foods):

    print("\nMatching foods:")

    for index, food in enumerate(foods, start=1):
        name = food[1]
        calories_per_100g = food[2]

        print(
            f"{index}. {name} "
            f"({calories_per_100g} kcal / 100 g)"
        )

    try:
        selection_text = input(
            "\nSelect the food number: "
        ).strip()

        selection = int(selection_text)

        if selection < 1 or selection > len(foods):
            print("Invalid food selection.")
            return None

    except ValueError:
        print("You must enter a food number.")
        return None

    return foods[selection - 1]


def choose_portion(portions):

    print("\nAvailable portions:")

    for index, portion in enumerate(portions, start=1):
        portion_id, description, grams = portion

        print(
            f"{index}. {description} "
            f"= {grams} grams"
        )

    try:
        selection_text = input(
            "\nSelect the portion number: "
        ).strip()

        selection = int(selection_text)

        if selection < 1 or selection > len(portions):
            print("Invalid portion selection.")
            return None

    except ValueError:
        print("You must enter a portion number.")
        return None

    return portions[selection - 1]


def calculate_portion_nutrition(
    food,
    portion,
    quantity
):


    (
        fdc_id,
        name,
        calories_per_100g,
        protein_per_100g,
        carbohydrates_per_100g,
        fat_per_100g,
        fiber_per_100g,
        source
    ) = food

    (
        portion_id,
        portion_description,
        portion_grams
    ) = portion

    total_grams = portion_grams * quantity
    ratio = total_grams / 100

    result = {
        "name": name,
        "portion": portion_description,
        "quantity": quantity,
        "total_grams": total_grams,
        "calories": calories_per_100g * ratio,
        "protein": protein_per_100g * ratio,
        "carbohydrates": carbohydrates_per_100g * ratio,
        "fat": fat_per_100g * ratio,
        "fiber": fiber_per_100g * ratio,
        "source": source
    }

    return result


def display_result(result):

    print("\n" + "=" * 55)
    print("Food:", result["name"])
    print("Portion:", result["portion"])
    print("Quantity:", result["quantity"])

    print(
        "Estimated total weight:",
        f'{result["total_grams"]:.1f}',
        "grams"
    )

    print("Data source:", result["source"])
    print("=" * 55)

    print(
        f'Calories: {result["calories"]:.1f} kcal'
    )

    print(
        f'Protein: {result["protein"]:.2f} g'
    )

    print(
        "Carbohydrates: "
        f'{result["carbohydrates"]:.2f} g'
    )

    print(
        f'Fat: {result["fat"]:.2f} g'
    )

    print(
        f'Fiber: {result["fiber"]:.2f} g'
    )


def main():
    project_directory = Path(__file__).resolve().parent
    database_path = project_directory / "nutrition.db"

    if not database_path.exists():
        print("The nutrition.db file could not be found.")
        return

    search_text = input(
        "Enter a food name to search: "
    ).strip()

    if not search_text:
        print("The food name cannot be empty.")
        return

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    try:
        foods = search_fndds_foods(
            cursor,
            search_text
        )

        if not foods:
            print(
                f"\nNo FNDDS foods were found for "
                f"'{search_text}'."
            )

            print(
                "Try using fewer or more general words."
            )

            return

        selected_food = choose_food(foods)

        if selected_food is None:
            return

        portions = get_portions(
            cursor,
            selected_food[0]
        )

        if not portions:
            print(
                "\nNo portion information was found "
                "for this food."
            )

            return

        selected_portion = choose_portion(portions)

        if selected_portion is None:
            return

        try:
            quantity_text = input(
                "\nEnter the quantity "
                "(examples: 1, 2, 0.5): "
            ).strip()

            quantity = float(
                quantity_text.replace(",", ".")
            )

            if quantity <= 0:
                print(
                    "The quantity must be greater than zero."
                )

                return

        except ValueError:
            print("You must enter a numeric quantity.")
            return

        result = calculate_portion_nutrition(
            selected_food,
            selected_portion,
            quantity
        )

        display_result(result)

    except sqlite3.Error as error:
        print("\nA database error occurred:")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    main()