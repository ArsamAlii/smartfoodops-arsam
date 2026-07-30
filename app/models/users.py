from datetime import datetime
from sqlalchemy import DateTime,String #sql datatypes
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class User(Base):#user is a table in postgresql(creates a database model)
    __tablename__="users"

    user_id: Mapped[int] = mapped_column(primary_key=true)

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    email: Mapped[str]= mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        Datetime,
        default=datetime.utcnow,
        nullable=False,
    )