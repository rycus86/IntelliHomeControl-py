#include <Enrf24.h>
#include <nRF24L01.h>
#include <string.h>
#include <SPI.h>
#include <Energia.h>
#include <ihControl.h>

// ------------------------
// This is the LIGHT device
// ------------------------

char desc[] = { 101 };

Enrf24 radio(PB_5, PB_0, PA_6);
IHControl control(&radio, "Ldemo", 5, desc, 1);

boolean btnPushed = false;

int l_level = 0;
int l_target = 0;
int dim_cnt = 0;

void setup() {
  char init_state[5];
  
  Serial.begin(9600);

  control.enable_debug();
  control.setup();
  
  control.debug_config();
  
  pinMode(PUSH1, INPUT_PULLUP);
  pinMode(RED_LED, OUTPUT);
  
  memset(init_state, 0, 5);
  control.send_state(init_state);
}

void set_level(int level) {
  char state[5];
  
  analogWrite(RED_LED, level);
  l_level = level;
  l_target = level;
  
  memset(state, 0, 5);
  state[0] = level;
  control.send_state(state);
}

void loop() {
  char inbuf[33];
  boolean btnState;
  int level;
  char tmp[5];
  int cmd;
  
  if(l_target != l_level) {
    if(dim_cnt++ % 1000 == 0) {
      level = l_level + (l_target < l_level ? -1 : 1);
      if (level == l_target) {
        set_level(level);
      } else {
        analogWrite(RED_LED, level);
        l_level = level;
      }
    }
  }
  
  control.check();

  if (control.read(inbuf)) {
    Serial.print("Received packet: ");
    Serial.println(inbuf);

    cmd = control.get_command_id(inbuf);    
    if(cmd == 2) {
      l_target = inbuf[2];
    } else if(cmd == 1) {
      set_level(255);
    } else if(cmd == 0) {
      set_level(0);
    }
  } 
  else 
  {
    btnState = digitalRead(PUSH1) == LOW;
    if (btnState != btnPushed) {
      if(!btnPushed && btnState) { // button is now pressed (HI->LO edge)
        if(l_level == 0) {
          set_level(255);
        } else {
          set_level(0);
        }
      }
      
      btnPushed = btnState;
    }
  }
}

