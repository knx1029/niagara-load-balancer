x=1
while [ true ]
do
    echo "$x ifconfig eth1 192.168.1.1/24"
    x=$((x+1))
    ifconfig eth1 192.168.1.1/24
    sleep 30
done
