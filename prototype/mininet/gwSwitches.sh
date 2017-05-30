
echo "set default gw"
curl -X POST -d '{"gateway":"192.168.0.2"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"gateway":"192.168.0.1"}' http://localhost:8080/router/0000000000000002
echo ""
curl -X POST -d '{"gateway":"192.168.1.1"}' http://localhost:8080/router/0000000000000003
echo ""
