'''
Created on Dec 2, 2013

Helper module to parse system arguments.

@author: rycus
'''

import sys

class __ArgData(object):
    ''' Stub class to hold any data. '''
    pass

''' Is the process running in non-interactive mode? '''
server = False

''' Communication related parameters. '''
communication = __ArgData()
communication.modes = [ 'mcast' ]
communication.ports = [ None   ]
communication.hosts = [ None    ]

''' Parameters for entities. '''
entities = __ArgData()
entities.search_path = []

''' Parameters for images. '''
images = __ArgData()
images.search_path = []

''' Settings and parameters for localization. '''
localizations = __ArgData()
localizations.default = 'en'
localizations.search_path = []

def __initialize():
    ''' Parses the system arguments. '''
    
    for arg in sys.argv:
        if arg.lower() == '--server':
            server = True
        elif arg.lower().startswith('--entities='):
            entities.search_path = arg[len('--entities='):].split(';')
        elif arg.lower().startswith('--images='):
            images.search_path = arg[len('--images='):].split(';')
        elif arg.lower().startswith('--loc='):
            localizations.search_path = arg[len('--loc='):].split(';')
        elif arg.lower().startswith('--lang='):
            localizations.default = arg[len('--lang='):]
        elif arg.lower().startswith('--communication='):
            # --communication=mcast@host:port
            # --communication=bcast:port
            # --communication=udp:port
            # --communication=tcp:port
            
            del communication.modes[:]
            del communication.ports[:]
            del communication.hosts[:]
            
            comms = arg[len('--communication='):].split(';')
            for c in comms:
                if '@' in c:
                    if ':' in c:
                        mode, host_port = c.split('@')
                        host, port = host_port.split(':')
                    else:
                        mode, host = c.split('@')
                        port = None
                elif ':' in c:
                    mode, port = c.split(':')
                    host = None
                else:
                    mode, port, host = c, None, None
                    
                communication.modes.append(mode)
                communication.ports.append(port)
                communication.hosts.append(host)

__initialize()
