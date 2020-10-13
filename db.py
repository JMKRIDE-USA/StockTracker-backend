import sqlite3
import datetime
from random import randint

DB_PATH = 'inventory.db'

class FatalError(Exception):
    pass

class NonFatalError(Exception):
    pass

class DB:
    def __init__(self):
        self._conn = None
        self.uid = randint(100000, 999999)

    def log(self, *args):
        print("[QUID: {}][{}]".format(self.uid, datetime.datetime.now()), *args)

    def log_query(self, query_string):
        self.log("[DEBUG] Running: \"{query_string}\"".format(query_string=query_string))

    def connect(self):
        try:
            self._conn = sqlite3.connect(DB_PATH)
        except sqlite3.Error as error:
            self.log("Error connecting to DB:", error)
            raise FatalError from error

        return self._conn

    def close_connection(self):
        if self._conn:
            try:
                self._conn.close()
                return True
            except sqlite3.Error as error:
                self.log("Error connecting to DB:", error)
                raise FatalError from error
        else:
            return False
    
    def get_cursor(self):
        try:
            cursor = self._conn.cursor()
        except sqlite3.Error as error:
            self.log("Error creating cursor:", error)
            raise FatalError from error

        return cursor

    def execute_cursor(self, cursor, sql, write=False):
        try:
            cursor.execute(sql)
        except sqlite3.Error as error:
            self.log("Error executing cursor:", error)
            raise FatalError from error

        if write:
            try:
                self._conn.commit()
            except sqlite3.Error as error:
                self.log("Error committing writes:", error)
                raise FatalError from error

    def fetch_results(self, cursor):
        result = []
        try:
            result = cursor.fetchall()
            cursor.close()
        except sqlite3.Error as error:
            self.log("Error fetching/closing cursor:", error)
            raise FatalError from error
            
        return result

  
def query(sql, write=False):
    db = DB()
    db.log_query(sql)

    result = None

    try:
        db.connect()
        cursor = db.get_cursor()
        db.execute_cursor(cursor, sql, write=write)

        result = db.fetch_results(cursor)

        db.close_connection()
    except sqlite3.Error as error:
        db.log("[Uncaught Exception]: ", error)
    except FatalError as error:
        db.log("Fatal Error Occurred:", error)
    
    finally:  # do your best to clean up your mess
        try:
            db.cursor.close()
        except:
            pass
        try:
            db.close_connection()
        except:
            pass

    if not result and not write:
        db.log("Failed to produce result.")
    else:
        db.log("[DEBUG] Result:", result) 

    return result
