# Project Notes


### Completed
- Created SQLAlchemy models.
- Configured relationships between tables.
- Generated and applied Alembic migrations.
- Implemented Pydantic schemas.
- Implemented authentication schemas.
- Implemented security utilities (password hashing and JWT).

### Bugs Encountered
- Alembic initially generated an empty migration because models were not imported in `app/db/base.py`.
- Fixed incorrect import `sqlalpchemy` → `sqlalchemy`.
- Fixed `Mapped_column` typo → `mapped_column`.
- Fixed `Datetime` import issue.
- Fixed `relationship` import issue.
- Fixed `bcrypt` 5.0 incompatibility by downgrading to `bcrypt==4.0.1`.

### Key Learnings
- SQLAlchemy only detects models that are imported into `Base.metadata`.
- Passwords should never be stored in plain text.
- JWT tokens contain signed user information and an expiration time.
- Business logic should be placed in the service layer, not in API routes.

### Next Tasks
- Implement `auth_service.py`.
- Implement registration endpoint.
- Implement login endpoint.

### Questions
- None