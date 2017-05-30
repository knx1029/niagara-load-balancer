import sys
from string import maketrans
from collections import deque

HW_ID = 0
SW_ID = 1
BE_ID = -1
## Apply wildcard masking to IP or Port
USE_IP = False
## Allows referring device using ID not IP
DEVICE_ID = True

## read the mapping from vip id -> ip
def read_vip2ip(filename):
  file = open(filename, 'r')
  vip2ip = dict()

  while (True):
    str = file.readline()
    if (str == None or len(str) == 0):
      break
    strs = str.rsplit(' ')
    id, ip = int(strs[0]), strs[1]
    vip2ip[id] = ip

  file.close()
  return vip2ip



## read the mapping from device id -> ip, 
## states (is be/sw/hw)
## hard-coded require one sw to have a
## default rule sending to all be
def read_id2ip(filename):
  file = open(filename, 'r')
  id2ip = dict()

  hw_id = 0
  sw_id = []
  while (True):
    str = file.readline()
    if (str == None or len(str) == 0):
      break
    strs = str.rsplit(' = ')
    state = strs[0]
    n = int(strs[1])
    for i in range(n):
      str = file.readline()
      strs = str[:-1].rsplit(' ')
      id, ip = int(strs[0]), strs[1]
      ## Allows referring device using ID not IP
      if (DEVICE_ID):
        id2ip[id] = (id, state)
      else:
        id2ip[id] = (ip, state)
      if (state_is_sw(state)):
        default_be = int(strs[-1])
        sw_id.append((id, default_be))
      elif (state_is_hw(state)):
        hw_id = id

  file.close()
  return id2ip, hw_id, sw_id

## read the config of hardware rules and software rules
def read_config(filename, hw_id, sw_id):
  def config_cmp(a, b):
    return -a.count('*') + b.count('*')

  file = open(filename, 'r')

  config = dict()
  hw_config, sw_config, be_config = [], [], []
  config_is_hw = False
  ## generate be config, which is a reverse
  while (True):
    s = file.readline()
    if (s == None or len(s) == 0):
      break
    # a new rule list starts
    if '#' in s:
      if ('root' in s):
        config_is_hw = True
      else:
        config_is_hw = False
        index = int(s.rsplit('switch ')[-1])
        dev_id, _ = sw_id[index]
    # continue appending
    else:
      tokens = s.rsplit(', ')
      x = []
      for token in tokens:
        xs = token.rsplit(':')
        x.append(xs[1])
      pattern = x[0]
      vip_id = int(x[2])

      index = int(x[1])
      via_id, _ = sw_id[index]
    
      sw_config.append((pattern, via_id, vip_id))
      be_config.append((pattern, via_id, vip_id))
      if (config_is_hw):
        hw_config.append((pattern, via_id, vip_id))

  
  file.close()
  hw_config.sort(cmp = config_cmp)
  sw_config.sort(cmp = config_cmp)
  be_config.sort(cmp = config_cmp)

  config[HW_ID] = hw_config
  config[SW_ID] = sw_config
  config[BE_ID] = be_config


  return config


def write_rule(filename, version, rules, id2ip):

  file = open(filename, 'w')
  file.write('version = {}\n'.format(version))

  for dev_id in rules:
    print dev_id, len(rules[dev_id])

  for id in id2ip:
    ip, state = id2ip[id]

    if (state_is_be(state)):
      dev_rules = rules[BE_ID]
    else:
      dev_rules = rules[id]
      pass

    file.write('switch = {}\n'.format(ip))

    file.write('rules = {}\n'.format(len(dev_rules)))
    for r in dev_rules:
      file.write('{}\n'.format(r))
      print r
    file.write('\n')

  file.close()



# check state
def state_is_be(state):
 return ("be" in state.lower())

def state_is_sw(state):
 return ("sw" in state.lower())

def state_is_hw(state):
 return ("hw" in state.lower())


# translate ip to binary
def ip_to_binary(ip):
  ips = ip.rsplit('.')
  l = 0
  for v in ips:
    l = (l << 8) + int(v)
  return bin(l)[2:]


