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


def get_global_priority(eg_priority, fg_priority, mark):
    p = ((eg_priority & RULE_PRIORITY_MASK) +
         (fg_priority << FG_PRIORITY_SHIFT) +
         (mark << PRIORITY_BASE_SHIFT))
    return p


def get_global_priority_for_rules(fg_priority,
                                  fg_id,
                                  mark,
                                  rules):
        
    def f(rule):
        # rule_id, priority, match, action
        rule_id, (p, match, action) = rule
        priority = get_global_priority(eg_priority = p,
                                       fg_priority = fg_priority,
                                       mark = mark)
        return Rule(rule_id, fg_id, priority, match, action)

    return map(f, rules)

class Rule:
    def __init__(self,
                 rule_id = 0,
                 fg_id = 0,
                 priority = 0,
                 match = Match(),
                 action = Action()):

        self.m_rule_id = rule_id
        self.m_fg_id = fg_id
        self.m_priority = priority
        self.m_match = match
        self.m_action = action

    def __str__(self):
        return "id:{0},fg:{1},p:{2},m:{3},a:{4}".format(
            self.m_rule_id,
            self.m_fg_id,
            hex(self.m_priority),
            self.m_match,
            self.m_action)

    @staticmethod
    def parse_rule(s):
        tokens = s.rsplit(',')
        for token in tokens:
            xs = token.rsplit(':')
            if (xs[0] == 'id'):
                rule_id = int(xs[1], 0)
            elif (xs[0] == 'fg'):
                fg_id = int(xs[1], 0)
            elif (xs[0] == 'p'):
                priority = int(xs[1], 0)
            elif (xs[0] == 'm'):
                match = Match.parse_match(xs[1])
            elif (xs[0] == 'a'):
                action = Action.parse_action(xs[1])

        return Rule(rule_id = rule_id,
                    priority = priority,
                    fg_id = fg_id,
                    match = match,
                    action = action)
            

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

    ARGV = ["-mode", "multi_vip",
            "-ecmp", "none",
            "-heu", "-error", "0.001"]

    ## insert ecmp group acquires the policy lock
    ## modify and destroy acquires the group lock

    def __init__(self):
        Lockable.__init__(self)
        self.m_ecmp_id = 0
        self.m_groups = dict()
        self.m_id2rules = dict()

    def create_ecmp_group(self, dst_weights):
        ecmp_id = 0
        with self.m_lock:
            self.m_ecmp_id += 1
            ecmp_id = self.m_ecmp_id

        ecmp_group = EcmpGroup(ecmp_id, dst_weights)

        ecmp_group.lock()

        self.m_groups[ecmp_id] = ecmp_group
        self.m_id2rules[ecmp_id] = []
        self.__compute_abstract_rules(ecmp_id, ecmp_group)

        ecmp_group.unlock()

        return ecmp_id

    def destroy_ecmp_group(self, ecmp_id):
        try:
            ecmp_group = self.m_groups[ecmp_id]

            ecmp_group.lock()

            ecmp_id = ecmp_group.m_ecmp_id
            self.m_groups.pop(ecmp_id, None)
            self.m_id2rules.pop(ecmp_id, None)

            ecmp_group.unlock()
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def add_to_ecmp_group(self, ecmp_id, dst_weights):
        try:
            ecmp_group = self.m_groups[ecmp_id]

            ecmp_group.lock()

            ecmp_group.add(dst_weights)
            self.__compute_abstract_rules(ecmp_id, ecmp_group)

            ecmp_group.unlock()
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def delete_from_ecmp_group(self, ecmp_id, dst_list):
        try:
            ecmp_group = self.m_groups[ecmp_id]

            ecmp_group.lock()

            ecmp_group.delete(dst_list)
            self.__compute_abstract_rules(ecmp_id, ecmp_group)

            ecmp_group.unlock()
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def change_ecmp_weights(self, ecmp_id, dst_weights):
        try:
            ecmp_group = self.m_groups[ecmp_id]

            ecmp_group.lock()

            ecmp_group.update(dst_weights)
            self.__compute_abstract_rules(ecmp_id, ecmp_group)

            ecmp_group.unlock()
        except KeyError:
            msg = "unknown ecmp_id = %d" % ecmp_id
            raise CommandFailure(msg = msg)

    def get_gateways(self):
        gw_set = set()
        groups = list(self.m_groups.values())
        for ecmp_group in groups:
            ecmp_group.lock()
            gw_list = ecmp_group.get_gateways()
            gw_set.update(gw_list)
            ecmp_group.unlock()

        return gw_set


    ## for now, we assume mode is always 0,
    ## meaning matching on the lower bits of sip
    def apply(self,
              ecmp_id,
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

            rules = self.m_id2rules[ecmp_id]
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

    ## compute the abstract rule for ecmp_id
    ## must be called while holding ecmp_group's lock
    def __compute_abstract_rules(self,
                                 ecmp_id,
                                 ecmp_group):

        args = parse_args(EcmpPolicy.ARGV)
        if (ecmp_group == None):
            ecmp_group = self.m_groups[ecmp_id]

        ## get the weights
        total_w = sum(ecmp_group.m_dst.values())
        dst_weights = [(x[0], x[1] * 1.0 / total_w) 
                      for x in ecmp_group.m_dst.items()]
        n_weights = len(dst_weights)
        weights = zip(range(0, n_weights),
                      map(lambda x:x[1], dst_weights))

        if (n_weights == 0):
            self.m_id2rules[ecmp_id] = []
            return

        ## call multiple vip algorithm, although it is only one VIP
        rules, imb = solve_multi_vip(args,
                                     [(0, 1.0, weights)],
                                     MAX_NUM_RULES)

        ## reverse the prefix matching and add gateway
        def f(rule):
            return (rule[0][::-1], (dst_weights[rule[1]][0]))

        rules_with_dst = map(f, rules)
        rules_with_priority = zip(range(0, len(rules_with_dst)),
                                  rules_with_dst)

        self.m_id2rules[ecmp_id] = rules_with_priority


    def get_data(self):
        data = {}
        ecmp_ids = list(self.m_groups.keys())
        for ecmp_id in ecmp_ids:
            try:
                ecmp_group = self.m_groups[ecmp_id]
                
                ecmp_group.lock()

                eg_data = ecmp_group.get_data()
#                eg = ", ". join(eg_data)
                rules = ["{}".format(k)
                         for k in self.m_id2rules[ecmp_id]]
                ecmp_group.unlock()

                data[ecmp_id] = (eg_data, rules)

            except KeyError:
                pass

        return data
        

    def show(self):
        print "show ecmp policy"
        data = self.get_data()
        for ecmp_id, (eg_str, rules_str) in data.items():
            print "ecmp_group %d: " % ecmp_id, eg_str
            print "abstract rule with priority"
            print "\n".join(rules_str)
            print ""


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
            match = fg.m_match
            if (matched and fg_id and fg.m_fg_id != fg_id):
                matched = False
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


class FGRuleStatus():
    STABLE = 1
    UPDATING = 2
    CLEARING = 3


## stores all the rules for one flow group
## in different phases (using, installing, clearing, pending)
class FGRuleStore(Lockable):

    def __init__(self, fg_id, priority):
        Lockable.__init__(self)
        self.m_priority = priority
        self.m_fg_id = fg_id
        self.m_active_version = 1
        self.m_using = []
        self.m_installing = None
        self.m_clearing = None
        self.m_pending = None

    def append(self, new_rules):
        with self.m_lock:
            self.m_pending = new_rules

    ## must be called with self.m_lock
    def __status(self):
        # stable is no installing and no clearing.
        if (self.m_installing == None) and (self.m_clearing == None):
            return FGRuleStatus.STABLE
        # stable is installing is not None
        elif (self.m_installing != None):
            return FGRuleStatus.UPDATING
        # stable is clearing is not None
        elif (self.m_clearing != None):
            return FGRuleStatus.CLEARING

    def check_destroyable(self):
        with self.m_lock:
            return (self.__status() == FGRuleStatus.STABLE and
                    self.m_pending == None and
                    len(self.m_using) == 0)

    def check_and_update(self):
        with self.m_lock:
            if (self.__status() == FGRuleStatus.STABLE and 
                self.m_pending != None):
                self.m_installing = get_global_priority_for_rules(
                    fg_priority = self.m_priority,
                    fg_id = self.m_fg_id,
                    mark = self.m_active_version ^ 1,
                    rules = self.m_pending);
                self.m_pending = None
                return self.m_installing
            else:
                return None

    def finish_update_and_clear(self):
        with self.m_lock:
            if (self.__status() != FGRuleStatus.UPDATING):
                return None
            self.m_clearing = self.m_using
            self.m_using = self.m_installing
            self.m_active_version ^= 1
            self.m_installing = None
            return self.m_clearing

    def finish_clear_and_stablize(self):
        with self.m_lock:
            if (self.__status() != FGRuleStatus.CLEARING):
                return False
            self.m_clearing = None
            return True


    def get_data(self):

        def __rules2str(rules):
#            print rules
            if (rules == None):
                return None
            elif (len(rules) == 0):
                return []
            elif (isinstance(rules[0], Rule)):
                return [str(x) for x in rules]
            elif (len(rules[0]) == 4):
                return ["(id:{0},p:{1},m:{2},a:{3})".format(
                        x[0], x[1], str(x[2]), str(x[3]))
                        for x in rules]
            elif (len(rules[0]) == 2):
                return ["(id:{0},p:{1},m:{2},a:{3})".format(
                        x[0], x[1][0], str(x[1][1]), str(x[1][2]))
                        for x in rules]
            return None

        def __status2str(status):
            if (status == FGRuleStatus.STABLE):
                return "STABLE"
            elif (status == FGRuleStatus.UPDATING):
                return "UPDATING"
            elif (status == FGRuleStatus.CLEARING):
                return "CLEARING"
            return "UNKNOWN"

        with self.m_lock:
            status = ("priority=%d, status=%s" % 
                      (self.m_priority, __status2str(self.__status())))
            rules = {"using" : __rules2str(self.m_using),
                     "installing" : __rules2str(self.m_installing),
                     "pending" : __rules2str(self.m_pending),
                     "clearing" : __rules2str(self.m_clearing)}

            return (status, rules)


    def show(self):
        (status, rules) = self.get_data()
        print status
        for (t, r) in rules.items():
            print t
            if r == None:
                print "None"
            else:
                print "[",
                print "\n".join(r),
                print "]"

        print ""


## manage all the flow groups and ecmp groups
## store rules and push flow mod
class RoutingTable(Lockable):

    def __init__(self, logger, sw_id):
        Lockable.__init__(self)
        self.m_rule_id = 1
        self.m_fg_table = FlowGroupTable()
        self.m_policy = EcmpPolicy()

        self.m_fg2store = dict()
        self.m_ecmp2fg = dict()
        self.m_fg2ecmp = dict()

        self.m_installing_queue = deque()
        self.m_install_fgs = dict()
        self.m_install_lock = threading.RLock()

        self.m_clearing_queue = deque()
        self.m_clear_fgs = dict()
        self.m_clear_lock = threading.RLock()

        self.m_destroy_fgs = set()
        self.m_active_rules = dict()
        self.m_empty_ecmp_id = self.create_ecmp_group({})

        ## set logger
        self.logger = logger
        self.sw_id = sw_id


    def start(self):

        def check_install():
            self.logger.info("RoutingTable starts checking install",
                             extra = self.sw_id)
            while (not self.m_check_install_stop):
                self.install()
                if USE_HUB_THREAD:
                    hub.sleep(0.1)
                else:
                    time.sleep(0.1)
            self.logger.info("RoutingTable finishes checking install",
                             extra = self.sw_id)


        def check_clear():
            self.logger.info("RoutingTable starts checking clear",
                             extra = self.sw_id)
            while (not self.m_check_clear_stop):
                self.clear()
                if USE_HUB_THREAD:
                    hub.sleep(0.1)
                else:
                    time.sleep(0.1)
            self.logger.info("RoutingTable finishes checking clear",
                              extra = self.sw_id)

        def check_done():
            self.logger.info("RoutingTable starts checking done",
                             extra = self.sw_id)
            while (not self.m_check_done_stop):
                self.done()
                if USE_HUB_THREAD:
                    hub.sleep(0.1)
                else:
                    time.sleep(0.1)
            self.logger.info("RoutingTable finishes checking done",
                              extra = self.sw_id)


        self.m_check_install_stop = False
        self.m_check_clear_stop = False
        self.m_check_done_stop = False

        if USE_HUB_THREAD:
            self.m_install_thread = hub.spawn(check_install)
            self.m_clear_thread = hub.spawn(check_clear)
            self.m_done_thread = hub.spawn(check_done)
        else:
            self.m_install_thread = Thread(target = check_install)
            self.m_clear_thread = Thread(target = check_clear)
            self.m_done_thread = Thread(target = check_done)
            self.m_install_thread.start()
            self.m_clear_thread.start()
            self.m_done_thread.start()

    def stop(self):
        self.m_check_install_stop = True
        self.m_check_clear_stop = True
        self.m_check_done_stop = True

        if USE_HUB_THREAD:
            hub.joinall([self.m_install_thread,
                         self.m_clear_thread,
                         self.m_done_thread])
            hub.kill(self.m_install_thread)
            hub.kill(self.m_clear_thread)
            hub.kill(self.m_done_thread)
        else:
            self.m_install_thread.join()
            self.m_clear_thread.join()
            self.m_done_thread.join()


    def create_ecmp_group(self, dst_weights):
        ecmp_id = self.m_policy.create_ecmp_group(dst_weights)
        with self.m_lock:
            self.m_ecmp2fg[ecmp_id] = []
            return ecmp_id

    def add_to_ecmp_group(self, ecmp_id, dst_weights):
        with self.m_lock:
            if (ecmp_id not in self.m_ecmp2fg or
                ecmp_id == self.m_empty_ecmp_id):
                msg = "unknown ecmp_id = %d" % ecmp_id
                raise CommandFailure(msg = msg)

            self.m_policy.add_to_ecmp_group(ecmp_id, dst_weights)
            id_store = self.m_ecmp2fg[ecmp_id]
            fg_ids = list(id_store)
            self.__append_update(fg_ids, ecmp_id)


    def delete_from_ecmp_group(self, ecmp_id, dst_list):
        with self.m_lock:
            if (ecmp_id not in self.m_ecmp2fg or
                ecmp_id == self.m_empty_ecmp_id):
                msg = "unknown ecmp_id = %d" % ecmp_id
                raise CommandFailure(msg = msg)

            self.m_policy.delete_from_ecmp_group(ecmp_id, dst_list)
            id_store = self.m_ecmp2fg[ecmp_id]
            fg_ids = list(id_store)
            self.__append_update(fg_ids, ecmp_id)

    def change_ecmp_weights(self, ecmp_id, dst_weights):
        with self.m_lock:
            if (ecmp_id not in self.m_ecmp2fg or
                ecmp_id == self.m_empty_ecmp_id):
                msg = "unknown ecmp_id = %d" % ecmp_id
                raise CommandFailure(msg = msg)

            self.m_policy.change_ecmp_weights(ecmp_id, dst_weights)
            id_store = self.m_ecmp2fg[ecmp_id]
            fg_ids = list(id_store)
            self.__append_update(fg_ids, ecmp_id)


    def destroy_ecmp_group(self, ecmp_id):
        with self.m_lock:
            if (ecmp_id not in self.m_ecmp2fg or
                ecmp_id == self.m_empty_ecmp_id):
                msg = "unknown ecmp_id = %d" % ecmp_id
                raise CommandFailure(msg = msg)
            id_store = self.m_ecmp2fg[ecmp_id]
            if (len(id_store) > 0):
                return False
            self.m_ecmp2fg.pop(ecmp_id, None)
            self.m_policy.destroy_ecmp_group(ecmp_id)
            return True


    def create_flow_group(self,
                          match,
                          action,
                          priority = 0):

        flow_group= self.m_fg_table.create_flow_group(match,
                                                      action,
                                                      priority)
        with self.m_lock:
            fg_id = flow_group.m_fg_id
            store = FGRuleStore(
                fg_id = fg_id,
                priority = flow_group.m_priority)
            ecmp_id = self.m_empty_ecmp_id
            self.m_ecmp2fg[ecmp_id].append(fg_id)
            self.m_fg2store[fg_id] = store
            self.m_fg2ecmp[fg_id] = ecmp_id

            return fg_id

    def apply_ecmp_to_flow_group(self, fg_id, ecmp_id):
        with self.m_lock:
            if ((fg_id in self.m_destroy_fgs) and
                (ecmp_id != self.m_empty_ecmp_id)):
                msg = "flow group %d is being deleted" % fg_id
                raise CommandFailure(msg = msg)
            if ((fg_id not in self.m_fg2ecmp) or
                (ecmp_id not in self.m_ecmp2fg)):
                msg = ("unknown flow group id %d or ecmp_id %d" % 
                       (fg_id, ecmp_id))
                raise CommandFailure(msg = msg)

            old_ecmp_id = self.m_fg2ecmp[fg_id]
            if (old_ecmp_id == ecmp_id and ecmp_id != self.m_empty_ecmp_id):
                return
            self.m_ecmp2fg[old_ecmp_id].remove(fg_id)
            self.m_ecmp2fg[ecmp_id].append(fg_id)
            self.m_fg2ecmp[fg_id] = ecmp_id
            self.__append_update([fg_id], ecmp_id)
    
    ## destory flow group, first empty its rules
    def destroy_flow_group(self, fg_id):
        with self.m_lock:
            if (fg_id in self.m_destroy_fgs):
                return
            if (fg_id not in self.m_fg2ecmp):
                msg = "unknown flow group id %d" % fg_id
                raise CommandFailure(msg = msg)
            self.m_destroy_fgs.add(fg_id)
            self.apply_ecmp_to_flow_group(fg_id,
                                          self.m_empty_ecmp_id)


    def __destroy_flow_group(self, fg_id):
        with self.m_lock:
            self.m_fg_table.destroy_flow_group(fg_id)
            self.m_ecmp2fg[self.m_empty_ecmp_id].remove(fg_id)
            self.m_fg2ecmp.pop(fg_id, None)
            self.m_fg2store.pop(fg_id, None)
            self.m_destroy_fgs.remove(fg_id)


    def __append_update(self, fg_ids, ecmp_id):
        for fg_id in fg_ids:
            with self.m_lock:
                if ((fg_id not in self.m_fg2ecmp) or
                    (ecmp_id not in self.m_ecmp2fg)):
                    continue

                store = self.m_fg2store[fg_id]
                fg = self.m_fg_table[fg_id]
                rules = self.m_policy.apply(ecmp_id,
                                            match = fg.m_match,
                                            action = fg.m_action)
                rule_count = len(rules)
                rule_id_beg = self.m_rule_id
                self.m_rule_id += rule_count
                rule_id_end = self.m_rule_id

                fg_rules = zip(range(rule_id_beg, rule_id_end),
                               rules)
                store.append(fg_rules)

    ## pull out installing
    def install(self):
        fg_ids = list(self.m_fg2store.keys())
        for fg_id in fg_ids:
            try:
                store = self.m_fg2store[fg_id]
                installing = store.check_and_update()
                if (installing != None):
                    installing_w_id = map(lambda x: (fg_id, x),
                                          installing)
                    self.m_install_fgs[fg_id] = len(installing)
                    self.m_installing_queue.extend(installing_w_id)
            except KeyError:
                pass


    ## pull out clearing
    def clear(self): 
        fg_ids = list(self.m_install_fgs.keys())
        updated_ids = [fg_id for fg_id in fg_ids
                       if self.m_install_fgs[fg_id] == 0]

        for fg_id in fg_ids:
            if (self.m_install_fgs[fg_id] == 0):
                self.m_install_fgs.pop(fg_id, None)
                store = self.m_fg2store[fg_id]
                clearing = store.finish_update_and_clear()
                if (clearing != None):
                    clearing_w_id = map(lambda x: (fg_id, x),
                                        clearing)
                    self.m_clear_fgs[fg_id] = len(clearing)
                    self.m_clearing_queue.extend(clearing_w_id)


    ## pull out done
    def done(self):
        fg_ids = list(self.m_clear_fgs.keys())
        for fg_id in fg_ids:
            if (self.m_clear_fgs[fg_id] == 0):
                self.m_clear_fgs.pop(fg_id, None)
                store = self.m_fg2store[fg_id]
                store.finish_clear_and_stablize()
                if (fg_id in self.m_destroy_fgs
                    and store.check_destroyable()):
                    self.__destroy_flow_group(fg_id)


    def pop_next_install_rule(self, success = True):
        if (len(self.m_installing_queue) == 0):
            return None
        data = self.m_installing_queue.popleft()
        (fg_id, rule) = data
        rid = rule.m_rule_id
        with self.m_install_lock:
            self.m_install_fgs[fg_id] = self.m_install_fgs[fg_id] - 1
        if (success):
            self.m_active_rules[rid] = rule
        else:
            ## if one failed then the ecmp apply must be removed
            self.logger.info("Failed to install rules for flow group %d"
                             + ", and will uninstall all",
                             fg_id,
                             extra = self.sw_id)
            self.apply_ecmp_to_flow_group(fg_id, self.m_empty_ecmp_id)
        return rule

    def peek_next_install_rule(self):
        if (len(self.m_installing_queue) == 0):
            return None
        data = self.m_installing_queue[0]
        (fg_id, rule) = data
        return rule

    def pop_next_clear_rule(self, success = True):
        if (len(self.m_clearing_queue) == 0):
            return None
        data = self.m_clearing_queue.popleft()
        (fg_id, rule) = data
        rid = rule.m_rule_id
        with self.m_clear_lock:
            self.m_clear_fgs[fg_id] = self.m_clear_fgs[fg_id] - 1
        self.m_active_rules.pop(rid, None)
        return rule

    def peek_next_clear_rule(self):
        if (len(self.m_clearing_queue) == 0):
            return None
        data = self.m_clearing_queue[0]
        (fg_id, rule) = data
        return rule


    def get_gateways(self):
        return self.m_policy.get_gateways()

    def get_rule(self,
                 sip = 0,
                 dip = 0,
                 ip_proto = 0,
                 sport = 0,
                 dport = 0):
        rids = list(self.m_active_rules.keys())
        best_rule = None
        for rid in rids:
            try:
                rule = self.m_active_rules[rid]
                _, p, match, action = rule
                if (match.match(sip = sip,
                                dip = dip,
                                ip_proto = ip_proto,
                                sport = sport,
                                dport = dport)):
                    if best_rule == None or best_rule[1] < p:
                        best_rule = rule
            except KeyError:
                pass
                        
        return best_rule

    def get_ecmp_group_data(self):
        with self.m_lock:
            data = self.m_policy.get_data()
            return data

    def get_flow_group_data(self):
        with self.m_lock:
            data = self.m_fg_table.get_data()
            return data

    def get_fg2ecmp_data(self):
        with self.m_lock:
            data = str(self.m_fg2ecmp)
            return data

    def get_active_rules_data(self):
        with self.m_lock:
            rules = sorted(self.m_active_rules.values(),
                           key = lambda r: r.m_priority,
                           reverse = True)
            data = ["{}".format(x) for x in rules]

            return data


    def get_install_rules_data(self):
        with self.m_lock:
            rules = sorted(self.m_installing_queue,
                           key = lambda r: r[1].m_priority,
                           reverse = True)
            data = ["${0}:{1}".format(x[0], x[1]) for x in rules]

            return data


    def get_clear_rules_data(self):
        with self.m_lock:
            rules = sorted(self.m_clearing_queue,
                           key = lambda r: r[1].m_priority,
                           reverse = True)
            data = ["${0}:{1}".format(x[0], x[1]) for x in rules]

            return data

    def show(self):
        with self.m_lock:
            print "-------------"
            print "> EcmpGroup"
#            print self.get_ecmp_group_data()
            self.m_policy.show()

            print "> FlowGroup"
#            print self.get_flow_group_data()
            self.m_fg_table.show()

            print "> Ecmp,Flowgroup mapping"
            print self.m_ecmp2fg
#            print self.get_fg2ecmp_data()
            print self.m_fg2ecmp

            print "> Destroy_fgs", self.m_destroy_fgs

            print "> RuleStore"
            for fg_id, store in self.m_fg2store.items():
                print fg_id
                store.show()

            print "> Active_rules"
            rules = sorted(self.m_active_rules.values(),
                           key = lambda r : r.m_priority,
                           reverse = True)
            print "\n".join("{}".format(x)
                            for x in self.get_active_rules_data())
                

            print "> Installing queue"
            print "\n".join("{0}:{1}".format(x[0],x[1])
                            for x in self.m_installing_queue)

            print "> Clearing queue"
            print "\n".join("{0}:{1}".format(x[0],x[1])
                            for x in self.m_clearing_queue)

            print "-------------"
            print ""

class ArpEntry:
    def __init__(self, dst_ip, dst_mac, src_mac, out_port, created_time):
        self.m_dst_ip = dst_ip
        self.m_dst_mac = dst_mac
        self.m_src_mac = src_mac
        self.m_out_port = out_port
        self.m_time = created_time

    def __str__(self):
        return ("dst_ip:%s,dst_mac:%s,src_mac:%s,out_port:%d,time:%s" %
                (self.m_dst_ip,
                 self.m_dst_mac,
                 self.m_src_mac,
                 self.m_out_port,
                 self.m_time))

class ArpTable(Lockable):
    def __init__(self):
        Lockable.__init__(self)
        self.m_table = dict()

    def add(self, dst_ip, dst_mac, src_mac, out_port):
        with self.m_lock:
            t = time.time()
            self.m_table[dst_ip] = ArpEntry(dst_ip, 
                                            dst_mac, 
                                            src_mac, 
                                            out_port,
                                            t)

    def get_ip(self, mac):
        with self.m_lock:
            for value in self.m_table.values():
                if (value.m_dst_mac == mac):
                    return value.m_dst_ip
            return None

    def get_entry(self, dst_ip):
        with self.m_lock:
            if (dst_ip in self.m_table):
                return self.m_table[dst_ip]
            else:
                return None

    def clear(self, threshold):
        with self.m_lock:
            t = time.time()
            new_table = {x[0]:x[1] for x in self.m_table.items()
                         if x[1].m_time > t - threshold}
            self.m_table = new_table

    def get_data(self):
        with self.m_lock:
            data = [str(x) for x in self.m_table.values()]
            return data

    def show(self):
        with self.m_lock:
            print "{",
            print "\n".join(str(entry)
                            for entry in self.m_table.values()),
            print "}"

## essential for a switch
class PortData(dict):
    def __init__(self, ports):
        super(PortData, self).__init__()
        for port in ports.values():
            data = Port(port.port_no, port.hw_addr)
            self[port.port_no] = data


class Port(object):
    def __init__(self, port_no, hw_addr):
        super(Port, self).__init__()
        self.port_no = port_no
        self.mac = hw_addr


class Address():
    ## nw_addr = addr/netmask
    def __init__(self,
                 address_id,
                 addr,
                 nw_addr,
                 prefix_len):
        self.address_id = address_id
        self.addr = addr
        self.nw_addr = nw_addr
        self.prefix_len = prefix_len

    def contains(self, ip):
        return bool(self.nw_addr == ipv4_apply_prefix_mask(ip,
                                                           self.prefix_len))

    def __str__(self):
        return "%d: %s/%d" % (self.address_id,
                              self.addr,
                              self.prefix_len)

    def get_data(self):
        return str(self)

    def show(self):
        print get_data(self)

class AddressData(Lockable):
    def __init__(self):
        Lockable.__init__(self)
        self.m_address_table = dict()
        self.m_address_id = 0

    def add_address(self, address):
        addr, nw_addr, prefix_len = nw_addr_prefix_aton(address)
        # Check overlaps ?
        # for other in self.values():
        #        other_mask = prefix_mask_ntob(other.netmask)
        #        add_mask = prefix_mask_ntob(mask, err_msg)
        #        if (other.nw_addr == ipv4_apply_prefix_mask(addr,
        #                                                    other.netmask)
        #            or nw_addr == ipv4_apply_prefix__mask(other.addr,
        #                                                  mask,
        #                                                  err_msg)):
        #            msg = ('Address overlaps [address_id=%d]'
        #                   % other.address_id)
        #            raise CommandFailure(msg = msg)

        with self.m_lock:
            self.m_address_id += 1
            self.m_address_id &= UINT32_MAX
            if self.m_address_id == 0:
                self.m_address_id = 1
            address_id = self.m_address_id

        address = Address(address_id,
                          addr,
                          nw_addr,
                          prefix_len)

        self.m_address_table[address_id] = address
        return address

    def __getitem__(self, address_id):
        return self.m_address_table[address_id]

    def delete_address(self, address_id):
        self.m_address_table.pop(address_id, None)

    def get_default_gw(self):
        with self.m_lock:
            return [address.addr
                    for address in self.m_address_table.values()]

    def get_address(self,
                    address_id = None,
                    ip = None):
        if address_id is not None:
            if address_id in self.m_address_table:
                return self.m_address_table[address_id]
            else:
                return None
        if ip is not None:
            addresses = list(self.m_address_table.values())
            for address in addresses:
                if (address.contains(ip)):
                    return address
        return None

    def get_data(self):
        addresses = list(self.m_address_table.values())
        data = [str(x) for x in addresses]
        return data

    def show(self):
        print '[',
        data = self.get_data()
        print "\n".join(data),
        print ']'

def TestShowRules(rules):
    print "\n".join("{0},{1},{2}".format(k[0],k[1],k[2]) for k in rules)
    print ""

def TestEcmpPolicy(mthread):

    policy = EcmpPolicy()

    ecmp_ids = []
    def ecmp1():
        dst_str = {"1.1.1.1": (1, ""),
                   "5.5.5.5": (5, None),
                   "2.2.2.2": (2, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        ecmp_id = policy.create_ecmp_group(dst)
        policy.show()

        sip = ip_addr_aton("10.1.0.0")
        raw_ip, sip, mask = nw_addr_aton("10.1.0.0&0xff000000")
        match = Match(sip = sip, sip_mask = mask)

        action = Action()
        rules = policy.apply(ecmp_id = ecmp_id,
                             match = match,
                             action = action)
        TestShowRules(rules)
        policy.destroy_ecmp_group(ecmp_id)
        policy.show()

    def ecmp2():
        dst_str = {"1.1.1.1": (2, None),
                   "5.5.5.5": (5, None),
                   "3.3.3.3": (1, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        ecmp_id = policy.create_ecmp_group(dst)

        ecmp_ids.append(ecmp_id)
        policy.show()

        raw_ip, sip, prefix_len = nw_addr_prefix_aton("11.1.0.0/8")
        mask = UINT32_MAX & (UINT32_MAX << (32 - prefix_len))
        match = Match(sip = sip, sip_mask = mask)
        action = Action()
        rules = policy.apply(ecmp_id = ecmp_id,
                             match = match,
                             action = action)
        TestShowRules(rules)

    def ecmp3():
        dst_str = {"4.4.4.4": (3, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        policy.add_to_ecmp_group(ecmp_id2, dst)
        policy.show()
        gw = policy.get_gateways()
        print gw

    def ecmp4():
        dst_str = ["1.1.1.1"]
        dst = [ip_addr_aton(x) for x in dst_str]
        policy.delete_from_ecmp_group(ecmp_id2, dst)
        policy.show()

    def ecmp5():
        dst_str = {"5.5.5.5": (3, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0],ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        policy.change_ecmp_weights(ecmp_id2, dst)
        policy.show()

    if mthread:
        thread1 = Thread(target = ecmp1)
        thread2 = Thread(target = ecmp2)
        thread3 = Thread(target = ecmp3)
        thread4 = Thread(target = ecmp4)
        thread5 = Thread(target = ecmp5)

        thread1.start()
        thread2.start()

        thread2.join()        
        ecmp_id2 = ecmp_ids[0]
        thread3.start()
        thread4.start()
        thread5.start()
        
        thread1.join()
        thread3.join()
        thread4.join()
        thread5.join()

    else:
        ecmp1()
        ecmp2()
        ecmp_id2 = ecmp_ids[0]
        ecmp3()
        ecmp4()
        ecmp5()

    

def TestFlowGroup(mthread):
    table = FlowGroupTable()
    fg_ids = []
    def fg1():
        _, ip, mask = nw_addr_aton("1.0.0.0&0xf000000")
        match = Match(sip = ip, sip_mask = mask)
        action = Action()
        fg = table.create_flow_group(match, action)
        fg_ids.append(fg.m_fg_id)
        print "fg1",
        table.show()
    
    def fg2():
        group = table.get_flow_group(fg_ids[0])
        print "fg2", str(group)

    def fg3():
        group = table.get_flow_group(sip = ip_addr_aton("1.0.0.1"))
        print "fg3", str(group)
        group = table.get_flow_group(sip = ip_addr_aton("3.0.0.1"),
                                     sport = 3)
        print "fg3", str(group)

    def fg4():
        _, ip, mask = nw_addr_aton("3.0.0.0&0xf000000")
        match = Match(sip = ip, sip_mask = mask)
        action = Action()
        fg = table.create_flow_group(match, action)
        fg_ids.append(fg.m_fg_id)
        print "fg4",
        table.show()

    def fg5():
        group = table.get_flow_group(sip = ip_addr_aton("3.0.0.1"))
        print "fg5", str(group)

    def fg6():
        table.destroy_flow_group(fg_ids[0])
        group = table.get_flow_group(fg_id = fg_ids[0])
        print "fg6", group

    if mthread:
        thread1 = Thread(target = fg1)
        thread2 = Thread(target = fg2)
        thread3 = Thread(target = fg3)
        thread4 = Thread(target = fg4)
        thread5 = Thread(target = fg5)
        thread6 = Thread(target = fg6)
        thread4.start()
        thread1.start()

        thread1.join()

        thread2.start()
        thread3.start()
        thread5.start()
        thread6.start()

        thread2.join()
        thread3.join()
        thread4.join()
        thread5.join()
        thread6.join()
    else:
        fg1()
        fg2()
        fg3()
        fg4()
        fg5()
        fg6()

def TestRuleStore(mthread):
    p = 1
    store = FGRuleStore(1, p)
    _, ip, mask = nw_addr_aton("10.1.0.0&0x00f00000")
    m = Match(sip = ip, sip_mask = mask)
    gw = ip_addr_aton("1.1.1.1")
    a = Action(gateway=gw)
    r1 = (1,(1,m,a))
    r2 = (2,(2,m,a))
    r3 = (3,(3,m,a))

    def rs1():
        store.append([r1])
        print "rs1",
        store.show()

    def rs2():
        store.append([r2])
        print "rs2",
        store.show()

    def rs3():
        store.append([r3])
        print "rs3",
        store.show()

    def mk():
        l = store.check_and_update()
        print "mk",
        store.show()
        l = store.finish_update_and_clear()
        print "mk",
        store.show()
        l = store.finish_clear_and_stablize()
        print "mk",
        store.show()

    if mthread:
        thread1 = Thread(target = rs1)
        thread2 = Thread(target = rs2)
        thread3 = Thread(target = rs3)
        thread4 = Thread(target = mk)
        thread5 = Thread(target = mk)

        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()
        thread5.start()

        thread1.join()
        thread2.join()
        thread3.join()
        thread4.join()
        thread5.join()

    else:
        rs1()
        mk()
        rs2()
        rs3()
        mk()
        
def TestRoutingTable(mthread):
    
    tbl = RoutingTable(None, 0)
    fg_ids = []
    ecmp_ids = []
    def rt1():
        _, sip, smask = nw_addr_aton("1.0.0.0&0xf000000")
        _, dip, dmask = nw_addr_aton("9.9.9.9&0xffffffff")
        match = Match(sip = sip, sip_mask = smask,
                      dip = dip, dip_mask = dmask)
        action = Action()
        fg_id = tbl.create_flow_group(match, action)
        fg_ids.append(fg_id)

        _, sip, smask = nw_addr_aton("2.0.0.0&0xf000000")
        _, dip, dmask = nw_addr_aton("9.9.9.9&0xffffffff")
        match = Match(sip = sip, sip_mask = smask,
                      dip = dip, dip_mask = dmask)
        action = Action()
        fg_id = tbl.create_flow_group(match, action)
        fg_ids.append(fg_id)

    def rt2():
        dst_str = {"1.1.1.1": (1, ""),
                   "2.2.2.2": (2, "")}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        ecmp_id = tbl.create_ecmp_group(dst)
        ecmp_ids.append(ecmp_id)

        dst_str = {"3.3.3.3": (1, None),
                   "4.4.4.4": (4, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        ecmp_id = tbl.create_ecmp_group(dst)
        ecmp_ids.append(ecmp_id)

    def rt3():
        ecmp_id = ecmp_ids[0]
        fg_id = fg_ids[0]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt4():
        ecmp_id = ecmp_ids[1]
        fg_id = fg_ids[1]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt5():
        ecmp_id = ecmp_ids[1]
        fg_id = fg_ids[0]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt6():
        ecmp_id = ecmp_ids[1]
        dst_str = {"7.7.7.7": (2, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        tbl.add_to_ecmp_group(ecmp_id, dst)

    def rt7():
        ecmp_id = ecmp_ids[0]
        fg_id = fg_ids[1]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt8():
        ecmp_id = ecmp_ids[1]
        dst_str = ["3.3.3.3"]
        dst = [ip_addr_aton(x) for x in dst_str]
#       gw_str = {"3.3.3.3":5}
#       gws = {ip_addr_aton(x[0]):x[t] for x in gw_str.items()}
        tbl.delete_from_ecmp_group(ecmp_id, dst)
#        tbl.change_ecmp_weights(ecmp_id, gws)

    def rt9():
        fg_id = fg_ids[0]
        tbl.destroy_flow_group(fg_id)
    

    install_stop = False
    def do_install():
        while (not install_stop):
            rule = tbl.pop_next_install_rule()
            if (rule == None):
               continue
            print "do install", str(rule)

    clear_stop = False
    def do_clear():
        while (not clear_stop):
            rule = tbl.pop_next_clear_rule()
            if (rule == None):
                continue
            print "do clear", str(rule)

    thread1 = Thread(target = do_install)
    thread2 = Thread(target = do_clear)
    tbl.start()
    thread1.start()
    thread2.start()
    rt1()
    rt2()
    if not mthread:
        rt3()
        rt4()
        rt5()
        rt6()
        rt7()
        rt8()
        rt9()
        time.sleep(1)
    else:
        thread3 = Thread(target = rt3)
        thread4 = Thread(target = rt4)
        thread5 = Thread(target = rt5)
        thread6 = Thread(target = rt6)
        thread7 = Thread(target = rt7)
        thread8 = Thread(target = rt8)
        thread9 = Thread(target = rt9)
        thread3.start()
        thread4.start()
        thread5.start()
        thread6.start()
        thread7.start()
        thread8.start()
        thread9.start()
        time.sleep(1)
        
        thread3.join()
        thread4.join()
        thread5.join()
        thread6.join()
        thread7.join()
        thread8.join()
        thread9.join()

    install_stop = True
    clear_stop = True
    thread1.join()
    thread2.join()
    tbl.stop()
    tbl.show()

#    tbl.install()
#    do_install()
#    tbl.clear()
#    do_clear()
#    tbl.done()



def TestRule():
    m = Match(sip = "10.0.0.0",
              sip_mask = 0xff000000,
              dip = "192.168.6.6",
              dip_mask = 0xffffffff,
              ip_proto = 6,
              sport = 4,
              dport = 5)
    print m

    a = Action(gateway = "192.168.1.1",
               sip = 0,
               dip = 0,
               sport = 0,
               dport = 0)

    print a
    rule = Rule(rule_id = 1,
                fg_id = 2,
                priority = 3,
                match = m,
                action = a)

    print rule

    s = str(rule)

    rule_ = Rule.parse_rule(s)

    print s

def TestArpTable():
    tbl = ArpTable()
    tbl.add(ip_addr_aton("1.1.1.1"),
            "00-00-00-00-00-01",
            "00-00-00-00-00-00",
            1)
    tbl.show()
    time.sleep(1)
    tbl.add(ip_addr_aton("1.1.1.2"),
            "00-00-00-00-00-02",
            "00-00-00-00-00-00",
            2)
    tbl.show()
    time.sleep(1)
    tbl.clear(1.5)
    tbl.show()

def TestAddressData():
    tbl = AddressData()
    a = "10.0.0.2/24"
    b = "192.168.0.3/16"
    a_id = tbl.add_address(a).address_id
    b_id = tbl.add_address(b).address_id
    tbl.show()
    print a_id
    print tbl.get_address(ip = ip_addr_aton('10.0.0.5'))
    print tbl.get_address(ip = ip_addr_aton('10.0.1.0'))
    tbl.delete_address(address_id = a_id)
    tbl.show()
    


# TestRule()
# TestEcmpPolicy(True)
# TestFlowGroup(True)
# TestRuleStore(False)
# TestRoutingTable(False)
# TestArpTable()
# TestAddressData()

if False:
    s = "{'a':3,'b':4 }"
    d = ast.literal_eval(s)
    print check_dict_type(d, str, int)
    s = "[3,4,5]"
    k = ast.literal_eval(s)
    print check_list_type(k, int)
