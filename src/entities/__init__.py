'''
Created on Dec 2, 2013

This module contains classes responsible
managing entities, their types, states and commands
and the history also.

@author: Viktor Adam
'''

import sqlite3
import time

from util.database import Database
from util.loader import import_modules
from util import sysargs

class EntityState(object):
    ''' Class representing a state of an entity. '''
    
    __all_states = []
    
    def __init__(self, sid, name):
        self.id   = sid
        self.name = name
        
        for s in EntityState.__all_states:
            if self.id == s.id:
                return
        
        # register this state as new
        EntityState.__all_states.append(self)
    
    def serialize(self):
        ''' Returns a network-compatible string representation of the object. '''
        return str(self.id) + ';' + str(self.name)
    
    def __str__(self):
        return self.name
    
    @classmethod
    def find(cls, sid):
        ''' Returns the state registered with "sid" identifier. '''
        for s in EntityState.__all_states:
            if s.id == sid:
                return s
        return None

# list of default states
STATE_UNKNOWN  = EntityState(1, 'Unknown')
STATE_ON       = EntityState(2, 'On')
STATE_OFF      = EntityState(3, 'Off')

class EntityCommand(object):
    ''' Class representing a command which can be sent to an entity. '''
    
    __all_commands = []
    
    RANGE_0_TO_100 = 'range(0-100)'
    
    def __init__(self, cid, name, parameter_type = None):
        self.id   = cid
        self.name = name
        self.parameter_type = parameter_type
    
        for c in EntityCommand.__all_commands:
            if self.id == c.id:
                return
        
        # register this command as new
        EntityCommand.__all_commands.append(self)
    
    def serialize(self):
        ''' Returns a network-compatible string representation of the object. '''
        res = str(self.id) + ';' + str(self.name) + ";"
        if self.parameter_type:
            res = res + str(self.parameter_type)
        return res
    
    def __str__(self):
        return self.name
    
    @classmethod
    def find(cls, cid):
        ''' Returns the command registered with "cid" identifier. '''
        for c in EntityCommand.__all_commands:
            if c.id == cid:
                return c
        return None

# list of default commands
COMMAND_ON  = EntityCommand(1, 'Turn On')
COMMAND_OFF = EntityCommand(2, 'Turn Off')

class EntityType(object):
    ''' Class representing an entity type. '''
    
    __all_types = []
    
    COMM_TYPE_RADIO = 0x01
    
    def __init__(self, type_id, type_name, entity_class, commands=[], color=None, image=None, communication_type=COMM_TYPE_RADIO):
        self.type_id      = type_id
        self.type_name    = type_name
        self.entity_class = entity_class
        self.commands     = commands
        self.color        = color
        self.image        = image
        self.comm_type    = communication_type
    
    def serialize(self):
        ''' Returns a network-compatible string representation of the object. '''
        res = str(self.type_id) + ';' + str(self.type_name) + ';' + (self.color if self.color else '') + ';' + (self.image if self.image else '')
        res = res + ';['
        if len(self.commands) > 0:
            for c in self.commands:
                res = res + c.serialize() + ','
            res = res[0:-1]
        res = res + ']'
        return res
        
    @classmethod
    def register(clazz, type_id, type_name, entity_class, commands=[], color=None, image=None):
        ''' Registers an entity type based on the given parameters. '''        
        instance = clazz(type_id, type_name, entity_class, commands, color, image)
        if isinstance(instance, EntityType):
            for t in EntityType.__all_types:
                if t.type_id == instance.type_id:
                    return
            
            # type not found yet
            print 'Registering entity type:', type_name
            EntityType.__all_types.append(instance)
    
    @classmethod
    def find(cls, type_id):
        ''' Returns the type registered with "type_id" identifier. '''
        for t in EntityType.__all_types:
            if t.type_id == type_id:
                return t
    
    @classmethod
    def all(cls):
        ''' Returns the list of all registered entity types. '''
        return EntityType.__all_types

