'''
Created on Dec 2, 2013

A reference entity implementation for Power devices
that can be controlled via RF communication.

@author: rycus
'''

from entities import Entity, EntityType
from entities import STATE_UNKNOWN, STATE_OFF, STATE_ON
from entities import COMMAND_ON, COMMAND_OFF

class GenericPower(Entity):
    ''' This type of entites are able to report their states as logical
        on (0x01) or off (0x00) state, and accept commands to switch this state. '''
    
    def __init__(self, unique_id, entity_type=EntityType.find(100), name='Unnamed entity', state=STATE_UNKNOWN, state_value=None, last_checkin=0):
        Entity.__init__(self, unique_id, entity_type, name=name, state=state, state_value=state_value, last_checkin=last_checkin)

    def state_changed(self, state_message):
        Entity.state_changed(self, state_message)
        
        state = state_message[0]
        if state == 0x00:
            if 0 != self.state_value:
                self.set_state(STATE_OFF, 0)
                return True
        elif state == 0x01:
            if 1 != self.state_value:
                self.set_state(STATE_ON, 1)
                return True
        
        return False

    def control(self, controller, command, value=None):
        if command.id == COMMAND_ON.id:
            controller.send_message(self.unique_id, [ chr(0x00), chr(0x01) ])
            self.log_command('Turning the power on')
            return
        elif command.id == COMMAND_OFF.id:
            controller.send_message(self.unique_id, [ chr(0x00), chr(0x00) ])
            self.log_command('Turning the power off')
            return  
        
        Entity.control(self, command, value=value)
        
    def describe_state(self):
        return str(self.state)

# register type
EntityType.register(100, 'Power', GenericPower, [COMMAND_ON, COMMAND_OFF], '#99CC00', 'power.png')
