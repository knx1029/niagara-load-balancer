# vip is 10.6.1.1
# direct 10.0/16 to 10.4.1.1 and 10.1/16 to 10.5.1.1

hswitch_id=0000000000000001

# let dumb switches direct vip to sswitches
if [ "$1" == "nomod" ]; then
    if [ "$2" == "1" ]; then
	curl -X POST -d '{"destination":"10.6.1.1/16", "gateway":"10.4.1.1"}' http://localhost:8080/router/0000000000000002
	curl -X POST -d '{"destination":"10.6.1.1/16", "gateway":"10.5.1.1"}' http://localhost:8080/router/0000000000000003
    elif [ "$2" == "2" ]; then
	curl -X POST -d '{"niagara":"1","vip":"10.6.1.1","sip":"10.0.0.0","pattern":"0xffff0000","gateway":"192.168.0.2"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "3" ]; then
	curl -X POST -d '{"niagara":"2","vip":"10.6.1.1","sip":"10.1.0.0","pattern":"0xffff0000","gateway":"192.168.1.2"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "4" ]; then
	curl -X DELETE -d '{"niagara_id":"1"}' http://localhost:8080/router/$hswitch_id
    fi

elif [ "$1" == "wildcard" ]; then
    if [ "$2" == "1" ]; then
	curl -X POST -d '{"destination":"10.6.1.1/16", "gateway":"10.4.1.1"}' http://localhost:8080/router/0000000000000002
	curl -X POST -d '{"destination":"10.6.1.1/16", "gateway":"10.5.1.1"}' http://localhost:8080/router/0000000000000003
    elif [ "$2" == "2" ]; then
	curl -X POST -d '{"niagara":"1","vip":"10.6.1.1","sip":"10.0.0.0","pattern":"0x00ff0000","gateway":"192.168.0.2"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "3" ]; then
	curl -X POST -d '{"niagara":"2","vip":"10.6.1.1","sip":"10.1.0.0","pattern":"0x00ff0000","gateway":"192.168.1.2"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "4" ]; then
	curl -X DELETE -d '{"niagara_id":"1"}' http://localhost:8080/router/$hswitch_id
    fi

elif [ "$1" == "mod" ]; then
    if [ "$2" == "1" ]; then
	curl -X DELETE -d '{"route_id":"4"}' http://localhost:8080/router/0000000000000002
	curl -X DELETE -d '{"route_id":"4"}' http://localhost:8080/router/0000000000000003
    elif [ "$2" == "2" ]; then
	curl -X POST -d '{"niagara":"1","vip":"10.6.1.1","sip":"10.0.0.0","pattern":"0x00ff0000","gateway":"192.168.0.2","dip":"10.4.1.3"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "3" ]; then
	curl -X POST -d '{"niagara":"2","vip":"10.6.1.1","sip":"10.1.0.0","pattern":"0x00ff0000","gateway":"192.168.1.2","dip":"10.5.1.3"}' http://localhost:8080/router/$hswitch_id
    elif [ "$2" == "4" ]; then
	curl -X DELETE -d '{"niagara_id":"2"}' http://localhost:8080/router/$hswitch_id
    fi

fi
