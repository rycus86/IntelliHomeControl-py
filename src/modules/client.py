'''
Created on Dec 4, 2013

@author: Viktor Adam
'''

import re
import base64
import os
import time

from util.module import ModuleBase
from util.localization import Localization
from util import sysargs

from modules.comm.udp import UDPHandler
from modules.comm.tcp import TCPHandler
from modules.comm import Header
from modules.radio import DeviceHandler, RFModule
from modules.auth import Authentication

from entities import Entity, EntityType, EntityCommand, EntityHistory

# Shorthand method for localization
_ = Localization.localize

class RadioHandler(DeviceHandler):
    ''' RF device handler implementation to process 
        device registrations and state messages. '''
    
    def describe(self, address, unique_id, data):
        ''' Registers a device for the given physical address. '''
        
        DeviceHandler.describe(self, address, unique_id, data)
        
        etype_id = data[0]
        etype = EntityType.find(etype_id)
        if etype:
            entity = Entity.find(unique_id)
            if entity is None:
                entity = Entity(unique_id, etype, 'Unknown device: ' + unique_id, last_checkin=time.time())
                entity.save()
                print 'Device registered:', entity
                ClientModule.instance().send_state_change(entity)
            else:
                entity.last_checkin = time.time()
                entity.save()
                print 'Device found:', entity
                ClientModule.instance().send_state_change(entity)
        else:
            print 'Entity type not found:', etype_id
        
    def receive(self, address, unique_id, flags, data):
        ''' Processes received data from a physical device. '''
        
        DeviceHandler.receive(self, address, unique_id, flags, data)
        
        entity = Entity.find(unique_id)
        if entity is None:
            print 'No device found with id:', unique_id
        else:
            if entity.state_changed(data):
                ClientModule.instance().send_state_change(entity)

