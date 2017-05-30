import sys
import threading

import socket
import struct
import ast
from argparse import ArgumentParser

from ryu.exception import OFPUnknownVersion
from ryu.exception import RyuException
from ryu.lib import dpid as dpid_lib
from ryu.lib import hub
from ryu.lib import mac as mac_lib
from ryu.lib import addrconv
from ryu.lib.packet import arp
from ryu.lib.packet import ethernet
from ryu.lib.packet import icmp
from ryu.lib.packet import ipv4
from ryu.lib.packet import packet
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.lib.packet import vlan
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_2
from ryu.ofproto import ofproto_v1_3

## import algorithm directory
import os, sys, inspect
paths = ["../algorithm/rule_lib"]
for relative_path in paths:
  cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], relative_path)))
  if cmd_subfolder not in sys.path:
#     print "import relative directory: ", cmd_subfolder
     sys.path.insert(0, cmd_subfolder)

from svip_solver import *
from mvip_solver import *

#import vip_rule
#from vip_rule.hw_layers import *
#from vip_rule.group import *
#from vip_rule.update import *

#USE_HUB_THREAD = False
USE_HUB_THREAD = True


UINT16_MAX = 0xffff
UINT32_MAX = 0xffffffff
UINT64_MAX = 0xffffffffffffffff

ETHERNET = ethernet.ethernet.__name__
VLAN = vlan.vlan.__name__
IPV4 = ipv4.ipv4.__name__
ARP = arp.arp.__name__
ICMP = icmp.icmp.__name__
TCP = tcp.tcp.__name__
UDP = udp.udp.__name__

MAX_SUSPENDPACKETS = 50  # Threshold of the packet suspends thread count.

ARP_REPLY_TIMER = 2  # sec
OFP_REPLY_TIMER = 1.0  # sec
CHK_ROUTING_TBL_INTERVAL = 30 #1800  # sec

SWITCHID_PATTERN = dpid_lib.DPID_PATTERN + r'|all'
VLANID_PATTERN = r'[0-9]{1,4}|all'

VLANID_NONE = 0
VLANID_MIN = 2
VLANID_MAX = 4094

## convert cookie and rule_id/ address_id
COOKIE_DEFAULT_ID = 0
COOKIE_ID_LEN = 32
COOKIE_TYPE_LEN = 8
COOKIE_ID_MASK = UINT32_MAX # (0 << COOKIE_ID_LEN) - 1
COOKIE_TYPE_MASK = (0 << COOKIE_TYPE_LEN) - 1
COOKIE_SHIFT_TYPE = COOKIE_ID_LEN
COOKIE_SHIFT_VLANID = COOKIE_ID_LEN + COOKIE_TYPE_LEN
COOKIE_TYPE_ADDRESSID = 0
COOKIE_TYPE_RULEID = 1



DEFAULT_ROUTE = '0.0.0.0/0'
IDLE_TIMEOUT = 1800  # sec
DEFAULT_TTL = 64


REST_COMMAND_RESULT = 'command_result'
REST_RESULT = 'result'
REST_DETAILS = 'details'
REST_OK = 'success'
REST_NG = 'failure'
REST_ALL = 'all'

REST_SWITCHID = 'switch_id'
REST_VLANID = 'vlan_id'

REST_NW = 'internal_network'

## ofp
REST_OF_TABLE = 'of_table'

## address
REST_ADDRESSID = 'address_id'
REST_ADDRESS = 'address'

REST_ARP = 'arp'

## routing
REST_ECMP_GROUP = 'ecmp_group'
REST_FLOW_GROUP = 'flow_group'
REST_FG2EG = 'flow2ecmp'
REST_RULES = 'rules'
REST_INSTALL_RULES = 'install_rules'
REST_CLEAR_RULES = 'clear_rules'

REST_ECMP_GATEWAY = 'gateways'
REST_ECMP_ID = 'ecmp_id'
REST_FLOW_GROUP_ID = 'fg_id'
REST_FG_PRIORITY = 'priority'
REST_RULEID = 'rule_id'
REST_DESTINATION = 'destination'
REST_GATEWAY = 'gateway'

REST_SIP = 'sip'
REST_DIP = 'dip'
REST_SPORT = 'sport'
REST_DPORT = 'dport'
REST_IP_PROTO = 'ip_proto'
REST_NEW_SIP = 'new_sip'
REST_NEW_DIP = 'new_dip'
REST_NEW_SPORT = 'new_sport'
REST_NEW_DPORT = 'new_dport'
REST_RETURN_GW = 'return_gw'

