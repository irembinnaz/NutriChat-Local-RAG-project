import json
import sqlite3
from pathlib import Path

from foundry_local_sdk import (
    Configuration,
    FoundryLocalManager
)

from prepare_documents import (
    read_documents,
    split_text_into_chunks
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


def prepare_document_chunks(documents):
    document_chunks = []

    for document in documents:
        source = document["source"]
        text = document["text"]

        chunks = split_text_into_chunks(text)

        for chunk_number, chunk_text in enumerate(
            chunks,
            start=1
        ):
            document_chunks.append(
                {
                    "source": source,
                    "chunk_number": chunk_number,
                    "text": chunk_text
                }
            )

    return document_chunks


def create_document_chunks_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source TEXT NOT NULL,
            chunk_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL,

            UNIQUE(source, chunk_number)
        )
        """
    )


def save_document_chunks(
    database_path,
    document_chunks,
    embeddings
):
    if len(document_chunks) != len(embeddings):
        raise ValueError(
            "The number of chunks and embeddings "
            "does not match."
        )

    connection = sqlite3.connect(
        database_path
    )

    cursor = connection.cursor()

    try:
        create_document_chunks_table(cursor)

        cursor.execute(
            """
            DELETE FROM document_chunks
            """
        )

        records = []

        for chunk, embedding in zip(
            document_chunks,
            embeddings
        ):
            embedding_json = json.dumps(
                list(embedding)
            )

            records.append(
                (
                    chunk["source"],
                    chunk["chunk_number"],
                    chunk["text"],
                    embedding_json
                )
            )

        cursor.executemany(
            """
            INSERT INTO document_chunks (
                source,
                chunk_number,
                text,
                embedding
            )
            VALUES (?, ?, ?, ?)
            """,
            records
        )

        connection.commit()

        print(
            f"\n{len(records)} document chunks "
            "were saved to the database."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def display_saved_chunks(database_path):
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

        print("\nSaved document chunks:")

        for record in records:
            (
                source,
                chunk_number,
                text,
                embedding_json
            ) = record

            embedding = json.loads(
                embedding_json
            )

            print("-" * 70)
            print("Source:", source)
            print("Chunk number:", chunk_number)
            print("Text:", text)

            print(
                "Embedding dimensions:",
                len(embedding)
            )

        print("\n" + "=" * 70)
        print(
            "Total saved chunks:",
            len(records)
        )
        print("=" * 70)

    finally:
        connection.close()


def main():
    print("Starting document ingestion...")

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

    embedding_model = None

    try:
        documents = read_documents()

        if not documents:
            print(
                "No documents were found "
                "inside the docs directory."
            )
            return

        print(
            "Documents found:",
            len(documents)
        )

        document_chunks = prepare_document_chunks(
            documents
        )

        if not document_chunks:
            print(
                "No text chunks could be created."
            )
            return

        print(
            "Document chunks created:",
            len(document_chunks)
        )

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

        chunk_texts = [
            chunk["text"]
            for chunk in document_chunks
        ]

        print(
            "\nGenerating embeddings for "
            f"{len(chunk_texts)} chunks..."
        )

        embedding_response = (
            embedding_client.generate_embeddings(
                chunk_texts
            )
        )

        embeddings = [
            item.embedding
            for item in embedding_response.data
        ]

        print(
            "Embeddings generated:",
            len(embeddings)
        )

        if embeddings:
            print(
                "Embedding dimensions:",
                len(embeddings[0])
            )

        save_document_chunks(
            database_path,
            document_chunks,
            embeddings
        )

        display_saved_chunks(
            database_path
        )

    except Exception as error:
        print(
            "\nAn error occurred during "
            "document ingestion:"
        )

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