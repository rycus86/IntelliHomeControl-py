'''
Created on Jun 24, 2013

@author: Viktor Adam
'''

import os
import unittest
import traceback

from util.database import Database

class DatabaseTest(unittest.TestCase): 
    
    DEBUG_Database_Messages = False
    DEBUG_Database_Contents = False
    
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName=methodName)
        
        # self.path = ':memory:'
        self.path = 'test.db'
        self.db = None
    
    def setUp(self):
        Database.DEBUG = DatabaseTest.DEBUG_Database_Messages
        self.db = Database(self.path)
    
    def tearDown(self):
        if DatabaseTest.DEBUG_Database_Contents:
            for line in self.db.dump():
                print 'D|', line
            
        os.remove(self.path)
    
    def testSelect(self):
        ''' get cursor for query '''
        cursor = self.db.select("SELECT 1 as col1, 'abc' as col2")
        self.assertIsNotNone(cursor)
        ''' fetch a row from the cursor '''
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        ''' check returned values '''
        self.assertEquals(row[0], 1)
        self.assertEquals(row[1], 'abc')
        self.assertEquals(row['col1'], 1)
        self.assertEquals(row['col2'], 'abc')
    
    def testWrite(self):
        ''' Load some sample data into the database '''
        self.db.write('create table test(a, b, c)')
        self.db.write('insert into test values (?, ?, ?)', 1, 2, 3)
        self.db.write("insert into test values ('abc', 'def', null)")
        self.db.write('insert into test values (:a, :b, :c)', { 'a':1, 'b':2, 'c':9 })
        ''' Select row count '''
        (numrows, ) = self.db.select('select count(*) from test').fetchone()
        self.assertEquals(numrows, 3)
        ''' Select all rows '''
        cursor = self.db.select('select * from test')
        for row in cursor:
            ''' Test values '''
            self.assertIn(row['a'], (1, 'abc'))
            self.assertIn(row['b'], (2, 'def'))
            self.assertIn(row['c'], (3, 9, None))
    
    def testWriter(self):
        with self.db.writer():
            self.db.write('create table writer (id, name)')
            self.db.write("insert into writer values (?, ?)", 1, 'abc')
            self.db.write("insert into writer values (:id, :nm)", { 'id': 2, 'nm': 'def' })
            
            with self.db.writer():
                for (num, ) in self.db.select('select count(*) from writer'):
                    self.assertEquals(num, 2)
            
        for row in self.db.select('select * from writer'):
            for k in row.keys():
                self.assertIn(row[k], (1, 2, 'abc', 'def'))
    
    def testThreads(self):
        thread_exceptions = []
        def runt():
            try:
                self.db.select('select 1 as one')
            except Exception as ex:
                thread_exceptions.append(ex)
        def wrt():
            try:
                thread_id = str(id(threading.current_thread()))
                with self.db.writer() as wr:
                    wr.execute('create table th_' + thread_id + '(a, b, c)')
                    wr.execute('insert into th_' + thread_id + ' values (?, ?, ?)', 1, 2, 3)
                    wr.execute('insert into th_' + thread_id + ' values (?, ?, ?)', 5, 4, 6)
                    wr.execute('insert into th_' + thread_id + ' values (:a, :b, :c)', { 'a': 9, 'b': 8, 'c': 7 })
                (numrows, ) = self.db.select('select count(*) from th_' + thread_id).fetchone()
                self.assertEquals(numrows, 3)
            except Exception as ex:
                thread_exceptions.append(ex)
                traceback.print_exc()
        
        import threading
        
        threads = []
        for x in xrange(3):  # @UnusedVariable
            th = threading.Thread(target=wrt)
            th.start()
            threads.append(th)
        for x in xrange(3):  # @UnusedVariable
            th = threading.Thread(target=runt)
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
        
        self.assertEquals(len(thread_exceptions), 0, 'Exceptions: ' + str(thread_exceptions))
    
if __name__ == "__main__":
    unittest.main()
