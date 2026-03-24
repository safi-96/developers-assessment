import uuid
from datetime import date, datetime, timezone

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    worklogs: list["Worklog"] = Relationship(back_populates="owner", cascade_delete=True)
    remittances: list["Remittance"] = Relationship(
        back_populates="owner", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


class TimeEntryBase(SQLModel):
    description: str | None = Field(default=None, max_length=255)
    hours: float = Field(default=0.0, ge=0)
    hourly_rate: float = Field(default=0.0, ge=0)
    is_disputed: bool = False
    is_removed: bool = False


class TimeEntry(TimeEntryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    worklog_id: uuid.UUID = Field(foreign_key="worklog.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    worklog: "Worklog" = Relationship(back_populates="entries")


class RemittanceBase(SQLModel):
    period_start: date
    period_end: date
    status: str = Field(default="COMPLETED", max_length=50)
    total_amount: float = Field(default=0.0, ge=0)


class Remittance(RemittanceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    owner: User | None = Relationship(back_populates="remittances")
    worklogs: list["Worklog"] = Relationship(back_populates="remittance")


class WorklogBase(SQLModel):
    task_name: str = Field(min_length=1, max_length=255)
    work_date: date
    is_adjusted: bool = False


class Worklog(WorklogBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    remittance_id: uuid.UUID | None = Field(
        default=None, foreign_key="remittance.id", index=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    owner: User | None = Relationship(back_populates="worklogs")
    remittance: Remittance | None = Relationship(back_populates="worklogs")
    entries: list[TimeEntry] = Relationship(back_populates="worklog", cascade_delete=True)


class TimeEntryPublic(TimeEntryBase):
    id: uuid.UUID
    worklog_id: uuid.UUID
    amount: float
    created_at: datetime


class WorklogPublic(WorklogBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    freelancer_email: str
    freelancer_name: str | None = None
    remittance_id: uuid.UUID | None = None
    remittance_status: str
    amount: float


class WorklogDetailPublic(WorklogPublic):
    entries: list[TimeEntryPublic]


class WorklogsPublic(SQLModel):
    data: list[WorklogPublic]
    count: int
    total_amount: float


class RemittancePublic(RemittanceBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime


class GenerateRemittancesRequest(SQLModel):
    period_start: date
    period_end: date
    excluded_worklog_ids: list[uuid.UUID] = []
    excluded_user_ids: list[uuid.UUID] = []


class GenerateRemittancesResponse(SQLModel):
    remittances: list[RemittancePublic]
    processed_worklog_ids: list[uuid.UUID]
    total_amount: float


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
