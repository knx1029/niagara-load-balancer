from utils import *

import logging
import socket
import struct

import json
from webob import Response

from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import WSGIApplication
from ryu.base import app_manager
from ryu.controller import dpset
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER
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

class DumbFlow:
    def __init__(self,
                 flow_id,
                 cookie,
                 priority,
                 dl_type = 0,
                 dl_dst = 0,
                 dl_vlan = 0,
                 src_ip = 0,
                 src_ip_mask = UINT32_MAX,
                 src_port = 0,
                 dst_ip = 0,
                 dst_ip_mask = UINT32_MAX,
                 dst_port = 0,
                 ip_proto = 0,
                 idle_timeout = 0,
                 actions = None):
        self.flow_id = flow_id
        self.cookie = cookie
        self.priority = priority
        self.dl_type = dl_type
        self.dl_dst = dl_dst
        self.dl_vlan = dl_vlan
        self.src_ip = src_ip
        self.src_ip_mask = src_ip_mask
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_ip_mask = dst_ip_mask
        self.dst_port = dst_port
        self.ip_proto = ip_proto
        self.idle_timeout = idle_timeout
        self.actions = actions

    def __str__(self):
        msg1 = "flow_id=%d,cookie=0x%x,priority=0x%x" % (self.flow_id,
                                                         self.cookie,
                                                         self.priority)
        msg2 = "dl_type=%s,dl_dst=%s,dl_vlan=%s" % (self.dl_type,
                                                    self.dl_dst,
                                                    self.dl_vlan)
        msg3 = "src_ip=%s&0x%x,dst_ip=%s&0x%x" % (self.src_ip,
                                                  self.src_ip_mask,
                                                  self.dst_ip,
                                                  self.dst_ip_mask)
        msg4 = "ip_proto=%d, src_port=%d,dst_port=%d" % (self.ip_proto,
                                                         self.src_port,
                                                         self.dst_port)

        msg5 = "actions=%s" % str(self.actions)
        return ",".join([msg1, msg2, msg3, msg4, msg5])

class DumbMessage:
    def __init__(self, body = 0):
        self.body = body

class ScreenLogger:
    def __init__(self):
        self.on = True
        pass

    def turn_on(self):
        self.on = True

    def turn_off(self):
        self.on = False    

    def info(self, s, *args,**kwargs):
        if (self.on):
            print "INFO: ", (s % args), "with argument --",
            for key in kwargs:
                print "(%s:%s)" % (key, kwargs[key]),
            print "\n"

class Debugger:
    def __init__(self):
        self.on = True
        pass

    def turn_on(self):
        self.on = True

    def turn_off(self):
        self.on = False

    def info(self, s):
        if (self.on):
            print s

    def info_(self, s):
        if (self.on):
            print s,",",

class DumbOfproto:
    def __init__(self):
        self.OFPP_NORMAL = "OFPP_NORMAL"
        self.OFPP_CONTROLLER = "OFPP_CONTROLLER"


class DumbDatapath:
    def __init__(self, dpid):
        self.id = dpid
        self.ofproto = DumbOfproto()