class EntityHistory(object):
    ''' Class representing an item of the entities' history. '''
    
    __tablename__  = 'history'
    __table_exists = 'SELECT 1 FROM ' + __tablename__ + ' LIMIT 1'
    __table_create = 'CREATE TABLE ' + __tablename__ + ' (timestamp, entityid, entityname, action, type)'
    __insert_stmt  = 'INSERT INTO ' + __tablename__ + ' (timestamp, entityid, entityname, action, type) VALUES (?, ?, ?, ?, ?)'
    
    Type_State   = 'state'
    Type_Command = 'command'
    
    def __init__(self, timestamp, entity_id, entity_name, action, action_type):
        self.timestamp   = timestamp
        self.entity_id   = entity_id
        self.entity_name = entity_name
        self.action      = action
        self.action_type = action_type
    
    @classmethod
    def count(cls, time_from, time_to, entity_id):
        ''' Returns the number of records between "time_from" and "time_to"
            for the entity with the given "entity_id" identifier.
            All parameters are optional. '''
        
        conditions = []
        parameters = dict()
        
        if time_from is not None:
            conditions.append('timestamp >= :ts_from')
            parameters['ts_from'] = time_from
        if time_to is not None:
            conditions.append('timestamp <= :ts_to')
            parameters['ts_to'] = time_to
        if entity_id is not None:
            conditions.append('entityid = :eid')
            parameters['eid'] = entity_id
            
        query = 'SELECT COUNT(rowid) FROM ' + EntityHistory.__tablename__
        if len(conditions) > 0:
            query = query + ' WHERE ' + ' AND '.join(conditions)
            
        return Database.instance().select(query, parameters).fetchone()[0]
    
    @classmethod
    def query(cls, time_from, time_to, entity_id, limit, offset):
        ''' Returns history at most "limit" records starting from "offset" 
            between "time_from" and "time_to" for the entity with the given "entity_id" identifier.
            The "limit" and "offset" parameters are required the rest are optional. '''
        
        conditions = []
        parameters = dict()
        
        if time_from is not None:
            conditions.append('timestamp >= :ts_from')
            parameters['ts_from'] = time_from
        if time_to is not None:
            conditions.append('timestamp <= :ts_to')
            parameters['ts_to'] = time_to
        if entity_id is not None:
            conditions.append('entityid = :eid')
            parameters['eid'] = entity_id
            
        query = 'SELECT timestamp, entityid, entityname, action, type FROM ' + EntityHistory.__tablename__
        if len(conditions) > 0:
            query = query + ' WHERE ' + ' AND '.join(conditions)

        query = query + ' ORDER BY timestamp DESC'

        if limit is not None:
            query = query + ' LIMIT :limit'
            parameters['limit'] = limit
            
            if offset is not None:
                query = query + ' OFFSET :offset'
                parameters['offset'] = offset
        
        db = Database.instance()
        for timestamp, entityid, entityname, action, actiontype in db.select(query, parameters):
            yield EntityHistory(timestamp, entityid, entityname, action, actiontype)
    
    @classmethod
    def log(cls, entity, action, action_type):
        ''' Saves an entry to the database. '''
        db = Database.instance()
        with db.writer():
            db.write(EntityHistory.__insert_stmt, time.time(), entity.unique_id, entity.name, action, action_type)
    
    @classmethod
    def check_database_table(cls):
        ''' Checks whether the related database table exists
            and creates it if is does not. '''
        db = Database.instance()
        with db.writer():
            try:
                db.select(EntityHistory.__table_exists)
            except:
                db.write(EntityHistory.__table_create)

EntityHistory.check_database_table()
        
