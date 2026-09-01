from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.database import get_db

from app.models.ai_interaction import AIInteraction
from app.models.enums import UserRole
from app.models.users import User


router = APIRouter(
    prefix="/assistant",
    tags=["AI Analytics"],
)


EXPECTED_TYPES = [
    "discovery",
    "recommendation",
    "order_explanation",
    "restaurant_content",
]


@router.get("/analytics")
def get_ai_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.RESTAURANT_ADMIN
        )
    ),
):
    """
    Return aggregate AI analytics.

    Includes:
    - total questions/interactions
    - answered vs refused
    - breakdown by assistance type
    - average latency
    - p95 latency
    - total tokens
    """

    # =========================================================
    # TOTAL QUESTIONS
    # =========================================================

    total_questions = (
        db.query(
            func.count(
                AIInteraction.interaction_id
            )
        )
        .scalar()
        or 0
    )

    # =========================================================
    # ANSWERED
    # =========================================================

    answered = (
        db.query(
            func.count(
                AIInteraction.interaction_id
            )
        )
        .filter(
            AIInteraction.refused.is_(False)
        )
        .scalar()
        or 0
    )

    # =========================================================
    # REFUSED
    # =========================================================

    refused = (
        db.query(
            func.count(
                AIInteraction.interaction_id
            )
        )
        .filter(
            AIInteraction.refused.is_(True)
        )
        .scalar()
        or 0
    )

    # =========================================================
    # TOTAL TOKENS
    # =========================================================

    total_tokens = (
        db.query(
            func.coalesce(
                func.sum(
                    AIInteraction.total_tokens
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    # =========================================================
    # AVERAGE LATENCY
    # =========================================================

    average_latency_ms = (
        db.query(
            func.coalesce(
                func.avg(
                    AIInteraction.latency_ms
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    # =========================================================
    # P95 LATENCY
    # =========================================================

    p95_latency_ms = (
        db.query(
            func.coalesce(
                func.percentile_cont(0.95)
                .within_group(
                    AIInteraction.latency_ms
                ),
                0,
            )
        )
        .scalar()
        or 0
    )

    # =========================================================
    # BREAKDOWN BY ASSISTANCE TYPE
    # =========================================================

    grouped = (
        db.query(
            AIInteraction.assistance_type,

            func.count(
                AIInteraction.interaction_id
            ).label("questions"),

            func.sum(
                case(
                    (
                        AIInteraction.refused.is_(False),
                        1,
                    ),
                    else_=0,
                )
            ).label("answered"),

            func.sum(
                case(
                    (
                        AIInteraction.refused.is_(True),
                        1,
                    ),
                    else_=0,
                )
            ).label("refused"),

            func.coalesce(
                func.sum(
                    AIInteraction.total_tokens
                ),
                0,
            ).label("total_tokens"),

            func.coalesce(
                func.avg(
                    AIInteraction.latency_ms
                ),
                0,
            ).label("average_latency_ms"),
        )
        .group_by(
            AIInteraction.assistance_type
        )
        .all()
    )

    # =========================================================
    # INITIALIZE EXPECTED TYPES
    # =========================================================

    breakdown = {
        assistance_type: {
            "questions": 0,
            "answered": 0,
            "refused": 0,
            "total_tokens": 0,
            "average_latency_ms": 0,
        }
        for assistance_type in EXPECTED_TYPES
    }

    # =========================================================
    # FILL BREAKDOWN
    # =========================================================

    for row in grouped:

        assistance_type = row.assistance_type

        if assistance_type not in breakdown:

            breakdown[assistance_type] = {
                "questions": 0,
                "answered": 0,
                "refused": 0,
                "total_tokens": 0,
                "average_latency_ms": 0,
            }

        breakdown[assistance_type] = {
            "questions": int(
                row.questions or 0
            ),

            "answered": int(
                row.answered or 0
            ),

            "refused": int(
                row.refused or 0
            ),

            "total_tokens": int(
                row.total_tokens or 0
            ),

            "average_latency_ms": round(
                float(
                    row.average_latency_ms or 0
                ),
                2,
            ),
        }

    # =========================================================
    # RETURN ANALYTICS
    # =========================================================

    return {
        "total_questions": int(
            total_questions
        ),

        "answered": int(
            answered
        ),

        "refused": int(
            refused
        ),

        "average_latency_ms": round(
            float(
                average_latency_ms
            ),
            2,
        ),

        "p95_latency_ms": round(
            float(
                p95_latency_ms
            ),
            2,
        ),

        "total_tokens": int(
            total_tokens
        ),

        "breakdown": breakdown,
    }