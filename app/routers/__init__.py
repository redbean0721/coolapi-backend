from .index import router as index_router
from .auth import router as auth_router
from .user import router as user_router

routers = [
    index_router,
    auth_router,
    user_router,
]