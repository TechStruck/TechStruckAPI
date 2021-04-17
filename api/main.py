from fastapi import FastAPI

from . import v1

app = FastAPI(openapi_url=None, redoc_url=None)

app.mount("/v1", v1.app)
