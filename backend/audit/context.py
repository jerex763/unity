from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuditContext:
    actor_id: int | None
    request_id: UUID


_current_context: ContextVar[AuditContext | None] = ContextVar(
    "audit_context",
    default=None,
)


def get_audit_context() -> AuditContext | None:
    return _current_context.get()


@contextmanager
def bind_audit_context(context: AuditContext) -> Iterator[None]:
    token = _current_context.set(context)
    try:
        yield
    finally:
        _current_context.reset(token)
