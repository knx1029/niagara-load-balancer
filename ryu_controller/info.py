from utils import *

import ast
import copy
import threading
from threading import Thread
from string import maketrans
import time
from ryu.lib import hub



## count the non-wildcard bits in the match
def get_default_match_priority(match):
    p = 1
    v = match.m_sip_mask
    while (v > 0):
        p += (v & 1)
        v = v >> 1
    v = match.m_dip_mask
    while (v > 0):
        p += (v & 1)
        v = v >> 1
    if (match.m_ip_proto):
        p += 1
    if (match.m_sport):
        p += 1
    if (match.m_dport):
        p += 1
    return p


## a single ecmp group
## dst_weights = {dst_ip: (weight, gw_ip)}
## if gw_ip == None then no NAT
## elif gw_ip == "" then NAT to dst_ip
## else NAT to dst_ip and forward to gw_ip
class EcmpGroup(Lockable):


    def __init__(self, ecmp_id, dst_weights):
        Lockable.__init__(self)
        self.m_ecmp_id = ecmp_id
        
        self.m_dst = {x[0]:x[1][0] for x in dst_weights.items()}
        self.m_nat = EcmpGroup._parse_parameter(dst_weights)


    @staticmethod
    def _parse_parameter(dst_weights):
        def f(s1, s2):
            if (s2 == None):
                return None
            elif (len(s2) == 0):
                return s1
            else:
                return s2

        return {x[0]:f(x[0], x[1][1]) for x in dst_weights.items()}
                
    def add(self, dst_weights):
        with self.m_lock:
            dst = {x[0]:x[1][0] for x in dst_weights.items()}
            nat = EcmpGroup._parse_parameter(dst_weights)
            self.m_dst.update(dst)
            self.m_nat.update(nat)

    def update(self, dst_weights):
        with self.m_lock:
            dst = {x[0]:x[1][0] for x in dst_weights.items()}
            nat = EcmpGroup._parse_parameter(dst_weights)
            self.m_dst.update(dst)
            self.m_nat.update(nat)

    def delete(self, dst_list):
        with self.m_lock:
            for dst in dst_list:
                self.m_dst.pop(dst, None)
                self.m_nat.pop(dst, None)

    def get_gateways(self):
        with self.m_lock:
            gw_set = []
            for dst in self.m_dst.keys():
                if self.m_nat[dst] == None:
                    gw_set.append(dst)
                else:
                    gw_set.append(self.m_nat[dst])
            return gw_set

    def get_data(self):
        with self.m_lock:
            data = {dst : (w, self.m_nat[dst]) 
                    for (dst, w) in self.m_dst.items()}
            return repr(data)

    def show(self):
        data = self.get_data()
        print ", ".join(data)


## ecmp policy that contains many groups and compute rules
class EcmpPolicy(Lockable):

    ## insert ecmp group acquires the policy lock
    ## modify and destroy acquires the group lock

    def __init__(self):
        Lockable.__init__(self)
        self.m_ecmp_id = 0
        self.m_groups = dict()

    def create_ecmp_group(self, dst_weights):
        ecmp_id = 0
        with self.m_lock:
            self.m_ecmp_id += 1
            ecmp_id = self.m_ecmp_id

        ecmp_group = EcmpGroup(ecmp_id, dst_weights)
        self.m_groups[ecmp_id] = ecmp_group
        return ecmp_id

    def destroy_ecmp_group(self, ecmp_id):
        try:
            ecmp_group = self.m_groups[ecmp_id]
            ecmp_id = ecmp_group.m_ecmp_id
            self.m_groups.pop(ecmp_id, None)
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def add_to_ecmp_group(self, ecmp_id, dst_weights):
        try:
            ecmp_group = self.m_groups[ecmp_id]
            ecmp_group.add(dst_weights)
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def delete_from_ecmp_group(self, ecmp_id, dst_list):
        try:
            ecmp_group = self.m_groups[ecmp_id]
            ecmp_group.delete(dst_list)
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def change_ecmp_weights(self, ecmp_id, dst_weights):
        try:
            ecmp_group = self.m_groups[ecmp_id]
            ecmp_group.update(dst_weights)
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def __getitem__(self, ecmp_id):
        return self.m_groups[ecmp_id]

    def get_gateways(self):
        gw_set = set()
        groups = list(self.m_groups.values())
        for ecmp_group in groups:
            gw_list = ecmp_group.get_gateways()
            gw_set.update(gw_list)

        return gw_set


    ## for now, we assume mode is always 0,
    ## meaning matching on the lower bits of sip
    def apply(self,
              ecmp_id,
              rules,
              mode = 0,
              match = Match(),
              action = Action()):

        ## rewrite the pattern
        def get_value_and_mask(pattern):
            transtab = maketrans("*01","001")
            value = pattern.translate(transtab)
            transtab = maketrans("*01", "011")
            mask = pattern.translate(transtab)
            return value, mask

        def get_value_and_mask_int(pattern):
            value, mask = get_value_and_mask(pattern)
            return int(value, 2), int(mask, 2)

        ## work starts here
        try:
            ecmp_group = self.m_groups[ecmp_id]

            ecmp_group.lock() 

            applied_rules = []
            ## for incoming packets
            for (priority, (pattern, dst)) in rules:
                applied_match = copy.copy(match)
                applied_action = copy.copy(action)
                if (mode == 0):
                    sip, mask = get_value_and_mask_int(pattern)
                    if ((applied_match.m_sip_mask & mask) != 0):
                        msg = "Cannot apply ecmp, invalid match"
                        raise CommandFailure(msg = msg)
