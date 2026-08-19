import json
import math
import sqlite3
import time
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
        sum(value * value for value in vector_a)
    )

    vector_b_length = math.sqrt(
        sum(value * value for value in vector_b)
    )

    if vector_a_length == 0 or vector_b_length == 0:
        return 0.0

    return dot_product / (
        vector_a_length * vector_b_length
    )


def select_cpu_variant_if_available(model):
    cpu_variant = next(
        (
            variant
            for variant in model.variants
            if "cpu" in variant.id.casefold()
        ),
        None
    )

    if cpu_variant is not None:
        model.select_variant(cpu_variant)


def get_embedding_model(manager):
    model_aliases = [
        "qwen3-embedding-0.6b",
        "qwen3-0.6b-embedding"
    ]

    last_error = None

    for model_alias in model_aliases:
        try:
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
    connection = sqlite3.connect(database_path)
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


def retrieve_relevant_chunks(
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


def create_context(retrieved_chunks):
    context_parts = []

    for result in retrieved_chunks:
        context_parts.append(
            (
                f"[Source: {result['source']}, "
                f"chunk {result['chunk_number']}]\n"
                f"{result['text']}"
            )
        )

    return "\n\n".join(context_parts)


def display_retrieved_chunks(retrieved_chunks):
    print("\nRetrieved document chunks:")

    for index, result in enumerate(
        retrieved_chunks,
        start=1
    ):
        print("-" * 70)
        print("Result:", index)
        print("Source:", result["source"])
        print("Chunk:", result["chunk_number"])

        print(
            "Similarity:",
            f'{result["similarity"]:.4f}'
        )

        print("Text:")
        print(result["text"])


def generate_rag_answer(
    chat_client,
    question,
    context
):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an English nutrition question-answering "
                "assistant using a local knowledge base. "
                "Answer the question using only the provided context. "
                "Do not invent information. "
                "If the context does not contain enough information, "
                "say: 'I do not have enough information in my local "
                "knowledge base to answer that question.' "
                "Keep the answer clear and concise. "
                "Do not provide medical diagnosis or personalized "
                "medical treatment."
            )
        },
        {
            "role": "user",
            "content": (
                f"QUESTION:\n{question}\n\n"
                f"CONTEXT:\n{context}\n\n"
                "Answer the question based only on the context."
            )
        }
    ]

    for attempt in range(2):
        try:
            print("\n" + "=" * 70)
            print("RAG ANSWER")
            print("=" * 70)
            print("Assistant: ", end="", flush=True)

            for chunk in chat_client.complete_streaming_chat(
                messages
            ):
                if not chunk.choices:
                    continue

                content = (
                    chunk.choices[0]
                    .delta
                    .content
                )

                if content:
                    print(
                        content,
                        end="",
                        flush=True
                    )

            print()
            return

        except Exception as error:
            operation_cancelled = (
                "Operation was cancelled"
                in str(error)
            )

            if operation_cancelled and attempt == 0:
                print(
                    "\nThe first attempt was cancelled. "
                    "Trying again in 3 seconds..."
                )

                time.sleep(3)

            else:
                raise


def display_sources(retrieved_chunks):
    unique_sources = []

    for result in retrieved_chunks:
        source = result["source"]

        if source not in unique_sources:
            unique_sources.append(source)

    print("\nSources used:")

    for source in unique_sources:
        print("-", source)


def main():
    print("Starting the RAG test...")

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

    question = input(
        "\nEnter a nutrition question: "
    ).strip()

    if not question:
        print("The question cannot be empty.")
        return

    embedding_model = None
    chat_model = None

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

        select_cpu_variant_if_available(
            embedding_model
        )

        print("\nLoading the embedding model...")

        embedding_model.download(
            lambda progress: print(
                f"\rEmbedding model download: "
                f"{progress:.1f}%",
                end="",
                flush=True
            )
        )

        print()
        embedding_model.load()

        embedding_client = (
            embedding_model.get_embedding_client()
        )

        print(
            "Generating the question embedding..."
        )

        question_response = (
            embedding_client.generate_embedding(
                question
            )
        )

        question_embedding = (
            question_response.data[0].embedding
        )

        retrieved_chunks = retrieve_relevant_chunks(
            question_embedding,
            document_chunks,
            top_k=3
        )

        display_retrieved_chunks(
            retrieved_chunks
        )

        context = create_context(
            retrieved_chunks
        )

        # The embedding model is no longer needed
        embedding_model.unload()
        embedding_model = None
        print("\nLoading the language model...")

        chat_model = manager.catalog.get_model(
            "phi-3.5-mini"
        )

        select_cpu_variant_if_available(
            chat_model
        )

        chat_model.download(
            lambda progress: print(
                f"\rLanguage model download: "
                f"{progress:.1f}%",
                end="",
                flush=True
            )
        )

        print()
        chat_model.load()

        chat_client = chat_model.get_chat_client()

        generate_rag_answer(
            chat_client,
            question,
            context
        )

        display_sources(
            retrieved_chunks
        )

    except Exception as error:
        print("\nThe RAG test failed:")
        print(
            type(error).__name__ + ":",
            error
        )

    finally:
        if embedding_model is not None:
            try:
                embedding_model.unload()
            except Exception:
                pass

        if chat_model is not None:
            try:
                chat_model.unload()
            except Exception:
                pass

        print("\nThe models were unloaded.")


if __name__ == "__main__":
    main()