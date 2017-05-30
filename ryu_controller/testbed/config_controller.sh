echo "$device_name {ip/rt/get/show} | hw_fwd_be/hw_fwd_ssw/hw_nat_be | flows | apply $ecmp_id $fg_id"
HSWITCH=hswitch
CLIENT=client
SERVER=server
SSWITCH=sswitch

HSWURL=http://localhost:8080/router/678c089e010d5ebe
# HSWURL=http://localhost:8080/router/678cdeb578ba62d0

## config client
if [ "$1" == "$CLIENT" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $CLIENT1-eth0 192.168.2.3
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.2.1
    elif [ "$2" == "sip" ]; then
	ip netns add sip1
	ip link add sip1eth0 type veth peer name sip1veth1
	ip link set sip1veth1 netns sip1
	ifconfig sip1eth0 192.168.124.1 pointopoint 192.168.124.2 up
	ip netns exec sip1 ifconfig sip1veth1 192.168.124.2 pointopoint 192.168.124.1 up
	sysctl -w net.ipv4.ip_forward=1
	ip netns exec sip1 route add default gw 192.168.124.1
    fi
fi


## config server
if [ "$1" == "$SERVER1" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig eth0 192.168.2.2/24
    elif [ "$2" == "rt" ]; then
	route add -net 192.168.2.0 netmask 255.255.255.0 gw 192.168.2.1
    elif [ "$2" == "vip" ]; then
	## an example to configure a virtual IP (192.168.124.2) at the server
	ip netns add vip1
	ip link add vip1eth0 type veth peer name vip1veth1
	ip link set vip1veth1 netns vip1
	ifconfig vip1eth0 192.168.124.1 pointopoint 192.168.124.2 up
	ip netns exec vip1 ifconfig vip1eth1 192.168.124.2 pointopoint 192.168.124.1 up
	sysctl -w net.ipv4.ip_forward=1
	ip netns exec vip1 route add default gw 192.168.124.1
    fi

fi

## config sswitch
if [ "$1" == "$SSWITCH" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SSWITCH2-eth0 192.168.2.2/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    elif [ "$2" == "nat" ]; then
	dip1=74.125.225.112
	dip2=74.125.225.113
	sip=192.168.1.2
	iptables -t nat -A POSTROUTING -d $dip1 -j SNAT --to-source $sip
	iptables -t nat -A POSTROUTING -d $dip2 -j SNAT --to-source $sip
#	iptables -t nat -A PREROUTING -d $vip -j DNAT --to-destination $dip
	sysctl -w net.ipv4.ip_forward=1

    fi
fi


## config HSWITCH
if [ "$1" == "$HSWITCH" ]; then
    if [ "$2" == "ip" ]; then
	echo "config hswitch"
	curl -X POST -d '{"address":"192.168.2.1/24"}' $HSWURL
	echo ""

    elif [ "$2" == "get" ]; then
	curl -X GET $HSWURL
	echo ""
    fi
fi


## config ecmp rules

## create ecmp_group
## hswitch nat to be
if [ "$1" == "internal" ]; then
    ## 1:1 split
    echo "create_ecmp 1:1 split for 192.168.3.1 and 192.168.4.1 (nat)"
    curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.3.1\":(1,\"192.168.2.2\"),\"192.168.4.1\":(1,\"192.168.2.2\")}"}' $HSWURL
    echo ""

    ## 1:3 split
    echo "create_ecmp 1:3 split for 192.168.3.1 and 192.168.4.1 (nat)"
    curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.3.1\":(1,\"192.168.2.2\"),\"192.168.4.1\":(3,\"192.168.2.2\")}"}' $HSWURL
    echo ""

    ## 1:2:3 split
    echo "create_ecmp 1:2:3 split for 192.168.3.1 and 192.168.4.1 and 192.168.5.1(nat)"
    curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.3.1\":(1,\"192.168.2.2\"),\"192.168.4.1\":(2,\"192.168.2.2\"),\"192.168.5.1\":(3,\"192.168.2.2\")}"}' $HSWURL
    echo ""

elif [ "$1" == "external" ]; then
    a=74.125.131.102
    b=74.125.131.104
    ## 1:1 split
    echo "create_ecmp 1:1 split for $a and $b (nat)"
    curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"74.125.131.102\":(1,\"192.168.2.2\"),\"74.125.131.104\":(1,\"192.168.2.2\")}"}' $HSWURL
    echo ""

    ## 1:3 split
    echo "create_ecmp 1:3 split for $a and $b (nat)"
    curl -X POST -d '{"ecmp_group":"create", "gateways":"\"{74.125.131.102\":(1,\"192.168.2.2\"),\"74.125.131.104\":(3,\"192.168.2.2\")}"}' $HSWURL
    echo ""

    ## 1:2:3 split
#    echo "create_ecmp 1:2:3 split for 192.168.3.1 and 192.168.4.1 and 192.168.5.1(nat)"
#    curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.3.1\":(1,\"192.168.2.2\"),\"192.168.4.1\":(2,\"192.168.2.2\"),\"192.168.5.1\":(3,\"192.168.2.2\")}"}' $HSWURL
#    echo ""


fi


if [ "$1" == "flows" ]; then

    ## VIP 192.168.7.7
    echo "Vip 192.168.7.7"
    curl -X POST -d '{"flow_group":"create", "sip":"192.168.0.0&0xffff0000", "dip":"192.168.7.7&0xffffffff", "return_gw":"192.168.2.3"}' $HSWURL
    echo ""

    ## VIP 192.168.8.8
    echo "Vip 192.168.8.8"
    curl -X POST -d '{"flow_group":"create", "sip":"192.168.0.0&0xffff0000", "dip":"192.168.8.8&0xffffffff", "return_gw":"192.168.2.3"}' $HSWURL
    echo ""

    ## VIP 192.168.9.9
    echo "Vip 192.168.9.9"
    curl -X POST -d '{"flow_group":"create", "sip":"192.168.0.0&0xffff0000", "dip":"192.168.9.9&0xffffffff", "return_gw":"192.168.2.3"}' $HSWURL
    echo ""
fi

## apply ecmp group
if [ "$1" == "apply" ]; then
    ## apply ecmp_id=$2 to fg_id=$3
    x={\"flow_group\":\"apply\"\,\"ecmp_id\":\"$2\"\,\"fg_id\":\"$3\"}
    curl -X POST -d $x $HSWURL
#    curl -X POST -d '{"flow_group":"apply", "ecmp_id":"3", "fg_id":"2"}' $HSWURL
    echo ""
fi

## currently disabled for the following operations
## delete ecmp group
if [ "$1" == "change_ecmp" ]; then
    ## change 1:1 to 3:1
    curl -X POST -d '{"ecmp_group":"change", "ecmp_id":"2","gateways":"{\"192.168.1.1\":(3,None)"}' $HSWURL
    echo ""

## delete ecmp group
elif [ "$1" == "del_ecmp" ]; then
    curl -X POST -d '{"ecmp_group":"destroy", "ecmp_id":"2"}' $HSWURL
    echo ""
    curl -X POST -d '{"ecmp_group":"destroy", "ecmp_id":"3"}' $HSWURL
    echo ""

## delete flow group
elif [ "$1" == "del_flow" ]; then
    curl -X DELETE -d '{"fg_id":1}' $HSWURL
    echo ""
    curl -X DELETE -d '{"fg_id":2}' $HSWURL
    echo ""
    curl -X DELETE -d '{"fg_id":3}' $HSWURL
    echo ""
    curl -X DELETE -d '{"fg_id":4}' $HSWURL
    echo ""
fi


