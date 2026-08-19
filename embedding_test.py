import math

from foundry_local_sdk import (
    Configuration,
    FoundryLocalManager
)


def cosine_similarity(vector_a, vector_b):
    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
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


def main():
    print("Starting the embedding test...")

    embedding_model = None

    documents = [
        (
            "Proteins help build and maintain muscles, "
            "tissues, and cells."
        ),
        (
            "Carbohydrates are one of the body's "
            "main sources of energy."
        ),
        (
            "Water is necessary for regulating body "
            "temperature and maintaining normal "
            "body functions."
        ),
        (
            "Eggs, cheese, yogurt, and milk are "
            "protein sources that can be included "
            "in breakfast."
        )
    ]

    question = "Why does the body need water?"

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
            "\nGenerating document embeddings..."
        )

        document_response = (
            embedding_client.generate_embeddings(
                documents
            )
        )

        document_embeddings = [
            item.embedding
            for item in document_response.data
        ]

        print(
            "Number of document embeddings:",
            len(document_embeddings)
        )

        print(
            "Embedding dimensions:",
            len(document_embeddings[0])
        )

        print("\nGenerating the question embedding...")

        question_response = (
            embedding_client.generate_embedding(
                question
            )
        )

        question_embedding = (
            question_response.data[0].embedding
        )

        results = []

        for index, document_embedding in enumerate(
            document_embeddings
        ):
            similarity = cosine_similarity(
                question_embedding,
                document_embedding
            )

            results.append(
                {
                    "document": documents[index],
                    "similarity": similarity
                }
            )

        results.sort(
            key=lambda result: result["similarity"],
            reverse=True
        )

        print("\nQuestion:")
        print(question)

        print("\nSimilarity results:")

        for result in results:
            print("-" * 70)
            print("Document:", result["document"])

            print(
                "Similarity:",
                f'{result["similarity"]:.4f}'
            )

        best_result = results[0]

        print("\n" + "=" * 70)
        print("MOST RELEVANT DOCUMENT")
        print("=" * 70)

        print(best_result["document"])

        print(
            "Similarity:",
            f'{best_result["similarity"]:.4f}'
        )

    except Exception as error:
        print("\nThe embedding test failed:")
        print(type(error).__name__ + ":", error)

    finally:
        if embedding_model is not None:
            try:
                embedding_model.unload()
                print("\nThe embedding model was unloaded.")

            except Exception:
                pass


if __name__ == "__main__":
    main()