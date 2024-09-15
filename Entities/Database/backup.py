import os
import threading
import time
from datetime import datetime

import bson
from pymongo import MongoClient


def start_timer():
    def entrypoint():  # this use to auto backup database every 24 hours
        while True:
            now = datetime.now()
            if now.hour <= 2 and now.minute <= 30:
                start_backup()
                time.sleep(72000)
            else:
                time.sleep(3)

    t = threading.Thread(target=entrypoint, daemon=True)
    t.start()


def dump(collections, conn, db_name, path):
    """
    MongoDB Dump
    :param collections: Database collections name
    :param conn: MongoDB client connection
    :param db_name: Database name
    :param path:
    :return:
    """

    db = conn[db_name]
    for coll in collections:
        with open(os.path.join(path, f'{coll}.bson'), 'wb+') as f:
            for doc in db[coll].find():
                f.write(bson.BSON.encode(doc))


def restore(path, conn, db_name):
    """
    MongoDB Restore
    :param path: Database dumped path
    :param conn: MongoDB client connection
    :param db_name: Database name
    :return:
    """

    db = conn[db_name]
    for coll in os.listdir(path):
        if coll.endswith('.bson'):
            try:
                with open(os.path.join(path, coll), 'rb+') as f:
                    db[coll.split('.')[0]].insert_many(bson.decode_all(f.read()))
            except:
                pass


def start_restore():
    DB_BACKUP_DIR = 'Backups/'
    conn = MongoClient("mongodb://localhost:27017/")
    db_name = 'KafehFekrDB'
    restore(DB_BACKUP_DIR, conn, db_name)


def start_backup():
    DB_BACKUP_DIR = 'Backups/'
    conn = MongoClient("mongodb://localhost:27017/")
    db_name = 'KafehFekrDB'
    collections = ['users', 'user_history', 'game_history', 'config']
    dump(collections, conn, db_name, DB_BACKUP_DIR)
