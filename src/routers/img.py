from fastapi import Depends, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi_limiter.depends import RateLimiter
from typing import Union
from src.database.mongodb import connect_to_mongodb
from src.utils.counter import update_counter

router = APIRouter()

@router.get("/img", dependencies=[Depends(RateLimiter(times=80, seconds=60))])
async def img(type: Union[str, None] = None, tag: Union[str, None] = None):
    try:
        random = list(connect_to_mongodb("img").aggregate([{"$sample": {"size": 1}}]))
        random_image = random[0]

        update_counter(name="random_pic")
        if type == "json":
            if tag is not None:
                pass
            else:
                content = {
                    "_id": str(random_image["_id"]),  # 轉換為字符串
                    "id": random_image["id"],
                    "fileName": random_image["fileName"],
                    "url": "https://api.redmc.xyz/img/" + random_image["fileName"],
                    "size": random_image["size"],
                    "tag": random_image["tags"],
                    "updateAt": random_image["updateAt"],
                    "origin": random_image["origin"]
                }
                return JSONResponse(content=content)
        else:
            if tag is not None:
                pass
            else:
                return RedirectResponse(url="https://api.redmc.xyz/img/" + random_image["fileName"])
    except Exception as error:
        raise HTTPException(detail=f"Internal Server Error: {str(error)}", status_code=500)
