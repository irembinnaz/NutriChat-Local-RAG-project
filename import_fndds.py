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


def find_nutrient_numbers(nutrient_path):

    targets = {
        "calories": None,
        "protein": None,
        "carbohydrates": None,
        "fat": None,
        "fiber": None
    }

    with nutrient_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            nutrient_number_text = row.get(
                "nutrient_nbr",
                ""
            ).strip()

            if not nutrient_number_text:
                continue

            try:
                nutrient_number = int(
                    float(nutrient_number_text)
                )
            except ValueError:
                continue

            nutrient_name = row.get(
                "name",
                ""
            ).strip()

            unit_name = row.get(
                "unit_name",
                ""
            ).strip().casefold()

            if (
                nutrient_name == "Energy"
                and unit_name == "kcal"
            ):
                targets["calories"] = nutrient_number

            elif nutrient_name == "Protein":
                targets["protein"] = nutrient_number

            elif nutrient_name == "Carbohydrate, by difference":
                targets["carbohydrates"] = nutrient_number

            elif nutrient_name == "Total lipid (fat)":
                targets["fat"] = nutrient_number

            elif nutrient_name == "Fiber, total dietary":
                targets["fiber"] = nutrient_number

    missing_nutrients = [
        field_name
        for field_name, nutrient_number in targets.items()
        if nutrient_number is None
    ]

    if missing_nutrients:
        raise ValueError(
            "The following nutrients could not be found: "
            + ", ".join(missing_nutrients)
        )

    return targets


def read_fndds_foods(food_path):

    foods = {}

    with food_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            data_type = row.get(
                "data_type",
                ""
            ).strip()

            if data_type != "survey_fndds_food":
                continue

            fdc_id_text = row.get(
                "fdc_id",
                ""
            ).strip()

            if not fdc_id_text:
                continue

            try:
                fdc_id = int(float(fdc_id_text))
            except ValueError:
                continue

            food_name = row.get(
                "description",
                ""
            ).strip()

            if not food_name:
                continue

            foods[fdc_id] = {
                "name": food_name,
                "calories": None,
                "protein": None,
                "carbohydrates": None,
                "fat": None,
                "fiber": None
            }

    return foods


def read_nutrient_values(
    food_nutrient_path,
    foods,
    nutrient_numbers
):
    number_to_field = {
        nutrient_numbers["calories"]: "calories",
        nutrient_numbers["protein"]: "protein",
        nutrient_numbers["carbohydrates"]: "carbohydrates",
        nutrient_numbers["fat"]: "fat",
        nutrient_numbers["fiber"]: "fiber"
    }

    values_read = 0
    foods_with_calories = set()

    with food_nutrient_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            fdc_id_text = row.get(
                "fdc_id",
                ""
            ).strip()

            nutrient_id_text = row.get(
                "nutrient_id",
                ""
            ).strip()

            if not fdc_id_text or not nutrient_id_text:
                continue

            try:
                fdc_id = int(float(fdc_id_text))
                nutrient_id = int(float(nutrient_id_text))
            except ValueError:
                continue

            if fdc_id not in foods:
                continue

            field_name = number_to_field.get(
                nutrient_id
            )

            if field_name is None:
                continue

            amount = to_float(
                row.get("amount")
            )

            if amount is None:
                continue

            foods[fdc_id][field_name] = amount
            values_read += 1

            if field_name == "calories":
                foods_with_calories.add(fdc_id)

    print(
        "Foods with calorie information:",
        len(foods_with_calories)
    )

    print(
        "Calorie and macronutrient values read:",
        values_read
    )


def read_measure_units(measure_unit_path):

    units = {}

    with measure_unit_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            unit_id_text = row.get(
                "id",
                ""
            ).strip()

            if not unit_id_text:
                continue

            try:
                unit_id = int(float(unit_id_text))
            except ValueError:
                continue

            unit_name = (
                row.get("name", "").strip()
                or row.get("abbreviation", "").strip()
            )

            units[unit_id] = unit_name

    return units


def format_amount(amount_text):

    amount = to_float(amount_text)

    if amount is None:
        return str(amount_text).strip()

    if amount.is_integer():
        return str(int(amount))

    return str(amount)


def read_portions(
    food_portion_path,
    foods,
    measure_units
):
    portions = []

    with food_portion_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            fdc_id_text = row.get(
                "fdc_id",
                ""
            ).strip()

            if not fdc_id_text:
                continue

            try:
                fdc_id = int(float(fdc_id_text))
            except ValueError:
                continue

            if fdc_id not in foods:
                continue

            grams = to_float(
                row.get("gram_weight")
            )

            if grams is None or grams <= 0:
                continue

            amount_text = row.get(
                "amount",
                ""
            ).strip()

            modifier = row.get(
                "modifier",
                ""
            ).strip()

            portion_description = row.get(
                "portion_description",
                ""
            ).strip()

            unit_id_text = row.get(
                "measure_unit_id",
                ""
            ).strip()

            unit_name = ""

            if unit_id_text:
                try:
                    unit_id = int(
                        float(unit_id_text)
                    )

                    unit_name = measure_units.get(
                        unit_id,
                        ""
                    )

                except ValueError:
                    unit_name = ""

            description_parts = []

            if amount_text:
                description_parts.append(
                    format_amount(amount_text)
                )

            if unit_name:
                description_parts.append(
                    unit_name
                )

            if modifier:
                description_parts.append(
                    modifier
                )

            description = " ".join(
                description_parts
            ).strip()

            if not description:
                description = portion_description

            elif (
                portion_description
                and portion_description.casefold()
                not in description.casefold()
            ):
                description += (
                    f" ({portion_description})"
                )

            if not description:
                description = "Portion"

            portions.append(
                (
                    fdc_id,
                    description,
                    grams
                )
            )

    return portions


