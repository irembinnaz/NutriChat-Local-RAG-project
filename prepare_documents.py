from pathlib import Path


def read_documents():

    project_directory = Path(__file__).resolve().parent
    docs_directory = project_directory / "docs"

    files = list(docs_directory.glob("*.txt"))

    if not files:
        print("No TXT documents were found in the docs directory.")
        return []

    documents = []

    for file in files:
        text = file.read_text(
            encoding="utf-8"
        )

        documents.append(
            {
                "source": file.name,
                "text": text
            }
        )

    return documents


def split_text_into_chunks(text):

    chunks = []

    for paragraph in text.split("\n\n"):
        cleaned_paragraph = paragraph.strip()

        if cleaned_paragraph:
            chunks.append(cleaned_paragraph)

    return chunks


def main():
    documents = read_documents()

    if not documents:
        return

    total_chunks = 0

    print(
        f"A total of {len(documents)} "
        "documents were found.\n"
    )

    for document in documents:
        source = document["source"]
        text = document["text"]

        chunks = split_text_into_chunks(text)

        print("=" * 50)
        print("Document:", source)
        print("Number of chunks:", len(chunks))
        print("=" * 50)

        for number, chunk in enumerate(
            chunks,
            start=1
        ):
            print(f"\nChunk {number}:")
            print(chunk)

        total_chunks += len(chunks)
        print()

    print("=" * 50)
    print(
        "Total number of documents:",
        len(documents)
    )
    print(
        "Total number of text chunks:",
        total_chunks
    )


if __name__ == "__main__":
    main()