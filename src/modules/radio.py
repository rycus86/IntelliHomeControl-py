'''
Created on Jul 7, 2013

This module defines classes responsible for the RF communication
on the Raspberry Pi with the nRF24L01 RF transceiver family.

@author: Viktor Adam
'''

import RPi.GPIO as GPIO
import spidev
import time
import threading
from Queue import Queue

from util.module import ModuleBase

class SpiCommand(object):
    ''' Class enumeration SPI command identifiers '''

    ''' 1 to 5 bytes
        Read command and status registers. 
        5 bit LSB = 5 bit Register Map Address '''
    R_REGISTER = 0b00000000
     
    ''' 1 to 5 bytes
        Write command and status registers. 
        5 bit LSB = 5 bit Register Map Address
        Executable in power down or standby modes only. '''
    W_REGISTER = 0b00100000
     
    ''' 1 to 32 bytes
        Read RX-payload: 1 to 32 bytes.
        A read operation always starts at byte 0. 
        Payload is deleted from FIFO after it is read. 
        Used in RX mode. '''
    R_RX_PAYLOAD = 0b01100001
     
    ''' 1 to 32 bytes
        Write TX-payload: 1 to 32 bytes. 
        A write operation always starts at byte 0 used in TX payload. '''
    W_TX_PAYLOAD = 0b10100000
    
    ''' 0 bytes
        Flush TX FIFO, used in TX mode '''
    FLUSH_TX = 0b11100001 
    
    ''' 0 bytes 
        Flush RX FIFO, used in RX mode 
        Should not be executed during transmission of acknowledge, 
        that is, acknowledge package will not be completed. '''
    FLUSH_RX = 0b11100010
    
    ''' 0 bytes 
        Used for a PTX device
        Reuse last transmitted payload.
        TX payload reuse is active until W_TX_PAYLOAD or FLUSH TX is executed. TX
        payload reuse must not be activated or deactivated during package transmission. '''
    REUSE_TX_PL = 0b11100011
    
    ''' 1 byte
        Read RX payload width for the top R_RX_PAYLOAD in the RX FIFO.
        Note: Flush RX FIFO if the read value is larger than 32 bytes. '''
    R_RX_PL_WID = 0b01100000
    
    ''' 1 to 32 bytes
        PPP = 3 bit LSB
        Used in RX mode.
        Write Payload to be transmitted together with
        ACK packet on PIPE PPP. (PPP valid in the
        range from 000 to 101). Maximum three ACK
        packet payloads can be pending. Payloads with
        same PPP are handled using first in - first out
        principle. Write payload: 1 to 32 bytes. A write
        operation always starts at byte 0. '''
    W_ACK_PAYLOAD = 0b10101000
    
    ''' 1 to 32 bytes
        Used in TX mode. 
        Disables AUTOACK on this specific packet. '''
    W_TX_PAYLOAD_NOACK = 0b10110000 
    
    ''' 0 bytes
        No Operation. 
        Might be used to read the STATUS register '''
    NOP = 0b11111111 

class Register(object):
    ''' Class enumerating register addresses '''
    
    ''' Configuration register '''
    CONFIG      = 0x00
    EN_AA       = 0x01
    EN_RXADDR   = 0x02
    SETUP_AW    = 0x03
    SETUP_RETR  = 0x04
    RF_CH       = 0x05
    RF_SETUP    = 0x06
    STATUS      = 0x07
    OBSERVE_TX  = 0x08
    RPD         = 0x09
    RX_ADDR_P0  = 0x0A
    RX_ADDR_P1  = 0x0B
    RX_ADDR_P2  = 0x0C
    RX_ADDR_P3  = 0x0D
    RX_ADDR_P4  = 0x0E
    RX_ADDR_P5  = 0x0F
    TX_ADDR     = 0x10
    RX_PW_P0    = 0x11
    RX_PW_P1    = 0x12
    RX_PW_P2    = 0x13
    RX_PW_P3    = 0x14
    RX_PW_P4    = 0x15
    RX_PW_P5    = 0x16
    FIFO_STATUS = 0x17
    # ACK_PLD
    # TX_PLD
    # RX_PLD
    DYNDP       = 0x1C
    FEATURE     = 0x1D

