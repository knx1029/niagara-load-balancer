# Built from rest_router in Ryu/app
# Nanxi Kang (nkang@cs.princeton.edu

from utils import *
from info import *
from rule_table import *
from OfCtl import *
from ecmp_router import *

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


# =============================
#          REST API
# =============================
#
#  Note: specify switch and vlan group, as follows.
#   {switch_id} : 'all' or switchID
#   {vlan_id}   : 'all' or vlanID
#

# 1. get address data and routing data.
#
# * get data of no vlan
# GET /router/{switch_id}
#
# * get data of specific vlan group
# GET /router/{switch_id}/{vlan_id}
#

# 2. set address data or routing data.
#
# * set data of no vlan
# POST /router/{switch_id}
#
# * set data of specific vlan group
# POST /router/{switch_id}/{vlan_id}
#
#  case1: set address data.
#    parameter = {"address": "A.B.C.D/M"}
#  case2-1: set ecmp data.
#    parameter = {"ecmp": "create", "gateways":"{'10.0.0.0':2}"}
#  case2-2: set flow data
#    parameter = {"gateway": "E.F.G.H}
#

# 3. delete address data or routing data.
#
# * delete data of no vlan
# DELETE /router/{switch_id}
#
# * delete data of specific vlan group
# DELETE /router/{switch_id}/{vlan_id}
#
#  case1: delete address data.
#    parameter = {"address_id": "<int>"} or {"address_id": "all"}
#  case2: delete routing data.
#    parameter = {"route_id": "<int>"} or {"route_id": "all"}
#
#