class Entity(object): 
    ''' Class representing an entity alias device. '''
    
    __tablename__  = 'entity'
    __table_exists = 'SELECT 1 FROM ' + __tablename__ + ' LIMIT 1'
    __table_create = 'CREATE TABLE ' + __tablename__ + ' (uniqueid PRIMARY KEY, typeid, name, stateid, statevalue, lastcheckin)'
    __query_find   = 'SELECT typeid, name, stateid, statevalue, lastcheckin FROM ' + __tablename__ + ' WHERE uniqueid = ?'
    __exists_query = 'SELECT 1 FROM ' + __tablename__ + ' WHERE uniqueid = ?'
    __insert_stmt  = 'INSERT INTO ' + __tablename__ + ' (uniqueid, typeid, name, stateid, statevalue, lastcheckin) VALUES (?, ?, ?, ?, ?, ?)'
    __update_stmt  = 'UPDATE ' + __tablename__ + ' SET name = ?, stateid = ?, statevalue = ?, lastcheckin = ? WHERE uniqueid = ?'
    __delete_stmt  = 'DELETE FROM ' + __tablename__ + ' WHERE uniqueid = ?'
    # list queries
    __list_query_all = 'SELECT uniqueid, typeid, name, stateid, statevalue, lastcheckin FROM ' + __tablename__
    __list_query_by_type = __list_query_all + ' WHERE typeid = :type'
    __list_query_by_name = __list_query_all + ' WHERE name LIKE :name'
    __list_query_by_type_and_name = __list_query_all + ' WHERE typeid = :type AND name LIKE :name'
    __list_query_order_by = ' ORDER BY name'
    
    def __init__(self, unique_id, entity_type, name='Unnamed entity', state=STATE_UNKNOWN, state_value=None, last_checkin=0):
        self.unique_id    = unique_id
        self.entity_type  = entity_type
        self.name         = name
        self.state        = state
        self.state_value  = state_value
        self.last_checkin = last_checkin
    
    def control(self, controller, command, value=None):
        ''' Sends the "command" with the "value" parameter
            to the entity with the help of the "controller"
            which is an instance of the ClientModule. '''
        
        # default execution: log doing nothing
        print 'Discarding command', command, 
        if value:
            print '(', value, ')',
        print '|', self
    
    def state_changed(self, state_message):
        ''' Processes state messages and returns True,
            if the state of the entity changes. '''
        
        print '[' + str(self) + ']:' ,'State message received:', state_message
        return False
    
    def set_state(self, state, value=None, update_last_checkin=True):
        ''' Sets the state of the entity, stores it into the database
            and logs it into the history. '''
        
        self.state          = state
        self.state_value    = value
        if update_last_checkin:
            self.last_checkin = time.time()
        
        self.save()
        self.log_state()
        
    def describe_state(self):
        ''' Returns the string representation of the current state. '''
        
        strstate = str(self.state)
        if self.state_value is not None:
            strstate = strstate + ': ' + str(self.state_value)
        return strstate
        
    def log_state(self):
        ''' Inserts an entry with the current state into the history. '''
        
        action = self.describe_state()
        EntityHistory.log(self, 'State changed to ' + action, EntityHistory.Type_State)
    
    def log_command(self, action):
        ''' Inserts an entry for the given command action into the history. '''
        
        EntityHistory.log(self, action, EntityHistory.Type_Command)
    
    def save(self):
        ''' Inserts or updates the entity in the database. '''
        
        db = Database.instance()
        with db.writer():
            row = Database.instance().select(Entity.__exists_query, self.unique_id).fetchone()
            if row is None:
                db.write(Entity.__insert_stmt, self.unique_id, self.entity_type.type_id, self.name, self.state.id, self.state_value, self.last_checkin)
            else:
                db.write(Entity.__update_stmt, self.name, self.state.id, self.state_value, self.last_checkin, self.unique_id)
    
    def serialize(self):
        ''' Returns a network-compatible string representation of the object. '''
        res = str(self.unique_id) + ';' + str(self.entity_type.type_id) + ';' + str(self.name) + ';'
        res = res + str(self.state.serialize()) + ';'
        if self.state_value:
            res = res + str(self.state_value)
        res = res + ';' + str(self.last_checkin)
        return res
    
    def __str__(self):
        return self.entity_type.type_name + ' [' + str(self.unique_id) + ']: ' + self.name + ' -- ' + \
                str(self.state) + ' (' + str(self.state_value) + ') at ' + time.ctime(self.last_checkin)
    
    @classmethod
    def find(cls, unique_id):
        ''' Returns the entity registered with "unique_id" identifier. '''
        row = Database.instance().select(Entity.__query_find, unique_id).fetchone()
        if row:
            return Entity.__create_from_db_row(unique_id, row)
    
    @classmethod
    def __create_from_db_row(cls, unique_id, row):
        ''' Instantiates an entity based on its parameters loaded from the database. '''
        
        etype, ename, estate, statevalue, lcheckin = row
        entity_type = EntityType.find(etype)
        clazz = entity_type.entity_class
        return clazz(unique_id, entity_type, ename, EntityState.find(estate), statevalue, lcheckin)
    
    @classmethod
    def delete(cls, unique_id):
        ''' Deletes the entity from the database with the given identifier. '''
        
        db = Database.instance()
        with db.writer():
            db.write(Entity.__delete_stmt, unique_id)
    
    @classmethod
    def list(cls, typeid=None, name_pattern=None):
        ''' Lists entities with the given type identifier and whose
            names match the given pattern. Both parameters are optional. '''
        
        query = Entity.__list_query_all
        query_parameters = { }
        
        if typeid is not None:
            if name_pattern is not None:
                query = Entity.__list_query_by_type_and_name
                query_parameters = { 'type': typeid, 'name': name_pattern }
            else:
                query = Entity.__list_query_by_type
                query_parameters = { 'type': typeid }
        elif name_pattern is not None:
            query = Entity.__list_query_by_name
            query_parameters = { 'name': name_pattern }
        
        query += Entity.__list_query_order_by
        
        selection = None
        if query_parameters is not None:
            selection = Database.instance().select(query, query_parameters)
        else:
            selection = Database.instance().select(query)
            
        for row in selection:
            # uniqueid, typeid, name, stateid, statevalue, lastcheckin
            unique_id, row = row[0], (row[1], row[2], row[3], row[4], row[5])
            yield Entity.__create_from_db_row(unique_id, row)
            
    @classmethod
    def check_database_table(cls):
        ''' Checks whether the related database table exists
            and creates it if is does not. '''
        
        db = Database.instance()
        with db.writer():
            try:
                db.select(Entity.__table_exists)
            except:
                db.write(Entity.__table_create)

Entity.check_database_table()

# load all modules containing entity definitions
__entities_paths = ['entities']
__entities_paths.extend(sysargs.entities.search_path)
import_modules(__entities_paths, 'entities')
