from utils import *
from info import *
from rule_table import *
from OfCtl import *

import logging

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


def get_priority(priority_type, vid = 0, rule = None):
    if (rule != None):
        priority = rule.priority
    else:
        priority = priority_type

    if (vid):
        priority += PRIORITY_VLAN_SHIFT

    return priority


def get_priority_type(priority, vid = 0):
    if (vid):
        priority -= PRIORITY_VLAN_SHIFT
    return priority


class EcmpRouter(object):

    def __init__(self, vlan_id, dp, port_data, logger):
#    def __init__(self, vlan_id, dp, ofctl, port_data, logger):
        super(EcmpRouter, self).__init__()
        self.vlan_id = vlan_id
        self.dp = dp
        self.sw_id = {'sw_id': dpid_lib.dpid_to_str(dp.id)}
        self.logger = logger

        self.port_data = port_data
        self.address_data = AddressData()
        self.routing_table = RoutingTable(logger, self.sw_id)
        self.arp_table = ArpTable()
        self.packet_buffer = SuspendPacketList(self.send_icmp_unreach_error)
        if USE_HUB_THREAD:
            self.ofctl = OfCtl.factory(dp, logger)
        else:
            self.ofctl = ofctl

        # Set flow: default route (drop)
        self.__set_default_drop()


    def start(self, waiters):
        self.routing_table.start()

        ## looping at work
        self._stop = False
        if USE_HUB_THREAD:
            self._install_thread = hub.spawn(self.__do_install)
            self._clear_thread = hub.spawn(self.__do_clear, waiters)
        
        else:
            self._install_thread = Thread(target = self.__do_install)
            self._clear_thread = Thread(target = self.__do_clear,
                                        args = [waiters])
            self._install_thread.start()
            self._clear_thread.start()
        pass

    def stop(self):
        self._stop = True
        if USE_HUB_THREAD:
            hub.joinall([self._install_thread,
                         self._clear_thread])
            hub.kill(self._install_thread)
            hub.kill(self._clear_thread)
        else:
            self._install_thread.join()
            self._clear_thread.join()
        self.routing_table.stop()
        pass

    def destroyable(self):
        address_data = self.address_data.get_data()
        if (len(address_data) > 0):
            return False
        active_rules = self.routing_table.get_active_rules_data()
        if (len(active_rules) > 0):
            return False
        return True


    ## delete all flows related to this router
    def delete(self, waiters):
        # Delete flow.
        msgs = self.ofctl.get_all_flow(waiters)
        for msg in msgs:
            for stats in msg.body:
                vlan_id, _ = EcmpRouter.cookie_to_id(REST_VLANID,
                                                     stats.cookie)
                if vlan_id == self.vlan_id:
                    self.ofctl.delete_flow(stats)
        assert len(self.packet_buffer) == 0

    ## translate rule cookie to id (vlan, address or rule)
    @staticmethod
    def cookie_to_id(id_type, cookie):
        if id_type == REST_VLANID:
            rest_id = cookie >> COOKIE_SHIFT_VLANID
        elif id_type == REST_ADDRESSID:
            type_id = (cookie >> COOKIE_SHIFT_TYPE) & COOKIE_TYPE_MASK
            if (type_id != COOKIE_TYPE_ADDRESSID):
                return 0, False
            rest_id = cookie & COOKIE_ID_MASK
        else:
            assert id_type == REST_RULEID 
            type_id = (cookie >> COOKIE_SHIFT_TYPE) & COOKIE_TYPE_MASK
            if (type_id != COOKIE_TYPE_RULEID):
                return 0, False
            rest_id = cookie & COOKIE_ID_MASK
        return rest_id, True

    ## translate id to rule cookie
    def _id_to_cookie(self, id_type, rest_id):
        vid = self.vlan_id << COOKIE_SHIFT_VLANID

        if id_type == REST_VLANID:
            cookie = rest_id << COOKIE_SHIFT_VLANID
        elif id_type == REST_ADDRESSID:
            cookie = (vid + 
                      (COOKIE_TYPE_ADDRESSID << COOKIE_SHIFT_TYPE) +
                      rest_id)
        else:
            assert id_type == REST_RULEID
            cookie = (vid +
                      (COOKIE_TYPE_RULEID << COOKIE_SHIFT_TYPE) +
                      rest_id)

        return cookie

    def _get_priority(self, priority_type, rule = None):
        return get_priority(priority_type,
                            vid = self.vlan_id,
                            rule = rule)

    def _response(self, msg):
        if msg and self.vlan_id:
            msg.setdefault(REST_VLANID, self.vlan_id)
        return msg

    ## ---------- Get Data  -------- ##

    ## request all the data in the address table and routing table
    def get_data(self, param, waiters):
        address_data = self.__get_address_data(param)
        routing_data = self.__get_routing_data(param)
        arp_data = self.__get_arp_data(param)
        oftbl_data = self.__get_of_table_data(param, waiters)

        data = {}
        data.update(address_data)
        data.update(routing_data)
        data.update(arp_data)
        data.update(oftbl_data)

        return self._response(data)

    ## get address data
    def __get_address_data(self, param):
        if (not param) or (REST_ADDRESS in param):
            address_data = self.address_data.get_data()
            return {REST_ADDRESS: address_data}
        else:
            return {}

    ## get arp data
    def __get_arp_data(self, param):
        if (not param) or (REST_ARP in param):
            arp_data = self.arp_table.get_data()
            return {REST_ARP: arp_data}
        else:
            return {}

    ## get routing table
    def __get_routing_data(self, param):
        res = {}
        if (not param) or (REST_ECMP_GROUP in param):
            ecmp_group_data = self.routing_table.get_ecmp_group_data()
            res[REST_ECMP_GROUP] = ecmp_group_data

        if (not param) or (REST_FLOW_GROUP in param):
            flow_group_data = self.routing_table.get_flow_group_data()
            res[REST_FLOW_GROUP] = flow_group_data

        if (not param) or (REST_FG2EG in param):
            flow2ecmp_data = self.routing_table.get_fg2ecmp_data()
            res[REST_FG2EG] = flow2ecmp_data

        if (not param) or (REST_RULES in param):
            active_rules = self.routing_table.get_active_rules_data()
            res[REST_RULES] = active_rules

        if (not param) or (REST_INSTALL_RULES in param):
            install_rules = self.routing_table.get_install_rules_data()
            res[REST_INSTALL_RULES] = install_rules

        if (not param) or (REST_CLEAR_RULES in param):
            clear_rules = self.routing_table.get_clear_rules_data()
            res[REST_CLEAR_RULES] = param
        
        return res


    def __get_of_table_data(self, param, waiters):
        if (not param) or (REST_OF_TABLE in param):
            data = []
            msgs = self.ofctl.get_all_flow(waiters)
            for msg in msgs:
                for stats in msg.body:
                    duration = stats.duration_sec
                    duration += stats.duration_nsec / 1e9
                    st = Stats(cookie = stats.cookie,
                               duration = duration,
                               npackets = stats.packet_count,
                               nbytes = stats.byte_count)
                    data.append(str(st))
            return {REST_OF_TABLE : data}
        else:
            return {}


    ## update address or routing data (ecmp group or flow group)
    def set_data(self, data):
        details = None
        try:
            ## Set address data
            if REST_ADDRESS in data:
                address = data[REST_ADDRESS]
                address_id = self.__set_address(address)
                details = 'Add address [address_id = %d]' % address_id
            ## Set ecmp group data
            elif REST_ECMP_GROUP in data:
                op = data[REST_ECMP_GROUP]
                if op == 'create':
                    dst_str = data[REST_ECMP_GATEWAY]
                    ecmp_id = self.__set_ecmp_group(op = op,
                                                    dst_str = dst_str)
                    details = 'Add ecmp group id = %d' % ecmp_id
                elif op == 'add' or op == 'change' or op == 'delete':
                    dst_str = data[REST_ECMP_GATEWAY]
                    ecmp_id_str = data[REST_ECMP_ID]
                    self.__set_ecmp_group(op = op,
                                         dst_str = dst_str,
                                         ecmp_id_str = ecmp_id_str)
                    details = 'Change ecmp group %s' % ecmp_id_str
                elif op == 'destroy':
                    ecmp_id_str = data[REST_ECMP_ID]
                    self.__set_ecmp_group(op = op,
                                         ecmp_id_str = ecmp_id_str)
                    details = 'Destroy ecmp group %s' % ecmp_id_str
            ## Set flow group data
            elif REST_FLOW_GROUP in data:
                op = data[REST_FLOW_GROUP]
                if op == 'create':
                    priority_str = 0
                    if (REST_FG_PRIORITY in data):
                        priority_str = data[REST_FG_PRIORITY]

                    ## parse match header fields
                    nw_sip_str = 0
                    nw_dip_str = 0
                    sport_str = 0
                    dport_str = 0
                    proto_str = 0
                    if (REST_SIP in data):
                        nw_sip_str = data[REST_SIP]
                    if (REST_DIP in data):
                        nw_dip_str = data[REST_DIP]
                    if (REST_SPORT in data):
                        sport_str = data[REST_SPORT]
                    if (REST_DPORT in data):
                        dport_str = data[REST_DPORT]
                    if (REST_IP_PROTO in data):
                        proto_str = data[REST_IP_PROTO]

                    ## parse rewrite header fields
                    new_sip_str = 0
                    new_dip_str = 0
                    new_sport_str = 0
                    new_dport_str = 0
                    if (REST_NEW_SIP in data):
                        new_sip_str = data[REST_NEW_SIP]
                    if (REST_NEW_DIP in data):
                        new_dip_str = data[REST_NEW_DIP]
                    if (REST_NEW_SPORT in data):
                        new_sport_str = data[REST_NEW_SPORT]
                    if (REST_NEW_DPORT in data):
                        new_dport_str = data[REST_NEW_DPORT]
                 
                    ## this is a hack: denote the gateway for returning packets
                    ## it is used when incoming packets are DNAT
                    ## and the returning packets are SNAT.
                    ## But the SNAT rule has to also do the routing
                    ## (Ideally, this is a natural composition if we have >1 tables)

                    return_gw_str = 0
                    if (REST_RETURN_GW in data):
                        return_gw_str = data[REST_RETURN_GW]

                    fg_id = self.__create_flow_group(
                        priority_str = priority_str,
                        nw_sip_str = nw_sip_str,
                        nw_dip_str = nw_dip_str,
                        sport_str = sport_str,
                        dport_str = dport_str,
                        proto_str = proto_str,
                        new_sip_str = new_sip_str,
                        new_dip_str = new_dip_str,
                        new_sport_str = new_sport_str,
                        new_dport_str = new_dport_str,
                        return_gw_str = return_gw_str);
                    details = 'Add flow group id = %d' % fg_id

                elif op == 'apply':
                    ecmp_id_str = data[REST_ECMP_ID]
                    fg_id_str = data[REST_FLOW_GROUP_ID]
                    self.__apply_ecmp(ecmp_id_str = ecmp_id_str,
                                      fg_id_str = fg_id_str)
                    details = 'Apply ecmp %s to %s' % (ecmp_id_str,
                                                       fg_id_str)
                elif op == 'destroy':
                    fg_id_str = data[REST_FLOW_GROUP_ID]
                    self.__destroy_flow_group(fg_id_str = fg_id_str)
                    details = 'Destroy flow group %s' % fg_id_str

        except CommandFailure as err_msg:
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: str(err_msg)}
            return self._response(msg)
        except KeyError:
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: "missing required fields"}
            return self._response(msg)

        if details == None:
            details = 'Invalid operations'
            msg = {REST_RESULT : REST_NG,
                   REST_DETAILS: details}
            return self._response(msg)
        else:
            msg = {REST_RESULT: REST_OK,
                   REST_DETAILS: details}
            return self._response(msg)

    ## ---------- <Get Data>  -------- ##

    ## ---------- Set Data  -------- ##

    ## Update address
    def __set_address(self, address):
        address = self.address_data.add_address(address)
        addr = address.addr
        nw_addr = address.nw_addr
        netmask = prefix_mask_ntob(address.prefix_len)

        cookie = self._id_to_cookie(REST_ADDRESSID, address.address_id)

        ## Set flow: host MAC learning (packet in)
        priority = self._get_priority(PRIORITY_MAC_LEARNING)
        self.ofctl.set_packetin_flow(cookie,
                                     priority,
                                     dl_type = ether.ETH_TYPE_IP,
                                     dl_vlan = self.vlan_id,
                                     dst_ip = nw_addr,
                                     dst_ip_mask = netmask)
        log_msg = 'Set host MAC learning (packet in) flow [cookie=0x%x]'
        self.logger.info(log_msg, cookie, extra = self.sw_id)

        ## Set Flow: IP handling(PacketIn)
        priority = self._get_priority(PRIORITY_IP_HANDLING)
        self.ofctl.set_packetin_flow(cookie,
                                     priority,
                                     dl_type = ether.ETH_TYPE_IP,
                                     dl_vlan = self.vlan_id,
                                     dst_ip = addr)
        log_msg = 'Set IP handling (packet in) flow[cookie=0x%x]'
        self.logger.info(log_msg, cookie, extra = self.sw_id)

        ## Set flow: L2 switching (normal)
        out_port = self.ofctl.dp.ofproto.OFPP_NORMAL
        priority = self._get_priority(PRIORITY_L2_SWITCHING)
        self.ofctl.set_routing_flow(cookie,
                                    priority,
                                    out_port,
                                    dl_vlan=self.vlan_id,
                                    src_ip = nw_addr,
                                    src_ip_mask = netmask,
                                    dst_ip = nw_addr,
                                    dst_ip_mask = netmask)

        self.logger.info('Set L2 switching (normal) flow [cookie=0x%x]',
                         cookie,
                         extra = self.sw_id)

        ## Send GARP
        self.send_arp_request(address.addr, address.addr)
        return address.address_id


    ## Update ecmp group data
    def __set_ecmp_group(self,
                         op,
                         dst_str = None,
                         ecmp_id_str = None):
        try:
            ## Convert input and check validity
            if (ecmp_id_str != None):
                ecmp_id = int(ecmp_id_str)
            if (dst_str):
                dst = ast.literal_eval(dst_str)

            if (op == 'create' or op == 'add' or op == 'update'):
