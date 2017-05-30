import sys
from string import maketrans
from collections import deque




## Apply wildcard masking to IP or Port
USE_IP = True
## Allows referring device using ID not IP
DEVICE_ID = True


# rewrite the pattern
def new_string(pattern, intab, outtab):
  transtab = maketrans(intab, outtab)
  return pattern.translate(transtab)


# translate ip to binary
def ip2int(ip):
  ips = ip.rsplit('.')
  l = 0
  for v in ips:
    l = (l << 8) + int(v)
  return l;

def ip2binary(ip):
  return bin(ip2int(ip))[2:]

def int2ip(v):
  return "{0}.{1}.{2}.{3}".format((v >> 24) & 0xff,
                                  (v >> 16) & 0xff,
                                  (v >> 8) & 0xff,
                                  v & 0xff)

def binary2ip(b):
  v = int(b, 0)
  return int2ip(v)


class RuleTranslator():

  HW = "HSW"
  SW = "SSW"
  BE = "BE"

  def __init__(self, hw_rules, sw_rules):
    self.hw_rules = hw_rules
    self.sw_rules = sw_rules
    pass

class AbstractRuleTranslator(RuleTranslator):
  def __init__(self, hw_rules, sw_rules):
    RuleTranslator.__init__(self, hw_rules, sw_rules)


  def translate_rules(self,
                      dev_id,
                      downstream_ids,
                      upstream_ids,
                      dev_class,
                      vip_info):
     if (dev_class == RuleTranslator.HW):
       return self.hw_rules
     elif (dev_class == RuleTranslator.SW):
       return self.sw_rules
     else:
       return []


class OfRuleTranslator(RuleTranslator):

  TCP_PROTO = 6
  UDP_PROTO = 17

  def __init__(self, hw_rules, sw_rules):
    RuleTranslator.__init__(self, hw_rules, sw_rules)
    self.template = "\"vip\":\"{0}\",\"sip\":\"{1}\",\"pattern\":\"{2}\""

  def translate_rules(self,
                      dev_id,
                      downstream_ids,
                      upstream_ids,
                      dev_class,
                      vip_info):

    print dev_id, dev_class
    if (dev_class == RuleTranslator.HW):
      target_rules = self.hw_rules
    elif (dev_class == RuleTranslator.SW):
      target_rules = self.sw_rules
    else:
      return []

    config = []
    for (pattern, dev_id, vip_id) in target_rules:
      mask_str = new_string(pattern, "*01", "011")
      value_str = new_string(pattern, "*01", "001")
      mask = int(mask_str, 2)
      value = int(value_str, 2)
      sip = int2ip(value)
      (vip_ip, vip_port, vip_proto) = vip_info[vip_id]

      match = self.template.format(vip_ip, sip, hex(mask))
      if (vip_port > 0):
        match = match + ",\"port\":\"{0}\"".format(vip_port)
      if (vip_proto == OfRuleTranslator.TCP_PROTO):
        match = match + ",\"proto\":\"tcp\""
      elif (vip_proto == OfRuleTranslator.UDP_PROTO):
        match = match + ".\"proto\":\"udp\""

      config.append((match, dev_id, vip_id))

    return config



class U32RuleTranslator(RuleTranslator):

  def __init__(self, hw_rules, sw_rules):
    RuleTranslator.__init__(self, hw_rules, sw_rules)

  def translate_rules(self,
                      dev_id,
                      downstream_ids,
                      upstream_ids,
                      dev_class,
                      vip_info):
    vipid2ip = dict()
    for vip_id in vip_info:
      vipid2ip[vip_id] = vip_info[vip_id][0]

    if (dev_class == RuleTranslator.HW):
      return self.__translate_hw_rules(vipid2ip)
    elif (dev_class == RuleTranslator.SW):
      return self.__translate_sw_rules(dev_id, downstream_ids, vipid2ip)
    elif (dev_class == RuleTranslator.BE):
      return self.__translate_be_rules(dev_id, upstream_ids, vipid2ip)
    else: 
      return None

  # currently each sw hold both hw rules + sw rules
  def __translate_sw_rules(self, sw_id, be_ids, vipid2ip):
    res = []
    ## this is a HACK, SSW only forwards to the first BE
    be_id = be_ids[0]
    for (pattern, dev_id, vip_id) in (self.hw_rules + self.sw_rules):
       u32_pattern = U32RuleTranslator.pattern2u32(pattern,
                                                   vipid2ip[vip_id],
                                                   False)
       if (dev_id == sw_id):
         res.append((u32_pattern, be_id, vip_id))
       else:
         res.append((u32_pattern, dev_id, vip_id))
    return res


  ## may not work for non-tracking
  def __translate_be_rules(self, be_id, sw_ids, vipid2ip):
    res = []
    sw_id = sw_ids[0]
    for (pattern, dev_id, vip_id) in (self.hw_rules + self.sw_rules):
       u32_pattern =  U32RuleTranslator.pattern2u32(pattern,
                                                    vipid2ip[vip_id],
                                                    True)
       # extract the signal rules
       if (dev_id == sw_id):
         res.append((u32_pattern, sw_id, vip_id))
    return res

  def __translate_hw_rules(self, vipid2ip):
    res = []
    for (pattern, dev_id, vip_id) in self.hw_rules:
       u32_pattern = U32RuleTranslator.pattern2u32(pattern,
                                                   vipid2ip[vip_id],
                                                   False)
       res.append((u32_pattern, dev_id, vip_id))
    return res
    


  # translate one config line to a u32 rule
  # src is the src_ip_pattern, dst is the vip_ip, 
  # via is the endpoint of the tunnel
  @staticmethod
  def pattern2u32(src, vip, reversed = False):

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
    dst = ip2binary(vip)
    src_mask_hex, src_value_hex = get_mask_value(src)
    dst_mask_hex, dst_value_hex = get_mask_value(dst)

    # protocol = "6&0xFF=0x0:0xF1"
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
        src_mask_hex,
        src_value_hex,
        dst_mask_hex,
        dst_value_hex);

    else: ## now use dst_port
      if (reversed):
        u32_p = "\"{} && 12&{}={} && 0>>22&0x3C@0>>16&{}={}\"".format(
          protocol,
          src_mask_hex,
          src_value_hex,
          dst_mask_hex,
          dst_value_hex);
      else:
        u32_p = "\"{} && 0>>22&0x3C@0&{}={} && 16&{}={}\"".format(
          protocol,
          src_mask_hex, src_value_hex,
          dst_mask_hex, dst_value_hex);

    return u32_p
