import os
import json
import sqlite3 as sl

from logging import warning
from typing import Protocol



class SessionProtocol(Protocol):

    @classmethod
    def fromData(cls, session_id:int, data:dict) -> 'SessionProtocol':
        '''create object of its type from raw dictionaty'''



class SQLiteSessionStorage:
    def __new__(cls):
        if not hasattr(cls,'_instance'):
            cls._instance = super(SQLiteSessionStorage, cls).__new__(cls)
        return cls._instance


    def __init__(self):
        SQLITE_DB = os.getenv("SQLITE_DB")
        if not SQLITE_DB:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            SQLITE_DB = os.path.join(dir_path, '../sqlite.db')
        self.connection = sl.connect(SQLITE_DB)

        create_table_query = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL FOREGN KEY
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL FOREGN KEY,
            content STRING NOT NULL,
            
        );
        
        """
        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_query)
            conn.commit()



    def getSession(self, session_id):
        with self.connection as conn:
            pass


class JsonSessionStorage:

    activeSessions = {} 

        
    def __init__(self, Session: SessionProtocol):
        activeSessions = {}

        self.SessionCls = Session

        SESSIONS_DIR = os.getenv("BOT_SESSIONS_DIR")
        if not SESSIONS_DIR:
            dir_path = os.path.dirname(os.path.realpath(__file__));
            SESSIONS_DIR = os.path.join(dir_path,'../.aiosessions')
        self.DIR = SESSIONS_DIR
        sessionFiles = os.scandir(self.DIR);

        for sessionFile in sessionFiles:
            session_id = int(sessionFile.name)
            with open(os.path.join(self.DIR, sessionFile), 'r') as file:
                jsonStr = file.read()

            sessionData = json.loads(jsonStr)
            
            self.activeSessions[session_id] = Session.fromData(session_id, sessionData)

        print(f'\n\nLoaded sessions: {self.activeSessions.keys()}\n')

        


    def save(self, session_id, sessionData:dict):
        session = self.getSession(session_id=session_id)
        session.__dict__.update(sessionData)

        filePath = os.path.join(self.DIR, str(session_id))
        with open(filePath, 'w') as file:
            json.dump(sessionData, file)


    def getSession(self, session_id):
        session_id = session_id
        if session_id not in self.activeSessions.keys():
            print(f'create new Session: {session_id}')
            self.activeSessions[session_id] = self.SessionCls(session_id)

        return self.activeSessions[session_id]
