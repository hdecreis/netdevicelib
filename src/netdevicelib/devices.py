#!/usr/local/bin/python

# ========================================================================
#  Classes which define devices
#
#  Brian Landers <blanders@sapient.com>
#  07.07.2001
#
#  $Id: devices.py,v 1.6 2002/06/19 22:59:41 bluecoat93 Exp $
# ========================================================================

import string, sys

# We requre Python 2.0
pyversion = string.split( string.split( sys.version )[0], "." )

if map( int, pyversion ) < [2, 0, 0]:
    sys.stderr.write( "Sorry, this library requires at least Python 2.0\n" )
    sys.exit(1);

# ------------------------------------------------------------------------

# Module documentation strings
__version__ = '$Revision: 1.6 $'.split()[-2]

# ------------------------------------------------------------------------

class Device:
    def __init__( self ):
        """ Constructor """
        self._class             = "BASE CLASS"
        
        self._needsEnable       = 1
        self._needsWakeup       = 0
        self._commands          = { 'disablePaging' : '',
                                    'enablePaging'  : '',
                                    'getConfig'     : '',
                                    'enable'        : '',
                                    'disable'       : '' }

        self._prompts           = { 'login'           : '',
                                    'username'        : '',
                                    'password'        : '',
                                    'command'         : '',
                                    'enable'          : '',
                                    'enabledIndicator': ''}

        # These are the default commands and prompts
        self.setCommand('erase-config',        'write erase')
        self.setCommand('write erase',         'write erase')
        self.setCommand('save-config',         'write mem')
        self.setCommand('reload',              'reload' )
        self.setCommand('enable',              'enable' )
        self.setCommand('disable',             'disable' )
        self.setCommand('config',              'config term' )
        self.setCommand('end',                 'end' )
        self.setPrompt( 'login',               '[Ll]ogin[:\s]*$' )
        self.setPrompt( 'username',            '[Uu]sername[:\s]*$' )
        self.setPrompt( 'password',            '[Pp]assw(?:or)?d[:\s]*$' )
        self.setPrompt( 'command-config',      '[\w\.-]+(?:\((ca-trustpoint|config[\w.-]*)\)#)\s*$' )
        self.setPrompt( 'command-enabled',     '[\w().-]+(>\s?\(enabled\)|(?<!#)#)\s*$' )
        self.setPrompt( 'command-notenabled',  '[\w().-]+(?<!rommon )(?:\d+)?[\$>]\s*$' )
        self.setPrompt( 'command',             '[\w().-]+(?<!#)[\$#>]\s?(?:\(enable\))?\s*$' )
        self.setPrompt( 'enable',              '[Pp]assword[:\s]*$' )
        self.setPrompt( 'enabledIndicator',    '(#|\(enable\))\s*$' )
        self.setPrompt( 'configIndicator',     '\(config\)' )
        self.setPrompt( 'initialconfig',       'Would you like to enter the initial configuration dialog\? \[yes/no\]:\s*' )
        self.setPrompt( 'rommon',              'rommon\s*#?\d+\s*>\s*$' )
        self.setPrompt( 'confirm',             '\[(confirm|Y|N|yes/no)\]' )
        self.setPrompt( 'booting',             '##################|@@@@@@@@@@@@@@@@|POST: PortASIC' )

    def getPrompt( self, inKey=None ):
        """ Get the RE to match a given prompt on the device """
        assert inKey != None
        
        try:
            return self._prompts[inKey]
        except KeyError:
            return ''

    def setPrompt( self, inKey=None, inValue=None ):
        """ Set the RE to match a given prompt on the device """
        assert inKey   != None
        assert inValue != None

        self._prompts[inKey] = inValue

    def getCommand( self, inKey=None ):
        """ Get the command to perform a given function on the device """
        assert inKey != None
        
        try:
            return self._commands[inKey]
        except KeyError:
            return ''

    def setCommand( self, inKey=None, inValue=None ):
        """ Set the command to perform a given function on the device """
        assert inKey   != None
        assert inValue != None

        self._commands[inKey] = inValue

    def needsEnable( self ):
        return self._needsEnable
    
    def needsWakeup( self, val=None ):
        ret = self._needsWakeup
        if val != None:
            self._needsWakeup = val
        return ret

