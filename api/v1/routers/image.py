from inspect import signature
from io import BytesIO
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from imggen.core import ImageType
from imggen.meme import MemeGenerator
from pydantic import HttpUrl

router = APIRouter(prefix="/image", tags=["Image"])
mg = MemeGenerator()
session = httpx.Client()


def retrive_url(url: str):
    b = BytesIO()
    with session.stream("GET", url) as stream:
        if stream.status_code != 200:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Resource at {url} returned status code {stream.status_code}",
            )
        size = int(stream.headers.get("content-length"), 0)
        if not size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to fetch resource at {url}",
            )
        if size > 1024 * 1024 * 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resource at {url} too large",
            )
        for chunk in stream.iter_bytes():
            b.write(chunk)

    b.seek(0)


class TextImageEndpoint:
    # This value of the below attribute makes asyncio.iscoroutinefunction return True
    # _is_coroutine = asyncio.coroutines._is_coroutine
    def __init__(self, genname: str):
        self.func = getattr(mg, genname)
        self.param_count = (
            len(signature(getattr(MemeGenerator, genname)).parameters) - 1
        )
        self.__doc__ = f"Writes given text on '{genname}' image"

    def __call__(self, texts: List[str] = Query(...)) -> StreamingResponse:
        if len(texts) != self.param_count:
            raise HTTPException(
                400,
                detail=f"Expected array of length {self.param_count}, got array of length {len(texts)}",
            )
        return StreamingResponse(self.func(*texts), media_type="image/jpg")


class PasteImageEndpoint:
    def __init__(self, genname: str):
        self.func = getattr(mg, genname)
        self.__doc__ = f"Returns a/an '{genname}' image"

    def __call__(self, url: HttpUrl = Query(...)):
        b = retrive_url(url)
        return StreamingResponse(self.func(b), media_type="image/jpg")


for attr_name in dir(MemeGenerator):
    attr = getattr(MemeGenerator, attr_name)
    if getattr(attr, "__image_generator__", False):
        sig = signature(attr)
        params = sig.parameters
        genname = attr_name

        if len(params) == 2 and list(params.values())[1].annotation == ImageType:

            router.add_api_route(
                "/" + attr_name,
                PasteImageEndpoint(attr_name),
                methods=["GET"],
                tags=["Paste on Image"],
                summary=f"Generates a/an '{attr_name}' image",
                operation_id=f"image_generator_{attr_name}",
            )

        elif all([p.annotation == str for p in list(params.values())[1:]]):
            router.add_api_route(
                "/" + attr_name,
                TextImageEndpoint(attr_name),
                methods=["GET"],
                tags=["Text on Image"],
                summary=f"Writes given text on '{attr_name}' image",
                operation_id=f"image_generator_{attr_name}",
            )

        else:
            raise RuntimeError(f"Couldn't understand type annotations for {attr_name}")
