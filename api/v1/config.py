from pydantic import BaseSettings


class Config(BaseSettings):
    signing_secret: str
    redis_uri: str

    class Config:
        env_file = ".env"
        env_prefix = "v1_"


config = Config()
