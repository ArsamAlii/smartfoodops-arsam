import asyncio
import json
import time

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse
from groq import APIConnectionError
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.core.observability import (
    correlation_id as request_correlation_id,
)
from app.db.database import get_db
from app.llm import GroqLLMProvider

from app.models.ai_interaction import AIInteraction
from app.models.enums import UserRole
from app.models.generated_content import GeneratedContent
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.users import User

from app.prompts import (
    PROMPT_RESTAURANT_DESCRIPTION_V1,
    PROMPT_RESTAURANT_PROMO_V1,
    PROMPT_RESTAURANT_HIGHLIGHTS_V1,
    PROMPT_RESTAURANT_HIGHLIGHTS_REPAIR_V1,
)

from app.schemas.generated_content import (
    DescriptionGenerationRequest,
    PromoGenerationRequest,
    HighlightsGenerationRequest,
    HighlightsResponse,
)


router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurant AI"],
)


# =============================================================
# SSE
# =============================================================

def sse_event(
    event_type: str,
    data: dict,
) -> str:
    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


# =============================================================
# RESTAURANT ACCESS
# =============================================================

def get_owned_restaurant(
    restaurant_id: int,
    db: Session,
    current_user: User,
) -> Restaurant:

    restaurant = db.get(
        Restaurant,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found.",
        )

    if restaurant.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this restaurant.",
        )

    return restaurant


# =============================================================
# BUILD RESTAURANT CONTEXT
# =============================================================
def build_restaurant_context(
    restaurant: Restaurant,
    db: Session,
    menu_item_id: int | None = None,
) -> tuple[str, int | None]:

    categories = sorted(
        restaurant.categories,
        key=lambda category: (
            category.order_index,
            category.category_id,
        ),
    )

    if menu_item_id is not None:

        selected_item = None

        for category in categories:
            for item in category.menu_items:
                if item.menu_item_id == menu_item_id:
                    selected_item = item
                    break

            if selected_item is not None:
                break

        if selected_item is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Menu item not found in this restaurant."
                ),
            )

        context = (
            f"Restaurant name: {restaurant.name}\n"
            f"Cuisine: {restaurant.cuisine}\n"
            f"Restaurant description: "
            f"{restaurant.description or 'N/A'}\n"
            f"Address: {restaurant.address}\n"
            f"Operating hours: "
            f"{restaurant.operating_hours or 'N/A'}\n\n"
            f"Menu category: "
            f"{selected_item.category.name}\n"
            f"Menu item:\n"
            f"Name: {selected_item.name}\n"
            f"Description: "
            f"{selected_item.description or 'N/A'}\n"
            f"Price: {selected_item.price}\n"
            f"Available: "
            f"{'Yes' if selected_item.is_available else 'No'}\n"
            f"Stock: {selected_item.stock}"
        )

        return (
            context,
            selected_item.menu_item_id,
        )

    lines = [
        f"Restaurant name: {restaurant.name}",
        f"Cuisine: {restaurant.cuisine}",
        (
            "Restaurant description: "
            f"{restaurant.description or 'N/A'}"
        ),
        f"Address: {restaurant.address}",
        (
            "Operating hours: "
            f"{restaurant.operating_hours or 'N/A'}"
        ),
        "",
        "Menu items:",
    ]

    for category in categories:

        lines.append(
            f"Category: {category.name}"
        )

        items = sorted(
            category.menu_items,
            key=lambda item: (
                item.order_index,
                item.menu_item_id,
            ),
        )

        for item in items:

            lines.append(
                (
                    f"- Name: {item.name} | "
                    f"Description: "
                    f"{item.description or 'N/A'} | "
                    f"Price: {item.price} | "
                    f"Available: "
                    f"{'Yes' if item.is_available else 'No'} | "
                    f"Stock: {item.stock}"
                )
            )

    return (
        "\n".join(lines),
        None,
    )

    # ---------------------------------------------------------
    # Whole restaurant context
    # ---------------------------------------------------------

    lines = [
        f"Restaurant name: {restaurant.name}",
        f"Cuisine: {restaurant.cuisine}",
        (
            "Restaurant description: "
            f"{restaurant.description or 'N/A'}"
        ),
        f"Address: {restaurant.address}",
        (
            "Operating hours: "
            f"{restaurant.operating_hours or 'N/A'}"
        ),
        "",
        "Menu items:",
    ]

    for category in categories:

        lines.append(
            f"Category: {category.name}"
        )

        items = sorted(
            category.menu_items,
            key=lambda item: (
                item.order_index,
                item.menu_item_id,
            ),
        )

        for item in items:

            lines.append(
                (
                    f"- Name: {item.name} | "
                    f"Description: "
                    f"{item.description or 'N/A'} | "
                    f"Price: {item.price} | "
                    f"Available: "
                    f"{'Yes' if item.is_available else 'No'} | "
                    f"Stock: {item.stock}"
                )
            )

    return (
        "\n".join(lines),
        None,
    )


# =============================================================
# SAVE GENERATED CONTENT
# =============================================================