# translate one config line to a u32 rule
# src is the src_ip, dst is the vip_ip, 
# via is the endpoint of the tunnel
def config2rule(src, dst, via, is_be, reversed = False):

  # rewrite the pattern
  def new_string(pattern, intab, outtab):
    transtab = maketrans(intab, outtab)
    return pattern.translate(transtab)


  # get u32 mask and value from the wildcard pattern
  def get_mask_value(wildcard):
    mask_str = new_string(wildcard, "*01", "011")
    value_str = new_string(wildcard, "*01", "001")

    mask = int(mask_str, 2)
    value = int(value_str, 2)

    mask_hex = hex(mask)
    value_hex = hex(value)

    return mask_hex, value_hex

  ## logic starts here
  src_mask_hex, src_value_hex = get_mask_value(src)
  dst_mask_hex, dst_value_hex = get_mask_value(dst)

#  protocol = "6&0xFF=0x0:0xF1"
# TCP?
  protocol = "6&0xFF=0x6"

## 12 : srcIP
## 16 : dstIP
##    : srcPort
##   : dstPort

  u32_p = None
  if (USE_IP):
    u32_p = "\"{} && 12&{}={} && 16&{}={}\"".format(
                           protocol,
                           src_mask_hex, src_value_hex,
                           dst_mask_hex, dst_value_hex);
  else: ## now use dst_port
    if (reversed):
       u32_p = "\"{} && 12&{}={} && 0>>22&0x3C@0>>16&{}={}\"".format(
                          protocol,
                          src_mask_hex, src_value_hex,
                          dst_mask_hex, dst_value_hex);

#      u32_p = "\"{} && 12&{}={} && 20>>16&{}={}\"".format(
#                           protocol,
#                           src_mask_hex, src_value_hex,
#                           dst_mask_hex, dst_value_hex);
    else:
       u32_p = "\"{} && 0>>22&0x3C@0&{}={} && 16&{}={}\"".format(
                           protocol,
                           src_mask_hex, src_value_hex,
                           dst_mask_hex, dst_value_hex);
#      u32_p = "\"{} && 20&{}={} && 16&{}={}\"".format(
#                           protocol,
#                           src_mask_hex, src_value_hex,
#                           dst_mask_hex, dst_value_hex);


  if (is_be):
    r = "iptables -m u32 --u32 {} -j SEND_TO {}".format(u32_p, via)
  else:
    r = "iptables -m u32 --u32 {} -j REDIRECT_TO {}".format(u32_p, via)

  return r


## translate the entire config
def translate(config, id2ip, vip2ip, hw_id, sw_id):
  rules = dict()

  ## translate hw config
  hw_config = config[HW_ID]
  hw_rules = []
  rules[hw_id] = hw_rules
  for (src, via_id, vip_id) in hw_config:
   # get ip and state of via
   via_ip , via_state = id2ip[via_id]
   # map vip to pattern
   vip_ip = vip2ip[vip_id]
   dst = ip_to_binary(vip_ip)
   r = config2rule(src, dst, via_ip, False)
   hw_rules.append(r)

  ## translate be config
  be_config = config[BE_ID]
  be_rules = []
  rules[BE_ID] = be_rules
  for (src, via_id, vip_id) in be_config:
    # get ip and state of via
    via_ip , via_state = id2ip[via_id]
    # map vip to pattern
    vip_ip = vip2ip[vip_id]
    dst = ip_to_binary(vip_ip)
    ## reverse it
    r = config2rule(dst, src, via_ip, False, True)
    be_rules.append(r)

  # customize sw config
  sw_config = config[SW_ID]
  for (id, be) in sw_id:
    sw_rules = []
    rules[id] = sw_rules
    for (src, via_id, vip_id) in sw_config:
      # map vip to pattern
      vip_ip = vip2ip[vip_id]
      dst = ip_to_binary(vip_ip)

      # get ip and state of via
      # if via_id is itself, rewrite to default be
      if via_id == id:
        via_ip , via_state = id2ip[be]
        r = config2rule(src, dst, via_ip, True)
      else:
        via_ip , via_state = id2ip[via_id]
        r = config2rule(src, dst, via_ip, False)
      sw_rules.append(r)

  return rules


## main

args = sys.argv
version = int(args[1])
config_input = args[2]
map_input = args[3]
vip_input = args[4]
rule_output = args[5]

id_to_ip, hw_id, sw_id = read_id2ip(map_input)
config = read_config(config_input, hw_id, sw_id)
vip_to_ip = read_vip2ip(vip_input)
rules = translate(config, id_to_ip, vip_to_ip, hw_id, sw_id)
write_rule(rule_output, version, rules, id_to_ip)

