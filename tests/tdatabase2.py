'''
Created on Aug 20, 2013

@author: Viktor Adam
'''

import unittest
from util.database import Database, RollbackException

class Test(unittest.TestCase):
    
    def setUp(self):
        # Database.DEBUG = True
        
        import os
        if os.path.exists('db'):
            for fpath in os.listdir('db'):
                os.remove('db/' + fpath)
            os.rmdir('db')
    
    def testInMemory(self):
        db = Database.in_memory_instance('abc')
        db.write('CREATE TABLE test1(a PRIMARY KEY, b)')
        db.write('INSERT INTO test1 VALUES (1, 2)')
        
        db.close()
        
        db = Database.in_memory_instance('abc')
        db.write('CREATE TABLE test1(a PRIMARY KEY, b)')
        db.write('INSERT INTO test1 VALUES (:a, :b)', { 'a': 3, 'b': '4' })
        for s in db.select('SELECT * FROM test1'):
            print 'Row:',
            for i in s:
                print i,
            print 
            
        print 'Dumping database:'
        for d in db.dump():
            print d
    
    def testDefault(self):
        db = Database.instance()
        db.write('CREATE TABLE test1(a PRIMARY KEY, b)')
        db.write('INSERT INTO test1 VALUES (1, 2)')
        
        for s in db.select('SELECT * FROM test1'):
            print 'Row:',
            for i in s:
                print i,
            print 
            
        print 'Dumping database:'
        for d in db.dump():
            print d
        
        # Cleanup
        import os
        os.remove('db/default.db')
        os.rmdir('db')
    
    def testRollback(self):
        path = 'db/rollback.db'
        
        db = Database.instance(path)
        db.write('CREATE TABLE test1(a PRIMARY KEY, b)')
        db.write('INSERT INTO test1 VALUES (1, 2)')
        
        with db.writer():
            db.write('INSERT INTO test1 VALUES (3, 4)')
            raise RollbackException
        
        try:
            with db.writer():
                raise Exception('unmanaged')
        except:
            pass # expected
        
        db.write('INSERT INTO test1 VALUES (5, 6)')
        
        for s in db.select('SELECT * FROM test1'):
            print 'Row:',
            for i in s:
                print i,
            print 
            
        print 'Dumping database:'
        for d in db.dump():
            print d
        
        # Cleanup
        import os
        os.remove(path)
        os.rmdir('db')
    
    def testSelectTableExists(self):
        db = Database.in_memory_instance('def')
        try:
            print 'Select #1:', db.select('SELECT 1 FROM test1')
        except: pass
        db.write('CREATE TABLE test1(a PRIMARY KEY, b)')
        try:
            print 'Select #1:', db.select('SELECT 1 FROM test1')
        except: pass
        db.close()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()