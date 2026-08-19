import json
import math
import re
import sqlite3
import time
from pathlib import Path

from foundry_local_sdk import (
    Configuration,
    FoundryLocalManager
)


MINIMUM_SIMILARITY = 0.40
CONTEXT_SCORE_MARGIN = 0.20


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

    context_parts = [
        result["text"].strip()
        for result in retrieved_chunks
        if result["text"].strip()
    ]

    return "\n\n".join(context_parts)


def create_source_list(retrieved_chunks):

    sources = []

    for result in retrieved_chunks:
        source_information = {
            "source": result["source"],
            "chunk_number": result["chunk_number"],
            "similarity": result["similarity"]
        }

        if source_information not in sources:
            sources.append(source_information)

    return sources


def collect_streaming_answer(
    chat_client,
    messages
):

    answer_parts = []

    for attempt in range(2):
        try:
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
                    answer_parts.append(content)

            return "".join(answer_parts).strip()

        except Exception as error:
            operation_cancelled = (
                "Operation was cancelled"
                in str(error)
            )

            if operation_cancelled and attempt == 0:
                answer_parts.clear()
                time.sleep(3)
                continue

            raise

    return ""


def clean_generated_answer(answer):

    cleaned_answer = answer.strip()

    cleaned_answer = re.sub(
        (
            r"^\s*(?:based on|according to|using)\s+"
            r"(?:the\s+)?(?:provided\s+)?"
            r"(?:context|information)[,:]?\s*"
        ),
        "",
        cleaned_answer,
        flags=re.IGNORECASE
    )

    cleaned_answer = re.sub(
        (
            r"\s*,?\s*as stated in\s+"
            r"[\w\-]+\.txt"
            r"(?:,?\s*chunk\s*\d+)?"
        ),
        "",
        cleaned_answer,
        flags=re.IGNORECASE
    )

    cleaned_answer = re.sub(
        (
            r"\s+The\s+(?:provided\s+)?context"
            r"[^.!?]*[.!?]?"
        ),
        " ",
        cleaned_answer,
        flags=re.IGNORECASE
    )

    cleaned_answer = re.sub(
        r"\s+",
        " ",
        cleaned_answer
    ).strip()

    return cleaned_answer



def is_too_general_question(question):

    normalized = re.sub(
        r"[^a-z0-9\s]",
        " ",
        question.casefold()
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    ).strip()

    general_phrases = {
        "tell me something",
        "tell me anything",
        "say something",
        "say anything",
        "give me information",
        "give me some information",
        "give me a fact",
        "tell me a fact",
        "what can you tell me",
        "what do you know",
        "help me",
        "explain something",
        "anything",
        "something"
    }

    return normalized in general_phrases

