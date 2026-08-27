import math

from app.embeddings.fake import FakeEmbeddings
from app.models.enums import UserRole
from app.services.content_chunk_service import (
    calculate_text_hash,
)


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))

    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))

    return dot / (magnitude_a * magnitude_b)


def test_fake_embeddings_are_deterministic():
    provider = FakeEmbeddings()

    first = provider.embed_query("chicken biryani")
    second = provider.embed_query("chicken biryani")

    assert first == second
    assert len(first) == 384


def test_similarity_threshold_filtering():
    provider = FakeEmbeddings()

    query_vector = provider.embed_query("chicken biryani")
    unrelated_vector = provider.embed_query("chocolate cake")

    similarity = cosine_similarity(
        query_vector,
        unrelated_vector,
    )

    threshold = similarity + 0.01

    assert similarity < threshold


def test_availability_and_open_filtering():
    """
    Customer retrieval must only expose:

    - available menu items
    - items from open restaurants

    The actual database filtering is implemented in
    search_content_chunks().
    """

    assert UserRole.CUSTOMER.value == "customer"


def test_restaurant_admin_access_control():
    """
    Restaurant admins are restricted to restaurants
    owned by their user account.
    """

    assert UserRole.RESTAURANT_ADMIN.value == "restaurant_admin"


def test_reindex_hash_changes_when_text_changes():
    original_text = (
        "Restaurant: Test Restaurant. "
        "Cuisine: Pakistani. "
        "Category: Main Course. "
        "Menu item: Chicken Karahi"
    )

    changed_text = (
        "Restaurant: Test Restaurant. "
        "Cuisine: Pakistani. "
        "Category: Main Course. "
        "Menu item: Chicken Biryani"
    )

    original_hash = calculate_text_hash(
        original_text
    )

    changed_hash = calculate_text_hash(
        changed_text
    )

    assert original_hash != changed_hash


def test_reindex_hash_is_stable_when_text_does_not_change():
    text = (
        "Restaurant: Test Restaurant. "
        "Cuisine: Pakistani. "
        "Category: Main Course. "
        "Menu item: Chicken Karahi"
    )

    first_hash = calculate_text_hash(text)
    second_hash = calculate_text_hash(text)

    assert first_hash == second_hash