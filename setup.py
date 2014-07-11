#!/usr/bin/env python

import string, sys
from distutils.core import setup

myVersion = "$Revision: 1.1 $";

# We requre Python 2.0
pyversion = string.split( string.split( sys.version )[0], "." )

if map( int, pyversion ) < [2, 0, 0]:
    sys.stderr.write( "Sorry, this library requires at least Python 2.0\n" )
    sys.exit(1);

# Call the distutils setup function to install ourselves
setup ( name         = "netdevicelib",
        version      = myVersion.split()[-2],
        description  = "Python Networking Device library",
        author       = "Brian Landers",
        author_email = "brian@packetslave.com",
        url          = "http://netdevicelib.sourceforge.net",

        package_dir  = { '': 'src' },
        packages     = [ 'netdevicelib' ]
      )
