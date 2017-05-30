sip=sip$2
veth=${sip}veth1
eth=${sip}eth0
vip=192.168.1$2.$2
ip=192.168.1$2.1$2

if [ "$1" == "add" ]; then
    ip netns add $sip
    ip link add $eth type veth peer name $veth
    ip link set $veth netns $sip
    ifconfig $eth $ip pointopoint $vip up
    ip netns exec $sip ifconfig $veth $vip pointopoint $ip up
    sysctl -w net.ipv4.ip_forward=1
    ip netns exec $sip route add default gw $sip

elif [ "$1" == "ex" ]; then
    ip netns add sip1
    ip link add sip1eth0 type veth peer name sip1veth1
    ip link set sip1veth1 netns sip1
    ifconfig sip1eth0 192.168.124.1 pointopoint 192.168.124.2 up
    ip netns exec sip1 ifconfig sip1veth1 192.168.124.2 pointopoint 192.168.124.1 up
    sysctl -w net.ipv4.ip_forward=1
    ip netns exec sip1 route add default gw 192.168.124.1

elif [ "$1" == "delete" ]; then
    ip netns exec $sip ifconfig $veth 0
    ip link delete $eth
    ip netns delete $sip
fi
