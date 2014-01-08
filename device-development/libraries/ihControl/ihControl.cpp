#include "ihControl.h"

// Fixed addresses for now
const uint8_t rxaddr[] = { 0x05, 0x05, 0x05, 0x05, 0x05 };
const uint8_t txaddr[] = { 0x12, 0x12, 0x12, 0x12, 0x12 };

char debug[255];

IHControl::IHControl(Enrf24* _radio, char* _serial_id, uint8_t _serial_id_len, char* _description, uint8_t _description_len) {
	radio 			= _radio;
	serial_id   	= _serial_id;
	serial_id_len 	= _serial_id_len;
	description 	= _description;
	description_len = _description_len;
	
	memset(last_state, 0, IHC_RF_DATA_LEN);
	reset();
}

void IHControl::reset() {
	address 			= 0xFF;
	check_cnt 			= 0;
	last_sent_msg_id 	= 0;
	description_sent 	= false;
}

boolean IHControl::is_ready() {
	return address != 0xFF; 
}

void IHControl::check() {
	if (!is_ready()) {
		if (check_cnt++ % 800000 == 0) {
			init();
		}
	} else if (!description_sent) {
		if (check_cnt++ % 200000 == 0) {
			describe();
		}
	} else {
		if (check_cnt++ % 4000000 == 0) {
			if (is_debug) {
				Serial.print("Sending last state: ");
				Serial.println(last_state);
			}
			
			send_state(last_state);
		}
	}
}

void IHControl::init() {
	int i;
	uint8_t m_id;
	
	m_id = ++last_sent_msg_id % 0x100;
	
	if (is_debug) {
		Serial.println("Sending INIT");
	}
			
	radio->write(0xFF);
	radio->write(m_id);
	radio->write(IHC_MSG_ASSIGN);
	radio->print(serial_id);
	for(i = serial_id_len; i < IHC_RF_PAYLOAD_LEN - 3; i++) {
		radio->write((uint8_t) 0x00);
	}
	radio->flush();
}

void IHControl::describe() {
	int i;
	uint8_t m_id;
	boolean ack = false;
	
	m_id = ++last_sent_msg_id % 0x100;
	
	if (is_debug) {
		Serial.println("Sending DESCRIBE");
	}
	
	radio->write(address);
	radio->write(m_id);
	radio->write(IHC_MSG_DESCRIBE);
	radio->print(description);
	for(i = description_len; i < IHC_RF_PAYLOAD_LEN - 3; i++) {
		radio->write((uint8_t) 0x00);
	}
	radio->flush();
	
	ack = wait_for_acknowledge();
	
	if (is_debug) {
		Serial.print("Sent DESCRIBE ");
		Serial.println(ack ? "(ACK)" : "(NON-ACK)");
	}
	
	if (ack) {
		description_sent = true;
		
		send_state(last_state);
	}
}

void IHControl::setup() {
	SPI.setModule(SSI0_BASE);
	SPI.setDataMode(SPI_MODE0);
	SPI.setBitOrder(1); // MSB-first
	
	radio->begin(IHC_RF_DATARATE, IHC_RF_CHANNEL);
	radio->autoAck(IHC_RF_AUTO_ACK);
	radio->setAutoAckParams(IHC_RF_RETR_CNT, IHC_RF_RETR_INTVAL);
	radio->setAddressLength(IHC_RF_ADDR_LEN);
	radio->setTXpower(IHC_RF_TX_POWER);
	radio->setSpeed(IHC_RF_DATARATE);
	radio->setPayloadSettings(false, IHC_RF_PAYLOAD_LEN);

	radio->setRXaddress((void*) rxaddr);
	radio->setTXaddress((void*) txaddr);
	
	radio->enableRX();
}

void IHControl::send_acknowledge(uint8_t msg_id) {
	int i;
	
    radio->write(address);
    radio->write(msg_id);
    radio->write(IHC_MSG_ACK);
    
    for(i = 3; i < IHC_RF_PAYLOAD_LEN; i++) {
      radio->write((uint8_t) 0x00);         
    }
    
    radio->flush();
    
    if (is_debug) {
    	Serial.println("Acknowledge sent");
    }
}