#                if not(check_dict_type(dst, str, int)):
                if not(check_dict_type(dst, str, tuple, int, str)):
                    raise ValueError("wrong type")
                invalid_w = [x for x in dst.values() if x <= 0]
                if (len(invalid_w) > 0):
                    raise ValueError("invalid weight")                
                dst = {ip_addr_aton(x[0]):(x[1][0], ip_addr_aton(x[1][1]))
                       for x in dst.items()}
            elif (op == 'delete'):
                if not(check_list_type(dst, str)):
                    raise SyntaxError()
                dst = [ip_addr_aton(x) for x in dst]

            ## Work starts
            if (op == 'create'):
                ecmp_id = self.routing_table.create_ecmp_group(dst)
                self.logger.info("Create ecmp group %d",
                                 ecmp_id,
                                 extra = self.sw_id)
                return ecmp_id
            elif (op == 'add'):
                self.routing_table.add_to_ecmp_group(ecmp_id, dst)
            elif (op == 'change'):
                self.routing_table.change_ecmp_weights(ecmp_id, dst)
            elif (op == 'delete'):
                self.routing_table.delete_from_ecmp_group(ecmp_id, dst)
            elif (op == 'destroy'):
                if (not self.routing_table.destroy_ecmp_group(ecmp_id)):
                    msg = ('Fail to destroy ecmp %d, related flows exist'
                           % ecmp_id)
                    raise CommandFailure(msg = msg)
            else:
                return

            self.logger.info('complete operation %s with ecmp_id = %d',
                             op,
                             ecmp_id,
                             extra = self.sw_id)
        except SyntaxError as e:
            msg = "Syntax error %s" % e.message
            raise CommandFailure(msg = msg)
        except ValueError as e:
            msg = "Value error %s" % e.message
            raise CommandFailure(msg = msg)


    ## Create a flow group
    def __create_flow_group(self,
                            priority_str,
                            nw_sip_str,
                            nw_dip_str,
                            sport_str,
                            dport_str,
                            proto_str,
                            new_sip_str,
                            new_dip_str,
                            new_sport_str,
                            new_dport_str,
                            return_gw_str):
        try:
            priority = int(priority_str)

            ## convert matching fields to Match
            match = Match()
            if nw_sip_str:
                _, sip, sip_mask, = nw_addr_aton(nw_sip_str)
                match.m_sip = sip
                match.m_sip_mask = sip_mask
            if nw_dip_str:
                _, dip, dip_mask,  = nw_addr_aton(nw_dip_str)
                match.m_dip = dip
                match.m_dip_mask = dip_mask
            if sport_str:
                match.m_sport = int(sport_str)
            if dport_str:
                match.m_dport = int(dport_str)
            if proto_str:
                match.set_ip_proto(proto_str)

            ## convert rewrite fields to Action
            action = Action()
            if new_sip_str:
                action.m_sip = ip_addr_aton(new_sip_str)
            if new_dip_str:
                action.m_dip = ip_addr_aton(new_dip_str)
            if new_sport_str:
                action.m_sport = int(new_sport_str)
            if new_dport_str:
                action.m_dport = int(new_dport_str)
            if return_gw_str:
                action.m_gateway = ip_addr_aton(return_gw_str)


            fg_id = self.routing_table.create_flow_group(match,
                                                         action,
                                                         priority)
            self.logger.info('create flow group %d', fg_id,
                             extra = self.sw_id)
            return fg_id
        except SyntaxError as e:
            msg = "request syntax error %s" % e.message
            raise CommandFailure(msg = msg)
        except ValueError as e:
            msg = "request value error %S" % e.message
            raise CommandFailure(msg = msg)


    ## apply a defined ecmp policy to a defined flow group
    def __apply_ecmp(self, ecmp_id_str, fg_id_str):
        try:
            ## convert input
            ecmp_id = int(ecmp_id_str)
            fg_id = int(fg_id_str)
            
            self.routing_table.apply_ecmp_to_flow_group(fg_id,
                                                        ecmp_id)
            self.logger.info('apply ecmp %d to flowgroup %d',
                             ecmp_id,
                             fg_id,
                             extra = self.sw_id)
        except SyntaxError as e:
            msg = "request syntax error %s" % e.message
            raise CommandFailure(msg = msg)
        except ValueError as e:
            msg = "request value error %S" % e.message
            raise CommandFailure(msg = msg)
        

    ## destroy a flow group
    def __destroy_flow_group(self, fg_id_str):
        try:
            fg_id = int(fg_id_str)
            self.routing_table.destroy_flow_group(fg_id)
            self.logger.info('destroy flowgroup %d',
                             fg_id,
                             extra = self.sw_id)
        except SyntaxError as e:
            msg = "request syntax error %s" % e.message
            raise CommandFailure(msg = msg)
        except ValueError as e:
            msg = "request value error %S" % e.message
            raise CommandFailure(msg = msg)

    ## ---------- <Set Data>  -------- ##

    ## ---------- Delete Data  -------- ##

    ## delete data from address, ecmp group or flow group
    def delete_data(self, data, waiters):
        details = None
        try:
            if REST_ADDRESSID in data:
                address_id_str = data[REST_ADDRESSID]
                details = self.__delete_address(address_id_str, waiters)
            elif REST_ECMP_ID in data:
                ecmp_id_str = data[REST_ECMP_ID]
                self.__set_ecmp_group(op = 'destroy',
                                      ecmp_id_str = ecmp_id_str)
                details = 'Destroy ecmp group %s' % ecmp_id_str
            elif REST_FLOW_GROUP_ID in data:
                fg_id_str = data[REST_FLOW_GROUP_ID]
                self.__destroy_flow_group(fg_id_str = fg_id_str)
                details = 'Destroy flow group %s' % fg_id_str

        except KeyError as e:
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: "missing required fields"}
            return self._response(msg)
        except SyntaxError as e:
            err_msg = "request syntax error %s" % e.message
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: str(err_msg)}
            return self._response(msg)
        except ValueError as e:
            err_msg = "request value error %s" % e.message
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: str(err_msg)}
            return self._response(msg)
        except CommandFailure as err_msg:
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: str(err_msg)}
            return self._response(msg)

        if (details == None):
            msg = {REST_RESULT: REST_NG,
                   REST_DETAILS: "Invalid parameters"}
        else:
            msg = {REST_RESULT: REST_OK,
                   REST_DETAILS: details}

        return self._response(msg)

    def __delete_address(self, address_id_str, waiters):
        try:
            address_id = int(address_id_str)
        except ValueError as e:
            err_msg = 'Invalid [%s] value. %s'
            raise ValueError(err_msg % (REST_ADDRESSID, e.message))

        if (self.__check_addr_relation_route(address_id)):
            msg = ('Fail to delete address %d, related rules exist'
                   % address_id)
            raise CommandFailure(msg = msg)

        # Get all flow.
        delete_list = []
        msgs = self.ofctl.get_all_flow(waiters)
        max_id = UINT16_MAX
        for msg in msgs:
            for stats in msg.body:
                ## check vlan id
                vlan_id, _ = EcmpRouter.cookie_to_id(REST_VLANID,
                                                       stats.cookie)
                if vlan_id != self.vlan_id:
                    continue
                ## check address id
                addr_id, ctype = (EcmpRouter.cookie_to_id(
                    REST_ADDRESSID,
                    stats.cookie))
                if (not ctype):
                    continue
                if address_id != addr_id:
                    continue
                delete_list.append(stats)

        ## delete address
        delete_ids = []
        for flow_stats in delete_list:
            # Delete flow
            self.ofctl.delete_flow(flow_stats)
            address_id, _ = EcmpRouter.cookie_to_id(REST_ADDRESSID,
                                                    flow_stats.cookie)

            del_addr = self.address_data.get_address(
                address_id = address_id)
            if del_addr is not None:
                # Clean up suspend packet threads.
                self.packet_buffer.delete(del_addr = del_addr)

                # Delete data.
                self.address_data.delete_address(address_id)
                if address_id not in delete_ids:
                    delete_ids.append(address_id)

        ## report the deletion
        msg = {}
        if delete_ids:
            delete_ids = ','.join(str(addr_id) for addr_id in delete_ids)
            details = 'Delete address [address_id=%s]' % delete_ids
            self.logger.info(details, extra = self.sw_id)
            msg = {REST_RESULT: REST_OK, REST_DETAILS: details}

        return msg

    ## Check exist of related routing data.
    def __check_addr_relation_route(self, address_id):
        gateways = self.routing_table.get_gateways()
        for gateway in gateways:
            address = self.address_data.get_address(ip = gateway)
            if address is not None:
                if address.address_id == address_id:
                    return True
        return False

    ## ---------- <Delete Data>  -------- ##

    ## ------------ internal update work ------------- ##

    ## update arp table based on arp msg
    ## TODO: currently arp table never expires
    def __update_arp_table(self, msg, header_list):
        # Set flow: routing to gateway.
        out_port = self.ofctl.get_packetin_inport(msg)
        src_mac = header_list[ARP].src_mac
        dst_mac = self.port_data[out_port].mac
        src_ip = header_list[ARP].src_ip

        self.arp_table.add(dst_ip = src_ip, 
                           dst_mac = src_mac,
                           src_mac = dst_mac,
                           out_port = out_port)
        gw = self.routing_table.get_gateways()
        return src_ip in gw

    def __do_clear(self):
        while (not self._stop):
            if (not self.__clear()):
                if USE_HUB_THREAD:
                    hub.sleep(0.1)
                else:
                    time.sleep(0.1)
    
    ## loop to install rules
    def __do_install(self):
        while (not self._stop):
            if (not self.__install()):
                if USE_HUB_THREAD:
                    hub.sleep(0.1)
                else:
                    time.sleep(0.1)
            else:
                self.logger.info("Install one rule",
                                 extra = self.sw_id)

    ## loop to uninstall rules
    def __do_clear(self, waiters):
        ## query the switch to retrieve the stats
        def get_stats():
            stats_list = []
            msgs = self.ofctl.get_all_flow(waiters)
            for msg in msgs:
                for stats in msg.body:
                    stats_list.append(stats)
            return stats_list

        ## retrieve the flow stats on switches
        stats_list = get_stats()
        latest_stats = True
        while (not self._stop):
            ## check the next rule to clear
            rule = self.routing_table.peek_next_clear_rule()
            if (rule == None):
                if USE_HUB_THREAD:
                    hub.sleep(0.1)
                else:
                    time.sleep(0.1)
                latest_stats = False
            elif (self.__clear_one_rule(stats_list, rule)):
                self.logger.info("Clear one installed rule",
                                 extra = self.sw_id)
                self.routing_table.pop_next_clear_rule()
                latest_stats = False
            elif (latest_stats):
                self.logger.info("Clear on uninstalled rule",
                                 extra = self.sw_id)
                self.routing_table.pop_next_clear_rule()
                latest_stats = False
            else:
                ## if a next rule exist, but cannot clean 
                ## then we will refetch the flow stats
                self.logger.info("Fail to clear a rule, refetch rules",
                                 extra = self.sw_id)
                stats_list = get_stats()
                latest_stats = True

    def __clear_one_rule(self, stats_list, rule):
        delete_list = []
        for stats in stats_list:
            ## Check id, cookie correspondence
            vlan_id, _ = EcmpRouter.cookie_to_id(REST_VLANID,
                                                 stats.cookie)
            if vlan_id != self.vlan_id:
                continue
            rule_id, ctype = EcmpRouter.cookie_to_id(REST_RULEID,
                                                     stats.cookie)
            if (not ctype):
                continue
            if rule_id == rule.m_rule_id:
                delete_list.append(stats)
                
        if (len(delete_list) == 0):
            return False

        ## Delete flows.
        delete_ids = []
        for flow_stats in delete_list:
            self.ofctl.delete_flow(flow_stats)
            rule_id, _ = EcmpRouter.cookie_to_id(REST_RULEID,
                                                 flow_stats.cookie)
            stats_list.remove(flow_stats)
            if rule_id not in delete_ids:
                delete_ids.append(rule_id)

            ## case: Default route deleted. -> set flow (drop)
            rule_type = get_priority_type(flow_stats.priority,
                                          vid = self.vlan_id)
            if rule_type == PRIORITY_DEFAULT_ROUTING:
                self.__set_default_drop()

        msg = {}
        if delete_ids:
            delete_ids = ','.join(str(rule_id) 
                                  for rule_id in delete_ids)
            log_msg = 'Delete rule [rule_id=%s]'
            self.logger.info(log_msg, delete_ids, extra = self.sw_id)

        return True


    ## check rules to install
    ## return True if some rules are installed
    def __install(self):
        ## read the next rule to install
        rule = self.routing_table.peek_next_install_rule()
        if (rule == None):
            return False
        rule_id = rule.m_rule_id
        priority = rule.m_priority
        match = rule.m_match
        action = rule.m_action
        gateway = action.m_gateway
        ## if it is a normal flow
        if (gateway == 0):
            if (action.m_dip == 0 or action.m_dip_mask != UINT32_MAX):
                self.routing_table.pop_next_install_rule(False)
                self.logger.info("Discard a rule %s",
                                 str(rule),
                                 extra = self.sw_id)
                return False

            gateway = action.m_dip

        ## get the arp entry
        entry = self.arp_table.get_entry(gateway)
        if (entry == None):
            self.send_arp_all_gw()
            hub.sleep(ARP_REPLY_TIMER)
            entry = self.arp_table.get_entry(gateway)
            if (entry == None):
                self.routing_table.pop_next_install_rule(False)
                self.logger.info("Unknown gateway for rule %s",
                                 str(rule),
                                 extra = self.sw_id)
                return False

        cookie = self._id_to_cookie(REST_RULEID, rule_id)
        self.ofctl.set_routing_flow(cookie,
                                    priority,
                                    out_port = entry.m_out_port,
                                    dl_vlan = self.vlan_id,
                                    src_ip = match.m_sip,
                                    src_ip_mask = match.m_sip_mask,
                                    dst_ip = match.m_dip,
                                    dst_ip_mask = match.m_dip_mask,
                                    src_port = match.m_sport,
                                    dst_port = match.m_dport,
                                    ip_proto = match.m_ip_proto,
                                    new_src_mac = entry.m_src_mac,
                                    new_dst_mac = entry.m_dst_mac,
                                    new_src_ip = action.m_sip,
                                    new_dst_ip = action.m_dip,
                                    new_src_port = action.m_sport,
                                    new_dst_port = action.m_dport,
                                    dec_ttl = True)

        self.routing_table.pop_next_install_rule()
        self.logger.info('Set flow [cookie=0x%x]',
                         cookie,
                         extra = self.sw_id)
        return True

    ## ------------ <internal update work> ------------- ##

    ## set a default drop rule
    def __set_default_drop(self):
        cookie = self._id_to_cookie(REST_VLANID, self.vlan_id)
        priority = self._get_priority(PRIORITY_DEFAULT_ROUTING)
        out_port = None  # for drop

        self.ofctl.set_routing_flow(cookie,
                                    priority,
                                    out_port,
                                    dl_vlan = self.vlan_id)
        self.logger.info('Set default drop flow [cookie=0x%x]',
                         cookie,
                         extra = self.sw_id)


    ## set packet in for a rule
    def __set_rule_packetin(self, rule):
        rule_id = rule.m_rule_id
        priority = rule.m_priority
        match = rule.m_match
        action = rule.m_action

        cookie = self._id_to_cookie(REST_RULEID, rule_id)

        self.ofctl.set_packetin_flow(cookie,
                                     priority,
                                     dl_type = ether.ETH_TYPE_IP,
                                     dl_vlan = self.vlan_id,
                                     src_ip = match.m_sip,
                                     src_ip_mask = match.m_sip_mask,
                                     dst_ip = match.m_dip,
                                     dst_ip_mask = match.m_dip_mask,
                                     ip_proto = match.m_ip_proto,
                                     src_port = match.m_sport,
                                     dst_port = matchm.m_dport)
        self.logger.info('Set (packet in) flow [cookie=0x%x]',
                         log_msg,
                         cookie,
                         extra = self.sw_id)

        
    ## handle packet in
    def packet_in_handler(self, msg, header_list):
        # Check invalid TTL (for OpenFlow V1.2/1.3)
        ofproto = self.dp.ofproto
        if ofproto.OFP_VERSION == ofproto_v1_2.OFP_VERSION or \
                ofproto.OFP_VERSION == ofproto_v1_3.OFP_VERSION:
            if msg.reason == ofproto.OFPR_INVALID_TTL:
                self._packetin_invalid_ttl(msg, header_list)
                return

        # Analyze event type.
        if ARP in header_list:
            self._packetin_arp(msg, header_list)
            return

        if IPV4 in header_list:
            rt_ports = self.address_data.get_default_gw()
            if header_list[IPV4].dst in rt_ports:
                # Packet to router's port.
                if ICMP in header_list:
                    if header_list[ICMP].type == icmp.ICMP_ECHO_REQUEST:
                        self._packetin_icmp_req(msg, header_list)
                        return
                elif TCP in header_list or UDP in header_list:
                    self._packetin_tcp_udp(msg, header_list)
                    return
            else:
                # Packet to internal host or gateway router.
                self._packetin_to_node(msg, header_list)
                return

    ## handle ARP
    def _packetin_arp(self, msg, header_list):
        src_addr = self.address_data.get_address(
            ip = header_list[ARP].src_ip)
        if src_addr is None:
            return
        # case: Receive ARP from the gateway
        #  Update routing table.
        # case: Receive ARP from an internal host
        #  Learning host MAC.
        gw_flg = self.__update_arp_table(msg, header_list)
        if (not gw_flg):
            self._learning_host_mac(msg, header_list)

        # ARP packet handling.
        in_port = self.ofctl.get_packetin_inport(msg)
        src_ip = header_list[ARP].src_ip
        dst_ip = header_list[ARP].dst_ip
        srcip = ip_addr_ntoa(src_ip)
        dstip = ip_addr_ntoa(dst_ip)
        rt_ports = self.address_data.get_default_gw()

        if src_ip == dst_ip:
            # GARP -> packet forward (normal)
            output = self.ofctl.dp.ofproto.OFPP_NORMAL
            self.ofctl.send_packet_out(in_port, output, msg.data)

            self.logger.info('Receive GARP from [%s].',
                             srcip,
                             extra = self.sw_id)
            self.logger.info('Send GARP (normal).', extra = self.sw_id)

        elif dst_ip not in rt_ports:
            dst_addr = self.address_data.get_address(ip = dst_ip)
            if (dst_addr is not None and
                src_addr.address_id == dst_addr.address_id):
                # ARP from internal host -> packet forward (normal)
                output = self.ofctl.dp.ofproto.OFPP_NORMAL
                self.ofctl.send_packet_out(in_port, output, msg.data)

                self.logger.info('Receive ARP from an internal host [%s].',
                                 srcip, extra = self.sw_id)
                self.logger.info('Send ARP (normal)', extra = self.sw_id)
        else:
            if header_list[ARP].opcode == arp.ARP_REQUEST:
                # ARP request to router port -> send ARP reply
                src_mac = header_list[ARP].src_mac
                dst_mac = self.port_data[in_port].mac
                arp_target_mac = dst_mac
                output = in_port
                in_port = self.ofctl.dp.ofproto.OFPP_CONTROLLER

                self.ofctl.send_arp(arp.ARP_REPLY,
                                    self.vlan_id,
                                    dst_mac,
                                    src_mac,
                                    dst_ip,
                                    src_ip,
                                    arp_target_mac,
                                    in_port,
                                    output)

                log_msg = 'Receive ARP request from [%s] to router port [%s].'
                self.logger.info(log_msg,
                                 srcip,
                                 dstip,
                                 extra = self.sw_id)
                self.logger.info('Send ARP reply to [%s]',
                                 srcip,
                                 extra = self.sw_id)

            elif header_list[ARP].opcode == arp.ARP_REPLY:
                #  ARP reply to router port -> suspend packets forward
                log_msg = 'Receive ARP reply from [%s] to router port [%s].'
                self.logger.info(log_msg,
                                 srcip,
                                 dstip,
                                 extra = self.sw_id)

                packet_list = self.packet_buffer.get_data(src_ip)
                if packet_list:
                    # stop ARP reply wait thread.
                    for suspend_packet in packet_list:
                        self.packet_buffer.delete(pkt = suspend_packet)

                    # send suspend packet.
                    output = self.ofctl.dp.ofproto.OFPP_TABLE
                    for suspend_packet in packet_list:
                        self.ofctl.send_packet_out(suspend_packet.in_port,
                                                   output,
                                                   suspend_packet.data)
                        self.logger.info('Send suspend packet to [%s].',
                                         srcip,
                                         extra = self.sw_id)

    def _packetin_icmp_req(self, msg, header_list):
        # Send ICMP echo reply.
        in_port = self.ofctl.get_packetin_inport(msg)
        self.ofctl.send_icmp(in_port,
                             header_list,
                             self.vlan_id,
                             icmp.ICMP_ECHO_REPLY,
                             icmp.ICMP_ECHO_REPLY_CODE,
                             icmp_data = header_list[ICMP].data)

        srcip = ip_addr_ntoa(header_list[IPV4].src)
        dstip = ip_addr_ntoa(header_list[IPV4].dst)
        log_msg = 'Receive ICMP echo request from %s to router port %s.'
        self.logger.info(log_msg, srcip, dstip, extra = self.sw_id)
        self.logger.info('Send ICMP echo reply to [%s].',
                         srcip,
                         extra = self.sw_id)

    def _packetin_tcp_udp(self, msg, header_list):
        # Send ICMP port unreach error.
        in_port = self.ofctl.get_packetin_inport(msg)
        self.ofctl.send_icmp(in_port,
                             header_list,
                             self.vlan_id,
                             icmp.ICMP_DEST_UNREACH,
                             icmp.ICMP_PORT_UNREACH_CODE,
                             msg_data = msg.data)

        srcip = ip_addr_ntoa(header_list[IPV4].src)
        dstip = ip_addr_ntoa(header_list[IPV4].dst)
        self.logger.info('Receive TCP/UDP from %s to router port %s.',
                         srcip,
                         dstip,
                         extra = self.sw_id)
        self.logger.info('Send ICMP destination unreachable to [%s].',
                         srcip,
                         extra = self.sw_id)

    def _packetin_to_node(self, msg, header_list):
        if len(self.packet_buffer) >= MAX_SUSPENDPACKETS:
            self.logger.info('Packet is dropped, MAX_SUSPENDPACKETS exceeded.',
                             extra = self.sw_id)
            return

        # Send ARP request to get node MAC address.
        in_port = self.ofctl.get_packetin_inport(msg)
        src_ip = None
        dst_ip = header_list[IPV4].dst
        srcip = ip_addr_ntoa(header_list[IPV4].src)
        dstip = ip_addr_ntoa(dst_ip)

        address = self.address_data.get_address(ip = dst_ip)
        if address is not None:
            log_msg = 'Receive IP packet from [%s] to an internal host [%s].'
            self.logger.info(log_msg, srcip, dstip, extra = self.sw_id)
            src_ip = address.addr
        else:
            rule = self.routing_table.get_rule(dip = dst_ip)
            if route is not None:
                log_msg = 'Receive IP packet from [%s] to [%s].'
                self.logger.info(log_msg,
                                 srcip,
                                 dstip,
                                 extra = self.sw_id)
                gateway_ip = rule.m_action.m_gateway
                gw_address = self.address_data.get_address(ip = gateway_ip)
                if gw_address is not None:
                    src_ip = gw_address.addr
                    dst_ip = route.gateway_ip

        if src_ip is not None:
            self.packet_buffer.add(in_port, header_list, msg.data)
            self.send_arp_request(src_ip, dst_ip, in_port = in_port)
            self.logger.info('Send ARP request (flood)',
                             extra = self.sw_id)

    def _packetin_invalid_ttl(self, msg, header_list):
        # Send ICMP TTL error.
        srcip = ip_addr_ntoa(header_list[IPV4].src)
        self.logger.info('Receive invalid ttl packet from [%s].', srcip,
                         extra=self.sw_id)

        in_port = self.ofctl.get_packetin_inport(msg)
        src_ip = self._get_send_port_ip(header_list)
        if src_ip is not None:
            self.ofctl.send_icmp(in_port,
                                 header_list,
                                 self.vlan_id,
                                 icmp.ICMP_TIME_EXCEEDED,
                                 icmp.ICMP_TTL_EXPIRED_CODE,
                                 msg_data = msg.data,
                                 src_ip = src_ip)
            self.logger.info('Send ICMP time exceeded to [%s].',
                             srcip,
                             extra = self.sw_id)

    def send_arp_all_gw(self):
        gateways = self.routing_table.get_gateways()
        for gateway in gateways:
            address = self.address_data.get_address(ip = gateway)
            if address is not None:
                self.send_arp_request(address.addr, gateway)

    def send_arp_request(self, src_ip, dst_ip, in_port=None):
        # Send ARP request from all ports.
        for send_port in self.port_data.values():
            if in_port is None or in_port != send_port.port_no:
                src_mac = send_port.mac
                dst_mac = mac_lib.BROADCAST_STR
                arp_target_mac = mac_lib.DONTCARE_STR
                inport = self.ofctl.dp.ofproto.OFPP_CONTROLLER
                output = send_port.port_no
                self.ofctl.send_arp(arp.ARP_REQUEST,
                                    self.vlan_id,
                                    src_mac,
                                    dst_mac,
                                    src_ip,
                                    dst_ip,
                                    arp_target_mac,
                                    inport,
                                    output)

    def send_icmp_unreach_error(self, packet_buffer):
        # Send ICMP host unreach error.
        self.logger.info('ARP reply wait timer was timed out.',
                         extra=self.sw_id)
        src_ip = self._get_send_port_ip(packet_buffer.header_list)
        if src_ip is not None:
            self.ofctl.send_icmp(packet_buffer.in_port,
                                 packet_buffer.header_list,
                                 self.vlan_id,
                                 icmp.ICMP_DEST_UNREACH,
                                 icmp.ICMP_HOST_UNREACH_CODE,
                                 msg_data = packet_buffer.data,
                                 src_ip = src_ip)

            dstip = ip_addr_ntoa(packet_buffer.dst_ip)
            self.logger.info('Send ICMP destination unreachable to [%s].',
                             dstip,
                             extra = self.sw_id)


    def _learning_host_mac(self, msg, header_list):
        # Set flow: routing to internal Host.
        out_port = self.ofctl.get_packetin_inport(msg)
        src_mac = header_list[ARP].src_mac
        dst_mac = self.port_data[out_port].mac
        src_ip = header_list[ARP].src_ip

        gateways = self.routing_table.get_gateways()
        if src_ip not in gateways:
            address = self.address_data.get_address(ip = src_ip)
            if address is not None:
                cookie = self._id_to_cookie(REST_ADDRESSID, address.address_id)
                priority = self._get_priority(PRIORITY_IMPLICIT_ROUTING)
                self.ofctl.set_routing_flow(cookie,
                                            priority,
                                            out_port,
                                            dl_vlan=self.vlan_id,
                                            new_src_mac = dst_mac,
                                            new_dst_mac = src_mac,
                                            dst_ip = src_ip,
                                            idle_timeout = IDLE_TIMEOUT,
                                            dec_ttl = True)
            self.logger.info('Set implicit routing flow [cookie=0x%x]',
                                 cookie, extra=self.sw_id)

    def _get_send_port_ip(self, header_list):
        try:
            src_mac = header_list[ETHERNET].src
            if IPV4 in header_list:
                src_ip = header_list[IPV4].src
            else:
                src_ip = header_list[ARP].src_ip
        except KeyError:
            self.logger.debug('Receive unsupported packet.',
                              extra = self.sw_id)
            return None

        address = self.address_data.get_address(ip = src_ip)
        if address is not None:
            return address.addr
        else:
            gateway_ip = self.arp_table.get_ip(mac = src_mac)
            if gateway_ip is not None:
                address = self.address_data.get_address(ip = gateway_ip)
                if address is not None:
                    return address.addr

        self.logger.debug('Receive packet from unknown IP[%s].',
                          ip_addr_ntoa(src_ip), 
                          extra = self.sw_id)
        return None