def import_to_database(
    database_path,
    foods,
    portions
):
    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    cursor = connection.cursor()

    try:

        cursor.execute(
            "DROP TABLE IF EXISTS fndds_portions"
        )

        cursor.execute(
            "DROP TABLE IF EXISTS fndds_foods"
        )


        cursor.execute(
            "DROP TABLE IF EXISTS fndds_porsiyonlar"
        )

        cursor.execute(
            "DROP TABLE IF EXISTS fndds_besinler"
        )

        cursor.execute(
            """
            CREATE TABLE fndds_foods (
                fdc_id INTEGER PRIMARY KEY,

                name TEXT NOT NULL,

                calories_per_100g REAL NOT NULL,
                protein_per_100g REAL,
                carbohydrates_per_100g REAL,
                fat_per_100g REAL,
                fiber_per_100g REAL,

                source TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE fndds_portions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                fdc_id INTEGER NOT NULL,

                description TEXT NOT NULL,
                grams REAL NOT NULL,

                FOREIGN KEY (fdc_id)
                    REFERENCES fndds_foods(fdc_id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX idx_fndds_food_name
            ON fndds_foods(name)
            """
        )

        cursor.execute(
            """
            CREATE INDEX idx_fndds_portion_fdc_id
            ON fndds_portions(fdc_id)
            """
        )

        food_records = []

        for fdc_id, food_information in foods.items():

            if food_information["calories"] is None:
                continue

            food_records.append(
                (
                    fdc_id,
                    food_information["name"],
                    food_information["calories"],
                    food_information["protein"],
                    food_information["carbohydrates"],
                    food_information["fat"],
                    food_information["fiber"],
                    "USDA FNDDS 2021-2023"
                )
            )

        cursor.executemany(
            """
            INSERT INTO fndds_foods (
                fdc_id,
                name,
                calories_per_100g,
                protein_per_100g,
                carbohydrates_per_100g,
                fat_per_100g,
                fiber_per_100g,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            food_records
        )

        inserted_fdc_ids = {
            record[0]
            for record in food_records
        }

        valid_portions = [
            (
                fdc_id,
                description,
                grams
            )
            for fdc_id, description, grams in portions
            if fdc_id in inserted_fdc_ids
        ]

        cursor.executemany(
            """
            INSERT INTO fndds_portions (
                fdc_id,
                description,
                grams
            )
            VALUES (?, ?, ?)
            """,
            valid_portions
        )

        connection.commit()

        print("\nImport completed successfully.")

        print(
            "FNDDS foods imported:",
            len(food_records)
        )

        print(
            "Portions imported:",
            len(valid_portions)
        )

        print("\nFirst 10 example foods:")

        cursor.execute(
            """
            SELECT
                fdc_id,
                name,
                calories_per_100g,
                protein_per_100g,
                carbohydrates_per_100g,
                fat_per_100g
            FROM fndds_foods
            ORDER BY name
            LIMIT 10
            """
        )

        for record in cursor.fetchall():
            (
                fdc_id,
                name,
                calories,
                protein,
                carbohydrates,
                fat
            ) = record

            print("-" * 55)
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
            print("FDC ID:", fdc_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def main():
    project_directory = Path(__file__).resolve().parent

    fndds_directory = (
        project_directory
        / "data"
        / "fndds_raw"
    )

    database_path = (
        project_directory
        / "nutrition.db"
    )

    required_files = {
        "food": (
            fndds_directory
            / "food.csv"
        ),
        "nutrient": (
            fndds_directory
            / "nutrient.csv"
        ),
        "food_nutrient": (
            fndds_directory
            / "food_nutrient.csv"
        ),
        "food_portion": (
            fndds_directory
            / "food_portion.csv"
        ),
        "measure_unit": (
            fndds_directory
            / "measure_unit.csv"
        )
    }

    print("Starting FNDDS import...")
    print("Data directory:", fndds_directory)
    print("Database:", database_path)

    for file_name, file_path in required_files.items():
        if not file_path.exists():
            print("\nMissing file:", file_name)
            print("Expected location:", file_path)
            return

    try:
        print(
            "\nFinding nutrient numbers..."
        )

        nutrient_numbers = find_nutrient_numbers(
            required_files["nutrient"]
        )

        print(
            "Nutrient numbers found:",
            nutrient_numbers
        )

        print("\nReading FNDDS foods...")

        foods = read_fndds_foods(
            required_files["food"]
        )

        print(
            "FNDDS foods found:",
            len(foods)
        )

        print(
            "\nReading calorie and "
            "macronutrient values..."
        )

        read_nutrient_values(
            required_files["food_nutrient"],
            foods,
            nutrient_numbers
        )

        foods_with_calories = sum(
            1
            for food_information in foods.values()
            if food_information["calories"] is not None
        )

        print(
            "Total foods with calorie information:",
            foods_with_calories
        )

        print("\nReading measurement units...")

        measure_units = read_measure_units(
            required_files["measure_unit"]
        )

        print(
            "Measurement units found:",
            len(measure_units)
        )

        print("\nReading portions...")

        portions = read_portions(
            required_files["food_portion"],
            foods,
            measure_units
        )

        print(
            "Portions found:",
            len(portions)
        )

        print(
            "\nImporting data into SQLite..."
        )

        import_to_database(
            database_path,
            foods,
            portions
        )

    except Exception as error:
        print("\nAn error occurred during the import:")
        print(type(error).__name__ + ":", error)


if __name__ == "__main__":
    main()