PRIORITY_VLAN_SHIFT = 1 << 15
PRIORITY_NORMAL = 0
PRIORITY_ARP_HANDLING = 1
PRIORITY_DEFAULT_ROUTING = 1
PRIORITY_MAC_LEARNING = 2
PRIORITY_STATIC_ROUTING = 2
PRIORITY_IMPLICIT_ROUTING = 3
PRIORITY_L2_SWITCHING = 4
PRIORITY_IP_HANDLING = 5


## this gives the real priority of rules
## across flow groups and ecmp groups
PRIORITY_BASE_SHIFT = 7
FG_PRIORITY_SHIFT = PRIORITY_BASE_SHIFT + 1
RULE_PRIORITY_MASK = (1 << PRIORITY_BASE_SHIFT) - 1
MAX_NUM_RULES = (1 << PRIORITY_BASE_SHIFT)
MAX_FG_PRIORITY = (1 << (16 - FG_PRIORITY_SHIFT - 1)) - 1


class NotFoundError(RyuException):
    message = 'Router SW is not connected. : switch_id=%(switch_id)s'


class CommandFailure(RyuException):
    pass

def check_dict_type(d, key_type, value_type, *args):
    if (not (type(d) is dict)):
        return False
    for k, v in d.items():
        if (type(k) is not key_type) or (type(v) is not value_type):
            raise ValueError()
        if (value_type == tuple):
            if (not check_tuple_type(v, *args)):
                return False
    return True

def check_tuple_type(d, *args):
    if (type(d) is not tuple):
        return False
    if (len(d) != len(args)):
        return False
    for i in range(len(args)):
        if (d[i] != None) and (type(d[i]) is not args[i]):
            return False
    return True

def check_list_type(l, item_type):
    if (not (type(l) is list)):
        return False
    for i in l:
        if (type(i) is not item_type):
            raise ValueError()
    return True

## from socket -> addrconv
def ip_addr_aton(ip_str, err_msg = None):
    try:
        if (ip_str is None) or (len(ip_str) == 0):
            return ip_str
        return addrconv.ipv4.bin_to_text(socket.inet_aton(ip_str))
    except (struct.error, socket.error) as e:
        if err_msg is not None:
            e.message = '%s %s' % (err_msg, e.message)
        raise ValueError(e.message)

## from addrconv -> socket
def ip_addr_ntoa(ip):
    if (ip is None):
        return ip
    if (type(ip) is str) and (len(ip) == 0):
        return ip
    return socket.inet_ntoa(addrconv.ipv4.text_to_bin(ip))


def prefix_mask_ntob(prefix_len, err_msg = None):
    try:
        return (UINT32_MAX << (32 - prefix_len)) & UINT32_MAX
    except ValueError:
        msg = 'illegal netmask'
        if err_msg is not None:
            msg = '%s %s' % (err_msg, msg)
        raise ValueError(msg)


def ipv4_apply_prefix_mask(address,
                           prefix_len,
                           err_msg = None):

    mask_int = prefix_mask_ntob(prefix_len, err_msg)
    return ipv4_apply_mask(address,
                           mask_int,
                           err_msg)

def ipv4_apply_mask(address,
                    mask_int,
                    err_msg = None):
    import itertools

    assert isinstance(address, str)
    assert isinstance(mask_int, int)
    address_int = ipv4_text_to_int(address)
    return ipv4_int_to_text(address_int & mask_int)
                        

def ipv4_int_to_text(ip_int):
    assert isinstance(ip_int, (int, long))
    return addrconv.ipv4.bin_to_text(struct.pack('!I', ip_int))


def ipv4_text_to_int(ip_text):
    if ip_text == 0:
        return ip_text
    assert isinstance(ip_text, str)
    return struct.unpack('!I', addrconv.ipv4.text_to_bin(ip_text))[0]

## parse ip address with wildcard mask
## returns ip, masked_ip, mask in order
def nw_addr_aton(nw_addr, err_msg = None):
    try:
        ip_mask = nw_addr.split('&')
        if (len(ip_mask) != 1) and (len(ip_mask) != 2):
            raise ValueError('invalid masked ip')

        addr = ip_addr_aton(ip_mask[0],
                            err_msg = err_msg)
        netmask = int(ip_mask[1], 0)
        nw_addr = ipv4_apply_mask(addr,
                                  netmask,
                                  err_msg)
        return addr, nw_addr, netmask

    except ValueError as e:
        if err_msg is not None:
            e.message = '%s %s' % (err_msg, e.message)
        raise ValueError(e.message)

