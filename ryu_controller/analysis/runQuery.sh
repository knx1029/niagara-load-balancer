fg=2
if [ "$1" != "" ]; then
    fg=$1
fi

ppath=/home/ryu
PYTHONPATH=$ppath python analyze.py -fg_id $fg -mode gw -create_new
while [ true ]; do
# if  [ "1" == "0" ]; then
    PYTHONPATH=$ppath python analyze.py -fg_id $fg -mode gw
    sleep 5
# fi
done
