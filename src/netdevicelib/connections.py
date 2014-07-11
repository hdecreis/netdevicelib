#!/usr/local/bin/python

# ========================================================================
#  Classes which define connections to devices
#
#  Brian Landers <blanders@sapient.com>
#  07.07.2001
#
#  $Id: connections.py,v 1.11 2002/06/19 22:59:40 bluecoat93 Exp $
# ========================================================================

import getopt, re, string, sys, telnetlib, types, time
from sshlib.ssh import Ssh

# We requre Python 2.0
pyversion = string.split( string.split( sys.version )[0], "." )

if map( int, pyversion ) < [2, 0, 0]:
    sys.stderr.write( "Sorry, this library requires at least Python 2.0\n" )
    sys.exit(1);
    
from netdevicelib.devices import DeviceFactory

# ------------------------------------------------------------------------

# Module documentation strings
__version__ = '$Revision: 1.11 $'.split()[-2]

# Exceptions
LoginFailedException   = "Login failed. Bad username or password"
EnableFailedException  = "Enable failed. Access denied"
DisableFailedException = "Disable command failed."

# ------------------------------------------------------------------------
class Connection:
    """ Base class for all connections """
    
    def __init__( self, inDevice=None, inTimeout=10 ):
        """ Constructor """
        assert inDevice != None

        self._device      = inDevice
        self._timeout     = inTimeout
        self._isDebugging = 0
        self._isOpen      = 0
        self._lastPrompt  = ''

    # Virtual methods -- must be overridden
    def open( self, inHost=None, inPort=23 ):
        """ Open the connection to the device """
        raise RuntimeError, "Unimplemented base class method called"

    def close( self ):
        """ Close the connection to the device """
        raise RuntimeError, "Unimplemented base class method called"

    def login( self, inUser=None, inPass=None ):
        """ Login to the device using a username and password """
        raise RuntimeError, "Unimplemented base class method called"

    def cmd( self, inCmd=None, inPrompt=None ):
        """ Run a command on the device and return the output """
        raise RuntimeError, "Unimplemented base class method called"

    # Base class methods -- may be overridden
    def _debuglog( self, inMessage="No Message" ):
        """ Write a debug message to STDERR if debugging is enabled """
        
        if self.debug():
            sys.stderr.write( "DEBUG: %s\n" % inMessage )

    def debug( self, inLevel=None ):
        """ Accessor method for the debugging flag """

        if inLevel != None:
            self._isDebugging = inLevel

        return self._isDebugging
    
    def isEnabled( self ):
        """ Returns true if the connection is in 'superuser' mode """
        pass
    
    def isLoggedIn( self ):
        """ Returns true if the connection is already logged in """
        pass

    def enable( self, inPass=None ):
        """ Put the connection in 'superuser' mode """
        pass

    def disable( self ):
        """ Take the connection out of 'superuser' mode """
        pass

    def getLastPrompt( self ):
        """ Accessor method to get the last prompt we saw """
        return self._lastPrompt

    def disablePaging( self ):
        """ Helper function to disable screen paging for a connection """
        self.cmd( self._device.getCommand('disablePaging') )

    def enablePaging( self ):
        """ Helper function to enable screen paging for a connection """
        self.cmd( self._device.getCommand('enablePaging') )

    def wakeup( self ):
        """ Helper function to send CRLF's to the device in order to wake it up """
        pass
  
    def getConfig( self ):
        """ Helper function to get the current config from a connection """
        if self._device._needsEnable and not self.isEnabled() and self._type != 'ssh':
            raise RuntimeError( "You must be enabled first" )
        
        return self.cmd( self._device.getCommand('getConfig') )

# ------------------------------------------------------------------------

class SshConnection( Connection ):
    """ Encapsulates an Ssh Connection to a device """
    
    def __init__( self, inDevice=None ):
        """ Constructor """
        assert inDevice != None
        
        Connection.__init__( self, inDevice )
        self._conn = Ssh()

    def open( self, inHost=None, inPort=22 ):
        """ Open the connection to the device """
        assert inHost != None
        
        self._conn.open( inHost, inPort )
        self._isOpen = 1
        self._debuglog( "Connection open" )
        if self._device.needsWakeup():
            self.wakeup()

    def wakeup( self ):
        """ Helper function to send CRLF's to the device in order to wake it up """
        self._debuglog( "Trying to wakeup the device with CRLF (twice)" )
        self._conn.write("\r\n")
        self._conn.write("\015\012")

    def close( self ):
        """ Close the connection to the device """
        
        if self._isOpen:
            self.enablePaging()
            if self._device.getCommand('logout'):
                self._conn.cmd(self._device.getCommand('logout'))
            self._conn.close()
        self._isOpen = 0

