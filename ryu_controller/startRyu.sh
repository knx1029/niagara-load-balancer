echo "rest_router | niagara_hswitch | ecmp_router | analyze"
if [ "$1" == "rest_router" ]; then
PYTHONPATH=/home/ryu/ /home/ryu/bin/ryu-manager /home/ryu/ryu/app/$1.py

elif [ "$1" == "niagara_hswitch" ]; then
PYTHONPATH=/home/ryu/ /home/ryu/bin/ryu-manager /home/niagara/$1.py

elif [ "$1" == "ecmp_router" ]; then
#PYTHONPATH=/home/ryu/ /home/ryu/bin/ryu-manager /home/niagara/ecmp_router/controller.py
ryu-manager controller.py
fi
