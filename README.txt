netdevicelib 0.1
Brian Landers <brian@packetslave.com>
06/15/2002

netdevicelib is a Python package providing an API for access to
network devices such as Cisco routers and switches. It allows easy
access to devices for the purpose of configuration, command execution,
and other tasks.  It is modelled after the Net::Telnet::Cisco module
for Perl, but is designed to be extensible to multiple vendors and
multiple types of connections (ssh, serial, etc.)

Usage:

    from netdevicelib.connections import ConnectionFactory

    conn = ConnectionFactory().createConnection( "telnet", "IOS" )
    conn.open( router1.example.com )
    conn.login( "myusername", "mypassword" );

    lines = conn.cmd( "show version" )
    print lines

Notes:

    Right now, netdevicelib is in a very preliminary state, and most
    likely makes a lot of assumptions about the devices to which it is
    connecting.  This is due to the limited number of devices
    available for testing.  Feedback is most welcome and suggestions
    for improvement are encouraged.  If it doesn't work with your
    device, please provide whatever information you can to help fix
    the problem.
