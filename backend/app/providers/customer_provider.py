from abc import abstractmethod

from app.domain.customers import Customer
from app.providers.base import Provider


class CustomerProvider(Provider):
    @abstractmethod
    async def get_customer(self, customer_id: str | None, contact: str | None) -> Customer:
        """Return known customer profile by id or contact."""