#                    if (applied_action.m_gateway or
                    if (applied_action.m_dip and ecmp_group.m_nat[dst] != None):
                        msg = "Cannot apply ecmp, invalid action"
                        raise CommandFailure(msg = msg)

                    ## change mask
                    applied_match.m_sip_mask |= mask
                    ## change source ip
                    sip_int = ipv4_text_to_int(applied_match.m_sip)
                    sip_int |= sip
                    applied_match.m_sip = ipv4_int_to_text(sip_int)
                    ## change gateway
                    if ecmp_group.m_nat[dst] != None:
                        applied_action.m_gateway = ecmp_group.m_nat[dst]
                        applied_action.m_dip = dst
                    else:
                        applied_action.m_gateway = dst
                    applied_rules.append((priority,
                                          applied_match,
                                          applied_action))
                else:
                    raise NotImplementedError()

            ## hack here to get reverse NAT working
            if (match.m_dip_mask == UINT32_MAX):

                reversed_match = match.reverse()
                default_priority = 0
                for dst, gw in ecmp_group.m_nat.items():
                    if gw != None:
                        applied_match = copy.copy(reversed_match)
                        ## Matches on the DNAT IP
                        applied_match.m_sip = dst
                        ## SNAT the sip back
                        applied_action = Action(sip = match.m_dip,
                                                gateway = action.m_gateway)
                        applied_rules.append((default_priority,
                                              applied_match,
                                              applied_action))
                                          

            ecmp_group.unlock()
            return applied_rules

        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def get_data(self):
        data = {}
        groups = list(self.m_groups.values())
        for ecmp_group in groups:
            ecmp_id = ecmp_group.m_ecmp_id
            eg_data = ecmp_group.get_data()
            data[ecmp_id] = eg_data

        return data
        

    def show(self):
        with self.m_lock:
            print "show ecmp policy"
            data = self.get_data()
            for ecmp_id, eg_str in data.items():
                print "ecmp_group %d: " % ecmp_id, eg_str



## immutable flow group that should be applied by the same ecmp group
class FlowGroup():
    def __init__(self, 
                 match = Match(),
                 action = Action(),
                 fg_id = 0,
                 priority = 0):

        self.m_fg_id = fg_id
        self.m_match = match
        self.m_action = action
        self.m_priority = priority

    def __str__(self):
        return "id:%d, p:%d, m:%s, a:%s" % (self.m_fg_id,
                                            self.m_priority,
                                            str(self.m_match),
                                            str(self.m_action))

    def get_data(self):
        return str(self)

    def show(self):
        print self.get_data()


## store flow groups
class FlowGroupTable(Lockable):

    def __init__(self):
        Lockable.__init__(self)
        self.m_fg_id = 0
        self.m_groups = dict()

    ## acquire global lock when creating or destroying group

    def create_flow_group(self,
                          match = Match(),
                          action = Action(),
                          priority = 0):

        ## key is (src_ip, src_ip_mask, dst_ip, dst_ip_mask)
        key = match.id()
        fg_ids = list(self.m_groups.keys())
        for fg_id in fg_ids:
            fg = self.m_groups[fg_id]
            fg_key = fg.m_match.id()
            if (fg_key == key):
                msg = 'Duplicated flow group for key=%s' % key
                raise CommandFailure(msg = msg)

        if (priority > MAX_FG_PRIORITY):
            msg = 'priority too big %d (> %d)' % (priority, MAX_FG_PRIORITY)
            raise CommandFailure(msg = msg)

        ## allocate fg_id
        with self.m_lock:
            self.m_fg_id += 1
            self.m_fg_id &= UINT32_MAX
            fg_id = self.m_fg_id

        ## create flow group
        if (priority == 0):
            priority = get_default_match_priority(match)


        flow_group = FlowGroup(fg_id = fg_id,
                               match = match,
                               action = action,
                               priority = priority)

        self.m_groups[fg_id] = flow_group

        return flow_group

    def __getitem__(self, fg_id):
        return self.m_groups[fg_id]
            

    def destroy_flow_group(self, fg_id):
        self.m_groups.pop(fg_id, None)
        
    def get_flow_group(self,
                       fg_id = 0,
                       sip = 0,
                       dip = 0,
                       ip_proto = 0,
                       sport = 0,
                       dport = 0):

        fgs = list(self.m_groups.values())

        best_fg = None
        for fg in fgs:
            matched = True
            if (matched and fg_id and fg.m_fg_id != fg_id):
                matched = False
                continue

            match = fg.m_match
            if (matched):
                matched = match.match(sip = sip,
                                      dip = dip,
                                      ip_proto = ip_proto,
                                      sport = sport,
                                      dport = dport)
            if (matched):
                if (best_fg == None or
                    fg.m_priority > best_fg.m_priority):
                    best_fg = fg
        return best_fg


    def get_data(self):
        data = {}
        fgs = list(self.m_groups.values())
        data = {fg.m_fg_id : fg.get_data()
                for fg in fgs}
        return data

    def show(self):
        data = self.get_data()
        for fg_id, fg_str in data.items():
            print "flow group %d " % fg_id, fg_str

