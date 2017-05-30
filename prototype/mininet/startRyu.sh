
if [ "$1" == "rest_router" ]; then
PYTHONPATH=/home/ryu/ /home/ryu/bin/ryu-manager /home/ryu/ryu/app/$1.py
#elif [ "$1" == "niagara" ]; then
else
PYTHONPATH=/home/ryu/ /home/ryu/bin/ryu-manager /home/niagara/$1.py
fi