def save_generated_content(
    db: Session,
    restaurant_id: int,
    menu_item_id: int | None,
    content_type: str,
    content,
    prompt_version: str,
    model: str,
) -> GeneratedContent:

    generated = GeneratedContent(
        restaurant_id=restaurant_id,
        menu_item_id=menu_item_id,
        content_type=content_type,
        content=content,
        prompt_version=prompt_version,
        model=model,
    )

    db.add(generated)
    db.commit()
    db.refresh(generated)

    return generated


# =============================================================
# DESCRIPTION
# =============================================================

@router.post(
    "/{restaurant_id}/generate/description",
)
async def generate_description(
    restaurant_id: int,
    request: DescriptionGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    restaurant = get_owned_restaurant(
        restaurant_id,
        db,
        current_user,
    )

    (
        restaurant_context,
        menu_item_id,
    ) = build_restaurant_context(
        restaurant,
        db,
        request.menu_item_id,
    )

    user_prompt = (
        PROMPT_RESTAURANT_DESCRIPTION_V1.format(
            restaurant_context=restaurant_context,
        )
    )

    llm = GroqLLMProvider()

    start_time = time.perf_counter()
    correlation_id = request_correlation_id.get()

    async def stream():

        generated_text = ""

        try:

            async for token in llm.stream(
                system_prompt=(
                    "You are a SmartFoodOps restaurant "
                    "content assistant. "
                    "Use only the supplied restaurant and "
                    "menu data. Never invent facts."
                ),
                user_prompt=user_prompt,
            ):

                generated_text += token

                yield sse_event(
                    "text",
                    {
                        "content": token,
                    },
                )

                await asyncio.sleep(0)

            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            save_generated_content(
                db=db,
                restaurant_id=restaurant.restaurant_id,
                menu_item_id=menu_item_id,
                content_type="description",
                content=generated_text,
                prompt_version=(
                    "PROMPT_RESTAURANT_DESCRIPTION_V1"
                ),
                model=llm.model,
            )

            db.add(
                AIInteraction(
                    user_id=current_user.user_id,
                    question=(
                        "Restaurant description generation"
                    ),
                    assistance_type="restaurant_content",
                    retrieved_chunk_ids=[],
                    order_id=None,
                    answer=generated_text,
                    model=llm.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms,
                    refused=False,
                    correlation_id=correlation_id,
                )
            )

            db.commit()

            yield sse_event(
                "metadata",
                {
                    "content_type": "description",
                    "restaurant_id": (
                        restaurant.restaurant_id
                    ),
                    "menu_item_id": menu_item_id,
                },
            )

            yield sse_event(
                "done",
                {},
            )

        except asyncio.CancelledError:

            if generated_text:

                save_generated_content(
                    db=db,
                    restaurant_id=(
                        restaurant.restaurant_id
                    ),
                    menu_item_id=menu_item_id,
                    content_type="description",
                    content=generated_text,
                    prompt_version=(
                        "PROMPT_RESTAURANT_DESCRIPTION_V1"
                    ),
                    model=llm.model,
                )

            raise

        except APIConnectionError:

            yield sse_event(
                "error",
                {
                    "message": (
                        "AI service is temporarily unavailable. "
                        "Please try again."
                    ),
                },
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# =============================================================
# PROMO
# =============================================================

@router.post(
    "/{restaurant_id}/generate/promo",
)
async def generate_promo(
    restaurant_id: int,
    request: PromoGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    restaurant = get_owned_restaurant(
        restaurant_id,
        db,
        current_user,
    )

    (
        restaurant_context,
        _,
    ) = build_restaurant_context(
        restaurant,
        db,
    )

    user_prompt = (
        PROMPT_RESTAURANT_PROMO_V1.format(
            restaurant_context=restaurant_context,
        )
    )

    llm = GroqLLMProvider()

    start_time = time.perf_counter()
    correlation_id = request_correlation_id.get()

    async def stream():

        generated_text = ""

        try:

            async for token in llm.stream(
                system_prompt=(
                    "You are a SmartFoodOps restaurant "
                    "marketing assistant. "
                    "Use only the supplied restaurant and "
                    "menu data. Never invent facts."
                ),
                user_prompt=user_prompt,
            ):

                generated_text += token

                yield sse_event(
                    "text",
                    {
                        "content": token,
                    },
                )

                await asyncio.sleep(0)

            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            save_generated_content(
                db=db,
                restaurant_id=restaurant.restaurant_id,
                menu_item_id=None,
                content_type="promo",
                content=generated_text,
                prompt_version=(
                    "PROMPT_RESTAURANT_PROMO_V1"
                ),
                model=llm.model,
            )

            db.add(
                AIInteraction(
                    user_id=current_user.user_id,
                    question=(
                        "Restaurant promo generation"
                    ),
                    assistance_type="restaurant_content",
                    retrieved_chunk_ids=[],
                    order_id=None,
                    answer=generated_text,
                    model=llm.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms,
                    refused=False,
                    correlation_id=correlation_id,
                )
            )

            db.commit()

            yield sse_event(
                "metadata",
                {
                    "content_type": "promo",
                    "restaurant_id": restaurant.restaurant_id,
                },
            )

            yield sse_event(
                "done",
                {},
            )

        except asyncio.CancelledError:

            if generated_text:

                save_generated_content(
                    db=db,
                    restaurant_id=restaurant.restaurant_id,
                    menu_item_id=None,
                    content_type="promo",
                    content=generated_text,
                    prompt_version=(
                        "PROMPT_RESTAURANT_PROMO_V1"
                    ),
                    model=llm.model,
                )

            raise

        except APIConnectionError:

            yield sse_event(
                "error",
                {
                    "message": (
                        "AI service is temporarily unavailable. "
                        "Please try again."
                    ),
                },
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================
# HIGHLIGHTS
# =============================================================

@router.post(
    "/{restaurant_id}/generate/highlights",
)
async def generate_highlights(
    restaurant_id: int,
    request: HighlightsGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    restaurant = get_owned_restaurant(
        restaurant_id,
        db,
        current_user,
    )

    (
        restaurant_context,
        _,
    ) = build_restaurant_context(
        restaurant,
        db,
    )

    initial_prompt = (
        PROMPT_RESTAURANT_HIGHLIGHTS_V1.format(
            count=request.count,
            restaurant_context=restaurant_context,
        )
    )

    llm = GroqLLMProvider()

    start_time = time.perf_counter()
    correlation_id = request_correlation_id.get()

    # ---------------------------------------------------------
    # First generation
    # ---------------------------------------------------------

    try:

        raw_parts = []

        async for token in llm.stream(
            system_prompt=(
                "You are a SmartFoodOps restaurant "
                "content assistant. "
                "Return ONLY valid JSON matching the "
                "requested highlights schema. "
                "Never invent menu items or facts."
            ),
            user_prompt=initial_prompt,
        ):

            raw_parts.append(token)

        raw_output = "".join(
            raw_parts
        ).strip()

    except APIConnectionError:

        raise HTTPException(
            status_code=503,
            detail=(
                "AI service is temporarily unavailable. "
                "Please try again."
            ),
        )

    # ---------------------------------------------------------
    # Validate first response
    # ---------------------------------------------------------

    try:

        parsed = json.loads(
            raw_output
        )

        validated = HighlightsResponse.model_validate(
            parsed
        )

    except Exception as first_error:

        # -----------------------------------------------------
        # ONE REPAIR RETRY
        # -----------------------------------------------------

        repair_prompt = (
            PROMPT_RESTAURANT_HIGHLIGHTS_REPAIR_V1.format(
                validation_error=str(first_error),
                restaurant_context=restaurant_context,
            )
        )

        try:

            repair_parts = []

            async for token in llm.stream(
                system_prompt=(
                    "You are repairing malformed JSON. "
                    "Return ONLY valid JSON matching the "
                    "requested schema."
                ),
                user_prompt=repair_prompt,
            ):

                repair_parts.append(token)

            repaired_output = "".join(
                repair_parts
            ).strip()

            repaired_parsed = json.loads(
                repaired_output
            )

            validated = HighlightsResponse.model_validate(
                repaired_parsed
            )

        except Exception:

            raise HTTPException(
                status_code=502,
                detail=(
                    "The AI service returned invalid "
                    "highlight data after one repair attempt."
                ),
            )

    # ---------------------------------------------------------
    # Validated result
    # ---------------------------------------------------------

    validated_json = validated.model_dump()

    async def stream_validated():

        try:

            serialized = json.dumps(
                validated_json,
                ensure_ascii=False,
            )

            chunk_size = 80

            for index in range(
                0,
                len(serialized),
                chunk_size,
            ):

                yield sse_event(
                    "text",
                    {
                        "content": serialized[
                            index:index + chunk_size
                        ],
                    },
                )

                await asyncio.sleep(0)

            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            save_generated_content(
                db=db,
                restaurant_id=restaurant.restaurant_id,
                menu_item_id=None,
                content_type="highlights",
                content=validated_json,
                prompt_version=(
                    "PROMPT_RESTAURANT_HIGHLIGHTS_V1"
                ),
                model=llm.model,
            )

            db.add(
                AIInteraction(
                    user_id=current_user.user_id,
                    question=(
                        "Restaurant highlights generation"
                    ),
                    assistance_type="restaurant_content",
                    retrieved_chunk_ids=[],
                    order_id=None,
                    answer=json.dumps(
                        validated_json,
                        ensure_ascii=False,
                    ),
                    model=llm.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms,
                    refused=False,
                    correlation_id=correlation_id,
                )
            )

            db.commit()

            yield sse_event(
                "metadata",
                {
                    "content_type": "highlights",
                    "restaurant_id": (
                        restaurant.restaurant_id
                    ),
                    "validated": True,
                },
            )

            yield sse_event(
                "done",
                {},
            )

        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        stream_validated(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )