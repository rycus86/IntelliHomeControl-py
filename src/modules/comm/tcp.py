'''
Created on Dec 5, 2013

TCP/IP based communication handler implementation.

@author: Viktor Adam
'''

import socket
import threading
import traceback

from modules.comm import CommunicationHandler

class SenderInfo(object):
    ''' Class containing information about a client connection. '''
    
    def __init__(self, socket, address):
        self.socket     = socket
        self.address    = address
        self.session_id = None
        self.enabled    = True
    
    def __str__(self):
        return str(self.address)

class TCPHandler(CommunicationHandler):
    ''' Class for the TCP/IP based communication handler implementation. '''
    
    def __init__(self, host, port, handler, read_timeout=0.5, backlog=5):
        CommunicationHandler.__init__(self, host, port, handler)
        
        self.__enabled = True
        
        self.__timeout      = read_timeout
        self.__backlog      = backlog 
        self.__send_lock    = threading.RLock()
        self.__connections  = []
    
    def start(self):
        CommunicationHandler.start(self)
        self.__create_socket()
        self.__create_socket_acceptor().start()
        
    def stop(self):
        self.__enabled = False
        self.__server_socket.close()
        CommunicationHandler.stop(self)
        
    def __create_socket(self):
        ''' Creates, configures and binds the server socket. '''
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.__server_socket.settimeout( self.__timeout )
        self.__server_socket.bind( (self.host, self.port) )
        self.__server_socket.listen( self.__backlog )
        
        bound_port = self.__server_socket.getsockname()[1]
        
        print 'TCP socket bound on', str(self.host) + ':' + str(bound_port)
    
    def __listen(self):
        ''' Accepts client connections. '''
        while self.__enabled:
            try:
                (client_socket, client_address) = self.__server_socket.accept()
                print 'Socket accepted from', client_address
                
                client_socket.settimeout(self.__timeout)
                
                self.__create_receiver(client_socket, client_address).start()
            except socket.timeout:
                pass # ok, wait for connections until enabled
    
    def __create_socket_acceptor(self):
        ''' Creates a thread for the accept loop of the server socket. '''
        return threading.Thread(target=self.__listen, name='TCP|Listen')
    
    def __do_receive(self, sock, cli_address):
        ''' Waits incoming data on TCP socket and dispatches it. '''
        sender = SenderInfo(sock, cli_address)
        self.__connections.append(sender)
        
        while self.__enabled and sender.enabled:
            try:
                head   = sock.recv(1)
                if not head:
                    print 'TCP socket closed:', cli_address
                    break
                
                header = ord( head )
                
                length = sock.recv(2)
                if len(length) != 2:
                    print 'TCP socket closed:', cli_address
                    break
                    
                lhi, llo = ord(length[0]), ord(length[1])
                length = ( lhi << 8 ) | llo # lhi * 256 + llo
                
                data   = ''
                
                if self.__enabled and length > 0:                
                    data = sock.recv(length) # TODO: does this return 'length' bytes?
                    
                if self.__enabled:
                    self.handler(self, sender, header, data)
                    
            except socket.timeout:
                pass # no data received in timeout interval, but it is normal
            except Exception as ex:
                print 'Exception received on TCP receiver thread [', cli_address, ']:', ex
                traceback.print_exc()
        
        # main loop exited
        sock.close()
        
        self.__connections.remove(sender)
    
    def __create_receiver(self, socket, address):
        ''' Creates a thread to handle the client connection. '''
        return threading.Thread(target=self.__do_receive, name='TCP|Receiver|' + str(address), args=(socket, address))
    
    def send(self, header, data, sender):
        ''' Send a message to the given destination. '''
        
        self.__send_lock.acquire()
        try:
            if data is None:
                data = ''
                
            data = data.encode('ascii', 'ignore')
            length = len(data)
            
            lhi, llo = (length & 0xFF00) >> 8, length & 0x00FF
            
            message = [ chr(header), chr(lhi), chr(llo) ]
            if len(data) > 0:
                message.extend(data)
            
            sender.socket.sendall(''.join(message))
        finally:
            self.__send_lock.release()
            
    def broadcast(self, header, message):
        ''' Sends a message on all registered client connections. '''
        
        self.__send_lock.acquire()
        try:
            for target in self.__connections:
                self.send(header, message, target)
        finally:
            self.__send_lock.release()
            
    def authentication_succeeded(self, session_id, sender):
        ''' Sets the session identifier of a client connection. '''
        sender.session_id = session_id
    
    def authentication_failed(self, sender):
        ''' Closes the client connection which authentication failed. '''
        sender.enabled = False
        sender.socket.close()
    
    def is_valid_session(self, message, sender):
        return True # if the session is not valid than it was closed before
    