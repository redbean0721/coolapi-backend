from uvicorn.config import LOGGING_CONFIG
import logging


class ColorizingStreamHandler(logging.StreamHandler):
    """自定義處理器，將 INFO 訊息顯示為綠色，其他級別顯示各自顏色，並根據級別調整空格"""
    
    COLORS = {
        "INFO": "\033[0;32m",  # 綠色
        "WARNING": "\033[0;33m",  # 黃色
        "ERROR": "\033[0;31m",  # 紅色
        "CRITICAL": "\033[1;31m",  # 較亮的紅色
        "DEBUG": "\033[0;34m",  # 藍色
        "WHITE": "\033[0m",  # 白色
    }

    def emit(self, record):
        # 構建日誌消息
        msg = self.format(record)
        # 插入顏色
        level_color = self.COLORS.get(record.levelname, self.COLORS["WHITE"])  # 根據日誌級別選擇顏色
        # 這裡分開處理，使得級別和其他部分的顏色不同
        parts = msg.split(" - ", 1)  # 按 " - " 分開前後兩部分
        timestamp_part = parts[0]  # 時間戳部分
        level_part = parts[1].split(":")[0]  # 取得 INFO、WARNING 等級
        message_part = parts[1][len(level_part)+1:]  # 訊息部分

        # 根據日誌級別設定空格
        if record.levelname == "INFO":
            level_spacing = "     "  # INFO後面空 4 格
        elif record.levelname == "WARNING":
            level_spacing = "  "  # WARNING後面空 2 格
        elif record.levelname == "ERROR":
            level_spacing = "    "  # ERROR後面空 4 格
        elif record.levelname == "DEBUG":
            level_spacing = "    "  # ERROR後面空 4 格
        else:
            level_spacing = " "  # 其他級別保持默認

        # 用顏色格式化並添加空格
        colored_msg = f"{timestamp_part} - {self.COLORS['WHITE']}{level_color}{level_part}{self.COLORS['WHITE']}:{level_spacing}{self.COLORS['WHITE']}{message_part}"
        
        # 將最終顏色化的消息輸出
        stream = self.stream
        stream.write(f"{colored_msg}\n")


def setup_logging():
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelprefix)s %(message)s"
    LOGGING_CONFIG["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"

    LOGGING_CONFIG["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
    LOGGING_CONFIG["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
