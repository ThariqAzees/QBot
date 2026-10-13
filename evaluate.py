"""
Evaluation harness -- reproduces the paper's Table II / Fig. 2-3 style
similarity-rate analysis, but against the ground-truth
evaluation_questions.csv (question, expected_answer, source_document,
difficulty, question_type) instead of the paper's unlabelled user logs.

For each question we:
    1. get QBot's generated answer (fresh session per question, so no
       cross-question history leakage)
    2. embed both the generated answer and the expected_answer
    3. cosine-similarity between them -> bucket into high/medium/low
       (thresholds in config.py)
    4. also record whether the top retrieved chunk came from the
       question's own source_document (retrieval accuracy)

Run:
    python evaluate.py                       # full 135-question set
    python evaluate.py --limit 10             # quick smoke test
    python evaluate.py --csv path/to/other.csv

Writes a detailed per-question CSV to eval_results.csv and prints the
summary tables to stdout.
"""
import argparse
import time

import pandas as pd

import chatbot
import config
from utils.embedding_client import cosine_similarity, embed_text


def classify(score: float) -> str:
    if score >= config.HIGH_SIMILARITY:
        return "high"
    if score >= config.LOW_SIMILARITY:
        return "medium"
    return "low"


def run(csv_path: str, limit: int | None, out_path: str):
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)

    rows = []
    for i, row in df.iterrows():
        qid = row["question_id"]
        question = row["question"]
        expected = row["expected_answer"]

        result = chatbot.answer(question, session_id=f"eval-{qid}", use_history=False)
        generated = result["answer"]

        sim = cosine_similarity(embed_text(generated), embed_text(str(expected)))
        bucket = classify(sim)

        top_source = result["sources"][0]["source_document"] if result["sources"] else None
        retrieval_hit = (top_source == row.get("source_document"))

        rows.append({
            "question_id": qid,
            "question": question,
            "expected_answer": expected,
            "generated_answer": generated,
            "answer_similarity": round(sim, 4),
            "similarity_bucket": bucket,
            "retrieval_confidence": result["similarity_category"],
            "expected_source": row.get("source_document"),
            "top_retrieved_source": top_source,
            "retrieval_source_match": retrieval_hit,
            "difficulty": row.get("difficulty"),
            "question_type": row.get("question_type"),
        })
        print(f"[{i+1}/{len(df)}] {qid} sim={sim:.3f} ({bucket})  "
              f"source_match={retrieval_hit}")
        time.sleep(0.05)  # gentle on rate limits

    out = pd.DataFrame(rows)
    out.to_csv(out_path, index=False)

    print("\n" + "=" * 60)
    print(f"Overall mean answer similarity: {out['answer_similarity'].mean():.4f}")
    print(f"Retrieval source-match rate:    {out['retrieval_source_match'].mean():.4f}")
    print(f"Success rate (>= {config.LOW_SIMILARITY} similarity): "
          f"{(out['answer_similarity'] >= config.LOW_SIMILARITY).mean():.4f}")

    print("\nSimilarity bucket distribution:")
    print(out["similarity_bucket"].value_counts(normalize=True).round(4))

    print("\nMean similarity by difficulty:")
    print(out.groupby("difficulty")["answer_similarity"].mean().round(4))

    print("\nMean similarity by question_type:")
    print(out.groupby("question_type")["answer_similarity"].mean().round(4))

    print("\nMean similarity by source document:")
    print(out.groupby("expected_source")["answer_similarity"].mean().round(4))

    print(f"\nDetailed results written to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/evaluation_questions.csv")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default="eval_results.csv")
    args = parser.parse_args()
    run(args.csv, args.limit, args.out)
