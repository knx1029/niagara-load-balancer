echo "1. config: $device_name {ip/rt}"
echo "2. display: $sw_name {show / get {\"address\",\"arp\",\"rules\",\"install_rules\",\"clear_rules\",\"ecmp_group\",\"flow2ecmp\",\"flow_group\",\"of_table\"}}"
echo "3. preset ecmp policy: hw_fwd_be/hw_fwd_ssw/hw_nat_be"
echo "4. preset flows: flows"
echo "5. apply $ecmp_id $fg_id | del_ecmp $ecmp_id | del_flow $flow_id"
echo "6. change_ecmp | create_ecmp ONLY SHOWS SAMPLE COMMAND"
echo ""

HSWITCH=s1
GWSWITCH=s2
CLIENT1=h1s2
CLIENT2=h2s2
CLIENT3=h3s2
CLIENT4=h4s2
SERVER1=h1s1
SERVER2=h2s1
SSWITCH1=h3s1
SSWITCH2=h4s1

HSWURL=http://localhost:8080/router/0000000000000001
GWSURL=http://localhost:8080/router/0000000000000002

## config client
if [ "$1" == "$CLIENT1" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $CLIENT1-eth0 10.0.0.1/8
    elif [ "$2" == "rt" ]; then
	route add default gw 10.1.1.1
    fi

elif [ "$1" == "$CLIENT2" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $CLIENT2-eth0 10.0.0.2/8
    elif [ "$2" == "rt" ]; then
	route add default gw 10.1.1.1
    fi

elif [ "$1" == "$CLIENT3" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $CLIENT3-eth0 10.0.0.3/8
    elif [ "$2" == "rt" ]; then
	route add default gw 10.1.1.1
    fi

elif [ "$1" == "$CLIENT4" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $CLIENT4-eth0 10.0.0.4/8
    elif [ "$2" == "rt" ]; then
	route add default gw 10.1.1.1
    fi
fi


## config server
if [ "$1" == "$SERVER1" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SERVER1-eth0 192.168.1.1/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
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

elif [ "$1" == "$SERVER2" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SERVER2-eth0 192.168.1.2/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    fi
fi

## config sswitch
if [ "$1" == "$SSWITCH1" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SSWITCH1-eth0 192.168.2.1/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    elif [ "$2" == "nat" ]; then
	vip=$3
	dip=192.168.1.1
	iptables -t nat -A POSTROUTING -d $dip -j SNAT --to-source 192.168.2.1
	iptables -t nat -A PREROUTING -d $vip -j DNAT --to-destination $dip
	sysctl -w net.ipv4.ip_forward=1
    fi

elif [ "$1" == "$SSWITCH2" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SSWITCH2-eth0 192.168.2.2/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    elif [ "$2" == "nat" ]; then
	vip=$3
	dip=192.168.1.2
	iptables -t nat -A POSTROUTING -d $dip -j SNAT --to-source 192.168.2.2
	iptables -t nat -A PREROUTING -d $vip -j DNAT --to-destination $dip
	sysctl -w net.ipv4.ip_forward=1
    fi
fi


## config GWSWITCH
if [ "$1" == "$GWSWITCH" ]; then
    if [ "$2" == "ip" ]; then
	curl --silent -X POST -d '{"address":"10.1.1.1/8"}' $GWSURL
	echo ""

	curl --silent -X POST -d '{"address":"192.168.3.2/16"}' $GWSURL
	echo ""
    elif [ "$2" == "rt" ]; then
	## create a route to HSWITCH
	curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.3.1\":(1,None)}"}' $GWSURL
	echo ""

	## set the route as default
	curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.0.0&0xffff0000"}' $GWSURL
	echo ""
	curl --silent -X POST -d '{"flow_group":"apply", "ecmp_id":"2", "fg_id":"1"}' $GWSURL
	echo ""
    elif [ "$2" == "show" ]; then
	ovs-ofctl -O openflow13 dump-flows $GWSWITCH
    elif [ "$2" == "get" ]; then
	if [ "$3" == "" ]; then
	    curl --silent -X GET $GWSURL
	    echo ""
	else
	    curl --silent -X GET -d \'\{$3\}\' $GWURL
	    echo ""
	fi
    elif [ "$2" == "br" ]; then
	ovs-vsctl set Bridge $GWSWITCH protocols=OpenFlow13
    fi
fi


## config HSWITCH
if [ "$1" == "$HSWITCH" ]; then
    if [ "$2" == "ip" ]; then
	echo "config hswitch"
	curl --silent -X POST -d '{"address":"192.168.3.1/16"}' $HSWURL
	echo ""
    elif [ "$2" == "rt" ]; then
	## create a route to GWSWITCH
	curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.3.2\":(1,None)}"}' $HSWURL
	echo ""
	## set the route as default
	curl --silent -X POST -d '{"flow_group":"create", "dip":"10.0.0.0&0xff000000", "sip":"192.168.0.0&0xffff0000"}' $HSWURL
	echo ""
	curl --silent -X POST -d '{"flow_group":"apply", "ecmp_id":"2", "fg_id":"1"}' $HSWURL
	echo ""
    elif [ "$2" == "show" ]; then
	ovs-ofctl -O openflow13 dump-flows $HSWITCH

    elif [ "$2" == "get" ]; then
	if [ "$3" == "" ]; then
	    curl --silent -X GET $HSWURL
	    echo ""
	else
	    curl --silent -X GET -d \'\{$3\}\' $HSWURL
	    echo ""
	fi
    elif [ "$2" == "br" ]; then
	ovs-vsctl set Bridge $HSWITCH protocols=OpenFlow13
    fi
fi


## config ecmp rules

## create ecmp_group
## hswitch forward to be
if [ "$1" == "hw_fwd_be" ]; then
    ## 1:1 split
    echo "create_ecmp 1:1 split for 192.168.1.1 and 192.168.1.2"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,None),\"192.168.1.2\":(1,None)}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,None),\"192.168.1.2\":(1,None)}"}' $HSWURL
    echo ""

    ## 2:1 split
    echo "create_ecmp 2:1 split for 192.168.1.1 and 192.168.1.2"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(2,None),\"192.168.1.2\":(1,None)}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(2,None),\"192.168.1.2\":(1,None)}"}' $HSWURL
    echo ""
	
# hswitch forward to ssw
elif [ "$1" == "hw_fwd_ssw" ]; then
    ## 1:1 split
    echo "create_ecmp 1:1 split for 192.168.2.1 and 192.168.2.2"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.2.1\":(1,None),\"192.168.2.2\":(1,None)}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.2.1\":(1,None),\"192.168.2.2\":(1,None)}"}' $HSWURL
    echo ""

    ## 2:1 split
    echo "create_ecmp 2:1 split for 192.168.2.1 and 192.168.2.2"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.2.1\":(2,None),\"192.168.2.2\":(1,None)}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.2.1\":(2,None),\"192.168.2.2\":(1,None)}"}' $HSWURL
    echo ""	

## hswitch nat to be
elif [ "$1" == "hw_nat_be" ]; then
    ## 1:1 split
    echo "create_ecmp 1:1 split for 192.168.1.1 and 192.168.1.2 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    echo ""

    ## 2:1 split
    echo "create_ecmp 2:1 split for 192.168.1.1 and 192.168.1.2 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(2,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(2,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    echo ""


    ## 3:1 split
    echo "create_ecmp 3:1 split for 192.168.1.1 and 192.168.1.2 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(3,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(3,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    echo ""

fi


if [ "$1" == "flows" ]; then
    ## VIP 192.168.6.6
    echo "Vip 192.168.6.6"
    echo curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.6.6&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.6.6&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    echo ""

    ## VIP 192.168.7.7
    echo "Vip 192.168.7.7"
    echo curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.7.7&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.7.7&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    echo ""

    ## VIP 192.168.8.8
    echo "Vip 192.168.8.8"
    echo curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.8.8&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.8.8&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    echo ""

    ## VIP 192.168.9.9
    echo "Vip 192.168.9.9"
    echo curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.9.9&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.9.9&0xffffffff", "return_gw":"192.168.3.2"}' $HSWURL
    echo ""
fi

## apply ecmp group
if [ "$1" == "apply" ]; then
    ## apply ecmp_id=$2 to fg_id=$3
    x={\"flow_group\":\"apply\"\,\"ecmp_id\":\"$2\"\,\"fg_id\":\"$3\"}
    echo curl --silent -X POST -d $x $HSWURL
    curl --silent -X POST -d $x $HSWURL
    echo ""

## delete ecmp group
elif [ "$1" == "del_ecmp" ]; then

    x={\"ecmp_group\":\"destroy\"\,\"ecmp_id\":\"$2\"}
    echo curl --silent -X POST -d $x $HSWURL
    curl --silent -X POST -d $x $HSWURL
    echo ""

## delete flow group
elif [ "$1" == "del_flow" ]; then
    x={\"fg_id\":$2}
    echo curl --silent -X DELETE -d $x  $HSWURL
    curl --silent -X DELETE -d $x $HSWURL
    echo ""

## create ecmp group
elif [ "$1" == "create_ecmp" ]; then
    echo "** here is an example command"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,None),\"192.168.1.2\":(1,None)}"}' $HSWURL
    echo ""

## currently disabled for the following operations
## delete ecmp group
elif [ "$1" == "change_ecmp" ]; then
    ## change 1:1 to 3:1
    echo "** here is an example command"
    echo curl --silent -X POST -d '{"ecmp_group":"change", "ecmp_id":"2","gateways":"{\"192.168.1.1\":(3,None)"}' $HSWURL
#    curl --silent -X POST -d '{"ecmp_group":"change", "ecmp_id":"2","gateways":"{\"192.168.1.1\":(3,None)"}' $HSWURL
    echo ""

fi