class RAGPipeline:

    def __init__(self, database_path=None):
        project_directory = (
            Path(__file__).resolve().parent
        )

        self.database_path = (
            Path(database_path)
            if database_path is not None
            else project_directory / "nutrition.db"
        )

        self.manager = None
        self.document_chunks = []
        self.embedding_model = None
        self.embedding_client = None
        self.chat_model = None
        self.chat_client = None

    def start(self):

        if not self.database_path.exists():
            raise FileNotFoundError(
                "The nutrition.db file could not be found."
            )

        self.document_chunks = load_document_chunks(
            self.database_path
        )

        if not self.document_chunks:
            raise RuntimeError(
                "No document chunks were found. "
                "Run document_ingestion.py first."
            )

        configuration = Configuration(
            app_name="FoundryRagProject"
        )

        try:
            FoundryLocalManager.initialize(
                configuration
            )

        except Exception as error:
            error_message = str(error).casefold()

            if "already been initialized" not in error_message:
                raise

        self.manager = FoundryLocalManager.instance
        if self.embedding_model is None:
            self.embedding_model = get_embedding_model(
                self.manager
            )

            select_cpu_variant_if_available(
                self.embedding_model
            )

            self.embedding_model.download(
                lambda progress: None
            )

            self.embedding_model.load()
            self.embedding_client = (
                self.embedding_model.get_embedding_client()
            )

        if self.chat_model is None:
            self.chat_model = self.manager.catalog.get_model(
                "phi-3.5-mini"
            )

            select_cpu_variant_if_available(
                self.chat_model
            )

            self.chat_model.download(
                lambda progress: None
            )

            self.chat_model.load()
            self.chat_client = self.chat_model.get_chat_client()

    def create_question_embedding(self, question):
        if self.embedding_client is None:
            self.start()

        response = self.embedding_client.generate_embedding(
            question
        )

        return response.data[0].embedding

    def generate_answer(
        self,
        question,
        context
    ):
        if self.chat_client is None:
            self.start()

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly English nutrition assistant. "
                    "Answer the user's question directly and naturally. "
                    "Use only the supplied nutrition information. "
                    "Do not invent facts. "
                    "Do not mention documents, sources, file names, "
                    "chunks, similarity scores, retrieval, embeddings, "
                    "context, or a knowledge base. "
                    "Do not begin with phrases such as "
                    "'Based on the provided context'. "
                    "Write two or three short, clear sentences. "
                    "Do not provide a medical diagnosis or personalized "
                    "medical treatment."
                )
            },
            {
                "role": "user",
                "content": (
                    f"User question:\n{question}\n\n"
                    f"Nutrition information:\n{context}\n\n"
                    "Give a direct, natural answer to the user."
                )
            }
        ]

        answer = collect_streaming_answer(
            self.chat_client,
            messages
        )

        if not answer:
            return (
                "I could not generate an answer right now. "
                "Please try again."
            )

        cleaned_answer = clean_generated_answer(
            answer
        )

        if not cleaned_answer:
            return (
                "I could not generate an answer right now. "
                "Please try again."
            )

        return cleaned_answer

    def close(self):
        for model in (self.chat_model, self.embedding_model):
            if model is None:
                continue

            try:
                model.unload()
            except Exception:
                pass

        self.chat_model = None
        self.chat_client = None
        self.embedding_model = None
        self.embedding_client = None

    def answer_question(
        self,
        question,
        top_k=3
    ):
        if self.manager is None:
            self.start()

        cleaned_question = question.strip()

        if not cleaned_question:
            raise ValueError(
                "The question cannot be empty."
            )

        if is_too_general_question(cleaned_question):
            return {
                "answer": (
                    "Please ask a specific nutrition-related "
                    "question."
                ),
                "sources": [],
                "retrieved_chunks": []
            }

        question_embedding = (
            self.create_question_embedding(
                cleaned_question
            )
        )

        retrieved_chunks = retrieve_relevant_chunks(
            question_embedding,
            self.document_chunks,
            top_k=top_k
        )

        if not retrieved_chunks:
            return {
                "answer": (
                    "I do not have enough information "
                    "to answer that question."
                ),
                "sources": [],
                "retrieved_chunks": []
            }

        best_similarity = retrieved_chunks[0][
            "similarity"
        ]

        if best_similarity < MINIMUM_SIMILARITY:
            return {
                "answer": (
                    "I do not have enough information "
                    "to answer that question."
                ),
                "sources": [],
                "retrieved_chunks": []
            }

        context_threshold = max(
            MINIMUM_SIMILARITY,
            best_similarity - CONTEXT_SCORE_MARGIN
        )

        context_chunks = [
            result
            for result in retrieved_chunks
            if result["similarity"] >= context_threshold
        ]

        if not context_chunks:
            context_chunks = [
                retrieved_chunks[0]
            ]

        context = create_context(
            context_chunks
        )

        answer = self.generate_answer(
            cleaned_question,
            context
        )

        return {
            "answer": answer,
            "sources": create_source_list(
                context_chunks
            ),
            "retrieved_chunks": context_chunks
        }


def main():
    print("Starting the reusable RAG pipeline...")

    question = input(
        "\nEnter a nutrition question: "
    ).strip()

    pipeline = RAGPipeline()

    try:
        pipeline.start()

        result = pipeline.answer_question(
            question,
            top_k=3
        )

        print("\n" + "=" * 70)
        print("ANSWER")
        print("=" * 70)
        print(result["answer"])

    except Exception as error:
        print("\nThe RAG pipeline failed:")
        print(
            type(error).__name__ + ":",
            error
        )

    finally:
        pipeline.close()


if __name__ == "__main__":
    main()