'''
Created on Sep 19, 2013

Package definition implementing a class
to store settings in database.

@author: Viktor Adam
'''

class Settings(object):
    ''' Utility class to store key-value settings 
        in the application database. '''
    
    __tablename__   = 'settings'
    __exists_query  = 'SELECT 1 FROM ' + __tablename__ + ' LIMIT 1'
    __create_stmt   = 'CREATE TABLE ' + __tablename__ + ' (key PRIMARY KEY, value)'
    __select_query  = 'SELECT value FROM ' + __tablename__ + ' WHERE key = ?'
    __insert_stmt   = 'INSERT INTO ' + __tablename__ + ' VALUES (:key, :value)'
    __update_stmt   = 'UPDATE ' + __tablename__ + ' SET value = :value WHERE key = :key'
    
    @classmethod
    def __initialize(cls, db):
        ''' Checks whether the related database table exists
            and creates it if it does not. '''
        try:
            db.select( Settings.__exists_query )
        except:
            db.write( Settings.__create_stmt )
    
    @classmethod
    def get(cls, db, key, def_value=None):
        ''' Returns the value for the given key, or
            the default value if there is no value for it in the database. '''
        Settings.__initialize(db)
        for row in db.select(Settings.__select_query, key):
            return row[0]
        return def_value # did not get any rows from SELECT

    @classmethod
    def set(cls, db, key, value):
        ''' Stores the given value for the key in the database. '''
        Settings.__initialize(db)
        try:
            db.write(Settings.__update_stmt, { 'key': key, 'value': value })
        except: # OK, the key probably did not exist in the table
            db.write(Settings.__insert_stmt, { 'key': key, 'value': value })
