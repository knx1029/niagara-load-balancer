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

## The basic OpenFlowController Wrap Class
class OfCtl(object):
    _OF_VERSIONS = {}

    @staticmethod
    def register_of_version(version):
        def _register_of_version(cls):
            OfCtl._OF_VERSIONS.setdefault(version, cls)
            return cls
        return _register_of_version

    @staticmethod
    def factory(dp, logger):
        of_version = dp.ofproto.OFP_VERSION
        if of_version in OfCtl._OF_VERSIONS:
            ofctl = OfCtl._OF_VERSIONS[of_version](dp, logger)
        else:
            raise OFPUnknownVersion(version=of_version)

        return ofctl

    def __init__(self, dp, logger):
        super(OfCtl, self).__init__()
        self.dp = dp
        self.sw_id = {'sw_id': dpid_lib.dpid_to_str(dp.id)}
        self.logger = logger

    def set_sw_config_for_ttl(self):
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
        # Abstract method
        raise NotImplementedError()


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
                                              data = ip_datagram)

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
        actions = [self.dp.ofproto_parser.OFPActionOutput(output, 0)]
        self.dp.send_packet_out(buffer_id = UINT32_MAX,
                                in_port = in_port,
                                actions = actions,
                                data = data)

        # TODO: Packet library convert to string
        # if data_str is None:
        #     data_str = str(packet.Packet(data))
        # self.logger.debug('Packet out = %s', data_str, extra=self.sw_id)


    def set_normal_flow(self, cookie, priority):

        out_port = self.dp.ofproto.OFPP_NORMAL
        actions = [self.dp.ofproto_parser.OFPActionOutput(out_port, 0)]
        self.set_flow(cookie, priority, actions = actions)


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

        miss_send_len = UINT16_MAX
        actions = [self.dp.ofproto_parser.OFPActionOutput(
            self.dp.ofproto.OFPP_CONTROLLER, miss_send_len)]
 
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
        self.dp.set_xid(stats)
        waiters_per_dp = waiters.setdefault(self.dp.id, {})
        event = hub.Event()
        msgs = []
        waiters_per_dp[stats.xid] = (event, msgs)
        self.dp.send_msg(stats)

        try:
            event.wait(timeout = OFP_REPLY_TIMER)
        except hub.Timeout:
            del waiters_per_dp[stats.xid]

        return msgs


@OfCtl.register_of_version(ofproto_v1_0.OFP_VERSION)
class OfCtl_v1_0(OfCtl):

    def __init__(self, dp, logger):
        super(OfCtl_v1_0, self).__init__(dp, logger)

    def get_packetin_inport(self, msg):
        return msg.in_port

    def get_all_flow(self, waiters):
        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser

        match = ofp_parser.OFPMatch(ofp.OFPFW_ALL, 0, 0, 0,
                                    0, 0, 0, 0, 0, 0, 0, 0, 0)
        stats = ofp_parser.OFPFlowStatsRequest(self.dp, 0, match,
                                               0xff, ofp.OFPP_NONE)
        return self.send_stats_request(stats, waiters)

    ## it only supports prefix matching
    def set_flow(self,
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
                 idle_timeout = 0,
                 actions = None):

        def count_ones(n):
            v = 0
            while (n > 0):
                v += (n & 1)
                n = n >> 2
            return v

        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser
        cmd = ofp.OFPFC_ADD

        # Match
        wildcards = ofp.OFPFW_ALL
        if dl_type:
            wildcards &= ~ofp.OFPFW_DL_TYPE
        if dl_dst:
            wildcards &= ~ofp.OFPFW_DL_DST
        if dl_vlan:
            wildcards &= ~ofp.OFPFW_DL_VLAN
        if src_ip:
            src_ip_int = ipv4_text_to_int(src_ip)
        else:
            src_ip_int = 0
        if dst_ip:
            dst_ip_int = ipv4_text_to_int(dst_ip)
        else:
            dst_ip_int = 0
        if src_ip_mask:
            prefix_len = count_ones(src_ip_mask)
            v = (32 - prefix_len) << ofp.OFPFW_NW_SRC_SHIFT | \
                ~ofp.OFPFW_NW_SRC_MASK
            wildcards &= v
        if dst_ip_mask:
            prefix_len = count_ones(dst_ip_mask)
            v = (32 - prefix_len) << ofp.OFPFW_NW_DST_SHIFT | \
                ~ofp.OFPFW_NW_DST_MASK
            wildcards &= v
        if ip_proto:
            wildcards &= ~ofp.OFPFW_NW_PROTO

        match = ofp_parser.OFPMatch(wildcards, 0, 0, dl_dst, dl_vlan, 0,
                                    dl_type, 0, ip_proto,
                                    src_ip_int, dst_ip_int, 0, 0)
        actions = actions or []

        m = ofp_parser.OFPFlowMod(self.dp,
                                  match,
                                  cookie,
                                  cmd,
                                  idle_timeout = idle_timeout,
                                  priority = priority,
                                  actions = actions)

        self.dp.send_msg(m)


    ## if out_port is None, then it is a normal flow
    def set_routing_flow(self,
                         cookie,
                         priority,
                         out_port = None,
                         dl_vlan = 0,
                         src_ip = 0,
                         src_ip_mask = UINT32_MAX,
                         dst_ip = 0,
                         dst_ip_mask = UINT32_MAX,
                         new_src_mac = 0,
                         new_dst_mac = 0,
                         idle_timeout = 0,
                         **dummy):
        ofp_parser = self.dp.ofproto_parser

        dl_type = ether.ETH_TYPE_IP

        # Decrement TTL value is not supported at OpenFlow V1.0
        actions = []
        if out_port is not None:
            actions.append(ofp_parser.OFPActionOutput(out_port))
            if new_src_mac:
                actions.append(ofp_parser.OFPActionSetDlSrc(
                    mac_lib.haddr_to_bin(new_src_mac)))
            if new_dst_mac:
                actions.append(ofp_parser.OFPActionSetDlDst(
                    mac_lib.haddr_to_bin(new_dst_mac)))
        else:
            out_port = self.dp.ofproto.OFPP_NORMAL
            actions.append(ofp_parser.OFPActionOutput(out_port, 0))

        self.set_flow(cookie,
                      priority,
                      dl_type = dl_type,
                      dl_vlan = dl_vlan,
                      src_ip = src_ip,
                      src_ip_mask = src_ip_mask,
                      dst_ip = dst_ip,
                      dst_ip_mask = dst_ip_mask,
                      idle_timeout = idle_timeout,
                      actions = actions)
        
    def delete_flow(self, flow_stats):
        match = flow_stats.match
        cookie = flow_stats.cookie
        cmd = self.dp.ofproto.OFPFC_DELETE_STRICT
        priority = flow_stats.priority
        actions = []

        flow_mod = self.dp.ofproto_parser.OFPFlowMod(
            self.dp,
            match,
            cookie,
            cmd, priority = priority, 
            actions = actions)


        self.dp.send_msg(flow_mod)
        self.logger.info('Delete flow [cookie=0x%x]',
                         cookie,
                         extra = self.sw_id)


