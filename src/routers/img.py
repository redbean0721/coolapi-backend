from fastapi import Depends, APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from typing import Union, Optional
from src.database.mongodb import connect_to_mongodb
from src.utils.counter import update_counter
from src.database.mariadb import get_mariadb_connect
import logging
import datetime
import random

router = APIRouter()

class ImgJSONResponse(BaseModel):
    id: int
    fileName: str
    url: str
    size: float
    tag: Optional[str] = None
    updateAt: int
    origin: Optional[str] = None

class ImgListJSONResponse(BaseModel):
    status: bool
    code: int
    msg: str
    time: int
    data: dict

@router.get("/img", dependencies=[Depends(RateLimiter(times=80, seconds=60))])
async def img_desktop(type: Union[str, None] = None, tag: Union[str, None] = None) -> Optional[ImgJSONResponse]:
    conn, cursor = await get_mariadb_connect()

    try:
        cursor.execute("SELECT MAX(id) AS max_id FROM image")
        max_id = cursor.fetchone()["max_id"]
        if max_id is None:
            raise HTTPException(status_code=500, detail="No images found in the database.")

        cursor.execute("SELECT * FROM image WHERE id = %s", (random.randint(1, max_id),))
        image = cursor.fetchone()

        if type == "json":
            return JSONResponse(content={
                "id": image["id"],
                "fileName": image["fileName"],
                "url": "https://img.redbean0721.com/img/desktop/" + image["fileName"],
                "size": float(image["size"]),
                "tag": image["tags"],
                "updateAt": int(image["updateAt"].timestamp()) if image["updateAt"] else None,
                "origin": image["origin"]
            }, status_code=200)
        else:
            response = RedirectResponse(url="https://img.redbean0721.com/img/desktop/" + image["fileName"], status_code=302)
            response.headers["Cache-Control"] = "no-revalidate, max-age=0"
            return response
    except Exception as e:
        logging.error(f"Error fetching image: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()

@router.get("/img/list", dependencies=[Depends(RateLimiter(times=80, seconds=60))])
async def img_desktop_list(page: int = Query(1, ge=1, description="Page number, must >= 1"), pageSize: int = Query(20, description="Page size, must be -1 (for all) or >=1")) -> Optional[ImgListJSONResponse]:
    if page < 1 or (pageSize != -1 and pageSize < 1):
        raise HTTPException(status_code=422, detail="Invalid page or pageSize parameter.")
    conn, cursor = await get_mariadb_connect()
    try:
        # 查總筆數
        cursor.execute("SELECT COUNT(*) as total FROM image")
        total = cursor.fetchone()["total"]

        # 如果 pageSize = -1, 全部資料
        if pageSize == -1:
            cursor.execute("SELECT * FROM image ORDER BY id DESC")
        else:
            offset = (page - 1) * pageSize
            cursor.execute("SELECT * FROM image ORDER BY id DESC LIMIT %s OFFSET %s", (pageSize, offset))
        
        images = cursor.fetchall()

        data_list = []
        for image in images:
            data_list.append({
                "id": image["id"],
                "url": "https://img.redbean0721.com/img/desktop/" + image["fileName"],
                "fileName": image["fileName"],
                "size": float(image["size"]),
                "updatedAt": int(image["updateAt"].timestamp()) if image["updateAt"] else None,
                "origin": image["origin"],
                "tags": image["tags"] or ""
            })

        total_pages = 1 if pageSize == -1 else (total + pageSize - 1) // pageSize

        return JSONResponse(content={
            "status": True,
            "code": 200,
            "msg": "获取成功",
            "time": int(datetime.datetime.now().timestamp() * 1000),
            "data": {
                "totalCount": total,
                "totalPages": total_pages,
                "page": page,
                "pageSize": pageSize,
                "imgs": data_list
            }
        })
    except Exception as e:
        logging.error(f"Error fetching image list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()

@router.get("/img-phone", dependencies=[Depends(RateLimiter(times=80, seconds=60))])
async def img_phone(type: Union[str, None] = None, tag: Union[str, None] = None) -> Optional[ImgJSONResponse]:
    conn, cursor = await get_mariadb_connect()

    try:
        cursor.execute("SELECT MAX(id) AS max_id FROM image_phone")
        max_id = cursor.fetchone()["max_id"]
        if max_id is None:
            raise HTTPException(status_code=500, detail="No images found in the database.")

        cursor.execute("SELECT * FROM image_phone WHERE id = %s", (random.randint(1, max_id),))
        image = cursor.fetchone()

        if type == "json":
            return JSONResponse(content={
                "id": image["id"],
                "fileName": image["fileName"],
                "url": "https://img.redbean0721.com/img/phone/" + image["fileName"],
                "size": float(image["size"]),
                "tag": image["tags"],
                "updateAt": int(image["updateAt"].timestamp()) if image["updateAt"] else None,
                "origin": image["origin"]
            }, status_code=200)
        else:
            response = RedirectResponse(url="https://img.redbean0721.com/img/phone/" + image["fileName"], status_code=302)
            response.headers["Cache-Control"] = "no-revalidate, max-age=0"
            return response
    except Exception as e:
        logging.error(f"Error fetching phone image: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()


@router.get("/img-phone/list", dependencies=[Depends(RateLimiter(times=80, seconds=60))])
async def img_phone_list(page: int = Query(1, ge=1, description="Page number, must >= 1"), pageSize: int = Query(20, description="Page size, must be -1 (for all) or >=1")) -> Optional[ImgListJSONResponse]:
    if page < 1 or (pageSize != -1 and pageSize < 1):
        raise HTTPException(status_code=422, detail="Invalid page or pageSize parameter.")
    conn, cursor = await get_mariadb_connect()
    try:
        # 查總筆數
        cursor.execute("SELECT COUNT(*) as total FROM image_phone")
        total = cursor.fetchone()["total"]

        # 如果 pageSize = -1, 全部資料
        if pageSize == -1:
            cursor.execute("SELECT * FROM image_phone ORDER BY id DESC")
        else:
            offset = (page - 1) * pageSize
            cursor.execute("SELECT * FROM image_phone ORDER BY id DESC LIMIT %s OFFSET %s", (pageSize, offset))
        
        images = cursor.fetchall()

        data_list = []
        for image in images:
            data_list.append({
                "id": image["id"],
                "url": "https://img.redbean0721.com/img/phone/" + image["fileName"],
                "fileName": image["fileName"],
                "size": float(image["size"]),
                "updatedAt": int(image["updateAt"].timestamp()) if image["updateAt"] else None,
                "origin": image["origin"],
                "tags": image["tags"] or ""
            })

        total_pages = 1 if pageSize == -1 else (total + pageSize - 1) // pageSize

        return JSONResponse(content={
            "status": True,
            "code": 200,
            "msg": "获取成功",
            "time": int(datetime.datetime.now().timestamp() * 1000),
            "data": {
                "totalCount": total,
                "totalPages": total_pages,
                "page": page,
                "pageSize": pageSize,
                "imgs": data_list
            }
        })
    except Exception as e:
        logging.error(f"Error fetching phone image list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()
