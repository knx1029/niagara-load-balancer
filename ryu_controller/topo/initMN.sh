echo "1. config: $device_name {ip/rt}"
echo "2. display: $sw_name {show / get {\"address\",\"arp\",\"rules\",\"install_rules\",\"clear_rules\",\"ecmp_group\",\"flow2ecmp\",\"flow_group\",\"of_table\"}}"
echo "3. preset ecmp policy: hw_fwd_be/hw_fwd_ssw/hw_nat_be"
echo "4. preset flows: flows"
echo "5. apply $ecmp_id $fg_id | del_ecmp $ecmp_id | del_flow $flow_id"
echo "6. change_ecmp | create_ecmp ONLY SHOWS SAMPLE COMMAND"
echo ""

HSWITCH=s1
GWSWITCH=s2
SERVER1=hwh1
SERVER2=hwh2
SERVER3=hwh3
SERVER4=hwh4

HSWURL=http://localhost:8080/router/0000000000000001
GWSURL=http://localhost:8080/router/0000000000000002

## config server

if [ "$1" == "$SERVER1" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SERVER1-eth0 192.168.1.1/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    fi

elif [ "$1" == "$SERVER2" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SERVER2-eth0 192.168.1.2/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    fi
elif [ "$1" == "$SERVER3" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SERVER3-eth0 192.168.1.3/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    fi
elif [ "$1" == "$SERVER4" ]; then
    if [ "$2" == "ip" ]; then
	ifconfig $SERVER4-eth0 192.168.1.4/16
    elif [ "$2" == "rt" ]; then
	route add default gw 192.168.3.1
    fi
fi

## config client
if [ "$1" == "client" ]; then
    if [ "$2" == "ip" ]; then
	echo "do nothing"
    elif [ "$2" == "rt" ]; then
	route add default gw 10.1.1.1
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
if [ "$1" == "nat_policy" ]; then
    ## 1:1 split
    echo "create_ecmp 1:1 split for 192.168.1.1 and 192.168.1.2 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    echo ""

    ## 3:1 split
    echo "create_ecmp 3:1 split for 192.168.1.1 and 192.168.1.2 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(3,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(3,\"\"),\"192.168.1.2\":(1,\"\")}"}' $HSWURL
    echo ""

    ## 1:1:1:1 split
    echo "create_ecmp 1:1:1:1 split for 192.168.1.1 and 192.168.1.2 and 192.168.1.3 and 192.168.1.4 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\"),\"192.168.1.3\":(1,\"\"),\"192.168.1.4\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\"),\"192.168.1.3\":(1,\"\"),\"192.168.1.4\":(1,\"\")}"}' $HSWURL
    echo ""

    ## 1:1:1:0 split
    echo "create_ecmp 1:1:1 split for 192.168.1.1 and 192.168.1.2 and 192.168.1.3 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\"),\"192.168.1.3\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(1,\"\"),\"192.168.1.2\":(1,\"\"),\"192.168.1.3\":(1,\"\")}"}' $HSWURL
    echo ""


    ## 3:2:1 split
    echo "create_ecmp 3:2:1 split for 192.168.1.1 and 192.168.1.2 and 192.168.1.3 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(3,\"\"),\"192.168.1.2\":(2,\"\"),\"192.168.1.3\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(3,\"\"),\"192.168.1.2\":(2,\"\"),\"192.168.1.3\":(1,\"\")}"}' $HSWURL
    echo ""

    ## 4:3:2:1 split
    echo "create_ecmp 4:3:2:1 split for 192.168.1.1 and 192.168.1.2 and 192.168.1.3 and 192.168.1.4 (nat)"
    echo curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(4,\"\"),\"192.168.1.2\":(3,\"\"),\"192.168.1.3\":(2,\"\"),\"192.168.1.4\":(1,\"\")}"}' $HSWURL
    curl --silent -X POST -d '{"ecmp_group":"create", "gateways":"{\"192.168.1.1\":(4,\"\"),\"192.168.1.2\":(3,\"\"),\"192.168.1.3\":(2,\"\"),\"192.168.1.4\":(1,\"\")}"}' $HSWURL
    echo ""
fi


if [ "$1" == "flows" ]; then
    ## VIP 192.168.6.6
    echo "Vip 192.168.6.6"
    echo curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.6.6&0xffffffff", "dport":"12345", "ip_proto":"udp", "return_gw":"192.168.3.2"}' $HSWURL
    curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.6.6&0xffffffff", "dport":"12345", "ip_proto":"udp", "return_gw":"192.168.3.2"}' $HSWURL
    echo ""

    ## VIP 192.168.7.7
    echo "Vip 192.168.7.7"
    echo curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.7.7&0xffffffff", "dport":"54321", "return_gw":"192.168.3.2"}' $HSWURL
    curl --silent -X POST -d '{"flow_group":"create", "sip":"10.0.0.0&0xff000000", "dip":"192.168.7.7&0xffffffff", "dport":"54321", "return_gw":"192.168.3.2"}' $HSWURL
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
#    curl -X POST -d '{"ecmp_group":"change", "ecmp_id":"2","gateways":"{\"192.168.1.1\":(3,None)"}' $HSWURL
    echo ""

fi
