import sys
import random
from subprocess import call
from subprocess import Popen

RUN = False

def run(cmd):
  print cmd

  exitcode = 0
  if (RUN):
    exitcode = call(cmd, shell=True)
  return exitcode

# IP_ADDR, PORT, BANDWIDTH, TOTAL_DURATION, NUM_TESTS
server_ip = sys.argv[1]
server_port = sys.argv[2]
bandwidth = sys.argv[3]
RUN = (sys.argv[4] == "RUN")
template = "iperf3 -c {} -p {} -b {}M -t {}"

ts = []
for str in sys.argv[5:]:
  ts.append(int(str))

#print server_port, ts

exitcode = 1
last = 0
for t in ts:
    cmd = template.format(server_ip, server_port, bandwidth, t)
    exitcode = run(cmd)



#template = "netperf -H {} -p {},{{}} -t TCP_STREAM -l {} -- -m 1024"
#template = "netperf -H {} -p {},{{}} -t TCP_RR -l {} {}"
