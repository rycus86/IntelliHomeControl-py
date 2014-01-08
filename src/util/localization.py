'''
Created on Dec 28, 2013

Helper module to localize the application.

@author: Viktor adam
'''

import os
import threading

from util import sysargs

class Localization(object):
    ''' Utility class to translate key-based strings from resource files. '''
    
    __all = { }
    __language = sysargs.localizations.default
    __local = threading.local()
    
    @classmethod
    def initialize(cls):
        ''' Loads resorces from key-value .res files. 
            The files name without the extension should be the language code. '''
        
        paths = ['res']
        paths.extend(sysargs.localizations.search_path)
        
        for p in paths:
            folder = Localization.__find_path(p)
            if folder:
                for lf in os.listdir(folder):
                    lang, ext = os.path.splitext(lf)  # @UnusedVariable
                    Localization.parse(lang, os.path.join(folder, lf))
    
    @classmethod
    def __find_path(cls, path):
        ''' Find a valid absolute path for the given folder. ''' 
        
        package_dir  = os.path.dirname(__file__)
        root_dir     = os.path.dirname(package_dir)
        if os.path.basename(root_dir) == 'src':
            root_dir = os.path.dirname(root_dir)
        fpath  = os.path.join(root_dir, path)
        if os.path.exists(fpath):
            return os.path.abspath(fpath)
    
    @classmethod
    def parse(cls, language, filepath):
        ''' Parse the resource file at "filepath" using
            the given language to strore the results. '''
        
        if language not in Localization.__all:
            Localization.__all[language] = { } 
        
        lfile = open(filepath, 'r')
        try:
            for line in lfile:
                if '=' not in line: continue
                key, value = line.split('=', 1)
                Localization.__all[language][key.strip().lower()] = value.strip()
        finally:
            lfile.close()
            
        print 'Parsed', language, 'localizations from', filepath
    
    @classmethod
    def set_current_language(cls, language):
        ''' Sets the thread-local language. '''
        
        Localization.__local.language = language
    
    @classmethod
    def localize(cls, key, language=__language):
        ''' Localizes the key using the given language. '''
        
        try:
            local = Localization.__local.language
            if local:
                language = local
        except:
            pass
        
        k = str(key).lower()
        if language in Localization.__all and k in Localization.__all[language]:
            return Localization.__all[language][k]
        else:
            return '\'' + key + '\''

Localization.initialize()
