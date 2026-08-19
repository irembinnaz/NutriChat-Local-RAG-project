import re
import sqlite3
from pathlib import Path

from nutrition_chat import (
    calculate_food_nutrition,
    create_meal_tables,
    display_meal_result,
    display_today_summary,
    is_greeting,
    is_today_summary_question,
    normalize_text,
    parse_food_part,
    save_meal,
    split_meal_into_parts
)

from rag_pipeline import RAGPipeline


NUMBER_WORD_PATTERN = (
    r"a|an|one|two|three|four|five|"
    r"six|seven|eight|nine|ten|half"
)


def is_exit_message(text):

    normalized_text = normalize_text(text)

    exit_messages = {
        "exit",
        "quit",
        "bye",
        "goodbye"
    }

    return normalized_text in exit_messages


def is_small_talk(text):

    normalized_text = normalize_text(text)

    small_talk_messages = {
        "how are you",
        "how are you doing",
        "what are you",
        "who are you",
        "thank you",
        "thanks"
    }

    return normalized_text in small_talk_messages


def get_small_talk_answer(text):

    normalized_text = normalize_text(text)

    if normalized_text in {
        "how are you",
        "how are you doing"
    }:
        return (
            "I am ready to help. "
            "You can tell me what you ate or ask "
            "a nutrition question."
        )

    if normalized_text in {
        "what are you",
        "who are you"
    }:
        return (
            "I am a local nutrition assistant. "
            "I can calculate meals, keep a daily food log, "
            "and answer questions using local documents."
        )

    if normalized_text in {
        "thank you",
        "thanks"
    }:
        return "You're welcome!"

    return (
        "You can tell me what you ate or ask "
        "a nutrition question."
    )


def is_meal_message(text):

    normalized_text = normalize_text(text)

    meal_phrases = [
        "i ate",
        "i had",
        "i have eaten",
        "today i ate",
        "today i had",
        "for breakfast",
        "for lunch",
        "for dinner",
        "for snack"
    ]

    if any(
        phrase in normalized_text
        for phrase in meal_phrases
    ):
        return True

    quantity_pattern = (
        rf"^(?:\d+(?:\.\d+)?|{NUMBER_WORD_PATTERN})\s+"
    )

    if re.search(
        quantity_pattern,
        normalized_text
    ):
        return True

    return False


def process_meal_message(
    connection,
    cursor,
    user_message
):

    meal_parts = split_meal_into_parts(
        user_message
    )

    if not meal_parts:
        print(
            "Assistant: I could not identify "
            "any food in that message."
        )
        return

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
        print("\nAssistant:")

        for error in errors:
            print("-", error)

    if not results:
        print(
            "Assistant: I could not calculate "
            "this meal."
        )
        return

    print("\nAssistant:")
    display_meal_result(results)

    save_meal(
        connection,
        user_message,
        results
    )

    print(
        "\nAssistant: This meal was saved "
        "to today's food log."
    )


def display_rag_answer(result):

    print("\nAssistant:")
    print(result["answer"])

    sources = result.get(
        "sources",
        []
    )

    if not sources:
        return

    displayed_sources = set()

    print("\nSources:")

    for source in sources:
        source_key = (
            source["source"],
            source["chunk_number"]
        )

        if source_key in displayed_sources:
            continue

        displayed_sources.add(source_key)

        print(
            f"- {source['source']}, "
            f"chunk {source['chunk_number']}"
        )


def process_rag_question(
    rag_pipeline,
    question
):


    print(
        "\nAssistant: I am checking my "
        "local nutrition documents..."
    )

    result = rag_pipeline.answer_question(
        question,
        top_k=3
    )

    display_rag_answer(result)


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

    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    create_meal_tables(connection)

    cursor = connection.cursor()
    rag_pipeline = None

    print("=" * 65)
    print("LOCAL NUTRITION ASSISTANT")
    print("=" * 65)

    print(
        "You can describe a meal, ask for today's total, "
        "or ask a nutrition question."
    )

    print(
        "Examples:\n"
        "- I ate one apple and 150 grams of chicken breast.\n"
        "- What did I eat today?\n"
        "- Why is water important for the body?\n"
        "- Type 'exit' to close the program."
    )

    try:
        while True:
            user_message = input("\nYou: ").strip()

            if not user_message:
                continue

            if is_exit_message(user_message):
                print(
                    "Assistant: Goodbye! "
                    "Have a healthy day."
                )
                break

            if is_greeting(user_message):
                print(
                    "Assistant: Hello! "
                    "Tell me what you ate today or "
                    "ask me a nutrition question."
                )
                continue

            if is_small_talk(user_message):
                print(
                    "Assistant:",
                    get_small_talk_answer(
                        user_message
                    )
                )
                continue

            if is_today_summary_question(
                user_message
            ):
                display_today_summary(cursor)
                continue

            if is_meal_message(user_message):
                process_meal_message(
                    connection,
                    cursor,
                    user_message
                )
                continue

            try:
                if rag_pipeline is None:
                    rag_pipeline = RAGPipeline(
                        database_path
                    )

                    rag_pipeline.start()

                process_rag_question(
                    rag_pipeline,
                    user_message
                )

            except Exception as error:
                print(
                    "\nAssistant: The nutrition question "
                    "could not be answered."
                )

                print(
                    type(error).__name__ + ":",
                    error
                )

    except sqlite3.Error as error:
        print("\nA database error occurred:")
        print(error)

    finally:
        connection.close()

        print("\nThe database connection was closed.")


if __name__ == "__main__":
    main()