## The basic OpenFlowController Wrap Class
class DumbOfCtl(Lockable):
                     
    def __init__(self, dp, logger, debugger):
        Lockable.__init__(self)
        self.dp = dp
        self.sw_id = {'sw_id': str(dp.id)}
        self.logger = logger
        self.debugger = debugger
        self.flow_id = 0
        self.flows = dict()

    def set_sw_config_for_ttl(self):
        self.debugger.info(">>set_sw_config_for_ttl<<")
        self.debugger.info("")
        # OpenFlow v1_2/1_3.
        pass

    # here src and dst ip are non-prefix masked
    # and it matches on all five tuples
    def set_flow(self,
                 cookie,
                 priority,
                 dl_type = 0,
                 dl_dst = 0,
                 dl_vlan = 0,
                 src_ip = 0,
                 src_ip_mask = UINT32_MAX,
                 src_port = 0,
                 dst_ip = 0,
                 dst_ip_mask = UINT32_MAX,
                 dst_port = 0,
                 ip_proto = 0,
                 idle_timeout = 0,
                 actions = None):
        self.debugger.info_(">>set_flow")
        self.debugger.info_("cookie=0x%x, priority=%s" % (cookie, priority))
        self.debugger.info_("dl_type=%s, dl_dst=%s, dl_vlan=%s" % (dl_type, dl_dst,dl_vlan))
        self.debugger.info_("src_ip=%s&%x, dst_ip=%s&%x" % (src_ip, src_ip_mask, dst_ip, dst_ip_mask))
        self.debugger.info_("ip_proto=%d, src_port=%d, dst_port=%d" % (ip_proto, src_port, dst_port))
        self.debugger.info_("idle_timeout=%d, actions=%s" % (idle_timeout, actions))
        self.debugger.info("<<")
        self.debugger.info("")

        with (self.m_lock):
            self.flow_id += 1
            flow = DumbFlow(self.flow_id,
                            cookie = cookie,
                            priority = priority,
                            dl_type = dl_type,
                            dl_dst = dl_dst,
                            dl_vlan = dl_vlan,
                            src_ip = src_ip,
                            src_ip_mask = src_ip_mask,
                            src_port = src_port,
                            dst_ip = dst_ip,
                            dst_ip_mask = dst_ip_mask,
                            dst_port = dst_port,
                            ip_proto = ip_proto,
                            idle_timeout = idle_timeout,
                            actions = actions)
            self.flows[flow.flow_id] = flow


    def set_routing_flow(self,
                         cookie,
                         priority,
                         out_port = None,
                         dl_vlan = 0,
                         src_ip = 0,
                         src_ip_mask = UINT32_MAX,
                         src_port = 0,
                         dst_ip = 0,
                         dst_ip_mask = UINT32_MAX,
                         dst_port = 0,
                         ip_proto = 0,
                         new_src_mac = 0,
                         new_dst_mac = 0,
                         new_src_ip = 0,
                         new_src_port = 0,
                         new_dst_ip = 0,
                         new_dst_port = 0,
                         idle_timeout = 0,
                         dec_ttl = False):
        self.debugger.info_(">>set_routing_flow")
        if out_port == None:
            self.debugger.info("out_port=None")
        else:
            self.debugger.info_("out_port=%s" % out_port)
        self.debugger.info_("new_src_mac=%s, new_dst_mac=%s" % (new_src_mac, new_dst_mac))
        self.debugger.info_("new_src_ip=%s, new_dst_ip=%s" % (new_src_ip, new_dst_ip))
        self.debugger.info_("new_src_port=%d, new_dst_port=%d" % (new_src_port, new_dst_port))
        self.debugger.info("<<")
        self.debugger.info("")

        actions = ["new_src_mac=%s" % new_src_mac,
                   "new_dst_mac=%s" % new_dst_mac,
                   "new_src_ip=%s" % new_src_ip,
                   "new_dst_ip=%s" % new_dst_ip,
                   "new_src_port=%d" % new_src_port,
                   "new_dst_port=%d" % new_dst_port]

        dl_type = ether.ETH_TYPE_IP

        self.set_flow(cookie,
                      priority,
                      dl_type = dl_type,
                      dl_vlan = dl_vlan,
                      src_ip = src_ip,
                      src_ip_mask = src_ip_mask,
                      dst_ip = dst_ip_mask,
                      dst_ip_mask = dst_ip_mask,
                      idle_timeout = idle_timeout,
                      actions = actions)



    def send_arp(self,
                 arp_opcode,
                 vlan_id,
                 src_mac,
                 dst_mac,
                 src_ip,
                 dst_ip,
                 arp_target_mac,
                 in_port,
                 output):
        self.debugger.info_(">>send_arp")
        self.debugger.info_("arp_opcode=%d,vlan_id=%d" % (arp_opcode, vlan_id))
        self.debugger.info_("src_mac=%s,dst_mac=%s" % (src_mac, dst_mac))
        self.debugger.info_("src_ip=%s,dst_ip=%s" % (src_ip, dst_ip))
        self.debugger.info_("arp_target_mac=%s,in_port=%s" %(arp_target_mac, in_port))
        self.debugger.info("<<")
        self.debugger.info("")

        # Generate ARP packet
        if vlan_id != VLANID_NONE:
            ether_proto = ether.ETH_TYPE_8021Q
            pcp = 0
            cfi = 0
            vlan_ether = ether.ETH_TYPE_ARP
            v = vlan.vlan(pcp, cfi, vlan_id, vlan_ether)
        else:
            ether_proto = ether.ETH_TYPE_ARP
        hwtype = 1
        arp_proto = ether.ETH_TYPE_IP
        hlen = 6
        plen = 4

        pkt = packet.Packet()
        e = ethernet.ethernet(dst_mac, src_mac, ether_proto)
        a = arp.arp(hwtype,
                    arp_proto,
                    hlen,
                    plen,
                    arp_opcode,
                    src_mac,
                    src_ip,
                    arp_target_mac,
                    dst_ip)
        pkt.add_protocol(e)
        if vlan_id != VLANID_NONE:
            pkt.add_protocol(v)
        pkt.add_protocol(a)
        pkt.serialize()

        # Send packet out
        self.send_packet_out(in_port,
                             output,
                             pkt.data,
                             data_str = str(pkt))

    def send_icmp(self,
                  in_port,
                  protocol_list,
                  vlan_id,
                  icmp_type,
                  icmp_code,
                  icmp_data = None,
                  msg_data = None,
                  src_ip = None):
        self.debugger.info_(">>send_icmp")
        self.debugger.info_("in_port=%s,protocol_list=%s,vlan_id=d" % (in_port, protocol_list, vlan_id))
        self.debugger.info_("icmp_type=%d,icmp_code=%" % (icmp_type, icmp_code))
        self.debugger.info("<<")
        self.debugger.info("")

        # Generate ICMP reply packet
        csum = 0
        offset = ethernet.ethernet._MIN_LEN

        if vlan_id != VLANID_NONE:
            ether_proto = ether.ETH_TYPE_8021Q
            pcp = 0
            cfi = 0
            vlan_ether = ether.ETH_TYPE_IP
            v = vlan.vlan(pcp, cfi, vlan_id, vlan_ether)
            offset += vlan.vlan._MIN_LEN
        else:
            ether_proto = ether.ETH_TYPE_IP

        eth = protocol_list[ETHERNET]
        e = ethernet.ethernet(eth.src, eth.dst, ether_proto)

        if icmp_data is None and msg_data is not None:
            ip_datagram = msg_data[offset:]
            if icmp_type == icmp.ICMP_DEST_UNREACH:
                icmp_data = icmp.dest_unreach(data_len = len(ip_datagram),
                                              data=ip_datagram)
            elif icmp_type == icmp.ICMP_TIME_EXCEEDED:
                icmp_data = icmp.TimeExceeded(data_len = len(ip_datagram),
                                              data=ip_datagram)

        ic = icmp.icmp(icmp_type, icmp_code, csum, data = icmp_data)

        ip = protocol_list[IPV4]
        if src_ip is None:
            src_ip = ip.dst
        ip_total_length = ip.header_length * 4 + ic._MIN_LEN
        if ic.data is not None:
            ip_total_length += ic.data._MIN_LEN
            if ic.data.data is not None:
                ip_total_length += + len(ic.data.data)
        i = ipv4.ipv4(ip.version,
                      ip.header_length,
                      ip.tos,
                      ip_total_length,
                      ip.identification,
                      ip.flags,
                      ip.offset,
                      DEFAULT_TTL,
                      inet.IPPROTO_ICMP,
                      csum,
                      src_ip,
                      ip.src)

        pkt = packet.Packet()
        pkt.add_protocol(e)
        if vlan_id != VLANID_NONE:
            pkt.add_protocol(v)
        pkt.add_protocol(i)
        pkt.add_protocol(ic)
        pkt.serialize()

        # Send packet out
        self.send_packet_out(in_port,
                             self.dp.ofproto.OFPP_IN_PORT,
                             pkt.data,
                             data_str = str(pkt))



    def send_packet_out(self, in_port, output, data, data_str = None):
        self.debugger.info_(">>send_packet_out")
        self.debugger.info_("in_port=%s, output=%s" % (in_port, output))
        self.debugger.info("<<")
        self.debugger.info("")


    def set_normal_flow(self, cookie, priority):
        self.debugger.info_(">>set_normal_flow")
        self.debugger.info_("cookie=0x%x, priority=%s" % (cookie, priority))
        self.debugger.info("<<")
        self.debugger.info("")

    def set_packetin_flow(self,
                          cookie,
                          priority,
                          dl_type = 0,
                          dl_dst = 0,
                          dl_vlan = 0,
                          src_ip = 0,
                          src_ip_mask = UINT32_MAX,
                          dst_ip = 0,
                          dst_ip_mask = UINT32_MAX,
                          ip_proto = 0,
                          dst_port = 0,
                          src_port = 0):
        self.debugger.info_(">>set_packetin_flow, actions=[controller]")
        self.debugger.info("<<")
        self.debugger.info("")

        actions = ["packetin"]
 
        self.set_flow(cookie,
                      priority,
                      dl_type = dl_type,
                      dl_dst = dl_dst,
                      dl_vlan = dl_vlan,
                      src_ip = src_ip,
                      src_ip_mask = src_ip_mask,
                      ip_proto = ip_proto,
                      dst_ip = dst_ip,
                      dst_ip_mask = dst_ip_mask,
                      actions = actions)
        

    def send_stats_request(self, stats, waiters):
        self.debugger.info(">>send stats request<<")
        self.debugger.info("")


    def get_packetin_inport(self, msg):
        return msg.in_port

    def get_all_flow(self, waiters):
        with self.m_lock:
            self.debugger.info(">>get_all_flow<<")
            self.debugger.info("")

            body = list(self.flows.values())
            return [DumbMessage(body = body)]

    def delete_flow(self, flow_stats):
        with self.m_lock:
            self.debugger.info(">>delete_flow<<")
            self.debugger.info("")

            self.flows.pop(flow_stats.flow_id, None)
            self.logger.info('Delete flow [cookie=0x%x]',
                             flow_stats.cookie,
                             extra = self.sw_id)

