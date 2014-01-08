#include <Enrf24.h>
#include <SPI.h>
#include <ihControl.h>

// ------------------------
// This is the POWER device 
// ------------------------

char desc[] = { 100 };

Enrf24 radio(PB_5, PB_0, PA_6);
IHControl control(&radio, "Pdemo", 5, desc, 1);

boolean btnPushed = false;
boolean state_on = false;

void setup() {
  char init_state[5];
  
  Serial.begin(9600);

  control.enable_debug();
  control.setup();
  
  control.debug_config();
  
  pinMode(PUSH1, INPUT_PULLUP);
  pinMode(BLUE_LED, OUTPUT);
  
  memset(init_state, 0, 5);
  control.send_state(init_state);
}

void set_state(boolean on) {
  char state[5];
  int level;
  
  level = on ? 0x80 : 0x00;  
  analogWrite(BLUE_LED, level);
  state_on = on;
  
  memset(state, 0, 5);
  state[0] = on ? 0x01 : 0x00;
  control.send_state(state);
}

void loop() {
  char inbuf[33];
  boolean btnState;
  char tmp[5];
  int cmd;
  
  control.check();

  if (control.read(inbuf)) {
    Serial.print("Received packet: ");
    Serial.println(inbuf);
    
    cmd = control.get_command_id(inbuf);
    if(cmd == 1) {
      set_state(true);
    } else if(cmd == 0) {
      set_state(false);
    }
  } 
  else 
  {
    btnState = digitalRead(PUSH1) == LOW;
    if (btnState != btnPushed) {
      if(!btnPushed && btnState) { // button is now pressed (HI->LO edge)
        set_state(!state_on);
      }
      
      btnPushed = btnState;
    }
  }
}