class Bits(object):
    ''' Config bits '''
    Config_MASK_RX_DR   = 1 << 6
    Config_MASK_TX_DS   = 1 << 5
    Config_MASK_MAX_RT  = 1 << 4
    Config_EN_CRC       = 1 << 3
    Config_CRCO         = 1 << 2
    Config_PWR_UP       = 1 << 1
    Config_PRIM_RX      = 1 << 0
    ''' Address width '''
    Setup_AW_3_bytes    = 0b01
    Setup_AW_4_bytes    = 0b10
    Setup_AW_5_bytes    = 0b11
    ''' Automatic transmission '''
    Setup_Retr_ARD_250us  = 0x0 << 4 # Automatic retransmission delay
    Setup_Retr_ARD_500us  = 0x1 << 4
    Setup_Retr_ARD_750us  = 0x2 << 4
    Setup_Retr_ARD_1000us = 0x3 << 4
    Setup_Retr_ARD_1250us = 0x4 << 4
    Setup_Retr_ARD_1500us = 0x5 << 4
    Setup_Retr_ARD_1750us = 0x6 << 4
    Setup_Retr_ARD_2000us = 0x7 << 4
    Setup_Retr_ARD_2250us = 0x8 << 4
    Setup_Retr_ARD_2500us = 0x9 << 4
    Setup_Retr_ARD_2750us = 0xA << 4
    Setup_Retr_ARD_3000us = 0xB << 4
    Setup_Retr_ARD_3250us = 0xC << 4
    Setup_Retr_ARD_3500us = 0xD << 4
    Setup_Retr_ARD_3750us = 0xE << 4
    Setup_Retr_ARD_4000us = 0xF << 4
    Setup_Retr_ARC_Disabled  = 0x0; # Automatic retransmission count
    Setup_Retr_ARC_Upto_1RT  = 0x1;
    Setup_Retr_ARC_Upto_2RT  = 0x2;
    Setup_Retr_ARC_Upto_3RT  = 0x3;
    Setup_Retr_ARC_Upto_4RT  = 0x4;
    Setup_Retr_ARC_Upto_5RT  = 0x5;
    Setup_Retr_ARC_Upto_6RT  = 0x6;
    Setup_Retr_ARC_Upto_7RT  = 0x7;
    Setup_Retr_ARC_Upto_8RT  = 0x8;
    Setup_Retr_ARC_Upto_9RT  = 0x9;
    Setup_Retr_ARC_Upto_10RT = 0xA;
    Setup_Retr_ARC_Upto_11RT = 0xB;
    Setup_Retr_ARC_Upto_12RT = 0xC;
    Setup_Retr_ARC_Upto_13RT = 0xD;
    Setup_Retr_ARC_Upto_14RT = 0xE;
    Setup_Retr_ARC_Upto_15RT = 0xF;
    ''' RF Setup '''
    RF_Cont_Wave  = 1 << 7
    # RF_PLL_Lock = 1 << 4 # Only used in test
    RF_DR_1Mbps   = 0b000 << 3
    RF_DR_2Mbps   = 0b001 << 3
    RF_DR_250kbps = 0b100 << 3
    RF_PWR_18dBm  = 0b00  << 1
    RF_PWR_12dBm  = 0b01  << 1
    RF_PWR_6dBm   = 0b10  << 1
    RF_PWR_0dBm   = 0b11  << 1
    ''' Status '''
    Stat_RX_DR          = 1 << 6
    Stat_TX_DS          = 1 << 5
    Stat_MAX_RT         = 1 << 4
    Stat_RX_FIFO_Empty  = 0b111 << 1
    Stat_TX_Full        = 1 << 0
    ''' FIFO Status '''
    FifoStat_TX_REUSE   = 1 << 6
    FifoStat_TX_FULL    = 1 << 5
    FifoStat_TX_EMPTY   = 1 << 4
    FifoStat_RX_FULL    = 1 << 1
    FifoStat_RX_EMPTY   = 1 << 0

