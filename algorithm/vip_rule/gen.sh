

fold=mvip_data/
e=0.001
for w in b; do
for j in 64; do
for v in 400; do
#for t in 1 300; do
   folder="${fold}weight$j"
#   folder=svip_data/update
#   input="$folder/del_w${j}_${w}_${v}"
#   input="$folder/add_w${j}_${w}_${v}"
   input="$folder/w${j}_${w}_${v}"
#   traffic="$fold/v${v}_zipf${t}"
#   output="$folder/w${j}_${w}_v${v}_zipf${t}_out_ecmp_$arg.csv"
#   debug="$folder/w${j}_${w}_v${v}_zipf${t}_debug_ecmp_$arg"
#   output="$folder/w${j}_${w}_v${v}_zipf${t}_out_$arg.csv"
#   debug="$folder/w${j}_${w}_v${v}_zipf${t}_debug_$arg"
#   echo $input $traffic $output
   python random_input.py m $input $v $j $w
#   echo python random_input.py u $input $v $j $e $w
#   python random_input.py u $input $v $j $e $w
#done
done
done
done
