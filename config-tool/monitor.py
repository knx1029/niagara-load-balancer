import os
import sys
import time
from datetime import datetime


#YOU = "SW1"
#CHURN = "OLD_CHURN"
idx_labels = map(lambda(x):3*x, [3, 4])
if_labels = ["SW1", "SW2"]
churns = ["OLD_CHURN", "NEW_CHURN"]

def run_cmd(cmd):
#  print "Running ", cmd
  str = os.popen(cmd).read()
  return str

def analyze_(ret, pattern):
  tokens = ret.rsplit(pattern)
  tokens = tokens[1].rsplit(' ')
  res = long(tokens[0])
  return res

def log_num_packets(interface):
  label = str(datetime.now())

  now = time.time()
  cmd = "sudo ifconfig {} | grep \"RX\|TX\"".format(interface)
#  print cmd
  logs = run_cmd(cmd) 
  rets = logs.rsplit('\n')

  selectors = zip(idx_labels, if_labels)
  L = []
  for idx, if_label in selectors:
#    print rets[idx:idx+3]
    a = analyze_(rets[idx + 2], 'RX bytes:')
    b = analyze_(rets[idx + 0], 'RX packets:')
    c = analyze_(rets[idx + 2], 'TX bytes:')
    d = analyze_(rets[idx + 1], 'TX packets:')
    L.append((a, b, c, d, if_label))

  return now, L, label


interface = ""
you = 0
if len(sys.argv) > 1:
  you = int(sys.argv[1])
#  interface = sys.argv[1]

base_time, base_L, _  = log_num_packets(interface)
print "label", 
#for if_label in if_labels:
# print ",time_{}, #rec_bytes, #rec_packets, #sen_bytes, #send_packets".format(if_label),
print ",time,total_{}, {}, non_churn_{}".format(if_labels[you], churns[you], if_labels[you]),
print ""

while (True):
  now, L, label = log_num_packets(interface)

  churn = non_churn = base_L[0][0]
  for kth in range(len(L)):
    a, b, c, d, if_label = L[kth]
    base_a, base_b, base_c, base_d, _ = base_L[kth]
    if (you == kth):
      non_churn = a - base_a
    else:
      churn = a - base_a
  total = non_churn + churn
  print "{}".format(label),
  print ",{},{},{},{}".format(now - base_time, total, churn, non_churn)

 # for kth in range(len(L)):
 #   a, b, c, d, if_label = L[kth]
 #   base_a, base_b, base_c, base_d, _ = base_L[kth]
 #   print ",{},{},{},{},{}".format(now - base_time,
 #     a - base_a, b - base_b, c - base_c, d - base_d), ;
 # print ""
  base_L = L
  time.sleep(1.0)
