import multiprocessing

# === 基本設定 ===
bind = "0.0.0.0:8000"
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 4

# 使用 Uvicorn Worker 來支援 ASGI 應用 (支援 uvloop 和 httptools)
worker_class = "uvicorn.workers.UvicornWorker"
# worker_class = "uvicorn.workers.UvicornH11Worker"

# 限制每個 worker 的最大連接數
worker_connections = 2000

# keepalive 設定，保持連接的時間（秒）
keepalive = 5

# 設定請求的超時時間（秒）
timeout = 30

# === 日誌設定 ===
loglevel = "info"
accesslog = "-"  # 將訪問日誌輸出到標準輸出
errorlog = "-"   # 將錯誤日誌輸出到標準錯誤

# 自定義訪問日誌格式
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
# %(h)s: 客戶端 IP 地址
# %(l)s: 遠程用戶名（通常為 '-'）
# %(u)s: 認證用戶名
# %(t)s: 請求時間
# %(r)s: 請求行
# %(s)s: 狀態碼
# %(b)s: 響應大小
# %(f)s: 參照頁面
# %(a)s: 用戶代理