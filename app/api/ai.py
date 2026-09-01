import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.llm import GroqLLMProvider
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.users import User
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.prompts import (
    PROMPT_DISCOVERY_V1,
    PROMPT_ORDER_EXPLAIN_V1,
)
from app.schemas.ai import (
    AIAskRequest,
    AIAskResponse,
    AISource,
)
from app.services.content_chunk_service import search_content_chunks


router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"],
)


@router.post(
    "/ask",
    response_model=AIAskResponse,
)
async def ask_assistant(
    request: AIAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # =========================================================
    # ORDER-RELATED QUESTION WITHOUT ORDER ID
    # =========================================================

    order_keywords = [
        "order",
        "orders",
        "delivery",
        "delivered",
        "delaying",
        "delayed",
        "late",
        "rider",
        "cancelled",
        "canceled",
        "status",
        "tracking",
        "track",
        "where is my",
        "when will my",
        "my order",
    ]

    question_lower = request.question.lower()

    is_order_question = any(
        keyword in question_lower
        for keyword in order_keywords
    )

    if is_order_question and request.order_id is None:
        return AIAskResponse(
            question=request.question,
            answer=(
                "I can help you with your order, but I need "
                "your Order ID first. Please provide your "
                "Order ID and try again."
            ),
            sources=[],
        )

    # =========================================================
    # ORDER EXPLANATION MODE
    # =========================================================

    if request.order_id is not None:

        order = (
            db.query(Order)
            .filter(
                Order.order_id == request.order_id
            )
            .first()
        )

        # -----------------------------------------------------
        # Order does not exist
        # -----------------------------------------------------

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        # -----------------------------------------------------
        # Customer may ONLY access their own order
        # -----------------------------------------------------

        if order.customer_id != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to ask about this order."
                ),
            )

        # -----------------------------------------------------
        # Retrieve REAL order status history
        # -----------------------------------------------------

        status_history = (
            db.query(OrderStatusHistory)
            .filter(
                OrderStatusHistory.order_id
                == order.order_id
            )
            .order_by(
                OrderStatusHistory.status_history_id
            )
            .all()
        )

        # -----------------------------------------------------
        # Build verified order context
        # -----------------------------------------------------

        history_lines = []

        for history in status_history:

            line = (
                f"From: {history.from_status or 'none'} | "
                f"To: {history.to_status} | "
                f"Actor: {history.actor}"
            )

            if history.reason:
                line += (
                    f" | Reason: {history.reason}"
                )

            history_lines.append(line)

        history_context = "\n".join(history_lines)

        if not history_context:
            history_context = (
                "No order status history is available."
            )

        order_context = (
            f"Order ID: {order.order_id}\n"
            f"Restaurant ID: {order.restaurant_id}\n"
            f"Current status: {order.status}\n"
            f"Created at: {order.created_at}\n"
            f"Rider assigned: "
            f"{'Yes' if order.rider_id is not None else 'No'}\n"
            f"Rider ID: {order.rider_id or 'None'}\n\n"
            f"Status history:\n"
            f"{history_context}"
        )

        # -----------------------------------------------------
        # Build grounded order-explanation prompt
        # -----------------------------------------------------

        user_prompt = PROMPT_ORDER_EXPLAIN_V1.format(
            order_context=order_context,
            user_question=request.question,
        )

        # -----------------------------------------------------
        # Generate explanation
        # -----------------------------------------------------

        llm = GroqLLMProvider()

        response = await llm.generate(
            system_prompt=(
                "You are a SmartFoodOps order and "
                "delivery assistant. "
                "Use only the verified order data "
                "provided to you."
            ),
            user_prompt=user_prompt,
        )

        return AIAskResponse(
            question=request.question,
            answer=response.text,
            sources=[],
        )

    # =========================================================
    # MENU DISCOVERY MODE
    # =========================================================

    # ---------------------------------------------------------
    # 1. Retrieval configuration
    # ---------------------------------------------------------

    retrieval_top_k = int(
        os.getenv("RETRIEVAL_TOP_K", "5")
    )

    retrieval_min_similarity = float(
        os.getenv(
            "RETRIEVAL_MIN_SIMILARITY",
            "0.30",
        )
    )

    # ---------------------------------------------------------
    # 2. Retrieve orderable menu items
    # ---------------------------------------------------------

    results = search_content_chunks(
        db=db,
        query=request.question,
        current_user=current_user,
        limit=retrieval_top_k,
        similarity_threshold=retrieval_min_similarity,
    )

    # ---------------------------------------------------------
    # 3. Build grounded context and citations
    # ---------------------------------------------------------

    context_parts = []
    sources = []

    for chunk, similarity in results:

        restaurant = db.get(
            Restaurant,
            chunk.restaurant_id,
        )

        menu_item = db.get(
            MenuItem,
            chunk.menu_item_id,
        )

        if restaurant is None or menu_item is None:
            continue

        # Extra safety check using current database state.
        # A customer must never receive an unavailable item.

        if not restaurant.is_open:
            continue

        if not menu_item.is_available:
            continue

        if menu_item.stock is not None and menu_item.stock <= 0:
            continue

        context_parts.append(
            (
                f"Restaurant: {restaurant.name}\n"
                f"Cuisine: {restaurant.cuisine}\n"
                f"Category: {chunk.category}\n"
                f"Menu item: {menu_item.name}\n"
                f"Description: "
                f"{menu_item.description or 'N/A'}\n"
                f"Price: {menu_item.price}\n"
            )
        )

        sources.append(
            AISource(
                menu_item_id=menu_item.menu_item_id,
                restaurant_id=restaurant.restaurant_id,
                restaurant=restaurant.name,
                name=menu_item.name,
                category=chunk.category,
                price=str(menu_item.price),
                is_available=menu_item.is_available,
                similarity=float(similarity),
            )
        )

    # ---------------------------------------------------------
    # 4. Refuse when nothing orderable was retrieved
    # ---------------------------------------------------------

    if not context_parts:
        return AIAskResponse(
            question=request.question,
            answer=(
                "I could not find a suitable orderable item "
                "in the available restaurant menus."
            ),
            sources=[],
        )

    # ---------------------------------------------------------
    # 5. Build versioned discovery prompt
    # ---------------------------------------------------------

    context = "\n---\n".join(
        context_parts
    )

    user_prompt = PROMPT_DISCOVERY_V1.format(
        context=context,
        user_question=request.question,
    )

    # ---------------------------------------------------------
    # 6. Generate grounded answer
    # ---------------------------------------------------------

    llm = GroqLLMProvider()

    response = await llm.generate(
        system_prompt=(
            "You are a food-ordering assistant. "
            "Follow the supplied discovery prompt exactly."
        ),
        user_prompt=user_prompt,
    )

    # ---------------------------------------------------------
    # 7. Return answer + citations
    # ---------------------------------------------------------

    return AIAskResponse(
        question=request.question,
        answer=response.text,
        sources=sources,
    )