'''
Created on Dec 4, 2013

UDP based communication handler implementation.

@author: Viktor Adam
'''

import socket
import threading
import traceback

from modules.comm import CommunicationHandler, Header

class Flags(object):
    ''' Helper class defining message flags. '''
     
    MORE_FOLLOWS = 0x01 << 0

class UDPHandler(CommunicationHandler):
    ''' Class for the UDP based communication handler implementation. '''
    
    def __init__(self, host, port, handler=None, \
                 multicast=False, broadcast=False, \
                 ttl=8, loopback=False, reuse_address=True, \
                 read_timeout=0.5, buffer_size=1500):
        
        CommunicationHandler.__init__(self, host, port, handler)
        
        self.__enabled = True
        
        self.__ttl           = ttl
        self.__loopback      = 1 if loopback      else 0
        self.__reuse_address = 1 if reuse_address else 0
        self.__timeout       = read_timeout
        self.__buffer_size   = buffer_size
        self.__send_lock     = threading.RLock()
        
        self.__is_multicast  = multicast
        self.__is_broadcast  = broadcast
        
        self.__sessions      = { }
        
        self.__incomplete_messages  = { }
        
    def start(self):
        CommunicationHandler.start(self)
        self.__create_socket()
        self.__receiver = self.__create_receiver()
        self.__receiver.start()
    
    def stop(self):
        self.__enabled = False
        self.__udp_socket.close()
        CommunicationHandler.stop(self)
     
    def __create_socket(self):
        ''' Creates, configures and binds the UDP socket. '''
        
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        
        self.__udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, self.__reuse_address)
        if self.__is_broadcast:
            self.__udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.__udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,  self.__ttl)
        self.__udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, self.__loopback)
        self.__udp_socket.settimeout(self.__timeout)
        self.__udp_socket.bind(('0.0.0.0', self.port))
        
        if self.__is_multicast:
            import struct
            mreq = struct.pack("4sl", socket.inet_aton(self.host), socket.INADDR_ANY)
            self.__udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        bound_port = self.__udp_socket.getsockname()[1]
        
        print 'UDP socket bound on', str(self.host) + ':' + str(bound_port)
    
    def __merge_incomplete(self, header, data, sender, finish):
        ''' Merges incomplete incoming messages. '''
        
        if sender not in self.__incomplete_messages:
            self.__incomplete_messages[sender] = { }
            
        by_header = self.__incomplete_messages[sender]
        
        if header in by_header:
            merged = by_header[header] + data
            if finish:
                del by_header[header]
            else:
                by_header[header] = merged
            return merged
        else:
            if not finish:
                by_header[header] = data
            return data
    
    def __do_receive(self):
        ''' Waits data on UDP socket and dispatches it. '''
        while self.__enabled:
            try:
                data, sender = self.__udp_socket.recvfrom(self.__buffer_size)
                if self.__enabled and len(data) >= 2:
                    header, flags, message = ord(data[0]), ord(data[1]), data[2:]
                    finish = (flags & Flags.MORE_FOLLOWS) != Flags.MORE_FOLLOWS
                    merged = self.__merge_incomplete(header, message, sender, finish)
                    
                    if finish:
                        if header == Header.MSG_A_EXIT:
                            del self.__sessions[sender]
                        else:
                            self.handler(self, sender, header, merged)
            except socket.timeout:
                pass # no data received in timeout interval, but it is normal
            except Exception as ex:
                print 'Exception received on UDP receiver thread:', ex
                traceback.print_exc()
    
    def __create_receiver(self):
        ''' Creates a thread to handle incoming messages. '''
        return threading.Thread(target=self.__do_receive, name='UDP|Receiver')
    
    def send(self, header, data, destination):
        ''' Sends a message to the given destination 
            breaking it into several parts if needed. '''
        
        self.__send_lock.acquire()
        try:
            flags    = 0
            buf_size = self.__buffer_size
            max_size = buf_size - 2 # BufferSize - (HeaderLength + FlagsLength)
            
            # if isinstance(header, (int, long)):
            header = chr(header)
            
            if data is None:
                data = ''
                
            data = data.encode('ascii', 'ignore')
            data_len = len(data)
            
            while len(data) > max_size: # send the splitted parts first
                flags |= Flags.MORE_FOLLOWS
                part = header + chr(flags) + data[0:max_size]
                self.__udp_socket.sendto(part, destination)
                data = data[max_size:]
            
            flags &= ~ Flags.MORE_FOLLOWS
            
            if data or data_len == 0: # send the rest of the message
                part = header + chr(flags) + data
                self.__udp_socket.sendto(part, destination)
        finally:
            self.__send_lock.release()
            
    def broadcast(self, header, message):
        ''' Sends a message to all known client addresses. '''
        
        self.__send_lock.acquire()
        try:
            for target in self.__sessions:
                self.send(header, message, target)
        finally:
            self.__send_lock.release()
    
    def authentication_succeeded(self, session_id, sender):
        ''' Sets the session identifier for the sender. '''
        self.__sessions[sender] = session_id
    
    def authentication_failed(self, sender):
        ''' Sends invalid session response to the sender. '''
        self.send(Header.MSG_A_ERROR_INVALID_SESSION, None, sender)
    
    def is_valid_session(self, message, sender):
        ''' Returns True, if the sender is known and 
            the message prefix equals the related session identifier. '''
        return sender in self.__sessions and self.__sessions[sender] == message[0:32]
    
    def strip_session_prefix(self, message):
        ''' Returns the received string message from its 32th position. '''
        return message[32:]
    