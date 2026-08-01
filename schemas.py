from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, EmailStr

# Esquemas de Usuario & Autenticación
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Nombre del usuario")
    email: str = Field(..., description="Correo electrónico único")
    password: str = Field(..., min_length=4, description="Contraseña del usuario")

class UserLogin(BaseModel):
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., description="Contraseña")

class GoogleAuth(BaseModel):
    credential: str = Field(..., description="JWT Credential de Google Sign-In")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    picture: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Esquemas de Cuenta
class AccountBase(BaseModel):
    name: str
    balance: float

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Esquemas de Categoría
class CategoryBase(BaseModel):
    name: str
    monthly_budget: float

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Esquemas para Transacciones
class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Monto del gasto en CLP")
    account_id: int = Field(..., description="ID de la cuenta de origen")
    category_id: Optional[int] = Field(None, description="ID de la categoría del gasto")
    note: Optional[str] = Field(None, description="Nota o descripción del gasto")

class TransferCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Monto a transferir en CLP")
    account_id: int = Field(..., description="ID de la cuenta de origen")
    destination_account_id: int = Field(..., description="ID de la cuenta de destino")
    note: Optional[str] = Field(None, description="Nota o descripción del traspaso")

class IncomeCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Monto del ingreso en CLP")
    account_id: int = Field(..., description="ID de la cuenta receptora")
    note: Optional[str] = Field(None, description="Nota o descripción del ingreso")

class TransactionResponse(BaseModel):
    id: int
    amount: float
    transaction_type: str
    account_id: int
    account_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    destination_account_id: Optional[int] = None
    destination_account_name: Optional[str] = None
    date: datetime
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Esquemas para el Dashboard
class CategorySpent(BaseModel):
    category_id: int
    category_name: str
    monthly_budget: float
    total_spent: float
    percentage_used: float

class DashboardSummary(BaseModel):
    total_balance: float
    accounts: List[AccountResponse]
    categories_summary: List[CategorySpent]
    daily_hormiga_limit: float
    days_remaining_in_month: int
    committed_expenses: float = 0.0
    free_balance: float = 0.0


class PinLogin(BaseModel):
    pin: str
