from datetime import datetime
from app.schemas.order import OrderStatus
from pydantic import BaseModel, ConfigDict


class OrderStatusHistoryBase(BaseModel):
    from_status: OrderStatus #didnt used string here for validation (invalid inputs)
    to_status: OrderStatus

class OrderStatusHistoryCreate(OrderStatusHistoryBase):
    pass


class OrderStatusHistoryResponse(OrderStatusHistoryBase):
    status_history_id: int
    order_id: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)