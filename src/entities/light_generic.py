'''
Created on Dec 2, 2013

A reference entity implementation for Light devices
that can be controlled via RF communication.

@author: rycus
'''

from entities import Entity, EntityType, EntityCommand
from entities import STATE_UNKNOWN, STATE_ON, STATE_OFF
from entities import COMMAND_ON, COMMAND_OFF

# register non-default command
COMMAND_LIGHT_LEVEL = EntityCommand(100, 'Set level', EntityCommand.RANGE_0_TO_100)

class GenericLight(Entity):
    ''' This type of entites are able to report their states as brightness level 
        between 0x00 and 0xFF, and accept commands to control this level or to
        turn the device fully off or on. '''
    
    def __init__(self, unique_id, entity_type=EntityType.find(101), name='Unnamed entity', state=STATE_UNKNOWN, state_value=None, last_checkin=0):
        Entity.__init__(self, unique_id, entity_type, name=name, state=state, state_value=state_value, last_checkin=last_checkin)
    
    def state_changed(self, state_message):
        Entity.state_changed(self, state_message)
        
        state = state_message[0]
        if 0x00 < state < 0xFF:
            state = int(round((state * 100.0) / 255.0))
            if self.state_value != state:
                self.set_state(STATE_ON, state)
                return True
        elif state == 0x00 and 0 != self.state_value:
            self.set_state(STATE_OFF, 0)
            return True
        elif state == 0xFF and 100 != self.state_value:
            self.set_state(STATE_ON, 100)
            return True
        
        return False
    
    def control(self, controller, command, value=None):
        if command.id == COMMAND_LIGHT_LEVEL.id:
            if value is not None:
                msg = [ chr(0x00), chr(0x02), chr(int(round((int(value) * 255) / 100))) ]
                controller.send_message(self.unique_id, msg)
                
                self.log_command('Setting light level to ' + str(value))
                return
        elif command.id == COMMAND_ON.id:
            controller.send_message(self.unique_id, [ chr(0x00), chr(0x01) ])
            self.log_command('Turning the light on')
            return
        elif command.id == COMMAND_OFF.id:
            controller.send_message(self.unique_id, [ chr(0x00), chr(0x00) ])
            self.log_command('Turning the light off')
            return  
        
        Entity.control(self, command, value=value)
    
    def describe_state(self):
        if 0 < self.state_value < 100:
            return str(self.state) + ' (' + str(self.state_value) + '%)'
        else:
            return str(self.state)

# register type
EntityType.register(101, 'Light', GenericLight, [COMMAND_ON, COMMAND_OFF, COMMAND_LIGHT_LEVEL], '#CCCC00', 'light.png')
