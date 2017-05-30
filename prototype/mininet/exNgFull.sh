# vip is 10.6.1.1
# direct 10.0/16 to 10.4.1.1 and 10.1/16 to 10.5.1.1

hswitch_id=0000000000000001
s1_id=0000000000000002
s2_id=0000000000000003

# let dumb switches direct vip to sswitches
if [ "$1" == "rt" ]; then
    curl -X POST -d '{"destination":"10.6.1.1/16", "gateway":"10.4.1.1"}' http://localhost:8080/router/$s1_id
    curl -X POST -d '{"destination":"10.6.1.1/16", "gateway":"10.5.1.1"}' http://localhost:8080/router/$s2_id

# install niagara rules
elif [ "$1" == "ng" ]; then
    curl -X POST -d '{"niagara":"1","vip":"10.6.1.1","sip":"10.0.0.0","pattern":"0x00000000","gateway":"192.168.0.2"}' http://localhost:8080/router/$hswitch_id
    curl -X POST -d '{"niagara":"2","vip":"10.6.1.1","sip":"10.1.0.0","pattern":"0xffff0000","gateway":"192.168.1.2"}' http://localhost:8080/router/$hswitch_id

elif [ "$1" == "sw" ]; then
    if [ "$2" == "sswitch1" ]; then
	echo "setting" $2
	sysctl -w net.ipv4.ip_forward=1
	iptables -t nat -A POSTROUTING -s 10.0.0.0/16 -j SNAT --to-source 10.4.1.1
	iptables -t nat -A PREROUTING -d 10.6.1.1 -p icmp -j DNAT --to-destination 10.2.1.1
	iptables -t nat -A PREROUTING -d 10.6.1.1 -p tcp --dport 80 -j DNAT --to-destination 10.2.1.1
    elif [ "$2" == "sswitch2" ]; then
	echo "setting" $2
	sysctl -w net.ipv4.ip_forward=1
	iptables -t nat -A POSTROUTING -s 10.1.0.0/16 -j SNAT --to-source 10.5.1.1
	iptables -t nat -A PREROUTING -d 10.6.1.1 -p icmp -j DNAT --to-destination 10.3.1.1
	iptables -t nat -A PREROUTING -d 10.6.1.1 -p tcp --dport 80 -j DNAT --to-destination 10.3.1.1
    else
	echo "unknown" $2
    fi
elif [ "$1" == "sv" ]; then
    python -m SimpleHTTPServer 80

elif [ "$1" == "wget" ]; then
    wget -O - 10.6.1.1

elif [ "$1" == "rm" ]; then
    if [ "$2" == "rt" ]; then
	curl -X DELETE -d '{"route_id":"4"}' http://localhost:8080/router/$s1_id
	curl -X DELETE -d '{"route_id":"4"}' http://localhost:8080/router/$s2_id
    elif [ "$2" == "ng" ]; then
	curl -X DELETE -d '{"niagara_id":"all"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "sswitch1" ]; then
	iptables -t nat -D POSTROUTING -s 10.0.0.0/16 -j SNAT --to-source 10.4.1.1
	iptables -t nat -D PREROUTING -d 10.6.1.1 -p icmp -j DNAT --to-destination 10.2.1.1
    elif [ "$2" == "sswitch2" ]; then
	iptables -t nat -D POSTROUTING -s 10.1.0.0/16 -j SNAT --to-source 10.5.1.1
	iptables -t nat -D PREROUTING -d 10.6.1.1 -p icmp -j DNAT --to-destination 10.3.1.1
    fi
else
    echo "options = [rt | ng | sw {sswitch1, sswitch2} | sv | wget | rm {rt, ng, sswitch1, sswitch2}]"
fi
