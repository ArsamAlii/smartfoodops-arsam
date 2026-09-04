from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db

from app.models.restaurant import Restaurant
from app.models.users import User

from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
)
 
from app.services.content_chunk_service import (
    search_content_chunks,
)


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)

from app.models.menu_item import MenuItem
@router.post(
    "",
    response_model=SearchResponse,
)
def search_menu(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = search_content_chunks(
        db=db,
        query=request.query,
        current_user=current_user,
        limit=request.limit,
        similarity_threshold=request.similarity_threshold,
    )
    search_results = []

    for chunk, similarity in results:

        restaurant = db.get(
            Restaurant,
            chunk.restaurant_id,
        )
        menu_item = db.get(
            MenuItem,
            chunk.menu_item_id,
        )
        search_results.append(
            SearchResult(
                menu_item_id=chunk.menu_item_id,
                restaurant_id=chunk.restaurant_id,
                restaurant=restaurant.name,
                name=menu_item.name,
                category=chunk.category,
                cuisine=chunk.cuisine,
                price=chunk.price,
                is_available=chunk.is_available,
                similarity=float(similarity),
                text=chunk.text,
            )
        )

    return SearchResponse(
        query=request.query,
        results=search_results,
    )