size_t IHControl::read(char* buffer) {
	size_t rd;
	uint8_t addr, m_id, flag;
	int i;
	boolean set_address;
	
	if (radio->available(true)) {
		rd = radio->read(buffer);
		if (rd) {
			addr = buffer[0];
			
			if (is_debug) {
				sprintf(debug, "Received (from %d): ", addr);
				Serial.print(debug);
				Serial.println(buffer);
			}
	
			m_id = buffer[1];
			flag = buffer[2];
			
			if (is_debug) {
				sprintf(debug, "MsgID(%d) Flags(%X) LastSent(%d): ", m_id, flag, last_sent_msg_id);
				Serial.print(debug);
				Serial.println(buffer);
			}
			
			if (flag & IHC_MSG_RESET == IHC_MSG_RESET) {
				if (is_debug) {
					Serial.println("Reset");
				}
				
				reset();
			} else if (flag & IHC_MSG_ASSIGN) {
				if (is_debug) {
					sprintf(debug, "Assignment (%s): ", buffer+3);
					Serial.print(debug);
					Serial.println(buffer);
				}
				
				set_address = true;
				for(i = 0; i < serial_id_len; i++) {
					if(serial_id[i] != buffer[i + 3]) {
						set_address = false;
						break;
					}
				}
				
				if(set_address) {
					address = addr;
					if (is_debug) {
						sprintf(debug, "Address set to %d", address);
						Serial.println(debug);
					}
					
					send_acknowledge(m_id);
				}
			} else if (address == addr) {
				if (flag & IHC_MSG_ACK) {
					if (is_debug) {
						sprintf(debug, "ACK MsgID: %d / %d", m_id, last_sent_msg_id);
						Serial.println(debug);
					}
					
					// Acknowledge received
					return 0;
				} else {
					send_acknowledge(m_id);
					
					for(i = 0; i < IHC_RF_PAYLOAD_LEN - 3; i++) {
						buffer[i] = buffer[i + 3];
					}
					buffer[IHC_RF_PAYLOAD_LEN - 3] = 0;
					return IHC_RF_PAYLOAD_LEN - 3;
				}
			}
		}
	}
	
	return 0;
}

void IHControl::send_state(char* message) {
	int i;
	uint8_t m_id;
	boolean ack = false;
	
	for (i = 0; i < IHC_RF_DATA_LEN; i++) {
		last_state[i] = message[i];
	}
	
	if (!is_ready()) return;
	
	m_id = ++last_sent_msg_id % 0x100;

	radio->write(address);
	radio->write(m_id);
	radio->write(IHC_MSG_STATE);

	for (i = 0; i < IHC_RF_PAYLOAD_LEN - 3; i++) {
		radio->write((uint8_t) message[i]);
	}

	radio->flush();
	
	ack = wait_for_acknowledge();
	
	if (is_debug) {
		Serial.print("Sent message ");
		Serial.print(ack ? "(ACK)" : "(NON-ACK)");
		Serial.print(": ");
		Serial.println(message);
	}
}

int IHControl::get_command_id(char* message) {
	return (message[0] << 8) + message[1];
}

boolean IHControl::wait_for_acknowledge() {
	char buffer[IHC_RF_PAYLOAD_LEN];
	uint8_t addr, m_id, flag;
	
	ack_cnt = 0;
	
	while(ack_cnt++ < 800000) {
		if (radio->available(true)) {
			while (radio->read(buffer)) {
				addr = buffer[0];
				
				if (is_debug) {
					sprintf(debug, "Received (from %d): ", addr);
					Serial.print(debug);
					Serial.println(buffer);
				}
		
				m_id = buffer[1];
				flag = buffer[2];
				
				if (is_debug) {
					sprintf(debug, "MsgID(%d) Flags(%X) LastSent(%d): ", m_id, flag, last_sent_msg_id);
					Serial.print(debug);
					Serial.println(buffer);
				}
				
				if (address == addr && flag & IHC_MSG_ACK) {
					if (m_id == last_sent_msg_id) {
						return true;
					}
				}
			}
		}
	}
	
	return false;
}

void IHControl::enable_debug() {
	is_debug = true;
}

void IHControl::debug_config() {
	radio->debugConfig(debug);
	Serial.println(debug);
}