#	def whereami( self ):
#		matches = [
#			self._device.getPrompt('rommon'),
#            self._device.getPrompt('username'),
#            self._device.getPrompt('login'),
#            self._device.getPrompt('password'),
#            self._device.getPrompt('command-enabled') ]
#            self._device.getPrompt('command-notenabled') ]
#		]
#
    def login( self, inUser=None, inPass=None ):
        """ Login to the device using a username and password """

        # Whooooo's on the other end ? a little state machine is more suited to the task:
        # one's never know what state is the device in anyway

        self._conn.login(inUser,inPass)

        matches = [ self._device.getPrompt('rommon'),
                    self._device.getPrompt('username'),
                    self._device.getPrompt('login'),
                    self._device.getPrompt('password'),
                    self._device.getPrompt('command'),
                    self._device.getPrompt('initialconfig') ]
        
        self._debuglog( "Looking for a prompt. Any kind of prompt" )

        sentWakeup, sentUser, sentPass, loggedIn, result = 0,0,0,0,None

        while loggedIn != 1:
            self._debuglog( "Trying to match:\n\t" + "\n\t".join(matches) \
                + " in: " + self._lastPrompt )

            result = self._conn.expect( matches, self._timeout )
            
            if result[0] == 0:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found a rommon prompt: not logged-in, but we can stop trying." )
                loggedIn  = 1

            elif result[0] in [1,2]:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                if sentUser:
                    self._debuglog( "Still facing a login/username prompt. Login Failed" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found login/username prompt. Sending User" )
                assert inUser != None
                self._conn.write( inUser + "\n" )
                sentUser = 1
                
            elif result[0] == 3:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                if sentPass:
                    self._debuglog( "Still facing a password prompt. Login Failed" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found password prompt. Sending Pass" )
                assert inPass != None
                self._conn.write( inPass + "\n" )
                sentPass = 1
            
            elif result[0] == 4:
                self._debuglog( "Matched: [" + str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found a cmd prompt: We are logged in" )
                loggedIn = 1

            elif result[0] == 5:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found an initial config prompt: Successfully ignored config" )
                self._conn.write( "no" )
                self.crlf()
                time.sleep(3)
                self.crlf()
                self.wakeup()
                loggedIn = 1
 
            elif result[0] == -1:
                self._debuglog( "Matched: [" +  str(result[0]) + "].")
                if sentWakeup:
                    self._debuglog( "Still no prompt. Quitting" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found no prompt. Trying to wakeup the device with CRLF." )
                self.wakeup()
                sentWakeup = 1
           
        if(self._device._class == 'ASA'):
            self._debuglog( "Warning: disablePaging at logon time is disabled for ASA: run disablePaging() once in enabled mode." )
        else:
            self.disablePaging()
    
    def cmd( self, inCmd=None, inPrompt=None, inConfirm=False ):
        """ Run a command on the device and return the output """
        assert inCmd != None

        # Handle blank commands (i.e. unimplemented in the Device subclass)
        if inCmd == "":
            return ""
        
        self._debuglog( "running command (" + inCmd + ")" )
        self._conn.write( inCmd + "\n" )
    
        if inConfirm:
            self._conn.write( "y\n" )

        if inPrompt != None:
            if type( inPrompt ) == types.ListType:
                prompts = inPrompt
            else:
                prompts = [ inPrompt ]
        else:
            prompts = [ self._device.getPrompt('command') ]

        self._debuglog("Looking for cmd prompt:")
        self._debuglog( "Trying to match:\n\t" + "\n\t".join(prompts) \
                       + "\n             in: " + self._lastPrompt )

        result = self._conn.expect( prompts, self._timeout )

        # Store the last prompt we saw
        if result[1] != None:
            self._lastPrompt = result[1].group()

        # Remove the command itself from the output
        exp = re.compile( '^%s\s*$\n' % re.escape(inCmd), re.MULTILINE )
        output = exp.sub( '', result[2], 1 )
        
        # Remove the prompt from the output and return the results
        exp = re.compile( self._device.getPrompt('command') )
        return exp.sub( '', output )

    #def cmd( self, inCmd=None, inPrompt=None, inConfirm=False ):
    #    """ Run a command on the device and return the output """
    #    assert inCmd != None
    #
    #    # Handle blank commands (i.e. unimplemented in the Device subclass)
    #    if inCmd == "":
    #        return ""
    #    
    #    self._debuglog( "running command (" + inCmd + ")" )
    #    self._conn.write( inCmd + "\n" )
    #
    #    if inConfirm:
    #        self._conn.write( "y\n" )
    #
    #    if inPrompt != None:
    #        if type( inPrompt ) == types.ListType:
    #            prompts = inPrompt
    #        else:
    #            prompts = [ inPrompt ]
    #    else:
    #        prompts = [ self._device.getPrompt('command'),self._device.getPrompt('confirm') ]
    #
    #    self._debuglog("Looking for cmd/confirm prompt:")
    #    self._debuglog( "Trying to match:\n\t" + "\n\t".join(prompts) \
    #                   + "\n             in: " + self._lastPrompt )
    #
    #    confirmed = 0
    #    result = self._conn.expect( prompts, self._timeout )
    #
    #    # If expect returned a confirmation prompt, answer yes and expect again
    #    if result[0] == 1:
    #      if confirmed == 0:
    #          self._conn.write( "y" )
    #      else:
    #          self._conn.write( "yes" )
    #          self.crlf()
    #      result = self._conn.expect( prompts, self._timeout )
    #
    #    if result[0] == 1:
    #      if confirmed == 0:
    #          self._conn.write( "y" )
    #      else:
    #          self._conn.write( "yes" )
    #          self.crlf()
    #      result = self._conn.expect( prompts, self._timeout )
    #
    #    # Store the last prompt we saw
    #    if result[1] != None:
    #        self._lastPrompt = result[1].group()
    # 
    #    # Remove the command itself from the output
    #    exp = re.compile( '^%s\s*$\n' % re.escape(inCmd), re.MULTILINE )
    #    output = exp.sub( '', result[2], 1 )
    #    
    #    # Remove the prompt from the output and return the results
    #    exp = re.compile( self._device.getPrompt('command') )
    #    return exp.sub( '', output )

    def enable( self, inPass=None ):
        """ Put the connection in 'superuser' mode """

        if inPass == None:
            inPass = ''
 
        matches = [ self._device.getPrompt('rommon'),
                    self._device.getPrompt('password'),
                    self._device.getPrompt('command-enabled'),
                    self._device.getPrompt('command-notenabled'),
                ]
        
        self._debuglog( "Looking for enable ?" )

        result = None
        sentEnable, enabled, sentEnablePass, sentWakeup, sentExtraNewline = 0,0,0,0,0
        self._conn.write( self._device.getCommand('enable') + "\n" )
        
        while enabled != 1:
            self._debuglog( "Trying to match:\n\t" + "\n\t".join(matches) )
            result = self._conn.expect( matches, self._timeout )
            
            if result[0] == 0:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found a rommon prompt: not enabled, but we can stop trying." )
                enabled  = 1
            
            elif result[0] == 1:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )

                if sentEnablePass:
                    if sentExtraNewline:
                        self._debuglog( "Still facing a password prompt. Enable Failed" )
                        self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                        raise RuntimeError, LoginFailedException
                    else:
                        self._debuglog( "Still facing a password prompt. Extra Newline ?" )
                        self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                        self._conn.write("\n")
                        sentExtraNewline = 1
                self._debuglog( "Found password prompt. Sending Enable Pass" )
                self._conn.write( inPass + "\n" )
                sentEnablePass = 1
            
            elif result[0] == 3:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                if sentEnablePass:
                    self._debuglog( "Still facing a not-enabled prompt. Enable Failed" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found a not-enabled prompt. Sending Enable" )
                self._conn.write( self._device.getCommand('enable') + "\n" )
                sentEnable = 1
            
            elif result[0] == 2:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found an enabled cmd prompt: We are enabled" )
                enabled  = 1
           
            elif result[0] == -1:
                self._debuglog( "Matched: [" +  str(result[0]) + "].")
                if sentWakeup:
                    self._debuglog( "Still no command or password prompt. Quitting" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found no command or password prompt. Trying to wakeup the device with CRLF." )
                self.wakeup()
                sentWakeup = 1
            
    def disable( self ):
        """ Take the connection out of 'superuser' mode """
        
        self.cmd( self._device.getCommand('disable') )

        # Make sure we disabled
        if self.isEnabled():
            raise DisableFailedException

    def isEnabled( self ):
        """ Returns true if the connection is in 'superuser' mode """
        
        self._debuglog( "Trying to match " + self._device.getPrompt( 'enabledIndicator' ) \
            + " in " + self._lastPrompt )
        exp = re.compile( self._device.getPrompt( 'enabledIndicator' ) )
        if exp.search( self._lastPrompt ) == None:
            return 0
        else:
            return 1

    def isLoggedIn( self ):
        """ Returns true if the connection is already logged in """
    
        exp = re.compile( self._device.getPrompt( 'command' ) )
        if exp.search( self._lastPrompt ) == None:
            return 0
        else:
            return 1


class TelnetConnection( Connection ):
    """ Encapsulates a telnet connection to a device """
    
    def __init__( self, inDevice=None ):
        """ Constructor """
        assert inDevice != None
        
        Connection.__init__( self, inDevice )
        self._conn = telnetlib.Telnet()

    def open( self, inHost=None, inPort=23 ):
        """ Open the connection to the device """
        assert inHost != None
        
        self._conn.open( inHost, inPort )
        self._isOpen = 1
        self._debuglog( "Connection open" )
        if self._device.needsWakeup():
            self.wakeup()

    def crlf( self ):
        self._conn.write("\r\n")

    def wakeup( self ):
        """ Helper function to send CRLF's to the device in order to wake it up """
        self._debuglog( "Trying to wakeup the device with CRLF (twice)" )
        self.crlf()
        self.crlf()
        #self._conn.write("\015\012")

    def close( self ):
        """ Close the connection to the device """
        
        if self._isOpen:
            self.enablePaging()
            if self._device.getCommand('logout'):
                self._conn.cmd(self._device.getCommand('logout'))
            self._conn.close()
        self._isOpen = 0

    def login( self, inUser=None, inPass=None ):
        """ Login to the device using a username and password """

        # Whooooo's on the other end ? a little state machine is more suited to the task:
        # one's never know what state is the device in anyway

        inUser=inUser or ''
        inPass=inPass or ''

        matches = [ self._device.getPrompt('rommon'),
                    self._device.getPrompt('username'),
                    self._device.getPrompt('login'),
                    self._device.getPrompt('password'),
                    self._device.getPrompt('command') ,
                    self._device.getPrompt('initialconfig') ]
        
        self._debuglog( "Looking for a prompt. Any kind of prompt" )

        sentWakeup, sentUser, sentPass, loggedIn, result = 0,0,0,0,None

        while loggedIn != 1:
            self._debuglog( "Trying to match:\n\t" + "\n\t".join(matches) )
            result = self._conn.expect( matches, self._timeout )

            if result[0] == 0:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found a rommon prompt: not logged-in, but we can stop trying." )
                loggedIn  = 1
            
            if result[0] in [1,2]:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                if sentUser:
                    self._debuglog( "Still facing a login/username prompt. Login Failed" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found login/username prompt. Sending User" )
                assert inUser != None
                self._conn.write( inUser )
                self.crlf()
                sentUser = 1
                
            elif result[0] == 3:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                if sentPass:
                    self._debuglog( "Still facing a password prompt. Login Failed" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found password prompt. Sending Pass" )
                assert inPass != None
                self._conn.write( inPass )
                self.crlf()
                sentPass = 1
            
            elif result[0] == 4:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found a cmd prompt: We are logged in" )
                loggedIn = 1

            elif result[0] == 5:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found an initial config prompt: Successfully ignored config" )
                self._conn.write( "no" )
                self.crlf()
                time.sleep(3)
                self.crlf()
                self.wakeup()
            
            elif result[0] == -1:
                self._debuglog( "Matched: [" +  str(result[0]) + "].")
                if sentWakeup:
                    self._debuglog( "Still no prompt. Quitting" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found no prompt. Trying to wakeup the device with CRLF." )
                self.wakeup()
                sentWakeup = 1
            
        if(self._device._class == 'ASA'):
            self._debuglog( "Warning: disablePaging at logon time is disabled for ASA: run disablePaging() once in enabled mode." )
        else:
            self.disablePaging()
    
    def cmd( self, inCmd=None, inPrompt=None, inConfirm=False ):
        """ Run a command on the device and return the output """
        assert inCmd != None

        # Handle blank commands (i.e. unimplemented in the Device subclass)
        if inCmd == "":
            return ""
        
        self._debuglog( "running command (" + inCmd + ")" )
        self._conn.write( inCmd + "\n" )

        if inConfirm:
            self._conn.write( "y\n" )

        if inPrompt != None:
            if type( inPrompt ) == types.ListType:
                prompts = inPrompt
            else:
                prompts = [ inPrompt ]
        else:
            prompts = [ self._device.getPrompt('command') ]

        self._debuglog( "Looking for cmd prompt + (" + str(prompts) + ")" )

        result = self._conn.expect( prompts, self._timeout )

        # Store the last prompt we saw
        if result[1] != None:
            self._lastPrompt = result[1].group()

        # Remove the command itself from the output
        exp = re.compile( '^%s\s*$\n' % re.escape(inCmd), re.MULTILINE )
        output = exp.sub( '', result[2], 1 )
        
        # Remove the prompt from the output and return the results
        exp = re.compile( self._device.getPrompt('command') )
        return exp.sub( '', output )

    #def cmd( self, inCmd=None, inPrompt=None, inConfirm=False ):
    #        """ Run a command on the device and return the output """
    #        assert inCmd != None
    #
    #    # Handle blank commands (i.e. unimplemented in the Device subclass)
    #        if inCmd == "":
    #            return ""
    #        
    #        self._debuglog( "running command (" + inCmd + ")" )
    #        self._conn.write( inCmd )
    #        self.crlf()
    #
    #        if inConfirm:
    #            self._conn.write( "y" )
    #            self.crlf()
    #
    #        if inPrompt != None:
    #            if type( inPrompt ) == types.ListType:
    #                prompts = inPrompt
    #            else:
    #                prompts = [ inPrompt ]
    #        else:
    #            prompts = [ self._device.getPrompt('command'), self._device.getPrompt('confirm') ]
    #
    #        self._debuglog( "Looking for cmd prompt + (" + str(prompts) + ")" )
    #
    #        result = self._conn.expect( prompts, self._timeout )
    #
    #        self._debuglog("Looking for cmd/confirm prompt:")
    #        self._debuglog( "Trying to match:\n\t" + "\n\t".join(prompts) \
    #                       + "\n             in: " + self._lastPrompt )
    #
    #        confirmed = 0
    #        result = self._conn.expect( prompts, self._timeout )
    #
    #    # If expect returned a confirmation prompt, answer yes and expect again
    #        if result[0] == 1:
    #          if confirmed == 0:
    #              self._conn.write( "y" )
    #              confirmed = 1
    #          else:
    #              self._conn.write( "yes" )
    #              self.crlf()
    #          result = self._conn.expect( prompts, self._timeout )
    #
    #    # If expect returned a confirmation prompt, answer yes and expect again
    #        if result[0] == 1:
    #          if confirmed == 0:
    #              self._conn.write( "y" )
    #              confirmed = 1
    #          else:
    #              self._conn.write( "yes" )
    #              self.crlf()
    #          result = self._conn.expect( prompts, self._timeout )
    #
    #    # Store the last prompt we saw
    #        if result[1] != None:
    #          self._lastPrompt = result[1].group()
    #
    #    # Remove the command itself from the output
    #        exp = re.compile( '^%s\s*$\n' % re.escape(inCmd), re.MULTILINE )
    #        output = exp.sub( '', result[2], 1 )
    #        
    #    # Remove the prompt from the output and return the results
    #        exp = re.compile( self._device.getPrompt('command') )
    #        return exp.sub( '', output )
    #
    def enable( self, inPass=None ):
        """ Put the connection in 'superuser' mode """

        if self._device._needsEnable == 0:
            return True

        if inPass == None:
            inPass = ''
 
        matches = [ self._device.getPrompt('rommon'),
                    self._device.getPrompt('password'),
                    self._device.getPrompt('command-notenabled'),
                    self._device.getPrompt('command-enabled'),
                ]
        
        self._debuglog( "Looking for enable ?" )

        result = None
        sentEnable, enabled, sentEnablePass, sentWakeup, sentExtraNewline = 0,0,0,0,0
        self._conn.write( self._device.getCommand('enable') + "\n" )
        
        while enabled != 1:
            self._debuglog( "Trying to match:\n\t" + "\n\t".join(matches) )
            result = self._conn.expect( matches, self._timeout )
            
            if result[0] == 0:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found a rommon prompt: not enabled, but we can stop trying." )
                enabled  = 1

            elif result[0] == 1:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )

                if sentEnablePass:
                    if sentExtraNewline:
                        self._debuglog( "Still facing a password prompt. Enable Failed" )
                        self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                        raise RuntimeError, LoginFailedException
                    else:
                        self._debuglog( "Still facing a password prompt. Extra Newline ?" )
                        self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                        self._conn.write("\n")
                        sentExtraNewline = 1
                self._debuglog( "Found password prompt. Sending Enable Pass" )
                self._conn.write( inPass + "\n" )
                sentEnablePass = 1
            
            elif result[0] == 2:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                if sentEnablePass:
                    self._debuglog( "Still facing a not-enabled prompt. Enable Failed" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found a not-enabled prompt. Sending Enable" )
                self._conn.write( self._device.getCommand('enable') + "\n" )
                sentEnable = 1
            
            elif result[0] == 3:
                self._debuglog( "Matched: [" +  str(result[0]) + "]: " + matches[result[0]] )
                self._debuglog( "Found an enabled cmd prompt: We are enabled" )
                enabled  = 1
           
            elif result[0] == -1:
                self._debuglog( "Matched: [" +  str(result[0]) + "].")
                if sentWakeup:
                    self._debuglog( "Still no command or password prompt. Quitting" )
                    self._debuglog( "matched [" + str(result[0]) + "]:" + result[2] )
                    raise RuntimeError, LoginFailedException
                self._debuglog( "Found no command or password prompt. Trying to wakeup the device with CRLF." )
                self.wakeup()
                sentWakeup = 1
            
    def disable( self ):
        """ Take the connection out of 'superuser' mode """

        if self._device._needsEnable == 0:
            return True
        
        self.cmd( self._device.getCommand('disable') )

        # Make sure we disabled
        if self.isEnabled():
            raise DisableFailedException

    def isEnabled( self ):
        """ Returns true if the connection is in 'superuser' mode """

        if self._device._needsEnable == 0:
            return True
        
        self._debuglog( "Trying to match " + self._device.getPrompt( 'enabledIndicator' ) \
            + " in " + self._lastPrompt )
        exp = re.compile( self._device.getPrompt( 'enabledIndicator' ) )
        if exp.search( self._lastPrompt ) == None:
            return 0
        else:
            return 1

    def isLoggedIn( self ):
        """ Returns true if the connection is already logged in """
    
        exp = re.compile( self._device.getPrompt( 'command' ) )
        if exp.search( self._lastPrompt ) == None:
            return 0
        else:
            return 1

# ------------------------------------------------------------------------


    
class ConnectionFactory:
    """ Factory class for creating Connecton sub-class objects """
    
    def createConnection( self, inType=None, inClass=None ):
        """ Factory method to create Connection sub-class objects """
        assert inType  != None
        assert inClass != None

        # Create the device object
        device = DeviceFactory().createDevice( inClass )
        
        if inType == 'telnet':
            return TelnetConnection( device )
        elif inType == 'ssh':
            return SshConnection( device )
        else:
            raise RuntimeError( "Type '" + inType + "' not supported" )

# ========================================================================
#  Test driver
# ========================================================================

if __name__ == "__main__":

    # Parse our command-line arguments
    debugging = 0
    try:
        opts, args = getopt.getopt( sys.argv[1:], "d", ["debug"] )
    except getopt.GetoptError:
        print "Use -d or --debug for debugging"
        sys.exit(1)
    for o,a in opts:
        if o in ( '-d', '--debug' ):
            debugging = 1

    # Make sure they entered all the parameters we need
    if len( args ) < 5:
        print "usage: connections.py " + \
              "hostname type username password [enable] command"
        sys.exit(1)

    # Create the connection object
    conn = ConnectionFactory().createConnection( "telnet", args[1] )

    # Set the debugging flag if the user indicated debugging
    if debugging:
        conn.debug(1)

    # Open the connection and login
    conn.open( args[0] )
    conn.login( args[2], args[3] )

    # If the user provided an enable password, go into enable mode
    if len( args ) == 6:
        conn.enable( args[4] )
        cmd = args[5]
    else:
        cmd = args[4]

    # Run the command and print the output
    lines = conn.cmd( cmd )
    print lines

    # Finally, close the connection
    conn.close()
