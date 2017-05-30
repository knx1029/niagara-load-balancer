#import subprocess
import os
import sys

name2ip = {
"hwswitch": "10.99.88.80",
"sswitch1": "10.99.88.81",
"sswitch2": "10.99.88.82",
"be1":      "10.99.88.83",
"be2":      "10.99.88.84"}


def is_sw(name):
  return ("sswitch" in name)

def is_hw(name):
  return ("hwswitch" in name)

def is_be(name):
  return ("be" in name)

def is_switch(name):
  return is_sw(name) or is_hw(name)

def run_cmd(cmd):
  print "Running ", cmd
  ret = os.system(cmd)
  if (ret != 0):
    exit(ret)


## main

my_name = sys.argv[1]
op = sys.argv[2]
exe_file = "./bin/ng-vlan" #"/home/loadbalancer/bin/ng-vlan"

print "My name is {}, ip = {}".format(my_name, name2ip[my_name])

# connect all sw through tunnel version
if (op == 'connsw' and (is_sw(my_name) or is_hw(my_name))):
  vlan = int(sys.argv[3])
  # add vlan
  cmd = "sudo {} addvlan eth0 {}".format(exe_file, vlan)
  run_cmd(cmd)
  # add tunnel
  for name in name2ip:
    if (name != my_name and (is_sw(name) or is_hw(name))):
      ip = name2ip[name]
      cmd = "sudo {} addtunnel eth0 {} {}".format(exe_file, vlan, ip)
      run_cmd(cmd)

# disconnect all sw version tunnel
elif (op == 'disconnsw' and (is_sw(my_name) or is_hw(my_name))):
  vlan = int(sys.argv[3])
  # remove tunnel
  for name in name2ip:
    if (name != my_name and (is_sw(name) or is_hw(name))):
      ip = name2ip[name]
      cmd = "sudo {} deltunnel eth0 {} {}".format(exe_file, vlan, ip)
      run_cmd(cmd)
  # remove vlan
  cmd = "sudo {} delvlan eth0 {}".format(exe_file, vlan)
  run_cmd(cmd)

# connect sw to be
elif (op == 'addbe' and (is_sw(my_name) or is_be(my_name))):
  for name in name2ip:
    ip = name2ip[name]
    # from sw
    if is_sw(my_name) and is_be(name):
      # add backend
      cmd = "sudo {} addbackend eth0 {}".format(exe_file, ip)
      run_cmd(cmd)
    # from sw
    elif is_be(my_name) and is_sw(name):
      # add tunnel to sw
      cmd = "sudo {} addbetunnel eth0 {}".format(exe_file, ip)
      run_cmd(cmd)

# disconnect sw and be
elif (op == 'delbe' and (is_sw(my_name) or is_be(my_name))):
  for name in name2ip:
    ip = name2ip[name]
    # from sw
    if is_sw(my_name) and is_be(name):
      # add backend
      cmd = "sudo {} delbackend eth0 {}".format(exe_file, ip)
      run_cmd(cmd)
    # from sw
    elif is_be(my_name) and is_sw(name):
      # add tunnel to sw
#      cmd = "sudo {} delbetunnel eth0 {}".format(exe_file, ip)
      cmd = "sudo {} deltunnel eth0 0 {}".format(exe_file, ip)
      run_cmd(cmd)

# install routes on devices
elif (op == 'installroutes'):
  rule_file = sys.argv[3]
  if (is_be(my_name)):
    pass
#    cmd = "sudo {} installberoutes eth0 {}".format(exe_file, rule_file)
#    run_cmd(cmd)
  else:
    cmd = "sudo iptables -D PREROUTING -j NG_tcp_signals -t mangle"
    run_cmd(cmd)
    cmd = "sudo {} installroutes eth0 {}".format(exe_file, rule_file)
    run_cmd(cmd)

# install routes on devices
elif (op == 'installberoutes'):
  rule_file = sys.argv[3]
  if (is_be(my_name)):
    cmd = "sudo {} installberoutes eth0 {}".format(exe_file, rule_file)
    run_cmd(cmd)
    cmd = "sudo iptables -D PREROUTING -j NG_tcp_signals -t mangle"
    run_cmd(cmd)
    cmd = "sudo iptables -I PREROUTING -j NG_tcp_signals -t mangle"
    run_cmd(cmd)
  else:
    pass
#    cmd = "sudo {} installroutes eth0 {}".format(exe_file, rule_file)
#    run_cmd(cmd)


# update version
elif (op == 'updatevipversion' and is_hw(my_name)):
  vip_ip = sys.argv[3]
  old_version = int(sys.argv[4])
  version = int(sys.argv[5])
  cmd = "sudo {} updatevipversion {} {} {}".format(
            exe_file, vip_ip, old_version, version);
  run_cmd(cmd)

else:
  print "possible op is connsw|disconnsw|addbe|delbe|installroutes|updatevipversion"
