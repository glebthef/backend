from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User


async def lock_user(session: AsyncSession, user_id: int) -> User | None:
    """Блокирует строку пользователя до конца транзакции — перед любым
    изменением баланса, чтобы параллельные ставки, выплаты и пополнения
    не затёрли друг друга.

    populate_existing обязателен: get_authenticated_user мог уже загрузить
    этого User в сессию до блокировки, и без него SQLAlchemy вернёт тот
    устаревший баланс вместо свежего, прочитанного под блокировкой.
    """
    stmt = (
        select(User).where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)
