
echo "set gw @ hswitch"
curl -X POST -d '{"destination":"10.0.1.1/16", "gateway":"10.0.1.1"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"destination":"10.1.1.1/16", "gateway":"10.1.1.1"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"destination":"10.3.1.2/16", "gateway":"192.168.1.2"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"destination":"10.5.1.2/16", "gateway":"192.168.1.2"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"destination":"192.168.1.2/24", "gateway":"192.168.1.2"}' http://localhost:8080/router/0000000000000001
echo ""


echo "set gw @ s1"
curl -X POST -d '{"destination":"10.2.1.1/16", "gateway":"10.2.1.1"}' http://localhost:8080/router/0000000000000002
echo ""
curl -X POST -d '{"destination":"10.4.1.1/16", "gateway":"10.4.1.1"}' http://localhost:8080/router/0000000000000002
echo ""


echo "set gw @ s1"
curl -X POST -d '{"destination":"10.3.1.1/16", "gateway":"10.3.1.1"}' http://localhost:8080/router/0000000000000003
echo ""
curl -X POST -d '{"destination":"10.5.1.1/16", "gateway":"10.5.1.1"}' http://localhost:8080/router/0000000000000003
echo ""
