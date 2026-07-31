from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    balance = Column(Float, default=0.0, nullable=False)

    # Relaciones
    outgoing_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.account_id",
        back_populates="account"
    )
    incoming_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.destination_account_id",
        back_populates="destination_account"
    )

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', balance={self.balance})>"


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    monthly_budget = Column(Float, default=0.0, nullable=False)

    # Relación
    transactions = relationship("Transaction", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', monthly_budget={self.monthly_budget})>"


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False) # 'EXPENSE', 'INCOME', 'TRANSFER'
    
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    destination_account_id = Column(Integer, ForeignKey("account.id"), nullable=True)
    
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    note = Column(String, nullable=True)

    # Relaciones ORM
    account = relationship("Account", foreign_keys=[account_id], back_populates="outgoing_transactions")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], back_populates="incoming_transactions")
    category = relationship("Category", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.transaction_type}', amount={self.amount}, date={self.date})>"
