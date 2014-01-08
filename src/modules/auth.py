'''
Created on Sep 19, 2013

This module defines a system module to
handle basic authentication support.

@author: Viktor Adam
'''

import uuid
import hashlib

from util.module import ModuleBase
from util.database import Database

class Session(object):
    ''' Class storing data of a client session. '''
    
    def __init__(self, userid):
        self.user_id    = userid
        self.session_id = uuid.uuid4().get_hex()

class Authentication(ModuleBase): 
    ''' Very basic module to authenticate client sessions 
        and to handle user management. '''
    
    __tablename__   = 'auth'
    __exists_query  = 'SELECT 1 FROM ' + __tablename__ + ' LIMIT 1'
    __create_stmt   = 'CREATE TABLE ' + __tablename__ + ' (uid INTEGER PRIMARY KEY AUTOINCREMENT, username, password, administrator)'
    __admin_exists_query = 'SELECT username FROM ' + __tablename__ + ' WHERE administrator = 1'
    __admin_insert_stmt  = 'INSERT INTO ' + __tablename__ + '(username, password, administrator) VALUES (?, ?, 1)'
    __auth_query    = 'SELECT uid, administrator FROM ' + __tablename__ + ' WHERE username = ? AND password = ?'
    __list_query    = 'SELECT uid, username, administrator FROM ' + __tablename__ + ' ORDER BY administrator DESC, username ASC'
    __user_exists_query = 'SELECT uid FROM ' + __tablename__ + ' WHERE username = ?'
    __user_create_stmt  = 'INSERT INTO ' + __tablename__ + ' (username, password, administrator) VALUES (?, ?, 0)'
    __user_edit_stmt    = 'UPDATE ' + __tablename__ + ' SET username = ?, password = ? WHERE uid = ?'
    __user_delete_stmt  = 'DELETE FROM ' + __tablename__ + ' WHERE uid = ?'
    
    def initialize(self):
        ModuleBase.initialize(self)
        self.__sessions = { }
    
    def configure(self, database):
        ModuleBase.configure(self, database)
        
        # Checking database table
        try:
            database.select(Authentication.__exists_query)
        except:
            database.write(Authentication.__create_stmt)
            
        # Checking administrator user
        with database.writer():
            admin_username = database.select(Authentication.__admin_exists_query).fetchone()
            if not admin_username:
                database.write(
                       Authentication.__admin_insert_stmt, 
                       'admin', hashlib.md5('admin').hexdigest())
                print 'AUTH| Created default administrator user'
    
    def authenticate(self, username, password_hash):
        ''' Executes authentication with the given credentials,
            returns the session information if it succeeds. '''
        userid, admin = Database.instance().select(Authentication.__auth_query, username.lower(), password_hash).fetchone()
        if userid:
            return (self.__initialize_session(userid), admin)
    
    def __initialize_session(self, userid):
        ''' Creates a new session for the user with the given identifier. '''
        session = Session(userid)
        self.__sessions[session.session_id] = session
        return session.session_id
    
    def get_session(self, sessionid):
        ''' Returns the session parameters for the given identifier. '''
        if sessionid in self.__sessions:
            return self.__sessions[sessionid]
        
    def list_users(self):
        ''' Lists parameters of all known users in the database. '''
        for uid, username, admin in Database.instance().select(Authentication.__list_query):
            yield (uid, username, admin)
            
    def create_user(self, username, password):
        ''' Inserts a new user into the database with the given credentials. '''
        db = Database.instance()
        with db.writer():
            if db.select(Authentication.__user_exists_query, username.lower()).fetchone():
                return False
            else:
                db.write(Authentication.__user_create_stmt, username.lower(), password)
                return True
    
    def edit_user(self, uid, username, password):
        ''' Modifies the credentials of the user with the given identifier. '''
        db = Database.instance()
        with db.writer():
            existing_uid = db.select(Authentication.__user_exists_query, username.lower()).fetchone()[0]
            if existing_uid and existing_uid != uid:
                return False
            else:
                db.write(Authentication.__user_edit_stmt, username.lower(), password, uid)
                return True
    
    def delete_user(self, uid):
        ''' Deletes the user with the given identifier. '''
        db = Database.instance()
        with db.writer():
            db.write(Authentication.__user_delete_stmt, uid)

Authentication.register()
