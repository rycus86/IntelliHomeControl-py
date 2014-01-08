#ifndef __IHCONTROL_H__
#define __IHCONTROL_H__

#include <Enrf24.h>
#include <nRF24L01.h>
#include <string.h>
#include <SPI.h>
#include <Energia.h>

#define IHC_RF_DATARATE 	1000000
#define IHC_RF_CHANNEL 		40
#define IHC_RF_AUTO_ACK 	true
#define IHC_RF_RETR_CNT 	15
#define IHC_RF_RETR_INTVAL 	1000
#define IHC_RF_ADDR_LEN  	5
#define IHC_RF_TX_POWER 	0

// Header + MsgID + Flags + CMD[2] + Params[3]
// Header + MsgID + Flags + State[5]
#define IHC_RF_PAYLOAD_LEN 	8
#define IHC_RF_DATA_LEN 	(IHC_RF_PAYLOAD_LEN - 3)

#define IHC_MSG_STATE 		((uint8_t) 0x10)
#define IHC_MSG_COMMAND		((uint8_t) 0x20)
#define IHC_MSG_ASSIGN		((uint8_t) 0x40)
#define IHC_MSG_ACK 		((uint8_t) 0x80)
#define IHC_MSG_RESET 		((uint8_t) (IHC_MSG_ASSIGN | 0x01))
#define IHC_MSG_DESCRIBE	((uint8_t) (IHC_MSG_ASSIGN | 0x02))

class IHControl {
public:
	/** Constructor. */
	IHControl(Enrf24* radio, char* serial_id, uint8_t serial_id_len, char* description, uint8_t description_len);

	/** 
	 * Checks whether the device has to be
	 * 1) initialized, or
	 * 2) describer, or
	 * 3) its last state should be sent
	 */
	void check();

	/** Sets up the RF module. */
	void setup();
	/** Reads a message into the buffer. */
	size_t read(char* buffer);
	/** Sends a state message. */
	void send_state(char* message);

	/** Gets the command identifier from a message. */
	int get_command_id(char* message);

	/** Enables debugging. */
	void enable_debug();
	/** Prints the configuration of the RF module to the serial port. */
	void debug_config();

private:
	/** The RF handler object. */
	Enrf24* radio;
	/** The physical identifier of the device. */
	char* serial_id;
	/** The length of the physical identifier in bytes. */
	uint8_t serial_id_len;
	/** The description of the device. */
	char* description;
	/** The length of the description in bytes. */
	uint8_t description_len;
	/** The assigned logical address of the device. */
	uint8_t address;
	/** The identifier of the message last sent. */
	uint8_t last_sent_msg_id;
	/** Is debugging enabled? */
	boolean is_debug = false;
	/** Counter used in check() method. */
	int check_cnt;
	/** Counter used to wait for acknowledge responses. */
	int ack_cnt;
	/** Buffer storing the contents of the last message. */
	char last_state[IHC_RF_DATA_LEN];
	/** Is description successfully sent? */
	boolean description_sent;

	/** Send acknowledge to a message with the given identifier. */
	void send_acknowledge(uint8_t msg_id);
	/** Resets the assigned address and restarts communication. */
	void reset();
	/** Sends the INIT message. */
	void init();
	/** Sends the DESCRIBE message. */
	void describe();
	/** Returns true, if the device has an assigned address. */
	boolean is_ready();
	/** Waits for acknowledge and returns true if received it. */
	boolean wait_for_acknowledge();
};

#endif