class NXOSDevice( Device ):
    def __init__( self ):
        """ Constructor"""
        Device.__init__( self )
        
        self._class       = "NXOS"
        self._needsEnable = 0
        
        self.setCommand( 'disablePaging', 'terminal length 0' )
        self.setCommand( 'enablePaging',  'terminal length 24' )
        self.setCommand( 'getConfig',     'show running-config' )
        self.setPrompt(  'rommon',        'switch\(boot\)(?:\(config\))?#\s*$' )

class IOSDevice( Device ):
    def __init__( self ):
        """ Constructor"""
        Device.__init__( self )
        
        self._class       = "IOS"
        self._needsEnable = 1
        
        self.setCommand( 'disablePaging', 'terminal length 0' )
        self.setCommand( 'enablePaging',  'terminal length 24' )
        self.setCommand( 'getConfig',     'show running-config' )
        self.setCommand( 'rommon-confreg-ignoreconf', 'confreg 0x2142' )
        self.setCommand( 'rommon-boot', 'reset' )
        self.setCommand( 'default-confreg', 'config-register 0x2102' )

class CatOSDevice( Device ):
    def __init__( self ):
        """ Constructor """
        Device.__init__( self )
        
        self._class       = "CatOS"
        self._needsEnable = 1
        
        self.setCommand( 'disablePaging', 'set length 0' )
        self.setCommand( 'enablePaging',  'set length 24' )
        self.setCommand( 'getConfig',     'write term' )
        
class PixDevice( Device ):
    def __init__( self ):
        """ Constructor """
        Device.__init__( self )
        
        self._class       = "Pix"
        self._needsEnable = 1
        
        self.setCommand( 'disablePaging', 'no pager' )
        self.setCommand( 'enablePaging',  'pager' )
        self.setCommand( 'getConfig',     'write term' )

class ASADevice( Device ):
    def __init__( self ):
        """ Constructor """
        Device.__init__( self )
        
        self._class       = "ASA"
        self._needsEnable = 1
        

        self.setCommand( 'rommon-confreg-ignoreconf', 'confreg 0x00000040' )
	self.setCommand( 'rommon-boot',     'boot')
        self.setCommand( 'default-confreg', 'config-register 0x00000001'  )
        self.setCommand( 'disablePaging',   "conf t\r\nno pager\r\nend"   )
        self.setCommand( 'enablePaging',    "conf t\r\npager 24\r\nend"   )
        self.setCommand( 'getConfig',       'write term'                  )

class BBDevice( Device ):
    def __init__(self):
        """ Constructeur """
        Device.__init__( self )

        self._class       = "BB"
        self._needsEnable = 0

        self.setCommand( 'getConfig',          '/S\r\n' )
        self.setCommand( 'newLine',            '\r'  )
        self.setPrompt( 'password',            '[Pp]assw(?:or)?d[:\s]*$' )
        self.setPrompt( 'command-answer',      'Press <ESC> to Exit ...\s*$' )
        self.setPrompt( 'command',             'RPM>\s*$' )
        self.setPrompt( 'command-enabled',     'RPM>\s*$' )

class DeviceFactory:
    def createDevice( self, inClass=None ):
        assert inClass != None

        if inClass == 'IOS':
            return IOSDevice()
        elif inClass == 'NXOS':
            return NXOSDevice()
        elif inClass == 'CatOS':
            return CatOSDevice()
        elif inClass == 'Pix':
            return PixDevice()
        elif inClass == 'ASA':
            return ASADevice()
        elif inClass == 'BB':
            return BBDevice()
        else:
            raise RuntimeError( "Class '" + inClass + "' not supported" )

# ------------------------------------------------------------------------

if __name__ == "__main__":
    foo = DeviceFactory().createDevice( "IOS" )
