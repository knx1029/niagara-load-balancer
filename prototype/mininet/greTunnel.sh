if [ "$1" == "sswitch1" ]; then
ip tunnel add tunH mode gre remote 192.168.0.1 local 10.4.1.1 ttl 255
ip link set tunH up
ip addr add 192.168.3.1/24 dev tunH
fi