## parse ip address with prefix mask
## returns ip, masked_ip, prefix_len in order
def nw_addr_prefix_aton(nw_addr, err_msg = None):
    try:
        ip_mask = nw_addr.split('/')
        if (len(ip_mask) != 1) and (len(ip_mask) != 2):
            raise ValueError('invalid masked ip')

        addr = ip_addr_aton(ip_mask[0],
                            err_msg = err_msg)
        prefix_len = 32
        if len(ip_mask) == 2:
            prefix_len = int(ip_mask[1])
        if (prefix_len < 0) or (prefix_len > 32):
            raise ValueError('illegal netmask')

        nw_addr = ipv4_apply_prefix_mask(addr,
                                         prefix_len,
                                         err_msg)
        return addr, nw_addr, prefix_len
    except ValueError as e:
        if err_msg is not None:
            e.message = '%s %s' % (err_msg, e.message)
        raise ValueError(e.message)




## parsing
def parse_args(str):
    parser = ArgumentParser(description = 'run simulation')

    parser.add_argument('-mode', action = 'store',
                        choices = ['single_vip', 'multi_vip']);
#                        choices = ['single_vip', 'vip_stair', 'update',
#                                   'multi_vip', 'grouping'],
#                        help='modes: single_vip, vip_stair, update,'
#                        + 'multi_vip, grouping');
    parser.add_argument('-error', action = 'store', type = float, default = 0.001)
    parser.add_argument('-churn', action = 'store', type = float, default = 0.1)
#    parser.add_argument('-group', action = 'store', type = int, default = 100)
    parser.add_argument('-ecmp', action = 'store', default = 'max',
                        help='ecmp:max, none, #ecmp_rules');
    parser.add_argument('-heu', action = 'store_true')
    parser.add_argument('-bf', action = 'store_true')

    args = parser.parse_args(str)

    return args

## this gives parameters for rule generation algorithm
def translate_ecmp_arg(n_weights, arg):
    if arg == 'max':
        K = int(math.log(n_weights, 2.0))
        M = (1<<K)
        return (0, K, M)
    elif arg == 'none':
        return None
    else:
        M = int(arg)
        K = int(math.log(M, 2.0))
        return [(0, K, M)]


## call algorithm to generate rules for multiple vips
def solve_multi_vip(args, vips, c):

    ## Brute force or Heuristics
    algo_mode = BF
    if (args.heu):
        algo_mode = HEU
        
    ## construct ecmp metadata
    ecmp_info = translate_ecmp_arg(len(vips[0][2]), args.ecmp)
    
    ## run
    eps = args.error
    res = solve_two_layer_trees(vips, [c], eps, ecmp_info, algo_mode)
    c, (imb, root_rules), leaf_rules, _  = res[0]

    return root_rules, imb

## matches on L3 and L4 fields
## ip address are of addrconv type (string)
## ip mask are uint32
class Match:
    def __init__(self,
                 sip = 0,
                 sip_mask = 0,
                 dip = 0,
                 dip_mask = 0,
                 ip_proto = 0,
                 sport = 0,
                 dport = 0):
        self.m_sip = sip
        self.m_sip_mask = sip_mask
        self.m_dip = dip
        self.m_dip_mask = dip_mask
        self.m_ip_proto = ip_proto
        self.m_sport = sport
        self.m_dport = dport

    def __eq__(self, other):
        return ((self.m_sip == other.m_sip) and
                (self.m_dip == other.m_dip) and
                (self.m_sip_mask == other.m_sip_mask) and
                (self.m_dip_mask == other.m_dip_mask) and
                (self.m_ip_proto == other.m_ip_proto) and
                (self.m_sport == other.m_sport) and
                (self.m_dport == other.m_dport))

    def __str__(self):
        template = "sip={0}+sip_mask={1}+dip={2}+dip_mask={3}+proto={4}+sport={5}+dport={6}"

        return template.format(ip_addr_ntoa(self.m_sip),
                               hex(self.m_sip_mask),
                               ip_addr_ntoa(self.m_dip),
                               hex(self.m_dip_mask),
                               self.m_ip_proto,
                               self.m_sport,
                               self.m_dport)

    def set_ip_proto(self, proto_str):
        if proto_str == 'tcp':
            self.m_ip_proto = inet.IPPROTO_TCP
        elif proto_str == 'udp':
            self.m_ip_proto = inet.IPPROTO_UDP

    @staticmethod
    def parse_match(s):
        tokens = s.rsplit('+')
        for token in tokens:
            xs = token.rsplit('=')
            if (xs[0] == 'sip'):
                if (xs[1] == '0'):
                    sip = 0
                else:
                    sip = ip_addr_aton(xs[1])
            elif (xs[0] == 'dip'):
                if (xs[1] == '0'):
                    dip = 0
                else:
                    dip = ip_addr_aton(xs[1])
            elif (xs[0] == 'sip_mask'):
                sip_mask = int(xs[1], 0)
            elif (xs[0] == 'dip_mask'):
                dip_mask = int(xs[1], 0)
            elif (xs[0] == 'sport'):
                sport = int(xs[1], 0)
            elif (xs[0] == 'dport'):
                dport = int(xs[1], 0)
            elif (xs[0] == 'proto'):
                ip_proto = int(xs[1], 0)

        return Match(sip = sip,
                     sip_mask = sip_mask,
                     dip = dip,
                     dip_mask = dip_mask,
                     ip_proto = ip_proto,
                     sport = sport,
                     dport = dport)


    def reverse(self):
        r = Match(self.m_dip,
                  self.m_dip_mask,
                  self.m_sip,
                  self.m_sip_mask,
                  self.m_ip_proto,
                  self.m_dport,
                  self.m_sport)
        return r

    def id(self):
        a = ipv4_text_to_int(self.m_sip)
        am = self.m_sip_mask
        b = ipv4_text_to_int(self.m_dip)
        bm = self.m_dip_mask
        c = self.m_ip_proto
        d = (self.m_sport << 16) + self.m_dport
        return "%s&%s-%s&%s-%s-%s" % (a&am, am, b&bm, bm, c, d)

    def match(self,
              sip = 0,
              dip = 0,
              ip_proto = 0,
              sport = 0,
              dport = 0):
        matched = True
        if (matched and sip): 
            if (ipv4_apply_mask(sip, self.m_sip_mask) != self.m_sip):
                matched = False
        if (matched and dip):
            if (ipv4_apply_mask(dip, self.m_sip_mask) != self.m_dip):
                matched = False
        if (matched and self.m_ip_proto != ip_proto):
            if (ip_proto == 0 or self.m_ip_proto != 0):
                matched = False
        if (matched and self.m_sport != sport):
            if (sport == 0 or self.m_sport != 0):
                matched = False
        if (matched and self.m_dport != dport):
            if (dport == 0 or self.m_dport != 0):
                matched = False
        return matched

