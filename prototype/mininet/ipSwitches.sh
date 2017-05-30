
echo "config hswitch"
curl -X POST -d '{"address":"10.0.1.2/16"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"address":"10.1.1.2/16"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"address":"192.168.0.1/24"}' http://localhost:8080/router/0000000000000001
echo ""
curl -X POST -d '{"address":"192.168.1.1/24"}' http://localhost:8080/router/0000000000000001
echo ""

echo "config s1"
curl -X POST -d '{"address":"10.2.1.2/16"}' http://localhost:8080/router/0000000000000002
echo ""
curl -X POST -d '{"address":"10.4.1.2/16"}' http://localhost:8080/router/0000000000000002
echo ""
curl -X POST -d '{"address":"192.168.0.2/24"}' http://localhost:8080/router/0000000000000002
echo ""

echo "config s2"
curl -X POST -d '{"address":"10.3.1.2/16"}' http://localhost:8080/router/0000000000000003
echo ""
curl -X POST -d '{"address":"10.5.1.2/16"}' http://localhost:8080/router/0000000000000003
echo ""
curl -X POST -d '{"address":"192.168.1.2/24"}' http://localhost:8080/router/0000000000000003
echo ""


