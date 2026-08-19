import csv
from pathlib import Path


def check_csv_file(file_path: Path):
    print("\n" + "=" * 70)
    print("File:", file_path.name)
    print("=" * 70)

    if not file_path.exists():
        print("File not found.")
        return

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        print("Columns:")

        if reader.fieldnames:
            for column in reader.fieldnames:
                print("-", column)
        else:
            print("No columns were found.")
            return

        first_row = next(reader, None)

        print("\nExample from the first record:")

        if first_row is None:
            print("No data rows were found in the file.")
        else:
            for key, value in first_row.items():
                print(f"{key}: {value}")


def main():
    project_directory = Path(__file__).resolve().parent
    fndds_directory = project_directory / "data" / "fndds_raw"

    files_to_check = [
        "food.csv",
        "nutrient.csv",
        "food_nutrient.csv",
        "food_portion.csv",
        "measure_unit.csv",
        "survey_fndds_food.csv",
        "wweia_food_category.csv"
    ]

    print("Checking FNDDS files...")
    print("Directory:", fndds_directory)

    for file_name in files_to_check:
        check_csv_file(
            fndds_directory / file_name
        )

    print("\nCheck completed.")


if __name__ == "__main__":
    main()