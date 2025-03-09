import os
import sqlite3
from datetime import datetime
import logging

def create_counter():
    conn = sqlite3.connect('counter.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS counters (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        count INTEGER NOT NULL,
        last_updated TIMESTAMP NOT NULL
    )''')

    cursor.execute('''
            INSERT INTO counters (name, count, last_updated)
            VALUES (?, ?, ?)
        ''', ('random_pic', 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    cursor.execute('''
            INSERT INTO counters (name, count, last_updated)
            VALUES (?, ?, ?)
        ''', ('mcstatus', 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def check_counter():
    if not os.path.exists("counter.db"):
        create_counter()
        logging.info("Counter create successful!")
    else:
        logging.info("Counter exists!")

def query_counter(name):
    conn = sqlite3.connect('counter.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM counters
        WHERE name = ?
    ''', (name,))
    return cursor.fetchone()


def query_counter_json(name):
    query = query_counter(name)
    data = {
        "id": query[0],
        "name": query[1],
        "count": query[2],
        "last_updated": query[3]
    }
    return data


def query_all_counter():
    conn = sqlite3.connect('counter.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM counters
    ''')
    return cursor.fetchall()


def query_all_counter_json():
    data = []
    for item in query_all_counter():
        json_item = {
            "id": item[0],
            "name": item[1],
            "count": item[2],
            "last_updated": item[3],
        }
        data.append(json_item)
    return data


def update_counter(name):
    count = query_counter(name)[2]
    count_new = count + 1
    conn = sqlite3.connect('counter.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE counters
        SET count = ?,
            last_updated = ?
        WHERE name = ?
    ''', (count_new, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name))
    conn.commit()
    conn.close()
