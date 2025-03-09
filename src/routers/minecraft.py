from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from fastapi import APIRouter, Query, Depends
from typing import List, Optional
import datetime, time
from mcstatus import JavaServer, BedrockServer
from mcclient import SLPClient, QueryClient
import aiomcrcon
import logging

router = APIRouter()

class MinecraftPlayers(BaseModel):
    online: int
    max: int
    list: Optional[List[str]] = []  # 預設為空列表

class MinecraftStatusResponse(BaseModel):
    online: bool
    host: str
    port: int
    version: Optional[str] = None
    players: Optional[MinecraftPlayers] = None
    motd: Optional[str] = None
    latency: Optional[float] = None
    icon: Optional[str] = None
    plugins: Optional[List[str]] = None
    mods: Optional[List[str]] = None
    software: Optional[str] = None
    map: Optional[str] = None
    query_time: int
    

@router.get("/minecraft/status/java/mcstatus", dependencies=[Depends(RateLimiter(times=60, seconds=300))])
async def minecraft_status_java_mcstatus(host: str, port: int = Query(25565, ge=1, le=65535)) -> MinecraftStatusResponse:
    query_time = int(time.time())
    try:
        address = host if port == 25565 else f"{host}:{port}"
        server = JavaServer.lookup(address=address)
        status = server.status()

        # 嘗試查詢伺服器的更多信息
        query = None
        try:
            query = server.query()
        except Exception as query_exception:
            logging.warning(f"Query failed: {query_exception}")
            query = None  # 如果 query 失敗，將 query 設為 None

        return JSONResponse(content={
            "online": True,
            "host": host,
            "port": port,
            "version": status.version.name,
            "players": {
                "online": status.players.online,
                "max": status.players.max,
                "list": [player.name for player in status.players.sample or []]
            },
            "motd": status.description,
            "latency": round(status.latency, 2),
            "icon": status.favicon if hasattr(status, "favicon") else None,
            "plugins": query.software.plugins if query else [],
            "mods": [],
            "software": query.software.brand if query else None,
            "query_time": query_time,
        }, status_code=200)
    except Exception as e:
        logging.warning(e)
        return JSONResponse(content={
            "online": False,
            "host": host,
            "port": port,
            "query_time": query_time
        }, status_code=504)


@router.get("/minecraft/status/java/mcclient", dependencies=[Depends(RateLimiter(times=60, seconds=300))])
async def minecraft_status_java_mcclient(host: str, port: int = Query(25565, ge=1, le=65535)) -> MinecraftStatusResponse:
    query_time = int(time.time())
    try:
        address = host if port == 25565 else f"{host}:{port}"
        # 嘗試建立 SLP 客戶端來獲取伺服器狀態
        slp_client = SLPClient(host, port)
        status = slp_client.get_status()

        # 嘗試建立 Query 客戶端來獲取額外信息
        query = None
        try:
            query_client = QueryClient(host, port)
            query = query_client.get_status()
        except Exception as query_exception:
            logging.warning(f"Query failed: {query_exception}")
            query = None  # 如果 Query 失敗，將 query 設為 None

        return JSONResponse(content={
            "online": True,
            "host": status.host,
            "port": status.port,
            "version": status.version.name,
            "players": {
                "online": status.players.online,
                "max": status.players.max,
                "list": status.players.list
            },
            "motd": status.motd,
            "latency": None,
            "icon": status.favicon if hasattr(status, "favicon") else None,
            "plugins": query.plugins if query else [],
            "mods": [],
            "software": None,
            "query_time": query_time,
        }, status_code=200)
    except Exception as e:
        logging.warning(f"SLP failed: {e}")
        return JSONResponse(content={
            "online": False,
            "host": host,
            "port": port,
            "query_time": query_time
        }, status_code=504)

@router.get("/minecraft/status/bedrock", dependencies=[Depends(RateLimiter(times=60, seconds=300))])
async def minecraft_status_bedrock(host: str, port: int = Query(19132, ge=1, le=65535)) -> MinecraftStatusResponse:
    query_time = int(time.time())
    try:
        server = BedrockServer.lookup(address=f"{host}:{port}")
        status = server.status()
        return JSONResponse(content={
            "online": True,
            "host": host,
            "port": port,
            "version": status.version.name,
            "players": {
                "online": status.players.online,
                "max": status.players.max
            },
            "motd": status.description,
            "latency": round(status.latency, 2),
            "icon": status.favicon if hasattr(status, "favicon") else None,
            "plugins": [],
            "mods": [],
            "software": None,
            "query_time": query_time,
        }, status_code=200)
    except Exception as e:
        logging.warning(e)
        return JSONResponse(content={
            "online": False,
            "host": host,
            "port": port,
            "query_time": query_time
        }, status_code=504)

class MinecraftRconRequest(BaseModel):
    host: str
    port: int = Query(25575, ge=1, le=65535)
    password: str
    cmd: str

class MinecraftRconResponse(BaseModel):
    status: bool
    code: int
    msg: str

@router.post("/minecraft/rcon", dependencies=[Depends(RateLimiter(times=100, seconds=300))])
async def minecraft_rcon(request: MinecraftRconRequest) -> MinecraftRconResponse:
    try:
        client = aiomcrcon.Client(host=request.host, port=request.port, password=request.password)
        await client.connect()
        response = await client.send_cmd(request.cmd)
        await client.close()
        return JSONResponse(content={
            "status": True,
            "code": 200,
            "msg": response
        }, status_code=200)
    except aiomcrcon.RCONConnectionError:
        await client.close()
        return JSONResponse(content={
            "status": False,
            "code": 504,
            "msg": "Failed to establish connection with the RCON server."
        }, status_code=504)
    except aiomcrcon.IncorrectPasswordError:
        await client.close()
        return JSONResponse(content={
            "status": False,
            "code": 401,
            "msg": "Incorrect RCON password provided."
        }, status_code=401)
    except Exception as e:
        await client.close()
        logging.error(e)
        return JSONResponse(content={
            "status": False,
            "code": 500,
            "msg": f"Unexpected error: {str(e)}"
        }, status_code=500)
