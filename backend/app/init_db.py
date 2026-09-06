from .database import Base, engine
from . import models


def init_db() -> None:
    """Create all database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("LD76 Domain Finder database initialized.")