class OfCtl_after_v1_2(OfCtl):

    def __init__(self, dp, logger):
        super(OfCtl_after_v1_2, self).__init__(dp, logger)

    def set_sw_config_for_ttl(self):
        pass

    def get_packetin_inport(self, msg):
        in_port = self.dp.ofproto.OFPP_ANY
        for match_field in msg.match.fields:
            if match_field.header == self.dp.ofproto.OXM_OF_IN_PORT:
                in_port = match_field.value
                break
        return in_port

    def get_all_flow(self, waiters):
        pass


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

        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser
        cmd = ofp.OFPFC_ADD

        # Match
        match = ofp_parser.OFPMatch()
        if dl_type:
            match.set_dl_type(dl_type)
        if dl_dst:
            match.set_dl_dst(dl_dst)
        if dl_vlan:
            match.set_vlan_vid(dl_vlan)
        if src_ip:
            match.set_ipv4_src_masked(ipv4_text_to_int(src_ip),
                                      src_ip_mask)

        if dst_ip:
            match.set_ipv4_dst_masked(ipv4_text_to_int(dst_ip),
                                      dst_ip_mask)
        if ip_proto:
            if dl_type == ether.ETH_TYPE_IP:
                match.set_ip_proto(ip_proto)
                if ip_proto == inet.IPPROTO_TCP:
                    if src_port:
                        match.set_tcp_src(src_port)
                    if dst_port:
                        match.set_tcp_dst(dst_port)
                elif ip_proto == inet.IPPROTO_UDP:
                    if src_port:
                        match.set_udp_src(src_port)
                    if dst_port:
                        match.set_udp_dst(dst_port)
            elif dl_type == ether.ETH_TYPE_ARP:
                match.set_arp_opcode(ip_proto)


        # Instructions
        actions = actions or []
        inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                                 actions)]

        m = ofp_parser.OFPFlowMod(self.dp, cookie, 0, 0, cmd,
                                  idle_timeout, 0, priority, UINT32_MAX,
                                  ofp.OFPP_ANY, ofp.OFPG_ANY, 0, match,
                                  inst)

        self.dp.send_msg(m)

    ## if out_port is None, then it is a normal flow
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
        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser

        dl_type = ether.ETH_TYPE_IP

        actions = []

        if new_src_ip:
            actions.append(ofp_parser.OFPActionSetField(
                ipv4_src = new_src_ip))
        if new_src_port:
            if ip_proto == inet.IPPROTO_TCP:
                actions.append(ofp_parser.OFPActionSetField(
                    tcp_src = new_src_port))
            elif ip_proto == inet.IPPROTO_UDP:
                actions.append(ofp_parser.OFPActionSetField(
                    udp_src = new_src_port))
        if new_dst_ip:
            actions.append(ofp_parser.OFPActionSetField(
                ipv4_dst = new_dst_ip))
        if new_dst_port:
            if ip_proto == inet.IPPROTO_TCP:
                actions.append(ofp_parser.OFPActionSetField(
                    tcp_dst = new_dst_port))
            elif ip_proto == inet.IPPROTO_UDP:
                actions.append(ofp_parser.OFPActionSetField(
                    udp_dst = new_dst_port))

        ## output to a known port
        if out_port is not None:
            if dec_ttl:
                actions.append(ofp_parser.OFPActionDecNwTtl())
            if new_src_mac:
                actions.append(ofp_parser.OFPActionSetField(
                    eth_src = new_src_mac))
            if new_dst_mac:
                actions.append(ofp_parser.OFPActionSetField(
                    eth_dst = new_dst_mac))
            actions.append(ofp_parser.OFPActionOutput(out_port, 0))

        else:
            out_port = self.dp.ofproto.OFPP_NORMAL
            actions.append(ofp_parser.OFPActionOutput(out_port, 0))

        self.set_flow(cookie,
                      priority,
                      dl_type = dl_type,
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
    

    def delete_flow(self, flow_stats):
        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser

        cmd = ofp.OFPFC_DELETE
        cookie = flow_stats.cookie
        cookie_mask = UINT64_MAX
        match = ofp_parser.OFPMatch()
        inst = []

        flow_mod = ofp_parser.OFPFlowMod(self.dp, cookie, cookie_mask, 0,
                                         cmd, 0, 0, 0, UINT32_MAX,
                                         ofp.OFPP_ANY, ofp.OFPG_ANY, 0,
                                         match, inst)


        self.dp.send_msg(flow_mod)
        self.logger.info('Delete flow [cookie=0x%x]', cookie, extra=self.sw_id)

@OfCtl.register_of_version(ofproto_v1_2.OFP_VERSION)
class OfCtl_v1_2(OfCtl_after_v1_2):

    def __init__(self, dp, logger):
        super(OfCtl_v1_2, self).__init__(dp, logger)

    def set_sw_config_for_ttl(self):
        flags = self.dp.ofproto.OFPC_INVALID_TTL_TO_CONTROLLER
        miss_send_len = UINT16_MAX
        m = self.dp.ofproto_parser.OFPSetConfig(self.dp, flags,
                                                miss_send_len)
        self.dp.send_msg(m)
        self.logger.info('Set SW config for TTL error packet in.',
                         extra=self.sw_id)

    def get_all_flow(self, waiters):
        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser

        match = ofp_parser.OFPMatch()
        stats = ofp_parser.OFPFlowStatsRequest(self.dp, 0, ofp.OFPP_ANY,
                                               ofp.OFPG_ANY, 0, 0, match)
        return self.send_stats_request(stats, waiters)


@OfCtl.register_of_version(ofproto_v1_3.OFP_VERSION)
class OfCtl_v1_3(OfCtl_after_v1_2):

    def __init__(self, dp, logger):
        super(OfCtl_v1_3, self).__init__(dp, logger)

    def set_sw_config_for_ttl(self):
        packet_in_mask = (1 << self.dp.ofproto.OFPR_ACTION |
                          1 << self.dp.ofproto.OFPR_INVALID_TTL)
        port_status_mask = (1 << self.dp.ofproto.OFPPR_ADD |
                            1 << self.dp.ofproto.OFPPR_DELETE |
                            1 << self.dp.ofproto.OFPPR_MODIFY)
        flow_removed_mask = (1 << self.dp.ofproto.OFPRR_IDLE_TIMEOUT |
                             1 << self.dp.ofproto.OFPRR_HARD_TIMEOUT |
                             1 << self.dp.ofproto.OFPRR_DELETE)
        m = self.dp.ofproto_parser.OFPSetAsync(
            self.dp, [packet_in_mask, 0], [port_status_mask, 0],
            [flow_removed_mask, 0])
        self.dp.send_msg(m)
        self.logger.info('Set SW config for TTL error packet in.',
                         extra=self.sw_id)

    def get_all_flow(self, waiters):
        ofp = self.dp.ofproto
        ofp_parser = self.dp.ofproto_parser

        match = ofp_parser.OFPMatch()
        stats = ofp_parser.OFPFlowStatsRequest(self.dp, 0, 0, ofp.OFPP_ANY,
                                               ofp.OFPG_ANY, 0, 0, match)
        return self.send_stats_request(stats, waiters)
