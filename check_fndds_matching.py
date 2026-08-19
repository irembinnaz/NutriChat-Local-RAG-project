import csv
from pathlib import Path


def main():
    project_directory = Path(__file__).resolve().parent
    fndds_directory = project_directory / "data" / "fndds_raw"

    food_path = fndds_directory / "food.csv"
    food_nutrient_path = fndds_directory / "food_nutrient.csv"

    food_ids = set()
    nutrient_food_ids = set()

    food_examples = []
    nutrient_examples = []

    print("Checking food.csv...\n")

    with food_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        print("food.csv columns:")
        print(reader.fieldnames)

        for row in reader:
            if row.get("data_type", "").strip() != "survey_fndds_food":
                continue

            fdc_id_text = row.get("fdc_id", "").strip()

            if not fdc_id_text:
                continue

            fdc_id = int(float(fdc_id_text))
            food_ids.add(fdc_id)

            if len(food_examples) < 5:
                food_examples.append(
                    {
                        "fdc_id": fdc_id,
                        "description": row.get("description", "")
                    }
                )

    print("\nChecking food_nutrient.csv...\n")

    with food_nutrient_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        print("food_nutrient.csv columns:")
        print(reader.fieldnames)

        for row in reader:
            fdc_id_text = row.get("fdc_id", "").strip()

            if not fdc_id_text:
                continue

            try:
                fdc_id = int(float(fdc_id_text))
            except ValueError:
                continue

            nutrient_food_ids.add(fdc_id)

            if len(nutrient_examples) < 5:
                nutrient_examples.append(
                    {
                        "fdc_id": fdc_id_text,
                        "nutrient_id": row.get("nutrient_id", ""),
                        "amount": row.get("amount", "")
                    }
                )

    matching_ids = food_ids.intersection(nutrient_food_ids)

    print("\n" + "=" * 60)
    print("CHECK RESULT")
    print("=" * 60)

    print("Number of FNDDS food IDs:", len(food_ids))
    print(
        "Number of food IDs in food_nutrient.csv:",
        len(nutrient_food_ids)
    )
    print("Number of matching IDs:", len(matching_ids))

    print("\nFirst examples from food.csv:")

    for example in food_examples:
        print(example)

    print("\nFirst examples from food_nutrient.csv:")

    for example in nutrient_examples:
        print(example)

    print("\nFirst matching ID values:")
    print(sorted(matching_ids)[:10])


if __name__ == "__main__":
    main()