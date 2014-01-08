'''
Created on Aug 8, 2013

This module handles system modules by 
loading, configuring, starting and stopping them.

@author: Viktor Adam
'''

import pkgutil
import signal

from util.module import ModuleBase
from util.database import Database
from util import sysargs

def import_modules(paths, prefix):
    ''' Import all modules from paths with the given prefix. '''
    
    if len(prefix) == 0 or prefix[-1] != '.':
        prefix = prefix + '.'
    
    modules = pkgutil.iter_modules(path=paths, prefix=prefix)
    for loader, modname, ispkg in modules: 
        __import__(modname, globals(), locals(), [], -1)

class ModuleLoader(object):
    ''' Helper class to load, configure, start and stop system modules. '''
    
    @classmethod
    def load_and_configure_modules(cls, db):
        import_modules(['modules'], 'modules')

        for mod in ModuleBase.registered_modules():
            if isinstance(mod, ModuleBase):
                mod.initialize()
                mod.configure(db) 
    
    @classmethod
    def start_modules(cls):
        for mod in ModuleBase.registered_modules():
            if isinstance(mod, ModuleBase):
                mod.start()
                
    @classmethod
    def stop_modules(cls):
        for mod in reversed( ModuleBase.registered_modules() ):
            if isinstance(mod, ModuleBase):
                mod.stop()

def __wait_for_exit_signal():
    ''' Waits for a Unix USR1 signal. '''
    
    def handle_usr1(num, frame):
        pass
    
    signal.signal(signal.SIGUSR1, handle_usr1)
    signal.pause()

def main_entry():
    ''' Loads, configures and start system modules,
        then waits for the exit condition, finally
        it stop all started system modules '''
    
    database = Database.instance()
    ModuleLoader.load_and_configure_modules( database )
    ModuleLoader.start_modules()
    
    if sysargs.server:
        __wait_for_exit_signal()
    else:
        raw_input('Press ENTER to finish')
    
    ModuleLoader.stop_modules()

if __name__ == '__main__':
    main_entry()
