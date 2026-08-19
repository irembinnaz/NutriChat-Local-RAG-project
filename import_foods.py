import csv
import sqlite3
from pathlib import Path


def to_float(value):

    if value is None:
        return None

    cleaned_value = str(value).strip()

    if not cleaned_value:
        return None

    try:
        return float(cleaned_value.replace(",", "."))
    except ValueError:
        return None


def import_foods():

    project_directory = Path(__file__).resolve().parent

    csv_path = project_directory / "data" / "foods.csv"
    database_path = project_directory / "nutrition.db"

    if not csv_path.exists():
        print("The foods.csv file could not be found.")
        print("Expected location:", csv_path)
        return

    if not database_path.exists():
        print("The nutrition.db file could not be found.")
        print("Run database.py first.")
        return

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    imported_food_count = 0

    try:
        with csv_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline=""
        ) as csv_file:

            reader = csv.DictReader(
                csv_file,
                delimiter=";"
            )

            required_columns = {
                "name",
                "category",
                "calories_per_100g",
                "protein_per_100g",
                "carbohydrates_per_100g",
                "fat_per_100g",
                "fiber_per_100g",
                "portion_name",
                "portion_grams",
                "source"
            }

            existing_columns = set(
                reader.fieldnames or []
            )

            missing_columns = (
                required_columns - existing_columns
            )

            if missing_columns:
                print(
                    "The following columns are missing "
                    "from foods.csv:"
                )

                for column in sorted(missing_columns):
                    print("-", column)

                return

            for row in reader:
                name = row["name"].strip()

                if not name:
                    continue

                calories = to_float(
                    row["calories_per_100g"]
                )

                protein = to_float(
                    row["protein_per_100g"]
                )

                carbohydrates = to_float(
                    row["carbohydrates_per_100g"]
                )

                fat = to_float(
                    row["fat_per_100g"]
                )

                fiber = to_float(
                    row["fiber_per_100g"]
                )

                portion_grams = to_float(
                    row["portion_grams"]
                )


                if (
                    calories is None
                    or protein is None
                    or carbohydrates is None
                    or fat is None
                ):
                    print(
                        f"Skipped '{name}' because one or more "
                        "required nutritional values are missing."
                    )
                    continue

                cursor.execute(
                    """
                    INSERT INTO foods (
                        name,
                        category,
                        calories_per_100g,
                        protein_per_100g,
                        carbohydrates_per_100g,
                        fat_per_100g,
                        fiber_per_100g,
                        portion_name,
                        portion_grams,
                        source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(name) DO UPDATE SET
                        category = excluded.category,
                        calories_per_100g =
                            excluded.calories_per_100g,
                        protein_per_100g =
                            excluded.protein_per_100g,
                        carbohydrates_per_100g =
                            excluded.carbohydrates_per_100g,
                        fat_per_100g =
                            excluded.fat_per_100g,
                        fiber_per_100g =
                            excluded.fiber_per_100g,
                        portion_name =
                            excluded.portion_name,
                        portion_grams =
                            excluded.portion_grams,
                        source = excluded.source
                    """,
                    (
                        name,
                        row["category"].strip() or None,
                        calories,
                        protein,
                        carbohydrates,
                        fat,
                        fiber,
                        row["portion_name"].strip() or None,
                        portion_grams,
                        row["source"].strip()
                    )
                )

                imported_food_count += 1

        connection.commit()

        print(
            f"{imported_food_count} foods were imported "
            "from the CSV file into the database."
        )

        cursor.execute(
            """
            SELECT
                name,
                calories_per_100g,
                protein_per_100g,
                carbohydrates_per_100g,
                fat_per_100g
            FROM foods
            ORDER BY name
            """
        )

        foods = cursor.fetchall()

        print("\nFoods currently stored in the database:")

        for food in foods:
            (
                name,
                calories,
                protein,
                carbohydrates,
                fat
            ) = food

            print("-" * 40)
            print("Food:", name)
            print(
                "Calories:",
                calories,
                "kcal / 100 g"
            )
            print("Protein:", protein, "g")
            print(
                "Carbohydrates:",
                carbohydrates,
                "g"
            )
            print("Fat:", fat, "g")

    except Exception as error:
        connection.rollback()

        print("\nAn error occurred during the food import:")
        print(type(error).__name__ + ":", error)

    finally:
        connection.close()


if __name__ == "__main__":
    import_foods()