import pymysql
import redis
import urllib.parse

from config import config
from pymongo import MongoClient


class DB:
    def __init__(self):
        pass

    def get_mysql(self):
        if not hasattr(self, '_mysql') or self._mysql == None or self._mysql._closed:
            self._mysql = pymysql.connect(**config['mysql'])

        return self._mysql

    def get_mongo(self):
        if not hasattr(self, '_mongo') or self._mongo == None:
            mongo_config = {k: urllib.parse.quote(v) if isinstance(v, str) else v for k, v in config['mongo'].items()}

            uri = 'mongodb://{user}:{password}@{host}:{port}/{database}'.format(**mongo_config)
            self._mongo = MongoClient(uri)

        return self._mongo

    def get_redis(self):
        if not hasattr(self, '_redis') or self._redis == None:
            pool = redis.ConnectionPool(**config['redis'])
            self._redis = redis.Redis(connection_pool=pool)

        return self._redis

    def close_mysql(self):
        if hasattr(self, '_mysql') and self._mysql != None:
            self._mysql.close()

    def close_mongo(self):
        if hasattr(self, '_mongo') and self._mongo != None:
            self._mongo.close()

    def close_redis(self):
        if hasattr(self, '_redis') and self._redis != None:
            self._redis.connection_pool.disconnect()

    def push(self, key, value):
        db = self.get_redis()
        db.rpush(key, value)

    def len(self, key):
        db = self.get_redis()
        return db.llen(key)

    def range(self, key, start, end):
        db = self.get_redis()
        return db.lrange(key, start, end)

    def lpop(self, key):
        db = self.get_redis()
        return db.lpop(key)

    def batchpop(self, key, batch_size):
        '''
        pop most batch_size entry from redis
        '''
        db = self.get_redis()
        lst = [x for x in [db.lpop(key) for i in range(batch_size)] if x is not None]
        return lst

    def fetch(self, sql):
        db = self.get_mysql()
        cur = db.cursor()
        rows = []
        try:
            cur.execute(sql)
            rows = cur.fetchall()
        except Exception as e:
            print(e)
        finally:
            cur.close()
        return rows

    def execute(self, sqls):
        db = self.get_mysql()
        cur = db.cursor()
        try:
            for sql in sqls:
                cur.execute(sql)
            db.commit()
        except Exception as e:
            print(e)
        finally:
            cur.close()

    def executemany(self, sql, tup):
        db = self.get_mysql()
        cur = db.cursor()
        try:
            cur.executemany(sql, tup)
            db.commit()
        except Exception as e:
            print(e)
        finally:
            cur.close()

    def close(self):
        self.close_mysql()
        self.close_mongo()
        self.close_redis()
