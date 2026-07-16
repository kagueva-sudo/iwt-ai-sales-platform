from dataclasses import dataclass


@dataclass(slots=True)
class Customer:
    id: str | None
    contact: str | None
    name: str | None = None
    company: str | None = None
    notes: str | None = None
