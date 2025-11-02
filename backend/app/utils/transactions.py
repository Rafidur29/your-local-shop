from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session


@contextmanager
def smart_transaction(session: Session) -> Iterator:
    """
    Context manager that begins a transaction on the given Session.
    If a transaction is already active, start a nested SAVEPOINT (begin_nested).
    Otherwise start a normal transaction (begin).
    Usage:
        with smart_transaction(db):
            ... DB work ...
    """
    if session.in_transaction():
        cm = session.begin_nested()
    else:
        cm = session.begin()
    with cm:
        yield
