import sqlite3
from pathlib import Path


def create_database():

    project_directory = Path(__file__).resolve().parent
    database_path = project_directory / "nutrition.db"

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT,

            calories_per_100g REAL NOT NULL,
            protein_per_100g REAL NOT NULL,
            carbohydrates_per_100g REAL NOT NULL,
            fat_per_100g REAL NOT NULL,
            fiber_per_100g REAL,

            portion_name TEXT,
            portion_grams REAL,

            source TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding TEXT,

            UNIQUE(source, chunk_number)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_meal_logs_created_at
        ON meal_logs(created_at)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_meal_items_meal_log_id
        ON meal_items(meal_log_id)
        """
    )

    connection.commit()

    print("The database was updated successfully.")
    print("Database file:", database_path.resolve())

    print("\nAvailable tables:")

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )

    tables = cursor.fetchall()

    for table in tables:
        print("-", table[0])

    connection.close()


if __name__ == "__main__":
    create_database()