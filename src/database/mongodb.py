import logging, os
from pymongo import MongoClient

async def check_mongodb_connect():
    try:
        # client = MongoClient(os.getenv("MONGODB_URL"))
        client = MongoClient(
            host=os.getenv("MONGODB_HOST"),
            port=int(os.getenv("MONGODB_PORT")),
            username=os.getenv("MONGODB_PORTL"),
            password=os.getenv("MONGODB_PORT")
        )
        logging.info("MongoDB database connection successful.")
        client.close()
    except Exception as e:
        logging.error(f"Unable to connect to MongoDB database: {e}")


def connect_to_mongodb(collection_name):
    # client = MongoClient(os.getenv("MONGODB_URL"))
    client = MongoClient(
            host=os.getenv("MONGODB_HOST"),
            port=int(os.getenv("MONGODB_PORT")),
            username=os.getenv("MONGODB_PORTL"),
            password=os.getenv("MONGODB_PORT")
        )
    collection = client[os.getenv("MONGODB_DB")][collection_name]
    # collection = client["CoolAPI"][collection_name]
    return collection



# # 連接 MongoDB 使用 mongodb+srv 協議
# def connect_mongodb():
#     client = MongoClient(os.getenv("MONGODB_URL"))  # 直接使用 URI 進行連接
#     db = client[os.getenv("MONGODB_DB")]  # 選擇資料庫
#     return db

# # 使用連線
# db = connect_mongodb()

# # 顯示所有集合名稱
# print(db.list_collection_names())

# # 查詢 MongoDB 資料
# collection = db["your_collection"]
# data = collection.find()  # 查詢資料
# for doc in data:
#     print(doc)