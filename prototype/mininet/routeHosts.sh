
if [ "$1" == "client1" ]; then
ip route add default via 10.0.1.2
fi

if [ "$1" == "client2" ]; then
ip route add default via 10.1.1.2
fi

if [ "$1" == "server1" ]; then
ip route add default via 10.2.1.2
fi

if [ "$1" == "server2" ]; then
ip route add default via 10.3.1.2
fi

if [ "$1" == "sswitch1" ]; then
ip route add default via 10.4.1.2
fi

if [ "$1" == "sswitch2" ]; then
ip route add default via 10.5.1.2
fi
