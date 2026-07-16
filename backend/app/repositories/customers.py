from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import CustomerModel
from app.domain.customers import Customer


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create(self, customer: Customer) -> CustomerModel:
        customer_id = customer.id or customer.contact or str(uuid4())
        model = self.session.get(CustomerModel, customer_id)
        if model is not None:
            return model

        model = CustomerModel(
            id=customer_id,
            contact=customer.contact,
            name=customer.name,
            company=customer.company,
            notes=customer.notes,
        )
        self.session.add(model)
        return model
