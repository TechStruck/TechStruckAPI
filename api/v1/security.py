import datetime

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from jose import jwt
from pydantic import BaseModel, Field

from .config import config

api_key_security = APIKeyHeader(name="x-api-key")


from aioredis import create_redis_pool


class User(BaseModel):
    api_key: str
    user_id: int = Field(alias="id")
    rate_limiter: int = Field(alias="rl")
    random: str = Field(alias="r")


redis = None


async def init_redis():
    global redis
    if redis is not None:
        return
    redis = await create_redis_pool(config.redis_uri)


async def check_api_key(api_key: str = Security(api_key_security)) -> User:
    await init_redis()
    try:
        data = jwt.decode(api_key, config.signing_secret)
    except:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    user = User(**data, api_key=api_key)
    redis_cache_key = await redis.get(
        f"valid:{user.user_id}:{user.random}", encoding="utf-8"
    )
    if not redis_cache_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    return user


async def ratelimit(user: User = Security(check_api_key)):
    await init_redis()
    time = datetime.datetime.utcnow()
    redis_key = f"rl:{user.user_id}:{user.random}:{str(time.minute)}"
    reqs = int(await redis.incr(redis_key))
    if reqs > user.rate_limiter:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS)
    if reqs == 1:
        await redis.expire(redis_key, 60 - time.second)
