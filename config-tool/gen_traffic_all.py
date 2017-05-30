import sys
import random
from functools import partial
from multiprocessing.dummy import Pool
from subprocess import call
from subprocess import Popen

server_ip = "192.168.124.2"
server_port = 7777
duration = 15
max_bandwidth = 160
bandwidth = 32  #4*1024*1024*8
pool_size = 4


# IP_ADDR, PORT, BANDWIDTH, NUM_TESTS, DURATION
template = "python gen_one_conn.py {} {} {} NO {}"
template_ = "python gen_one_conn.py {} {} {} RUN {}"

def get_commands(template, ps, cuts):
  configs = zip(ps, cuts)
  commands = []
  for (p, cut) in configs:

    ts, last = [], 0
    for i in range(len(cut)):
      ts.append(cut[i] - last)
      last = cut[i]

    str = " ".join("{}".format(t) for t in ts)
#    if (p % 4 == 0 or p % 4 == 3):
#      command = template.format(server_ip, p, bandwidth * 2, str)
#    else:
    command = template.format(server_ip, p, bandwidth, str)
    commands.append(command)
  return commands


def run(commands, num):
  print num
  print "\n".join("{}".format(k) for k in commands)

  pool = Pool(num)
  for i, returncode in enumerate(pool.imap(partial(call, shell=True), commands)):
   if returncode != 0:
     print "Process {} failed".format(i)




client_port = []
if (len(sys.argv) < 3):
  print "gen_traffic_all $server_port_start $num_server_ports $num_tests/process duration RealTraffic[Y/N] [seed]"

else:
  port_begin = int(sys.argv[1])
  port_num = int(sys.argv[2])
  num_tests = int(sys.argv[3])
  duration = int(sys.argv[4])
  if (sys.argv[5] == "Y"):
    template = template_
  if (len(sys.argv) > 6):
    seed = int(sys.argv[6])
    random.seed(seed)

  pool_size = port_num
  bandwidth = max_bandwidth / port_num
  port_end = port_begin + port_num
  ps = range(port_begin, port_end)
  ds = [duration] * port_num

  cuts = []
  config = zip(ps, ds)
  for p, d in config:
    before = d / 9 * 4
    middle = d / 9
    after = d - before - middle
    cut = random.sample(range(before, before + middle), num_tests - 1)
    cut.sort()
    cut.append(d)
    cuts.append(cut)
    if (p % 4 == 1 or p % 4 == 2):
      print p, cut[0]

  commands = get_commands(template, ps, cuts)
  run(commands, pool_size)
