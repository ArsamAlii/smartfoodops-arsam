import json

from app.db.database import SessionLocal
from app.services.content_chunk_service import search_content_chunks

from app.models.enums import UserRole
from app.models.users import User
EVAL_FILE = "app/tests/evaluation/rag_eval.json"

TOP_K = 5
SIMILARITY_THRESHOLD = 0.30


def main():
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    db = SessionLocal()
    customer = (
        db.query(User)
        .filter(User.role == UserRole.CUSTOMER)
        .first()
    )

    if customer is None:
        raise RuntimeError("No customer user found for evaluation")
    hits = 0

    print("\nRAG RETRIEVAL EVALUATION")
    print("=" * 60)

    try:
        for index, item in enumerate(dataset, start=1):

            query = item["query"]
            expected_id = item["expected_menu_item_id"]

            results = search_content_chunks(
                db=db,
                query=query,
                current_user=customer,
                limit=5,
                similarity_threshold=0.30,
            )
            returned_ids = [
                chunk.menu_item_id
                for chunk, similarity in results
            ]

            hit = expected_id in returned_ids

            if hit:
                hits += 1

            print(f"\nQuery {index}: {query}")
            print(f"Expected item: {expected_id}")
            print(f"Returned: {returned_ids}")
            print(f"Hit: {hit}")

    finally:
        db.close()

    total = len(dataset)
    hit_rate = hits / total if total else 0

    print("\n" + "=" * 60)
    print(f"Hits: {hits}/{total}")
    print(f"Top-{TOP_K} Hit Rate: {hit_rate:.2%}")


if __name__ == "__main__":
    main()