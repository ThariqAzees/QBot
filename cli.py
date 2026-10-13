"""
Interactive command-line chat interface.

    python cli.py

Type 'exit' or 'quit' to stop. Each run gets its own session_id so history
doesn't bleed across separate terminal sessions.
"""
import uuid

import chatbot


def main():
    session_id = str(uuid.uuid4())
    print("QBot -- Anna University regulations assistant")
    print("(type 'exit' to quit)\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break

        result = chatbot.answer(question, session_id=session_id)

        print(f"\nQBot: {result['answer']}\n")
        if result["sources"]:
            print("Sources:")
            for s in result["sources"]:
                pages = f"p. {s['page_start']}" if s['page_start'] == s['page_end'] \
                    else f"pp. {s['page_start']}-{s['page_end']}"
                print(f"  - {s['source_document']}, {pages}  (score={s['score']})")
        print(f"[confidence: {result['similarity_category']}]")
        if result["related_questions"]:
            print("Related questions you might mean:")
            for q in result["related_questions"]:
                print(f"  - {q}")
        print()


if __name__ == "__main__":
    main()
