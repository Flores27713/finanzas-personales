import re

with open('models.py', 'r', encoding='utf-8') as f:
    content = f.read()

savings_model = '''
class SavingsGoal(Base):
    __tablename__ = "savings_goal"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_saved = Column(Float, default=0.0, nullable=False)
    target_date = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="savings_goals")
'''

content = content.replace('    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")', 
                          '    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")\n    savings_goals = relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")')

content += savings_model

with open('models.py', 'w', encoding='utf-8') as f:
    f.write(content)
