from src.database.mariadb import get_mariadb_connect
import asyncio, time, logging

stop_event = asyncio.Event()
_task = None  # 背景任務的 reference

async def delete_expired_sessions():
    logging.info("Starting expired sessions cleanup task...")
    try:
        while not stop_event.is_set():
            try:
                conn, cursor = await get_mariadb_connect()
                cursor.execute("DELETE FROM sessions WHERE expires_at <= %s", (int(time.time()),))
                conn.commit()
                cursor.close()
                logging.info("Expired sessions cleaned successfully.")
            except Exception as e:
                logging.error(f"Error during expired sessions cleanup: {e}")
            
            # 可中斷的 sleep（最長 3 天，但 stop_event 被 set 時會提前醒來）
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3 * 24 * 60 * 60)
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        logging.info("Expired session task cancelled gracefully.")

async def start_background_tasks():
    global _task
    stop_event.clear()
    _task = asyncio.create_task(delete_expired_sessions())
    logging.info("Background task startup completed")

async def stop_background_tasks():
    global _task
    logging.info("Stopping background tasks...")
    stop_event.set()
    if _task:
        try:
            await _task
        except asyncio.CancelledError:
            logging.info("Background task canceled successfully.")
