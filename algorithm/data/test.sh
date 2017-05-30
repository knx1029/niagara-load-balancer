f=univ1_41_177
t=asym
echo "ecmp"
#python mpath.py ecmp ${f}_trace_nbytes.txt > ${f}_ecmp_${t}_output.txt
echo "microte"
#python mpath.py microte ${f}_trace_nbytes.txt > ${f}_microte_${t}_output.txt
echo "input"
#python mpath.py input ${f}_trace_nbytes.txt > ${f}_input.txt
echo "rule_lib"
python ../../algorithm/rule_lib/main.py ${f}_input.txt > ${f}_${t}_output_.txt
echo "ng"
python mpath.py ng ${f}_trace_nbytes.txt ${f}_${t}_output_.txt> ${f}_ng_${t}_output_.csv


