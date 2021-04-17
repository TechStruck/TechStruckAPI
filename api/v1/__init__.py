from fastapi import Depends, FastAPI, Security

from .routers import image
from .security import api_key_security, check_api_key, ratelimit

app = FastAPI(
    title="TechStruck",
    version="1.0.0",
    dependencies=[
        Security(api_key_security),
        Security(check_api_key),
        Depends(ratelimit),
    ],
    responses={401: {"description": "Invalid or no api-key provided"}},
)

app.include_router(image.router)
