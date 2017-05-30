if [ "$1" == "create" ]; then
    ovs-vsctl add-br br0 -- set bridge br0 datapath_type=pica8
    ovs-vsctl add-port br0 ge-1/1/1 vlan_mode=trunk -- set interface ge-1/1/1 type=pica8
    ovs-vsctl add-port br0 ge-1/1/2 vlan_mode=trunk -- set interface ge-1/1/2 type=pica8
elif [ "$1" == "set" ]; then
    ovs-vsctl set-controller br0 tcp:192.168.1.1:6633
elif [ "$1" == "delete" ]; then
    ovs-vsctl del-br br0
elif [ "$1" == "dump" ]; then
    ovs-ofctl dump-flows br0
else
    echo "create | set | delete | dump"
fi
