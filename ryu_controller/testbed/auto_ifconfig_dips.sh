x=1
while [ true ]
do
    echo "$x ifconfig eth0 192.168.2.2/24 and add default route"
    if [ "$x" == "1" ]; then
	route add -net 192.168.0.0 netmask 255.255.0.0 gateway 192.168.2.1
    fi
    x=$((x+1))
#    ifconfig eth0 192.168.2.2/24
    ifconfig dip3eth0 192.168.3.2 pointopoint 192.168.3.1
    ifconfig dip4eth0 192.168.4.2 pointopoint 192.168.4.1
    ifconfig dip5eth0 192.168.5.2 pointopoint 192.168.5.1
    ifconfig dip6eth0 192.168.6.2 pointopoint 192.168.6.1
    sleep 30
done