class ClientModule(ModuleBase): 
    ''' System module implementation responsible for serving
        client connections with data. '''
    
    DEBUG = False
    
    DEFAULT_PORT          = 49001
    DEFAULT_BIND_ADDRESS  = '0.0.0.0'
    DEFAULT_BCAST_ADDRESS = '255.255.255.255'
    DEFAULT_MCAST_GROUP   = '227.1.1.10'

    def configure(self, database):
        ModuleBase.configure(self, database)
        
        self.__radio_handler = RadioHandler()
        self.__handlers = []
        
        # register communication handlers
        for idx in xrange(len(sysargs.communication.modes)):
            mode = sysargs.communication.modes[idx]
            port = sysargs.communication.ports[idx]
            host = sysargs.communication.hosts[idx]
            
            if mode.lower() == 'mcast':
                if port is None: port = ClientModule.DEFAULT_PORT
                if host is None: host = ClientModule.DEFAULT_MCAST_GROUP
                
                handler = UDPHandler(host, port, handler=self.handle_received_message, multicast=True)
                self.__handlers.append(handler)
                
            elif mode.lower() == 'bcast':
                if port is None: port = ClientModule.DEFAULT_PORT
                if host is None: host = ClientModule.DEFAULT_BCAST_ADDRESS
                
                handler = UDPHandler(host, port, handler=self.handle_received_message, broadcast=True)
                self.__handlers.append(handler)
                
            elif mode.lower() == 'udp':
                if port is None: port = ClientModule.DEFAULT_PORT
                if host is None: host = ClientModule.DEFAULT_BIND_ADDRESS
                
                handler = UDPHandler(host, port, handler=self.handle_received_message)
                self.__handlers.append(handler)
                
            elif mode.lower() == 'tcp':
                if port is None: port = ClientModule.DEFAULT_PORT
                if host is None: host = ClientModule.DEFAULT_BIND_ADDRESS
                
                handler = TCPHandler(host, port, handler=self.handle_received_message)
                self.__handlers.append(handler)
                
            else:
                print 'Unsupported communication mode:', mode
                
    def start(self):
        ModuleBase.start(self)
        
        for handler in self.__handlers:
            handler.start()
            
        RFModule.instance().register_device_handler(self.__radio_handler)
        
    def stop(self):
        RFModule.instance().unregister_device_handler(self.__radio_handler)
        
        for handler in self.__handlers:
            handler.stop()
            
        ModuleBase.stop(self)
    
    def handle_received_message(self, handler, sender, header, message):
        ''' Handles received messages from client connections. '''
        
        if header == Header.MSG_A_LOGIN:
            if ClientModule.DEBUG:
                print 'Login Message received from', sender, ':', header, message
            
            try:
                username, password = message.split(':')
                session_id, admin = Authentication.instance().authenticate(username, password)
                if session_id is not None:
                    handler.authentication_succeeded(session_id, sender)
                    self.respond(handler, header, session_id + ('*' if admin else ''), sender)
                else:
                    handler.authentication_failed(sender)
            except:
                handler.authentication_failed(sender)
        
        # needs session checking
        elif handler.is_valid_session(message, sender):
            
            original_message = message
            message = handler.strip_session_prefix(message)
            
            if ClientModule.DEBUG:
                print 'Message received from', sender, ':', header, 
                print '\'' + message + '\'',
                print '| original was', '\'' + original_message + '\''
            
            if header == Header.MSG_A_KEEPALIVE:
                self.respond(handler, header, None, sender)
            
            elif header == Header.MSG_A_LIST_DEVICE_TYPES:
                rsp = ''
                for t in EntityType.all():
                    rsp = rsp + t.serialize() + ','
                if len(rsp) > 0:
                    rsp = rsp[0:-1]
                rsp = '[' + rsp + ']'
                
                self.respond(handler, header, rsp, sender)
                
            elif header == Header.MSG_A_LIST_DEVICES:
                typeid, name_pattern = None, None
                if re.match('^[0-9]+;.*$', message):
                    typeid, name_pattern = message.split(';')
                    typeid = int(typeid)
                elif re.match('^[0-9]+', message):
                    typeid = int(message)
                elif len(message) > 0:
                    name_pattern = message
                
                rsp = ''
                for e in Entity.list(typeid, name_pattern):
                    rsp = rsp + e.serialize() + ','
                if len(rsp) > 0:
                    rsp = rsp[0:-1]
                rsp = '[' + rsp + ']'
                
                self.respond(handler, header, rsp, sender)
                
            elif header == Header.MSG_A_SEND_COMMAND:
                entity_id, cmd = message.split('#')
                cmd_param = None
                if ';' in cmd:
                    cmd, cmd_param = cmd.split(';')
                
                entity = Entity.find(entity_id)
                if entity:
                    command = EntityCommand.find( int(cmd) )
                    if command:
                        entity.control(self, command, cmd_param)
                        self.respond(handler, header, None, sender)
                    else:
                        self.respond(handler, Header.MSG_A_ERROR, _('error.not.found.command') + ': ' + str(cmd), sender)
                else:
                    self.respond(handler, Header.MSG_A_ERROR, _('error.not.found.device') + ': ' + str(entity_id), sender)
            
            elif header == Header.MSG_A_LOAD_TYPE_IMAGE:
                imgname = message
                
                content = None
                
                image_path = self.__find_image_path(imgname)
                if image_path: 
                    imgfile = file(image_path)
                    try:
                        content = base64.b64encode(imgfile.read())
                    finally:
                        imgfile.close()
                
                if content:
                    self.respond(handler, header, content, sender)
                else:
                    self.respond(handler, Header.MSG_A_ERROR, _('error.load.image') + ': ' + imgname, sender)
                    
            elif header == Header.MSG_A_RENAME_DEVICE:
                eid, name = message.split(';', 1)
                
                entity = Entity.find(eid)
                if entity:
                    entity.name = name
                    entity.save()
                    self.send_state_change(entity)
                else:
                    self.respond(handler, Header.MSG_A_ERROR, _('error.not.found.device') + ': ' + imgname, sender)
            
            elif header == Header.MSG_A_COUNT_HISTORY:
                ts_from, ts_to, entity_id = message.split(';')
                
                time_from = None
                if ts_from:
                    time_from = int(ts_from) / 1000.0
                time_to = None
                if ts_to:
                    time_to = int(ts_to) / 1000.0
                eid = None if len(entity_id) == 0 else entity_id
                
                count = EntityHistory.count(time_from, time_to, eid)
                self.respond(handler, header, str(count), sender)
            
            elif header == Header.MSG_A_LIST_HISTORY:
                ts_from, ts_to, entity_id, limit, offset = message.split(';')
                
                time_from = None
                if ts_from:
                    time_from = int(ts_from) / 1000.0
                time_to = None
                if ts_to:
                    time_to = int(ts_to) / 1000.0
                eid = None if len(entity_id) == 0 else entity_id
                
                rsp = ''
                for h in EntityHistory.query(time_from, time_to, eid, int(limit), int(offset)):
                    rsp = rsp + '#' + str(h.timestamp) + ';' + str(h.entity_id) + ';' + str(h.entity_name) + ';' + str(h.action) + ';' + str(h.action_type)
                
                self.respond(handler, header, rsp, sender)
                
            elif header == Header.MSG_A_LIST_USERS:
                rsp_items = []
                for uid, username, administrator in Authentication.instance().list_users():
                    rsp_items.append(str(uid) + ('*' if administrator else '#') + str(username))
                
                self.respond(handler, header, ';'.join(rsp_items), sender)
                
            elif header == Header.MSG_A_USER_CREATE:
                username, password = message.split(';')
                if Authentication.instance().create_user(username, password):
                    self.respond(handler, Header.MSG_A_USERS_CHANGED, None, sender)
                else:
                    self.respond(handler, Header.MSG_A_ERROR, _('error.create.user'), sender)
                
            elif header == Header.MSG_A_USER_EDIT:
                uid, username, password = message.split(';')
                if Authentication.instance().edit_user(int(uid), username, password):
                    self.respond(handler, Header.MSG_A_USERS_CHANGED, None, sender)
                else:
                    self.respond(handler, Header.MSG_A_ERROR, _('error.edit.user'), sender)
            
            elif header == Header.MSG_A_USER_DELETE:
                uid = int(message)
                Authentication.instance().delete_user(uid)
                
                self.respond(handler, Header.MSG_A_USERS_CHANGED, None, sender)
        
        else:
            print 'Auth failed for (raw) message: \'' + str(message) + '\''
            handler.authentication_failed(sender)
        
    def respond(self, handler, header, response, destination):
        ''' Responds to an incoming client message. '''        
        if ClientModule.DEBUG:
            print 'Responding to', destination, ':', header, '\'' + ('' if response is None else response) + '\''
        
        handler.send(header, response, destination)
    
    def send_state_change(self, entity):
        ''' Broadcast state change of an entity on all communication handlers. ''' 
        message = str(entity.serialize())
            
        for handler in self.__handlers:
            handler.broadcast(Header.MSG_A_STATE_CHANGED, message)
    
    def send_message(self, unique_id, message):
        ''' Sends a message to the entity identified by "unique_id". '''
        
        entity = Entity.find(unique_id)
        if entity is None:
            print 'No device found with id:', unique_id
        else:
            if entity.entity_type.comm_type == EntityType.COMM_TYPE_RADIO:
                self.__radio_handler.send(unique_id, message)
            else:
                print 'No communication type found for:', entity.entity_type, '| entity:', entity
     
    def __find_image_path(self, imgname):
        ''' Returns the valid absolute path for the image file with the given filename. '''
        
        if os.path.isabs(imgname):
            if os.path.exists(imgname):
                return imgname
        else:
            for sp in sysargs.images.search_path:
                image_path = os.path.join(sp, imgname)
                if os.path.exists(image_path):
                    return os.path.abspath(image_path)
            
        # look for the image in the default folder
        package_dir  = os.path.dirname(__file__)
        root_dir     = os.path.dirname(package_dir)
        if os.path.basename(root_dir) == 'src':
            root_dir = os.path.dirname(root_dir)
        image_folder = os.path.join(root_dir, 'images')
        image_path   = os.path.join(image_folder, imgname)
        if os.path.exists(image_path):
            return os.path.abspath(image_path)
    
ClientModule.register()