class SuspendPacketList(list):
    def __init__(self, timeout_function):
        super(SuspendPacketList, self).__init__()
        self.timeout_function = timeout_function

    def add(self, in_port, header_list, data):
        suspend_pkt = SuspendPacket(in_port, header_list, data,
                                    self.wait_arp_reply_timer)
        self.append(suspend_pkt)

    def delete(self, pkt = None, del_addr = None):
        if pkt is not None:
            del_list = [pkt]
        else:
            assert del_addr is not None
            del_list = [pkt for pkt in self if pkt.dst_ip in del_addr]

        for pkt in del_list:
            self.remove(pkt)
            hub.kill(pkt.wait_thread)
            pkt.wait_thread.wait()

    def get_data(self, dst_ip):
        return [pkt for pkt in self if pkt.dst_ip == dst_ip]

    def wait_arp_reply_timer(self, suspend_pkt):
        hub.sleep(ARP_REPLY_TIMER)
        if suspend_pkt in self:
            self.timeout_function(suspend_pkt)
            self.delete(pkt=suspend_pkt)


class SuspendPacket(object):
    def __init__(self, in_port, header_list, data, timer):
        super(SuspendPacket, self).__init__()
        self.in_port = in_port
        self.dst_ip = header_list[IPV4].dst
        self.header_list = header_list
        self.data = data
        # Start ARP reply wait timer.
        self.wait_thread = hub.spawn(timer, self)
