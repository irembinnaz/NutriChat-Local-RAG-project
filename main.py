import time

from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    print("Starting Foundry Local...")

    model = None

    try:

        configuration = Configuration(
            app_name="FoundryRagProject"
        )

        FoundryLocalManager.initialize(configuration)
        manager = FoundryLocalManager.instance

        model = manager.catalog.get_model(
            "phi-3.5-mini"
        )

        cpu_variant = next(
            (
                variant
                for variant in model.variants
                if "cpu" in variant.id.lower()
            ),
            None
        )

        if cpu_variant is None:
            print(
                "A CPU variant could not be found "
                "for this model."
            )

            print("Available model variants:")

            for variant in model.variants:
                print("-", variant.id)

            return

        model.select_variant(cpu_variant)

        print("Selected model variant:")
        print(model.id)

        print("\nDownloading the model...")

        model.download(
            lambda progress: print(
                f"\rDownload progress: {progress:.1f}%",
                end="",
                flush=True
            )
        )

        print("\nLoading the model...")
        model.load()

        client = model.get_chat_client()

        question = "Introduce yourself."

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful artificial intelligence assistant. "
                    "Always respond in English. "
                    "Write short, clear, and meaningful sentences. "
                    "Do not use unnecessary introductions, headings, "
                    "or numbered lists. "
                    "Do not make up information that you do not know."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ]

        print("\nQuestion:", question)

        for attempt in range(2):
            try:
                print("AI: ", end="", flush=True)

                for chunk in client.complete_streaming_chat(
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
                break

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
                    print(
                        "\nThe response could not be generated:"
                    )
                    print(error)
                    break

    except Exception as error:
        print(
            "\nAn error occurred while running the program:"
        )
        print(error)

    finally:

        if model is not None:
            try:
                model.unload()
            except Exception:
                pass

        print("\nThe model was unloaded.")


if __name__ == "__main__":
    main()