class NRF24L01P(object):
    ''' Class to manage the nRF24L01/nRF24L01+ transceiver. '''
    
    MSG_STATE    = 0x10
    MSG_COMMAND  = 0x20
    MSG_ASSIGN   = 0x40
    MSG_ACK      = 0x80
    MSG_RESET    = MSG_ASSIGN | 0x01
    MSG_DESCRIBE = MSG_ASSIGN | 0x02

    def __init__(self, addr_rx=None, addr_tx=None, input_pin=11, output_pin=12, payload_length=8, address_length=5, channel=40, debug=False):
        ''' Constructor '''
        self.__spi        = spidev.SpiDev(0, 0)
        self.__input_pin  = input_pin
        self.__output_pin = output_pin
        self.__addr_rx    = addr_rx if addr_rx else [0x12] * address_length
        self.__addr_tx    = addr_tx if addr_tx else [0x05] * address_length
        self.__pl_len     = payload_length
        self.__channel    = channel
        
        self.__vconfig = Bits.Config_MASK_MAX_RT | Bits.Config_EN_CRC | Bits.Config_CRCO
        
        # queue for messages to send
        self.__send_queue         = Queue()
        
        # message id generation related variables
        self.__next_message_id    = 0
        self.__message_id_lock    = threading.Lock()
        
        # list of registered message receivers
        self.__message_receivers  = []
        
        # device registration and address assignment related variables
        self.__rf_addresses       = dict()
        self.__addr_assign_lock   = threading.Lock()
        
        self.__enabled            = False
        self.__debug              = debug
        
        self.__init_gpio()
        self.__init_radio()
    
    def __init_gpio(self):
        ''' Initializes the GPIOs of the Raspberry Pi. '''
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.__output_pin, GPIO.OUT)
        GPIO.setup(self.__input_pin, GPIO.IN)
        GPIO.add_event_detect(self.__input_pin, GPIO.FALLING)
    
    def __init_radio(self):
        ''' Initializes the registers of the transceiver. '''
        
        # Setup Auto-acknowledge
        self.__write_command([SpiCommand.W_REGISTER | Register.EN_AA, 
                           0x01]) # auto-ack on P0
        
        # Setup Automatic retransmission
        self.__write_command([SpiCommand.W_REGISTER | Register.SETUP_RETR, 
                           Bits.Setup_Retr_ARD_1000us | Bits.Setup_Retr_ARC_Upto_15RT])
        # Setup RX address
        self.__write_command([SpiCommand.W_REGISTER | Register.EN_RXADDR, 
                           0x01]) # enable P0
        # Setup Address width
        self.__write_command([SpiCommand.W_REGISTER | Register.SETUP_AW, 
                           Bits.Setup_AW_5_bytes])
        # Setup RF Channel
        self.__write_command([SpiCommand.W_REGISTER | Register.RF_CH, 
                           self.__channel]) # Channel #40
        # Setup Data speed and power
        self.__write_command([SpiCommand.W_REGISTER | Register.RF_SETUP, 
                           Bits.RF_DR_1Mbps | Bits.RF_PWR_0dBm])
        # Setup Payload size
        self.__write_command([SpiCommand.W_REGISTER | Register.RX_PW_P0, 
                           self.__pl_len])
        
        # Setup Receive address
        cmd = [SpiCommand.W_REGISTER | Register.RX_ADDR_P0]
        cmd.extend(self.__addr_rx)
        self.__write_command(cmd) # Address: 0x0505050505
        # Setup Transmit address
        cmd = [SpiCommand.W_REGISTER | Register.TX_ADDR]
        cmd.extend(self.__addr_tx)
        self.__write_command(cmd) # Address: 0x1212121212
        # Setup Configuration register
        self.__write_command([SpiCommand.W_REGISTER | Register.CONFIG, 
                           self.__vconfig]) # MASK_MAX_RT, enable 2 bytes CRC, PWR_UP, PRX
    
    def __write_command(self, cmd):
        ''' Writes the command on the SPI bus. '''
        self.__spi.writebytes(cmd)
    
    def __read_register_value(self, address, length):
        ''' Reads the contents of a register on the given address. '''
        cmd = [SpiCommand.R_REGISTER | address]
        cmd.extend([SpiCommand.NOP for x in xrange(length)])  # @UnusedVariable
        return self.__spi.xfer(cmd)[1:] # cut leading status byte
    
    def __read_8bit_register_value(self, address):
        ''' Reads the contents of an 8 bit length register value. '''
        response = self.__read_register_value(address, 1)
        return response[0]
    
    def __read_status(self):
        ''' Reads the content of the status register. '''
        status = self.__spi.readbytes(1)
        return status[0]
    
    def __read_payload(self):
        ''' Reads the payload of a received message. '''
        cmd = [SpiCommand.R_RX_PAYLOAD]
        for x in xrange(self.__pl_len):  # @UnusedVariable
            cmd.append(SpiCommand.NOP)
        response = self.__spi.xfer(cmd)
        return response[1:] # cut leading status byte

    def __configure_for_idle(self):
        ''' Configures the transceiver to be idle. '''
        conf = Bits.Config_MASK_MAX_RT | Bits.Config_EN_CRC | Bits.Config_CRCO | Bits.Config_PRIM_RX
        # Setup Configuration register
        self.__write_command([SpiCommand.W_REGISTER | Register.CONFIG, conf])

    def __configure_for_reading(self):
        ''' Configures the transceiver to read packets. '''
        conf = Bits.Config_MASK_MAX_RT | Bits.Config_EN_CRC | Bits.Config_CRCO | \
                Bits.Config_PWR_UP | Bits.Config_PRIM_RX
        # Setup Configuration register
        self.__write_command([SpiCommand.W_REGISTER | Register.CONFIG, conf])
        
    def __configure_for_sending(self):
        ''' Configures the transceiver to send packets. '''
        conf = Bits.Config_MASK_MAX_RT | Bits.Config_EN_CRC | Bits.Config_CRCO | Bits.Config_PWR_UP
        # Setup Configuration register
        self.__write_command([SpiCommand.W_REGISTER | Register.CONFIG, conf])
    
    def __read_message(self, timeout=0):
        ''' Tries to read a message. '''
        self.__configure_for_reading()
        tm_start = time.time()
        
        while True:
            try:
                stat = self.__read_status()
                if stat & Bits.Stat_RX_FIFO_Empty != Bits.Stat_RX_FIFO_Empty:
                    fifoStatus = self.__read_8bit_register_value(Register.FIFO_STATUS)
                    if fifoStatus & Bits.FifoStat_RX_FULL > 0:
                        if self.__debug: 
                            print 'RX FIFO was full!'
                    
                    return self.__read_payload()
                else:
                    self.__reset_status()
                    
                    GPIO.output(self.__output_pin, GPIO.HIGH)
                    
                    # time.sleep(0.1)
                    max_wait = 5 if timeout <= 0 else (time.time()-tm_start) / 0.001
                    while max_wait > 0 and not GPIO.event_detected(self.__input_pin):
                        max_wait -= 1
                        time.sleep(0.001)
                    
                    GPIO.output(self.__output_pin, GPIO.LOW)
                # time.sleep(0.5)
                # TODO a sleep interval should be shorter than the max transmission interval (with retries)
            finally:
                if timeout > 0:
                    tm = time.time()
                    if tm - tm_start >= timeout:
                        break
    
    def __send_message(self, message):
        ''' Tries to send a message. '''
        self.__configure_for_sending()
        self.__reset_status()
        
        cmd = [SpiCommand.W_REGISTER | Register.RX_ADDR_P0]
        cmd.extend(self.__addr_tx)
        self.__write_command(cmd)
        
        cmd = [SpiCommand.W_TX_PAYLOAD]
        cmd.extend(message)
        self.__spi.writebytes(cmd) 
        
        GPIO.output(self.__output_pin, GPIO.HIGH)
        time.sleep(0.001) # do not stay in CE high for more than 4 ms
        GPIO.output(self.__output_pin, GPIO.LOW)
        
        ack_received = False
        it = 0
        max_wait = 10
        while max_wait > 0:
            if GPIO.event_detected(self.__input_pin):
                ack_received = True
                break
            it += 1 
            max_wait -= 1
            time.sleep(0.001)
        if self.__debug: 
            print 'TX waited', it, 'iterations for GPIO event'
        
        if not ack_received:
            status = self.__read_status()
            if self.__debug: 
                print 'TX non-ack status:', hex(status)
            if status & Bits.Stat_TX_DS == Bits.Stat_TX_DS:
                ack_received = True
        else:
            status = self.__read_status()
            if status & Bits.Stat_TX_DS != Bits.Stat_TX_DS:
                if self.__debug: 
                    print 'TX ack status:', hex(status)
            
        self.__reset_status()
        
        cmd = [SpiCommand.W_REGISTER | Register.RX_ADDR_P0]
        cmd.extend(self.__addr_rx)
        self.__write_command(cmd)
        
        return ack_received
    
    def __flush_rx(self):
        ''' Clears the contents of the receive buffer. '''
        self.__spi.writebytes([SpiCommand.FLUSH_RX])
    
    def __flush_tx(self):
        ''' Clears the contents of the transmit buffer. '''
        self.__spi.writebytes([SpiCommand.FLUSH_TX])
    
    def __reset_status(self):
        ''' Resets the status register of the transceiver. '''
        cmd = [SpiCommand.W_REGISTER | Register.STATUS, 
               Bits.Stat_RX_DR | Bits.Stat_TX_DS | Bits.Stat_MAX_RT] # Clear status register
        self.__write_command(cmd)
    
    def __generate_next_message_id(self):
        ''' Generates an identifier for the next message to send. '''
        with self.__message_id_lock:
            self.__next_message_id += 1
            if self.__next_message_id >= 0xFF:
                self.__next_message_id = 1
            msgid = self.__next_message_id
            return msgid
    
    def __send_with_acknowledge(self, address, message, flags=MSG_COMMAND):
        ''' Sends a message and wait for its (software) acknowledge. '''
        msg_sent     = False
        ack_received = False
        retries      = 3
        
        msgid = self.__generate_next_message_id()
        decorated_message = [ address, msgid, flags ]
        decorated_message.extend([ ord(b) for b in message ])
        while len(decorated_message) < self.__pl_len:
            decorated_message.append(0x00)
        
        while retries > 0 and (not msg_sent or not ack_received):
            retries = retries - 1
            
            for x in xrange(3):  # @UnusedVariable
                if self.__send_message(decorated_message):
                    if self.__debug:
                        print 'Sent message:', decorated_message
                    msg_sent = True
                    break
                else:
                    if self.__debug:
                        print 'Failed to send message', decorated_message
            
            if msg_sent:
                
                response = self.__read_message(0.3)
                if self.__debug:
                    print 'ACK.Response:', response
                if response:
                    if response[0] == address and response[1] == msgid and response[2] == NRF24L01P.MSG_ACK:
                        ack_received = True
                        if self.__debug:
                            print 'Acknowledge received for:', decorated_message
                    else:
                        if self.__debug:
                            print 'Bad response for ACK'
                else:
                    if self.__debug:
                        print 'No ACK response'
                
            else:
                if self.__debug:
                    print 'Failed to send message, status:', hex(self.__read_status())
                
        self.__flush_tx()
        
        return ack_received
    
    def __send_acknowledge(self, address, message_id):
        ''' Sends acknowledge to an incoming message with the given parameters. '''
        msg = [address, message_id, NRF24L01P.MSG_ACK]
        msg.extend([0x00] * (self.__pl_len - 3))
        if self.__debug: 
            print 'Sending acknowledge:', msg
        self.__send_message(msg)
        
    def __send_reset(self):
        ''' Sends a reset message to all RF devices. '''
        message_id = self.__generate_next_message_id()
        msg = [0xFF, message_id, NRF24L01P.MSG_RESET]
        msg.extend([0x00] * (self.__pl_len - 3))
        if self.__debug: 
            print 'Sending reset:', msg
        self.__send_message(msg) 
    
    def __dispatch_received_message(self, address, flags, data):
        ''' Handle and dispatch an incoming message. ''' 
        
        if address == 0xFF and flags & NRF24L01P.MSG_ASSIGN:
            ''' Device registration, first step. '''
            
            addr = -1
            sn = ''.join( [chr(d) if d > 0 else '' for d in data] )
                
            self.__addr_assign_lock.acquire()
            try:
                if sn in self.__rf_addresses:
                    addr = self.__rf_addresses[sn]
                else:
                    current_addresses = self.__rf_addresses.values()
                    for a in xrange(1, 255):
                        if a not in current_addresses:
                            addr = a
                            break
                        
            finally:
                self.__addr_assign_lock.release()
                
            if addr > 0:
                # if self.__debug: 
                print 'Registering', sn, 'with address:', addr
                self.__rf_addresses[sn] = addr
                self.__send_with_acknowledge(addr, sn, NRF24L01P.MSG_ASSIGN)
            else:
                # if self.__debug: 
                print 'Can not register', sn
        elif flags & NRF24L01P.MSG_DESCRIBE:
            ''' Device registration, seconds step. '''
            
            unique_id = None
            for addr in self.__rf_addresses:
                if self.__rf_addresses[addr] == address:
                    unique_id = addr
                    break
            
            if unique_id:
                for receiver in self.__message_receivers:
                    receiver.describe(address, unique_id, data)
        else:
            ''' Every other incoming message. '''
            unique_id = None
            for addr in self.__rf_addresses:
                if self.__rf_addresses[addr] == address:
                    unique_id = addr
                    break
            
            if unique_id:
                for receiver in self.__message_receivers:
                    receiver.receive(address, unique_id, flags, data)
    
    def __enqueue_message(self, address, message):
        ''' Enqueues a message which will be sent to the target. '''
        msg = [m for m in message]
        msg.extend([ chr(0x00) ] * (self.__pl_len - len(message) - 3))
        self.__send_queue.put( (address, msg) )
    
    def __main_loop(self):
        ''' The synchronous executor of the RF handler. '''
        
        # reset RF devices to initialize them again
        self.__send_reset()
        
        while self.__enabled:
            target = None
            msg    = None
            
            # if there is an incoming message, handle it
            incoming = self.__read_message(0.3)
            if incoming:
                address, msgid, flags, data = incoming[0], incoming[1], incoming[2], incoming[3:]
                if self.__debug: 
                    print 'DBG|Message from', address, '#' + str(msgid), 'Flags:', hex(flags), ':', data
                if 0 < address < 0xFF:
                    self.__send_acknowledge(address, msgid)
                self.__dispatch_received_message(address, flags, data)
                continue
            else:
                pass # Nothing received
                
            # if no message was received check for outgoing messages
            try:
                target, msg = self.__send_queue.get(False)
            except:
                pass
            
            # if there is one, send it
            if target and msg:
                if self.__send_with_acknowledge(target, msg):
                    if self.__debug: 
                        print 'Message successfully sent'
                else:
                    if self.__debug: 
                        print 'Message was not sent'
        
    def debugSingleRegister(self, name, address, length):
        ''' Prints the contents of a single register. '''
        response = self.__read_register_value(address, length)
        
        if len(name) < 15:
            name += '.' * (15 - len(name))
        name += ':'
        
        print name, response, '| HEX:', [hex(x) for x in response]
    
    def debugRegisters(self):
        ''' Prints the contents of the tranceiver's registers. '''
        
        self.debugSingleRegister('STATUS',      Register.STATUS,        1)
        self.debugSingleRegister('EN_AA',       Register.EN_AA,         1)
        self.debugSingleRegister('EN_RXADDR',   Register.EN_RXADDR,     1)
        self.debugSingleRegister('SETUP_AW',    Register.SETUP_AW,      1)
        self.debugSingleRegister('SETUP_RETR',  Register.SETUP_RETR,    1)
        self.debugSingleRegister('RF_CH',       Register.RF_CH,         1)
        self.debugSingleRegister('RF_SETUP',    Register.RF_SETUP,      1)
        self.debugSingleRegister('RX_ADDR_P0',  Register.RX_ADDR_P0,    5)
        self.debugSingleRegister('TX_ADDR',     Register.TX_ADDR,       5)
        self.debugSingleRegister('RX_PW_P0',    Register.RX_PW_P0,      1)
        self.debugSingleRegister('CONFIG',      Register.CONFIG,        1)
        self.debugSingleRegister('FIFO_STATUS', Register.FIFO_STATUS, 1)
        self.debugSingleRegister('DYNDP',       Register.DYNDP, 1)
        self.debugSingleRegister('FEATURE',     Register.FEATURE, 1)
        
    def start(self):
        ''' Starts the RF handler's execution. '''
        self.__enabled = True
        threading.Thread(None, self.__main_loop, 'RF|Handler', (), None, None).start()
    
    def stop(self):
        ''' Requests stopping of the handlers execution. '''
        self.__enabled = False
        
    def cleanup(self):
        ''' Turns off the tranceiver and cleans up GPIO related resources. '''
        try:
            self.__write_command([SpiCommand.W_REGISTER | Register.CONFIG, 0x00])
        finally:
            GPIO.cleanup()
        
    def send_message(self, target, message):
        ''' Initiates sending a message to the given target. '''
        if target in self.__rf_addresses:
            self.__enqueue_message(self.__rf_addresses[target], message)
        else:
            # if self.__debug: 
            print 'There is no known address for', target
    
    def register_message_receiver(self, receiver):
        ''' Registers a message receiver instance. '''
        self.__message_receivers.append(receiver)
        
    def unregister_message_receiver(self, receiver):
        ''' Unregisters a message receiver instance. '''
        self.__message_receivers.remove(receiver)

