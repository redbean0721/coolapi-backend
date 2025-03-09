from fastapi import Depends, APIRouter
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
import datetime
from src.utils.auth import verify_api_key, permission_check
from src.database.mariadb import query_in_mariadb
from typing import Union
import json

router = APIRouter()

class TemperatureHumidityData(BaseModel):
    key: str
    temperature: float
    humidity: float

@router.post("/post_temp_hum", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
async def post_temp_hum(data: TemperatureHumidityData):
    if not verify_api_key(data.key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not permission_check(data.key, "post_temp_hum"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    sensor = query_in_mariadb(query="SELECT description FROM api_keys WHERE api_key = ?", values=(data.key,))[0][0]

    # 將數據添加到 db.json 中
    with open('db.json', 'r+') as file:
        db_data = json.load(file)
        if sensor not in db_data:
            db_data[sensor] = []

        temp_hum_data = {
            "id": len(db_data[sensor]) + 1,
            "temperature": data.temperature,
            "humidity": data.humidity,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        db_data[sensor].append(temp_hum_data)
        file.seek(0)
        json.dump(db_data, file, indent=4)

    return JSONResponse(content={"message": "Data received and stored successfully"})

@router.get("/get_temp_hum", dependencies=[Depends(RateLimiter(times=120, seconds=60))])
async def get_temp_hum(key: str, sensor_id: Union[int, None] = None, item_id: Union[int, None] = None):
    if not verify_api_key(key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not permission_check(key, "get_temp_hum"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    with open('db.json', 'r') as file:
        db_data = json.load(file)

    if sensor_id is not None:
        # 如果提供了 sensor_id
        sensor_key = f"sensor_{sensor_id}"
        if sensor_key not in db_data:
            raise HTTPException(status_code=404, detail="Sensor not found")

        if item_id is not None:
            # 如果同時提供了 item_id
            data = db_data.get(sensor_key, [])
            for entry in data:
                if entry.get("id") == item_id:
                    return entry
            raise HTTPException(status_code=404, detail="Item not found")
        else:
            # 如果只提供了 sensor_id，返回 sensor_id 下的所有數據
            return JSONResponse(content=db_data.get(sensor_key, []), status_code=200)
    else:
        if item_id is not None:
            # 如果只提供了 item_id，變歷所有傳感器數據以尋找相應的項目
            found_data = []
            for sensor_key, sensor_data in db_data.items():
                for data in sensor_data:
                    if data.get("id") == item_id:
                        found_data.append({sensor_key: data})
            if found_data:
                return JSONResponse(content=found_data, status_code=200)
            else:
                raise HTTPException(status_code=404, detail="Item not found")
        else:
            return JSONResponse(content=db_data, status_code=200)
