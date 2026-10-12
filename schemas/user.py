import re
from datetime import date

from pydantic import BaseModel, field_validator

MIN_AGE = 18
MAX_AGE = 120
LOGIN_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


def full_years(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class UserCreate(BaseModel):
    login: str
    password: str
    birth_date: date
    agree_rules: bool
    agree_personal_data: bool

    @field_validator("login")
    @classmethod
    def check_login(cls, v: str) -> str:
        if not LOGIN_RE.fullmatch(v):
            raise ValueError("Логин: 3–30 символов, латиница, цифры и знаки _ . -")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if not 8 <= len(v) <= 50 or not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Пароль: от 8 до 50 символов, буквы и цифры")
        return v

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, v: date) -> date:
        age = full_years(v, date.today())
        if age < 0:
            raise ValueError("Дата рождения не может быть в будущем")
        if age > MAX_AGE:
            raise ValueError("Укажите корректную дату рождения")
        if age < MIN_AGE:
            raise ValueError("Регистрация доступна только лицам от 18 лет")
        return v

    @field_validator("agree_rules")
    @classmethod
    def check_rules(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Необходимо принять правила сервиса")
        return v

    @field_validator("agree_personal_data")
    @classmethod
    def check_personal_data(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Необходимо согласие на обработку персональных данных")
        return v


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    login: str
    balance: float
    is_admin: bool
    is_banned: bool