class RestRouterAPI(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,
                    ofproto_v1_2.OFP_VERSION,
                    ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'dpset': dpset.DPSet,
                 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(RestRouterAPI, self).__init__(*args, **kwargs)

        # logger configure
        RouterController.set_logger(self.logger)

        wsgi = kwargs['wsgi']
        self.waiters = {}
        self.data = {'waiters': self.waiters}

        mapper = wsgi.mapper
        wsgi.registory['RouterController'] = self.data
        requirements = {'switch_id': SWITCHID_PATTERN,
                        'vlan_id': VLANID_PATTERN}

        # For no vlan data
        path = '/router/{switch_id}'
        mapper.connect('router', path, controller=RouterController,
                       requirements=requirements,
                       action='get_data',
                       conditions=dict(method=['GET']))
        mapper.connect('router', path, controller=RouterController,
                       requirements=requirements,
                       action='set_data',
                       conditions=dict(method=['POST']))
        mapper.connect('router', path, controller=RouterController,
                       requirements=requirements,
                       action='delete_data',
                       conditions=dict(method=['DELETE']))
        # For vlan data
        path = '/router/{switch_id}/{vlan_id}'
        mapper.connect('router', path, controller=RouterController,
                       requirements=requirements,
                       action='get_vlan_data',
                       conditions=dict(method=['GET']))
        mapper.connect('router', path, controller=RouterController,
                       requirements=requirements,
                       action='set_vlan_data',
                       conditions=dict(method=['POST']))
        mapper.connect('router', path, controller=RouterController,
                       requirements=requirements,
                       action='delete_vlan_data',
                       conditions=dict(method=['DELETE']))

    @set_ev_cls(dpset.EventDP, dpset.DPSET_EV_DISPATCHER)
    def datapath_handler(self, ev):
        if ev.enter:
            RouterController.register_router(ev.dp, self.waiters)
        else:
            RouterController.unregister_router(ev.dp)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        RouterController.packet_in_handler(ev.msg)

    def _stats_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath

        if (dp.id not in self.waiters
                or msg.xid not in self.waiters[dp.id]):
            return
        event, msgs = self.waiters[dp.id][msg.xid]
        msgs.append(msg)

        if ofproto_v1_3.OFP_VERSION == dp.ofproto.OFP_VERSION:
            more = dp.ofproto.OFPMPF_REPLY_MORE
        else:
            more = dp.ofproto.OFPSF_REPLY_MORE
        if msg.flags & more:
            return
        del self.waiters[dp.id][msg.xid]
        event.set()

    # for OpenFlow version1.0
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def stats_reply_handler_v1_0(self, ev):
        self._stats_reply_handler(ev)

    # for OpenFlow version1.2/1.3
    @set_ev_cls(ofp_event.EventOFPStatsReply, MAIN_DISPATCHER)
    def stats_reply_handler_v1_2(self, ev):
        self._stats_reply_handler(ev)

    # TODO: Update routing table when port status is changed.


# REST command template
def rest_command(func):
    def _rest_command(*args, **kwargs):
        try:
            msg = func(*args, **kwargs)
            return Response(content_type='application/json',
                            body=json.dumps(msg))

        except SyntaxError as e:
            status = 400
            details = e.msg
        except (ValueError, NameError) as e:
            status = 400
            details = e.message

        except NotFoundError as msg:
            status = 404
            details = str(msg)

        msg = {REST_RESULT: REST_NG,
               REST_DETAILS: details}
        return Response(status=status, body=json.dumps(msg))

    return _rest_command


class RouterController(ControllerBase):

    _ROUTER_LIST = {}
    _LOGGER = None

    def __init__(self, req, link, data, **config):
        super(RouterController, self).__init__(req, link, data, **config)
        self.waiters = data['waiters']

    @classmethod
    def set_logger(cls, logger):
        cls._LOGGER = logger
        cls._LOGGER.propagate = False
        hdlr = logging.StreamHandler()
        fmt_str = '[RT][%(levelname)s] switch_id=%(sw_id)s: %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        cls._LOGGER.addHandler(hdlr)

    @classmethod
    def register_router(cls, dp, waiters):
        dpid = {'sw_id': dpid_lib.dpid_to_str(dp.id)}
        try:
            router = Router(dp, cls._LOGGER, waiters)
        except OFPUnknownVersion as message:
            cls._LOGGER.error(str(message), extra = dpid)
            return
        cls._ROUTER_LIST.setdefault(dp.id, router)
        cls._LOGGER.info('Join as router.', extra = dpid)

    @classmethod
    def unregister_router(cls, dp):
        if dp.id in cls._ROUTER_LIST:
            cls._ROUTER_LIST[dp.id].delete()
            del cls._ROUTER_LIST[dp.id]

            dpid = {'sw_id': dpid_lib.dpid_to_str(dp.id)}
            cls._LOGGER.info('Leave router.', extra = dpid)

    @classmethod
    def packet_in_handler(cls, msg):
        dp_id = msg.datapath.id
        if dp_id in cls._ROUTER_LIST:
            router = cls._ROUTER_LIST[dp_id]
            router.packet_in_handler(msg)

    # GET /router/{switch_id}
    @rest_command
    def get_data(self, req, switch_id, **_kwargs):
        return self._access_router(switch_id, VLANID_NONE,
                                   'get_data', req.body)

    # GET /router/{switch_id}/{vlan_id}
    @rest_command
    def get_vlan_data(self, req, switch_id, vlan_id, **_kwargs):
        return self._access_router(switch_id, vlan_id,
                                   'get_data', req.body)

    # POST /router/{switch_id}
    @rest_command
    def set_data(self, req, switch_id, **_kwargs):
        return self._access_router(switch_id, VLANID_NONE,
                                   'set_data', req.body)

    # POST /router/{switch_id}/{vlan_id}
    @rest_command
    def set_vlan_data(self, req, switch_id, vlan_id, **_kwargs):
        return self._access_router(switch_id, vlan_id,
                                   'set_data', req.body)

    # DELETE /router/{switch_id}
    @rest_command
    def delete_data(self, req, switch_id, **_kwargs):
        return self._access_router(switch_id, VLANID_NONE,
                                   'delete_data', req.body)

    # DELETE /router/{switch_id}/{vlan_id}
    @rest_command
    def delete_vlan_data(self, req, switch_id, vlan_id, **_kwargs):
        return self._access_router(switch_id, vlan_id,
                                   'delete_data', req.body)

    def _access_router(self, switch_id, vlan_id, func, rest_param):
        rest_message = []
        routers = self._get_router(switch_id)
        param = eval(rest_param) if rest_param else {}
        for router in routers.values():
            function = getattr(router, func)
            data = function(vlan_id, param, self.waiters)
            rest_message.append(data)

        return rest_message

    def _get_router(self, switch_id):
        routers = {}

        if switch_id == REST_ALL:
            routers = self._ROUTER_LIST
        else:
            sw_id = dpid_lib.str_to_dpid(switch_id)
            if sw_id in self._ROUTER_LIST:
                routers = {sw_id: self._ROUTER_LIST[sw_id]}

        if routers:
            return routers
        else:
            raise NotFoundError(switch_id=switch_id)


class Router(dict):
    def __init__(self, dp, logger, waiters):
        super(Router, self).__init__()
        self.dp = dp
        self.dpid_str = dpid_lib.dpid_to_str(dp.id)
        self.sw_id = {'sw_id': self.dpid_str}
        self.logger = logger

        self.port_data = PortData(dp.ports)

        ofctl = OfCtl.factory(dp, logger)
        cookie = COOKIE_DEFAULT_ID

        # Set SW config: TTL error packet in (for OFPv1.2/1.3)
        ofctl.set_sw_config_for_ttl()

        # Set flow: ARP handling (packet in)
        priority = get_priority(PRIORITY_ARP_HANDLING)
        ofctl.set_packetin_flow(cookie,
                                priority,
                                dl_type=ether.ETH_TYPE_ARP)
        self.logger.info('Set ARP handling (packet in) flow [cookie=0x%x]',
                         cookie,
                         extra = self.sw_id)

        # Set flow: L2 switching (normal)
        priority = get_priority(PRIORITY_NORMAL)
        ofctl.set_normal_flow(cookie, priority)
        self.logger.info('Set L2 switching (normal) flow [cookie=0x%x]',
                         cookie,
                         extra = self.sw_id)

        # Set VlanRouter for vid = None.
        ecmp_router = EcmpRouter(VLANID_NONE, dp, self.port_data, logger)
        self[VLANID_NONE] = ecmp_router

        self.logger.info('Start router',
                         extra = self.sw_id)
        ecmp_router.start(waiters)

        # Start cyclic routing table check.
        self.thread = hub.spawn(self._cyclic_update_routing_tbl)
        self.logger.info('Start cyclic routing table update.',
                         extra = self.sw_id)

    def delete(self):
        hub.kill(self.thread)
        self.thread.wait()
        self.logger.info('Stop cyclic routing table update.',
                         extra = self.sw_id)

    def _get_ecmp_router(self, vlan_id):
        ecmp_routers = []

        if vlan_id == REST_ALL:
            ecmp_routers = self.values()
        else:
            vlan_id = int(vlan_id)
            if (vlan_id != VLANID_NONE and
                    (vlan_id < VLANID_MIN or VLANID_MAX < vlan_id)):
                msg = 'Invalid {vlan_id} value. Set [%d-%d]'
                raise ValueError(msg % (VLANID_MIN, VLANID_MAX))
            elif vlan_id in self:
                ecmp_routers = [self[vlan_id]]

        return ecmp_routers

    def _add_ecmp_router(self, vlan_id, waiters):
        vlan_id = int(vlan_id)
        if vlan_id not in self:
            ecmp_router = EcmpRouter(vlan_id,
                                     self.dp,
                                     self.port_data,
                                     self.logger)
            self[vlan_id] = ecmp_router
            ecmp_router.start(waiters)
        return self[vlan_id]

    def _del_ecmp_router(self, vlan_id, waiters):
        #  Remove unnecessary VlanRouter.
        if vlan_id == VLANID_NONE:
            return

        ecmp_router = self[vlan_id]
        if (ecmp_router.destroyable()):
            ecmp_router.stop()
            ecmp_router.delete(waiters)
            del self[vlan_id]

#    def get_data(self, vlan_id, dummy1, dummy2):
    def get_data(self, vlan_id, param, waiters):
        ecmp_routers = self._get_ecmp_router(vlan_id)
        if ecmp_routers:
            msgs = [ecmp_router.get_data(param, waiters)
                    for ecmp_router in ecmp_routers]
        else:
            msgs = [{REST_VLANID: vlan_id}]

        return {REST_SWITCHID: self.dpid_str,
                REST_NW: msgs}

    def set_data(self, vlan_id, param, waiters):
        ecmp_routers = self._get_ecmp_router(vlan_id)
        if not ecmp_routers:
            ecmp_routers = [self._add_ecmp_router(vlan_id, waiters)]

        msgs = []
        for ecmp_router in ecmp_routers:
            try:
                msg = ecmp_router.set_data(param)
                msgs.append(msg)
                if msg[REST_RESULT] == REST_NG:
                    # Data setting is failure.
                    self._del_ecmp_router(ecmp_router.vlan_id, waiters)
            except ValueError as err_msg:
                # Data setting is failure.
                self._del_ecmp_router(ecmp_router.vlan_id, waiters)
                raise err_msg

        return {REST_SWITCHID: self.dpid_str,
                REST_COMMAND_RESULT: msgs}

    def delete_data(self, vlan_id, param, waiters):
        msgs = []
        ecmp_routers = self._get_ecmp_router(vlan_id)
        if ecmp_routers:
            for ecmp_router in ecmp_routers:
                msg = ecmp_router.delete_data(param, waiters)
                if msg:
                    msgs.append(msg)
                # Check unnecessary VlanRouter.
                self._del_ecmp_router(ecmp_router.vlan_id, waiters)
        if not msgs:
            msgs = [{REST_RESULT: REST_NG,
                     REST_DETAILS: 'Data is nothing.'}]

        return {REST_SWITCHID: self.dpid_str,
                REST_COMMAND_RESULT: msgs}

    def packet_in_handler(self, msg):
        pkt = packet.Packet(msg.data)
        # TODO: Packet library convert to string
        # self.logger.debug('Packet in = %s', str(pkt), self.sw_id)
        header_list = dict((p.protocol_name, p)
                           for p in pkt.protocols if type(p) != str)
        if header_list:
            # Check vlan-tag
            vlan_id = VLANID_NONE
            if VLAN in header_list:
                vlan_id = header_list[VLAN].vid

            # Event dispatch
            if vlan_id in self:
                self[vlan_id].packet_in_handler(msg, header_list)
            else:
                self.logger.debug('Drop unknown vlan packet. [vlan_id=%d]',
                                  vlan_id,
                                  extra = self.sw_id)

    def _cyclic_update_routing_tbl(self):
        while True:
            # send ARP to all gateways.
            for ecmp_router in self.values():
                ecmp_router.send_arp_all_gw()
                hub.sleep(1)

            hub.sleep(CHK_ROUTING_TBL_INTERVAL)
