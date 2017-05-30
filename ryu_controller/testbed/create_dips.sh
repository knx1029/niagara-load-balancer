dip=dip$2
veth=${dip}veth1
eth=${dip}eth0
vip=192.168.$2.1
ip=192.168.$2.2

if [ "$1" == "add" ]; then
    ip netns add $dip
    ip link add $eth type veth peer name $veth
    ip link set $veth netns $dip
    ifconfig $eth $ip pointopoint $vip up
    ip netns exec $dip ifconfig $veth $vip pointopoint $ip up
    sysctl -w net.ipv4.ip_forward=1
    ip netns exec $dip route add default gw $ip
elif [ "$1" == "delete" ]; then
    ip netns exec $dip ifconfig $veth 0
    ip link delete $eth
    ip netns delete $dip

elif [ "$1" == "nat" ]; then
#    dip1=74.125.225.112
#    dip2=74.125.225.113
    dip1=74.125.131.102
    dip2=74.125.131.104
    sip=128.12.92.60
    if [ "$2" == "add" ]; then
	iptables -t nat -A POSTROUTING -d $dip1 -s 192.168.6.1 -j SNAT --to-source $sip
#	iptables -t nat -A POSTROUTING -d $dip1 ! -s $sip -j SNAT --to-source $sip
#	iptables -t nat -A POSTROUTING -d $dip2 ! -s $sip -j SNAT --to-source $sip
	sysctl -w net.ipv4.ip_forward=1
    elif [ "$2" == "delete" ]; then
	iptables -t nat -D POSTROUTING -d $dip1 -s 192.168.6.1 -j SNAT --to-source $sip
#	iptables -t nat -D POSTROUTING -d $dip1 ! -s $sip -j SNAT --to-source $sip
#	iptables -t nat -D POSTROUTING -d $dip2 ! -s $sip -j SNAT --to-source $sip
    fi
fi

