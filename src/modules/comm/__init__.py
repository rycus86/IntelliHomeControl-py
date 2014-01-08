'''
Created on Dec 4, 2013

Basic communication related classes.

@author: Viktor Adam
'''

class Header(object):
    ''' Message header values used in server-client communication. '''
    
    MSG_A_LOGIN                 = 0xA1
    MSG_A_LIST_DEVICE_TYPES     = 0xA2
    MSG_A_LIST_DEVICES          = 0xA3
    MSG_A_SEND_COMMAND          = 0xA4
    MSG_A_STATE_CHANGED         = 0xA5
    MSG_A_LOAD_TYPE_IMAGE       = 0xA6
    MSG_A_RENAME_DEVICE         = 0xA7
    MSG_A_COUNT_HISTORY         = 0xB1
    MSG_A_LIST_HISTORY          = 0xB2
    MSG_A_LIST_USERS            = 0xC1
    MSG_A_USER_CREATE           = 0xC2
    MSG_A_USER_EDIT             = 0xC3
    MSG_A_USER_DELETE           = 0xC4
    MSG_A_USERS_CHANGED         = 0xC5
    MSG_A_KEEPALIVE             = 0xE0
    MSG_A_ERROR                 = 0xF0
    MSG_A_ERROR_INVALID_SESSION = 0xF1
    MSG_A_EXIT                  = 0xFE

class CommunicationHandler(object):
    ''' Abstract communication handler definition used to communicate with remote clients. '''
    
    def __init__(self, host, port, handler):
        self.host    = host
        self.port    = int(str(port))
        self.handler = handler
    
    def start(self):
        ''' Starts the handler. '''
        pass
    
    def stop(self):
        ''' Stops the handler.'''
        pass
    
    def send(self, header, data, destination):
        ''' Sends a message to the destination. '''
        pass
    
    def broadcast(self, header, message):
        ''' Broadcasts a device to all known clients. '''
        pass
    
    def authentication_succeeded(self, session_id, sender):
        ''' Informs the handler about a successful authentication. '''
        pass
    
    def authentication_failed(self, sender):
        ''' Informs the handler about a failed authentication. '''
        pass
    
    def is_valid_session(self, message, sender):
        ''' Returns True, if the sender and its message belongs to a valid session. '''
        return False
    
    def strip_session_prefix(self, message):
        ''' Returns the received message without the session identification. '''
        return message
    