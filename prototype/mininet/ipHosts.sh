
if [ "$1" == "client1" ]; then
ip addr del 10.0.0.1/8 dev client1-eth0
ip addr add 10.0.1.1/16 dev client1-eth0
fi

if [ "$1" == "client2" ]; then
ip addr del 10.0.0.2/8 dev client2-eth0
ip addr add 10.1.1.1/16 dev client2-eth0
fi

if [ "$1" == "server1" ]; then
ip addr del 10.0.0.3/8 dev server1-eth0
ip addr add 10.2.1.1/16 dev server1-eth0
fi

if [ "$1" == "server2" ]; then
ip addr del 10.0.0.4/8 dev server2-eth0
ip addr add 10.3.1.1/16 dev server2-eth0
fi

if [ "$1" == "sswitch1" ]; then
ip addr del 10.0.0.5/8 dev sswitch1-eth0
ip addr add 10.4.1.1/16 dev sswitch1-eth0
fi

if [ "$1" == "sswitch2" ]; then
ip addr del 10.0.0.6/8 dev sswitch2-eth0
ip addr add 10.5.1.1/16 dev sswitch2-eth0
fi


