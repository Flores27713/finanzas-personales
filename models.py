from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # Nulo si accede por Google
    google_id = Column(String, unique=True, nullable=True)
    picture = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    monthly_income = Column(Float, default=0.0, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    quick_buttons_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    savings_goals = relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    bank_name = Column(String, default="BancoEstado", nullable=False)
    account_type = Column(String, default="Cuenta Vista", nullable=False)
    balance = Column(Float, default=0.0, nullable=False)

    user = relationship("User", back_populates="accounts")

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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    monthly_budget = Column(Float, default=0.0, nullable=False)
    is_fixed = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', monthly_budget={self.monthly_budget})>"


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False) # 'EXPENSE', 'INCOME', 'TRANSFER'
    
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    destination_account_id = Column(Integer, ForeignKey("account.id"), nullable=True)
    
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    note = Column(String, nullable=True)

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", foreign_keys=[account_id], back_populates="outgoing_transactions")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], back_populates="incoming_transactions")
    category = relationship("Category", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.transaction_type}', amount={self.amount}, date={self.date})>"

class SavingsGoal(Base):
    __tablename__ = "savings_goal"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_saved = Column(Float, default=0.0, nullable=False)
    target_date = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="savings_goals")
