from dataclasses import dataclass


@dataclass(slots=True)
class InboundEmail:
    message_id: str
    from_address: str
    subject: str
    body: str
    imap_uid: str | None = None
