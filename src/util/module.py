'''
Created on Aug 8, 2013

This module defines the abstract base of all system modules.

@author: Viktor Adam
'''

class ModuleBase(object): # !COMMENT: ModuleBase.() in util.module
    '''
    Base class for modules.
    Modules have to extend this class and call one of these classmethods
    at the end of the module file:
        - <Module>.register(): instantiates the class <Module> with no arguments
        - <Module>.register(instance): registers the given module instance
    For example:
        from util.module import ModuleBase
        class ExampleModule(util.module.ModuleBase):
            pass
        ExampleModule.register()
    '''

    __registered_modules = []
    
    def initialize(self):
        ''' Initializes the module. '''
        print 'Initializing', self.__class__.__name__
    
    def configure(self, database):
        ''' Configures the module optionally using the given database instance. '''
        print 'Configuring', self.__class__.__name__
        
    def start(self):
        ''' Starts the module. '''
        print 'Starting', self.__class__.__name__
    
    def stop(self):
        ''' Stops the module. '''
        print 'Stopping', self.__class__.__name__
    
    @classmethod
    def register(clazz, instance=None):
        ''' Registers and instance of the module. '''
        
        if not instance:
            instance = clazz()
        
        if isinstance(instance, ModuleBase):
            if instance not in ModuleBase.__registered_modules:
                print 'Registering module:', clazz
                ModuleBase.__registered_modules.append(instance)
    
    @classmethod
    def registered_modules(clazz):
        ''' Returns the list of registered modules. '''
        return ModuleBase.__registered_modules
    
    @classmethod
    def instance(clazz):
        ''' Returns a registered module with the given class. '''
        for module in ModuleBase.__registered_modules:
            if isinstance(module, clazz):
                return module
