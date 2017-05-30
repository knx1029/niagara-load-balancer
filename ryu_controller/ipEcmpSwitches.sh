if [ "$1" == "address" ]; then

curl -X POST -d '{"address":"10.0.1.1/16"}' http://localhost:8080/router/0000000000000001
# echo ""
#curl -X POST -d '{"address":"10.1.1.1/16"}' http://localhost:8080/router/0000000000000001
#echo ""
#curl -X POST -d '{"address":"10.2.1.1/16"}' http://localhost:8080/router/0000000000000001
#echo ""

#curl -X POST -d '{"address":"10.1.1.1/8"}' http://localhost:8080/router/0000000000000001
echo ""

elif [ "$1" == "ecmp" ]; then

curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"10.0.0.2\":1,\"10.0.0.3\":1,\"10.0.0.4\":1,\"10.0.0.5\":1}"}' http://localhost:8080/router/0000000000000001
echo ""

curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"10.0.0.2\":1,\"10.0.0.3\":2,\"10.0.0.4\":2,\"10.0.0.5\":1}"}' http://localhost:8080/router/0000000000000001


#curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"10.2.0.2\":2}"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"10.3.0.2\":2}"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"ecmp_group":"create", "gateways":"{\"10.1.0.2\":2}"}' http://localhost:8080/router/0000000000000001
echo ""

elif [ "$1" == "flow" ]; then

curl -X POST -d '{"flow_group":"create", "sip":"10.0.0.1&0xffff0000", "dip":"10.6.0.1&0xffffffff"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"flow_group":"create", "dip":"10.2.0.2&0xffffffff"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"flow_group":"create", "dip":"10.3.0.2&0xffffffff"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"flow_group":"create", "dip":"10.1.0.2&0xffffffff"}' http://localhost:8080/router/0000000000000001
echo ""

elif [ "$1" == "apply" ]; then

#curl -X POST -d '{"flow_group":"apply", "ecmp_id":"2", "fg_id":"1"}' http://localhost:8080/router/0000000000000001
curl -X POST -d '{"flow_group":"apply", "ecmp_id":"3", "fg_id":"2"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"flow_group":"apply", "ecmp_id":"4", "fg_id":"3"}' http://localhost:8080/router/0000000000000001
#curl -X POST -d '{"flow_group":"apply", "ecmp_id":"5", "fg_id":"4"}' http://localhost:8080/router/0000000000000001
echo ""

elif [ "$1" == "del_ecmp" ]; then

curl -X POST -d '{"ecmp_group":"destroy", "ecmp_id":"2"}' http://localhost:8080/router/0000000000000001
echo ""

elif [ "$1" == "del_flow" ]; then

curl -X DELETE -d '{"fg_id":1}' http://localhost:8080/router/0000000000000001
echo ""

elif [ "$1" == "get" ]; then

curl http://localhost:8080/router/0000000000000001
echo ""


elif [ "$1" == "set" ]; then
ovs-vsctl set Bridge s1 protocols=OpenFlow13

elif [ "$1" == "show" ]; then

ovs-ofctl -O openflow13 dump-flows s1

fi

