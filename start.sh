#!/bin/bash
exec gunicorn -c gunicorn.conf.py app.main:app

# gunicorn main:app \
#     -k uvicorn.workers.UvicornWorker \  # 使用 Uvicorn 作為 Gunicorn 的工作類型
#     --workers 4 \                      # 啟動 4 個工作進程
#     --worker-connections 2000 \      # 每個工作進程允許的最大連接數
#     --max-requests 5000 \            # 每個工作進程在重啟前處理的最大請求數
#     --max-requests-jitter 500 \     # 在 max-requests 基礎上添加隨機抖動
#     --timeout 30 \                 # 工作進程無響應的超時時間（秒）
#     --keep-alive 5                  # 保持活動連接的時間（秒）