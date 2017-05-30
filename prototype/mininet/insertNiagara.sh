router_id=0000000000000001

if [ "$1" == "1" ]; then
curl -X POST -d '{"niagara":"1","vip":"10.4.1.3","sip":"10.0.0.0","pattern":"0xffff0000","gateway":"192.168.0.2"}' http://localhost:8080/router/$router_id
elif [ "$1" == "3" ]; then
curl -X POST -d '{"niagara":"2","vip":"10.4.1.3","sip":"10.1.0.0","pattern":"0xffff0000","proto":"tcp","dip":"10.4.1.1","dport":"80","gateway":"192.168.0.2"}' http://localhost:8080/router/$router_id
elif [ "$1" == "2" ]; then
curl http://localhost:8080/router/$router_id
elif [ "$1" == "4" ]; then
curl -X DELETE -d '{"niagara_id":"2"}' http://localhost:8080/router/$router_id
fi
