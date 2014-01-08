'''
Created on Dec 2, 2013

@author: Viktor Adam
'''

import unittest
import time
import sys

from util.database import Database
from entities import EntityType, Entity, EntityCommand, EntityHistory
from entities import STATE_ON, STATE_OFF
from entities import COMMAND_ON, COMMAND_OFF
from util.loader import import_modules

class Test(unittest.TestCase): 

    @classmethod
    def setUpClass(cls):
        search_path = sys.argv[0].split(':')
        import_modules(search_path, 'entities')
        EntityType.register(199, 'TestEntity', Entity)
        
        # empty history
        Database.instance().write('DELETE FROM history')
    
    def printall(self):
        print 'DB | uniqueid | typeid | name | state | statevalue | assignedid | lastcheckin'
        print 'DB | -------- | ------ | ---- | ----- | ---------- | ---------- | -----------'
        for row in Database.instance().select('SELECT * FROM entity'):
            print 'DB',
            for value in row:
                print '|', value,
            print

    def test_10_Create(self):
        te = Entity( 'UID-1234', EntityType.find(199) )
        te.save()
        self.printall()
    
    def test_11_modify1(self):
        te = Entity.find( 'UID-1234' )
        te.name = 'Test entity 1'
        te.state = STATE_ON
        te.state_value = '30%'
        te.assigned_id = 0x01
        te.last_checkin = time.time()
        te.save()
        self.printall()
        
    def test_12_modify2(self):
        te = Entity.find( 'UID-1234' )
        te.state = STATE_OFF
        te.state_value = None
        te.last_checkin = time.time()
        te.save()
        self.printall()
        
    def test_13_non_existent(self):
        te2 = Entity.find( 'UID-xxx' )
        print te2
        
    def test_14_find(self):
        te3 = Entity.find( 'UID-1234' )
        print te3
    
    def test_15_delete(self):
        Entity.delete( 'UID-1234' )
        self.printall()
        
    def test_20_light_create(self):
        tl = Entity('LIGHT-1', EntityType.find(101), name='Sample light')
        tl.assigned_id = 2
        tl.state = STATE_ON
        tl.last_checkin = time.time()
        tl.save()
        self.printall()
        print tl
        
    def test_21_light_command(self):
        tl = Entity.find( 'LIGHT-1' )
        tl.control(COMMAND_ON)
        tl.control(EntityCommand.find(100), 30)
        tl.control(COMMAND_OFF)
    
    def test_22_light_state_changed(self):
        tl = Entity.find( 'LIGHT-1' )
        tl.set_state(STATE_OFF)
        self.printall()
        print tl
    
    def test_23_power(self):
        tl = Entity('POWER-0', EntityType.find(100), 'Power plug')
        tl.assigned_id = 1
        tl.last_checkin = time.time() - 3600 # one hour before
        tl.save()
        self.printall()
        print tl
    
    def test_24_power_state_plus_control(self):
        tl = Entity.find( 'POWER-0' )
        tl.control(COMMAND_ON)
        self.printall()
        print tl
        
        tl.set_state(STATE_ON)
        self.printall()
        print tl
    
    def test_30_print_history(self):
        def ds(value):
            ret = str(value)
            return '0' + ret if len(ret) < 2 else ret
        
        print 'History size:', EntityHistory.count(None, None, None)
        
        for history in EntityHistory.query(None, None, None, None, None):
            year, month, day, hour, minute, sec, wday, yday, isdst = time.localtime(history.timestamp)  # @UnusedVariable
            strtime = ds(year) + '-' + ds(month) + '-' + ds(day) + ' '
            strtime = strtime + ds(hour) + ':' + ds(minute) + ':' + ds(sec)
            print strtime, '|', history.entity_name, '| (', history.action_type, ')', history.action
    
    def test_40_list(self):
        for e in Entity.list(None, None): print e
        for e in Entity.list(100, None): print e
        for e in Entity.list(101, None): print e
        for e in Entity.list(None, 'Power%'): print e
        for e in Entity.list(101, 'Power%'): print e
        for e in Entity.list(100, 'Power%'): print e
        print 'Serialized:'
        for e in Entity.list(None, None):
            print e.serialize()
        
        print 'As list:'
        rsp = ''
        for e in Entity.list(None, None):
            rsp = rsp + e.serialize() + ','
        if len(rsp) > 0:
            rsp = rsp[0:-1]
        rsp = '[' + rsp + ']'
        print rsp

if __name__ == "__main__":
    unittest.main()
