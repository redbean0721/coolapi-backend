from fastapi import Depends, APIRouter, Security, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, EmailStr
from src.database.mariadb import get_mariadb_connect
from src.utils.auth import setCookie, verifyCookie
import datetime
import bcrypt
import logging
import jwt
import os
from fastapi.responses import RedirectResponse
from logto import LogtoClient, LogtoConfig

client = LogtoClient(
    LogtoConfig(
        endpoint="https://sso.redbean0721.com/",
        appId="r33l8c7qa41jt0livw5a8",
        appSecret="NmVQ3broDzk9ZtJE0lVlp9YTCDOLvHNd",
    )
)

router = APIRouter()

@router.get("/logto", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def logto_logout():
    if client.isAuthenticated() is False:
        return "Not authenticated <a href='/api/logto/login'>Sign in</a>"

    return "Authenticated <a href='/api/logto/logout'>Sign out</a>"

@router.get("/logto/callback", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def logto_callback(request: Request, response: Response):
    try:
        await client.handleSignInCallback(request.url) # Handle a lot of stuff
        return RedirectResponse("/") # Redirect the user to the home page after a successful sign-in
    except Exception as e:
        # Change this to your error handling logic
        return "Error: " + str(e)
    # return JSONResponse(status_code=200, content={"message": "Login successful"})

@router.get("/logto/login", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def logto_logout():
    # Get the sign-in URL and redirect the user to it
    return RedirectResponse(await client.signIn(
        redirectUri="https://api.redbean0721.com/api/logto/callback",
    ))

@router.get("/logto/logout", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def logto_logout():
    return RedirectResponse(
        # Redirect the user to the home page after a successful sign-out
        await client.signOut(postLogoutRedirectUri="https://api.redbean0721.com/")
    )
