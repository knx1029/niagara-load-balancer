x=1
while [ true ]
do
    echo "$x ifconfig eth0 192.168.2.3/24 and add default route"
    x=$((x+1))
    if [ "$x" == "1" ]; then
	route add default gw 192.168.2.1
    fi
#    ifconfig  eth0 192.168.2.3/24
    ifconfig sip12eth0 192.168.112.112 pointopoint 192.168.112.12
    ifconfig sip13eth0 192.168.113.113 pointopoint 192.168.113.13
    ifconfig sip14eth0 192.168.114.114 pointopoint 192.168.114.14
    ifconfig sip15eth0 192.168.115.115 pointopoint 192.168.115.15
done
