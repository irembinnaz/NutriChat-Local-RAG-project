import json
import math
import sqlite3
from pathlib import Path

from foundry_local_sdk import (
    Configuration,
    FoundryLocalManager
)


def cosine_similarity(vector_a, vector_b):
    dot_product = sum(
        value_a * value_b
        for value_a, value_b in zip(
            vector_a,
            vector_b
        )
    )

    vector_a_length = math.sqrt(
        sum(
            value * value
            for value in vector_a
        )
    )

    vector_b_length = math.sqrt(
        sum(
            value * value
            for value in vector_b
        )
    )

    if vector_a_length == 0 or vector_b_length == 0:
        return 0.0

    return dot_product / (
        vector_a_length * vector_b_length
    )


def get_embedding_model(manager):
    model_aliases = [
        "qwen3-embedding-0.6b",
        "qwen3-0.6b-embedding"
    ]

    last_error = None

    for model_alias in model_aliases:
        try:
            print(
                "Trying embedding model:",
                model_alias
            )

            return manager.catalog.get_model(
                model_alias
            )

        except Exception as error:
            last_error = error

    raise RuntimeError(
        "The embedding model could not be found. "
        f"Last error: {last_error}"
    )


def load_document_chunks(database_path):
    connection = sqlite3.connect(
        database_path
    )

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                source,
                chunk_number,
                text,
                embedding
            FROM document_chunks
            ORDER BY
                source,
                chunk_number
            """
        )

        records = cursor.fetchall()

        document_chunks = []

        for record in records:
            (
                source,
                chunk_number,
                text,
                embedding_json
            ) = record

            document_chunks.append(
                {
                    "source": source,
                    "chunk_number": chunk_number,
                    "text": text,
                    "embedding": json.loads(
                        embedding_json
                    )
                }
            )

        return document_chunks

    finally:
        connection.close()


def find_relevant_chunks(
    question_embedding,
    document_chunks,
    top_k=3
):
    results = []

    for chunk in document_chunks:
        similarity = cosine_similarity(
            question_embedding,
            chunk["embedding"]
        )

        results.append(
            {
                "source": chunk["source"],
                "chunk_number": chunk["chunk_number"],
                "text": chunk["text"],
                "similarity": similarity
            }
        )

    results.sort(
        key=lambda result: result["similarity"],
        reverse=True
    )

    return results[:top_k]


def display_results(question, results):
    print("\n" + "=" * 70)
    print("QUESTION")
    print("=" * 70)
    print(question)

    print("\n" + "=" * 70)
    print("MOST RELEVANT DOCUMENT CHUNKS")
    print("=" * 70)

    for index, result in enumerate(
        results,
        start=1
    ):
        print("\n" + "-" * 70)
        print("Result:", index)
        print("Source:", result["source"])
        print(
            "Chunk number:",
            result["chunk_number"]
        )
        print(
            "Similarity:",
            f'{result["similarity"]:.4f}'
        )
        print("Text:")
        print(result["text"])


def main():
    print("Starting the retrieval test...")

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

    document_chunks = load_document_chunks(
        database_path
    )

    if not document_chunks:
        print(
            "No document chunks were found."
        )
        print(
            "Run document_ingestion.py first."
        )
        return

    print(
        "Document chunks loaded:",
        len(document_chunks)
    )

    question = input(
        "\nEnter a nutrition question: "
    ).strip()

    if not question:
        print("The question cannot be empty.")
        return

    embedding_model = None

    try:
        configuration = Configuration(
            app_name="FoundryRagProject"
        )

        FoundryLocalManager.initialize(
            configuration
        )

        manager = FoundryLocalManager.instance

        embedding_model = get_embedding_model(
            manager
        )

        print("\nDownloading the embedding model...")

        embedding_model.download(
            lambda progress: print(
                f"\rDownload progress: "
                f"{progress:.1f}%",
                end="",
                flush=True
            )
        )

        print("\nLoading the embedding model...")
        embedding_model.load()

        embedding_client = (
            embedding_model.get_embedding_client()
        )

        print(
            "\nGenerating the question embedding..."
        )

        question_response = (
            embedding_client.generate_embedding(
                question
            )
        )

        question_embedding = (
            question_response.data[0].embedding
        )

        results = find_relevant_chunks(
            question_embedding,
            document_chunks,
            top_k=3
        )

        display_results(
            question,
            results
        )

    except Exception as error:
        print("\nThe retrieval test failed:")
        print(
            type(error).__name__ + ":",
            error
        )

    finally:
        if embedding_model is not None:
            try:
                embedding_model.unload()

                print(
                    "\nThe embedding model "
                    "was unloaded."
                )

            except Exception:
                pass


if __name__ == "__main__":
    main()