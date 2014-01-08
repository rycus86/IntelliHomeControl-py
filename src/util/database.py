'''
Created on Jun 24, 2013

This module defines classes and functions related to SQLite database management.

@author: Viktor Adam
'''

import threading
import sqlite3
import os

class Database(object):
    ''' Class managing SQLite database connections. '''

    ''' Enables debugging SQL statements '''    
    DEBUG = False
    TEST_USE_IN_MEMORY_AS_DEFAULT = False
    
    __static_ins_path  = 'db/default.db'     # Default path for file-based database
    __static_ins_mem   = 'default.memory'    # Default name for in-memory database
    __static_instances = { }                 # Singleton database instances
    
    # Calculating correct default database location
    try:
        __package_dir  = os.path.dirname(__file__)
        __root_dir     = os.path.dirname(__package_dir)
        if os.path.basename(__root_dir) == 'src':
            __root_dir = os.path.dirname(__root_dir)
        __static_ins_path = os.path.join(__root_dir, __static_ins_path)
    except:
        pass
    
    @classmethod
    def instance(cls, path=None): 
        ''' Returns a database instance with the database file located at path. '''
        
        if Database.TEST_USE_IN_MEMORY_AS_DEFAULT:
            return Database.in_memory_instance(path)
        
        if not path:
            path = Database.__static_ins_path
        
        if path in Database.__static_instances: 
            return Database.__static_instances[path]
        else:
            dirname = os.path.dirname(path)
            if len(dirname) > 0 and not os.path.exists(dirname):
                os.mkdir(dirname)
            
            instance = Database(path)
            Database.__static_instances[path] = instance
            return instance
    
    @classmethod
    def in_memory_instance(cls, name=None):
        ''' Returns an in-memory database instance for the given name. '''
        
        name = name if name is not None else Database.__static_ins_mem
        mname = '*mem*' + name
        
        def on_delete():
            del Database.__static_instances[mname]
        
        class InMemoryDatabase(Database):
            def __init__(self):
                Database.__init__(self, ':memory:')
                self.__in_memory_conn = Database.connect(self)
                self.__is_valid = True
            def connect(self):
                return self.__in_memory_conn
            def commit(self):
                self.__in_memory_conn.commit()
            def close(self, commit=True):
                self.commit()
                self.__in_memory_conn.close()
                on_delete()

        if mname in Database.__static_instances:
            return Database.__static_instances[mname]
        else:
            instance = InMemoryDatabase()
            Database.__static_instances[mname] = instance
            return instance
    
    def __init__(self, path):
        self.__db_path = path               # Database path
        self.__wr_lock = threading.RLock()  # Write lock (reentrant)
        self.__wr_conn = None               # Writer connection
        self.__wr_count = 0;                # Writer reference counter
        
    def connect(self):
        ''' Creates an SQLite database connection object with Row factory '''
        conn = sqlite3.connect(self.__db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def select(self, sql, *parameters):
        ''' Executes a read-only SQL statement '''
        if parameters and len(parameters) > 0:
            if isinstance(parameters[0], dict):
                parameters = parameters[0] # use this dictionary as the only parameter
        
        if self.__wr_conn: # if we are in a writer session
            with self.__wr_lock:
                if self.__wr_conn: # if we are still writing
                    if Database.DEBUG: print 'RLK|', sql
                    return self.__wr_conn.execute(sql, parameters)
        
        # if we weren't writing
        with self.connect() as conn:
            if Database.DEBUG: print 'RNO|', sql
            return conn.execute(sql, parameters)
    
    def write(self, sql, *parameters):
        ''' Executes an SQL statement that writes the database '''
        if parameters and len(parameters) > 0:
            if isinstance(parameters[0], dict):
                parameters = parameters[0] # use this dictionary as the only parameter
        
        with self.__wr_lock:
            if self.__wr_conn: # if we are in a writer session
                if Database.DEBUG: print 'WLK|', sql
                cursor = self.__wr_conn.cursor()
                cursor.execute(sql, parameters)
                return cursor.lastrowid
            else: # use a single writer connection and commit after this statement
                with self.connect() as conn:
                    if Database.DEBUG: print 'WNO|', sql
                    cursor = conn.cursor()
                    cursor.execute(sql, parameters)
                    return cursor.lastrowid
    
    def writer(self):
        ''' 
        Creates a writer context object that automatically 
        uses the writer lock and commits the connection
        after the last writer session has exited the context.
        '''
        
        def on_enter():
            ''' When entering the context '''
            self.__wr_lock.acquire()
            try:
                if not self.__wr_conn:
                    self.__wr_conn = self.connect()
                    if Database.DEBUG: print 'BEGIN'
            finally:
                self.__wr_count += 1
                
        def on_exit(success):
            ''' When exiting the context '''
            try:
                if success:
                    if Database.DEBUG: print 'COMMIT'
                    self.__wr_conn.commit()
                else:
                    if Database.DEBUG: print 'ROLLBACK'
                    self.__wr_conn.rollback()
            finally:
                self.__wr_count -= 1
                if self.__wr_count == 0: 
                    self.__wr_conn = None
                self.__wr_lock.release()
                
        def on_execute(sql, *parameters):
            ''' Wrapper method for executing SQL statements in the writer session '''
            
            while parameters and len(parameters) > 0:
                # Do this until the parameter is either a simple dict or a tuple
                if isinstance(parameters[0], dict):
                    parameters = parameters[0]
                    break
                elif isinstance(parameters[0], tuple):
                    parameters = parameters[0]
                else: break
                
            # Do the actual SQL statement execution
            self.__wr_conn.execute(sql, parameters)
        
        class DBWriter(object):
            ''' Helper class to use in Python context (with) '''
            def __enter__(self):
                on_enter()
                return self
            def __exit__(self, exc_type, exc_value, traceback):
                on_exit(exc_value == None)
                return exc_type == RollbackException
            def execute(self, sql, *parameters):
                try:
                    on_execute(sql, parameters)
                except:
                    print 'GotException!' # TODO: handle exception
                    pass
                
        return DBWriter()
    
    def dump(self): # Does not work on ':memory:' databases
        ''' Produces an SQL dump of the current database state '''
        if self.__wr_conn: # if we are in a writer session
            with self.__wr_lock:
                if self.__wr_conn: # if we are still writing
                    for line in self.__wr_conn.iterdump():
                        yield line
                    return
        
        for line in self.connect().iterdump():
            yield line
        
    def __str__(self, *args, **kwargs):
        return 'Database instance #' + str(id(self))

class RollbackException(Exception):
    ''' Custom exception type for manually rolling back connections '''
    pass