## action includes: routing decision and rewrite L2/L3 header fields
class Action:
    def __init__(self,
                 gateway = 0,
                 sip = 0,
                 dip = 0,
                 sport = 0,
                 dport = 0):
        self.m_gateway = gateway
        self.m_sip = sip
        self.m_dip = dip
        self.m_sport = sport
        self.m_dport = dport

    def __eq__(self, other):
        return ((self.m_gateway == other.m_gateway) and
                (self.m_sip == other.m_sip) and
                (self.m_dip == other.m_dip) and
                (self.m_sport == other.m_sport) and
                (self.m_dport == other.m_dport))

    def __str__(self):
        template = "gateway={0}+sip={1}+dip={2}+sport={3}+dport={4}"
        return template.format(self.m_gateway,
                               self.m_sip,
                               self.m_dip,
                               self.m_sport,
                               self.m_dport)

    @staticmethod
    def parse_action(s):
        tokens = s.rsplit('+')
        for token in tokens:
            xs = token.rsplit('=')
            if (xs[0] == 'gateway'):
                if (xs[1] == '0'):
                    gateway = 0
                else:
                    gateway= ip_addr_aton(xs[1])
            elif (xs[0] == 'sip'):
                if (xs[1] == '0'):
                    sip = 0
                else:
                    sip = ip_addr_aton(xs[1])
            elif (xs[0] == 'dip'):
                if (xs[1] == '0'):
                    dip = 0
                else:
                    dip = ip_addr_aton(xs[1])
            elif (xs[0] == 'sport'):
                sport = int(xs[1], 0)
            elif (xs[0] == 'dport'):
                dport = int(xs[1], 0)

        return Action(gateway = gateway,
                      sip = sip,
                      dip = dip,
                      sport = sport,
                      dport = dport)

## the stats of each cookie in OpenFlow table
class Stats:
    def __init__(self,
                 cookie,
                 duration,
                 npackets,
                 nbytes):
        self.m_cookie = cookie
        self.m_duration = duration
        self.m_npackets = npackets
        self.m_nbytes = nbytes

    def __str__(self):
        return "cookie={0},duration={1},npackets={2},nbytes={3}".format(
            hex(self.m_cookie),
            self.m_duration,
            self.m_npackets,
            self.m_nbytes)

    @staticmethod
    def parse_stats(s):
        tokens = s.rsplit(',')
        for token in tokens:
            xs = token.rsplit('=')
            if (xs[0] == 'cookie'):
                cookie = int(xs[1], 0)
            elif (xs[0] == 'duration'):
                duration = float(xs[1])
            elif (xs[0] == 'npackets'):
                npackets = int(xs[1], 0)
            elif (xs[0] == 'nbytes'):
                nbytes = int(xs[1], 0)
        return Stats(cookie, duration, npackets, nbytes)


## instance with a lock
class Lockable:
    def __init__(self):
        self.m_lock = threading.RLock()

    def lock(self):
        self.m_lock.acquire()

    def unlock(self):
        self.m_lock.release()
