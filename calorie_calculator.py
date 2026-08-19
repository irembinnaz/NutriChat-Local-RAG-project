
import sqlite3
from pathlib import Path


def find_food(cursor, food_name):

    cursor.execute(
        """
        SELECT
            name,
            calories_per_100g,
            protein_per_100g,
            carbohydrates_per_100g,
            fat_per_100g,
            COALESCE(fiber_per_100g, 0),
            source
        FROM foods
        WHERE LOWER(name) = LOWER(?)

        UNION ALL

        SELECT
            name,
            calories_per_100g,
            COALESCE(protein_per_100g, 0),
            COALESCE(carbohydrates_per_100g, 0),
            COALESCE(fat_per_100g, 0),
            COALESCE(fiber_per_100g, 0),
            source
        FROM fndds_foods
        WHERE LOWER(name) = LOWER(?)

        LIMIT 1
        """,
        (
            food_name,
            food_name
        )
    )

    return cursor.fetchone()


def find_similar_foods(cursor, food_name):

    search_value = f"%{food_name}%"

    cursor.execute(
        """
        SELECT name
        FROM foods
        WHERE LOWER(name) LIKE LOWER(?)

        UNION

        SELECT name
        FROM fndds_foods
        WHERE LOWER(name) LIKE LOWER(?)

        ORDER BY name
        LIMIT 10
        """,
        (
            search_value,
            search_value
        )
    )

    return cursor.fetchall()


def calculate_calories():
    project_directory = Path(__file__).resolve().parent
    database_path = project_directory / "nutrition.db"

    if not database_path.exists():
        print("The nutrition.db file could not be found.")
        return

    food_name = input("Enter the exact food name: ").strip()

    if not food_name:
        print("The food name cannot be empty.")
        return

    try:
        grams_text = input("How many grams did you eat? ").strip()
        grams = float(grams_text.replace(",", "."))

        if grams <= 0:
            print("The gram amount must be greater than zero.")
            return

    except ValueError:
        print("You must enter the gram amount as a number.")
        return

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    try:
        food = find_food(
            cursor,
            food_name
        )

        if food is None:
            print(
                f"\n'{food_name}' was not found "
                "as an exact food name."
            )

            similar_foods = find_similar_foods(
                cursor,
                food_name
            )

            if similar_foods:
                print("\nSimilar food names:")

                for similar_food in similar_foods:
                    print("-", similar_food[0])

                print(
                    "\nRun the program again and enter "
                    "one of these names exactly."
                )

            else:
                print("No similar food names were found.")

            return

        (
            name,
            calories_per_100g,
            protein_per_100g,
            carbohydrates_per_100g,
            fat_per_100g,
            fiber_per_100g,
            source
        ) = food

        ratio = grams / 100

        calories = calories_per_100g * ratio
        protein = protein_per_100g * ratio
        carbohydrates = carbohydrates_per_100g * ratio
        fat = fat_per_100g * ratio
        fiber = fiber_per_100g * ratio

        print("\n" + "=" * 50)
        print("Food:", name)
        print("Amount consumed:", grams, "grams")
        print("Data source:", source)
        print("=" * 50)

        print(f"Calories: {calories:.1f} kcal")
        print(f"Protein: {protein:.2f} g")
        print(f"Carbohydrates: {carbohydrates:.2f} g")
        print(f"Fat: {fat:.2f} g")
        print(f"Fiber: {fiber:.2f} g")

    except sqlite3.Error as error:
        print("\nA database error occurred:")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    calculate_calories()