class DeviceHandler(object):
    ''' Base class for RF device handlers. '''
    
    def __init__(self):
        self.__rf = None
        
    def set_radio_handler(self, radio):
        ''' Sets the RF manager instance. '''
        self.__rf = radio
    
    def describe(self, address, unique_id, data):
        ''' Handles device registration. '''
        pass    
    
    def receive(self, address, unique_id, flags, data):
        ''' Handles state message from a device. '''
        pass
        
    def send(self, unique_id, message):
        ''' Sends a message to a device. '''
        self.__rf.send_message(unique_id, message)

class RFModule(ModuleBase):
    ''' System module implementation to define functions
        for RF communication management. ''' 
    
    def initialize(self):
        ModuleBase.initialize(self)
        self.__rf = NRF24L01P(payload_length=8, debug=False)
        self.__handlers = []
        
    def configure(self, database):
        ModuleBase.configure(self, database)
        self.__rf.register_message_receiver(self)
        
    def start(self):
        ModuleBase.start(self)
        self.__rf.start()
        
    def stop(self):
        try:
            self.__rf.stop()
            ModuleBase.stop(self)
        finally:
            self.__rf.cleanup()
    
    def register_device_handler(self, handler):
        ''' Registers a device handler instance. '''
        self.__handlers.append(handler)
        handler.set_radio_handler(self.__rf)
        
    def unregister_device_handler(self, handler):
        ''' Unregisters a device handler instance. '''
        self.__handlers.remove(handler)
    
    def describe(self, address, unique_id, data):
        ''' Dispatches device registrations. '''
        for handler in self.__handlers:
            handler.describe(address, unique_id, data)    
    
    def receive(self, address, unique_id, flags, data):
        ''' Dispatches state messages from devices. '''
        for handler in self.__handlers:
            handler.receive(address, unique_id, flags, data)

RFModule.register()
