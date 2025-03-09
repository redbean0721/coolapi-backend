import logging, os, pymysql
from dbutils.pooled_db import PooledDB
import pymysql.cursors

host = os.getenv("MARIADB_HOST")
port = int(os.getenv("MARIADB_PORT"))
user = os.getenv("MARIADB_USER")
password = os.getenv("MARIADB_PASSWORD")
database = os.getenv("MARIADB_DATABASE")

pool = PooledDB(
    creator=pymysql,  # 使用 pymysql 來建立連線
    mincached=2,       # 池中最小的空閒連線數量
    maxcached=10,      # 池中最多的空閒連線數量
    maxshared=5,       # 最多允許 5 個請求共享同一個連線
    maxconnections=10, # 最大連線數
    blocking=True,     # 當池中沒有連線時，是否阻塞請求，直到有連線可用
    setsession=["SET NAMES utf8", "SET time_zone = '+08:00'"],  # 設定字符集和時區
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
)

async def get_db_connection():
    return pool.connection()

async def check_mariadb_connect():
    try:
        # conn = pymysql.connect(host=host, port=int(port), user=user, password=password, database=database)
        conn = await get_db_connection()
        logging.info("MariaDB database connection successful.")
        conn.close()
    except pymysql.Error as e:
        logging.error(f"Unable to connect to MariaDB database: {e}")


async def query_in_mariadb(query: str, values: tuple = None):
    try:
        # conn = pymysql.connect(host=host, port=int(port), user=user, password=password, database=database)
        conn = await get_db_connection()
        cursor = conn.cursor()
        if values:
            cursor.execute(query, values)
        else:
            cursor.execute(query)
        result = cursor.fetchall()  # 或者使用 fetchone()，取決於你的需求
        return result
    except pymysql.Error as e:
        logging.error(f"Unable to connect to MariaDB database: {e}")
    finally:
        cursor.close()
        conn.close()


async def get_mariadb_connect():
    # Get connection and cursor
    conn = pool.connection()  # 使用同步方法來獲取連接
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # 使用字典游標
    return conn, cursor  # 返回連接和游標
