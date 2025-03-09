import logging, os, uvicorn
from dotenv import load_dotenv
from src.core.log import ColorizingStreamHandler, setup_logging

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        ColorizingStreamHandler(),  # 使用自定義的顏色處理器
    ],
)

setup_logging()

load_dotenv()
required_vars = ["API_TITLE", "API_VERSION", "API_HOST", "API_PORT", "REDIS_URL"]
for var in required_vars:
    if os.getenv(var) is None:
        raise ValueError(f"Env Var {var} is not set.")
logging.info("Env Var loaded successfully.")


from fastapi import FastAPI
from src.main import app, lifespan
root_app = FastAPI(lifespan=lifespan)
root_app.mount("/api", app)

if __name__ == "__main__":
    uvicorn.run(app=root_app, host=os.getenv("API_HOST"), port=int(os.getenv("API_PORT")), proxy_headers=True, forwarded_allow_ips='*')
