from info import *
from utils import *

import ast
import copy
import threading
from threading import Thread
from string import maketrans
import time
from ryu.lib import hub

from collections import deque


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

## returns set of rules = rules_a \ rule_b
def get_difference_of_rules(rules_a, rules_b):
    rules_c = []
    for rule_a in rules_a:
        found = False
        for rule_b in rules_b:
            if (rule_a == rule_b):
                found = True
                break
        if (not found):
            rules_c.append(rule_a)
    return rules_c

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

    def __eq__(self, other):
        return ((self.m_rule_id == other.m_rule_id) and
                (self.m_fg_id == other.m_fg_id) and
                (self.m_priority == other.m_priority) and
                (self.m_match == other.m_match) and
                (self.m_action == other.m_action))

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
        self.m_changing = None
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
                self.m_changing = get_global_priority_for_rules(
                    fg_priority = self.m_priority,
                    fg_id = self.m_fg_id,
#                    mark = self.m_active_version ^ 1,
                    mark = self.m_active_version,
                    rules = self.m_pending)
                ## incremental update
                self.m_installing = get_difference_of_rules(self.m_changing,
                                                            self.m_using)
                #self.m_installing = self.m_changing
                self.m_pending = None
                return self.m_installing
            else:
                return None

    def finish_update_and_clear(self):
        with self.m_lock:
            if (self.__status() != FGRuleStatus.UPDATING):
                return None
            ## incremental update
            self.m_clearing = get_difference_of_rules(self.m_using,
                                                      self.m_changing)
            self.m_using = self.m_changing
            #self.m_clearing = self.m_using
            #self.m_using = self.m_installing
            #self.m_active_version ^= 1
            self.m_installing = None
            self.m_changing = None
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
                     "changing": __rules2str(self.m_changing),
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


class FGMeasurement():

    def __init__(self, r0 = 0.5, p0 = 1.0):
        self.bit_balance = TrafficEval(r0)
        self.popularity = p0


## compute abstract rules
## an algorithm wrapper
class RuleEngine(Lockable):

    def __init__(self,
                 rule_limit,
                 default_rules = None,
                 eps = 1e-3):

        Lockable.__init__(self)
        self.m_rule_limit = rule_limit
        self.m_default_rules = default_rules
        self.m_eps = eps

        self.m_fg_rules = dict()
        self.m_fg_trunc_rules = dict()
        self.m_fg_popularity = dict()

        self.m_single_solver = SVipSolver()
        self.m_multiple_solver = SMVipSolver()


    ## compute the rules for fg_id
    def add_or_change_flow_group(self,
                                 fg_id,
                                 ecmp_group,
                                 fg_msr):

        ## get the weights
        total_w = sum(ecmp_group.m_dst.values())
        dst_weights = [(x[0], x[1] * 1.0 / total_w) 
                      for x in ecmp_group.m_dst.items()]
        n_weights = len(dst_weights)

        if (n_weights == 0):
            rules = []
        else:
            weights = zip(range(0, n_weights),
                          map(lambda x:x[1], dst_weights))
            rules = self.__compute_svip_rules(weights,
                                              fg_msr.bit_balance)
        if (rules == None):
            return False

        with self.m_lock:
            ## add gateway
            def f(r):
                if (len(r) > 2):
                    return (r[0], dst_weights[r[1]][0], r[2])
                return (r[0], dst_weights[r[1]][0])

            rule_with_dst = map(f, rules)
            self.m_fg_rules[fg_id] = rule_with_dst
            self.m_fg_popularity[fg_id] = fg_msr.popularity
            return True


    def remove_flow_group(self, fg_id):
        with self.m_lock:
            self.m_fg_rules.remove(fg_id)
            self.m_fg_trunc_rules.remove(fg_id)
            self.m_fg_popularity.remove(fg_id)


    def compute_rules(self):
        def f(rule):
            return (rule[0], rule[1])

        ## compute
        rules = self.__compute_mvip_rules()
        if (rules == None):
            return False

        with self.m_lock:
            self.m_fg_trunc_rules = dict()
            for (fg_id, fg_rules) in rules:
                if (fg_id != None):
                    r = map(f, fg_rules)
                    rules_with_priority = zip(range(0, len(r)), r)
                    self.m_fg_trunc_rules[fg_id] = rules_with_priority
            return True


    def get_rules(self, fg_id):
        with self.m_lock:
            if (fg_id not in self.m_fg_rules):
                return None
            elif (fg_id not in self.m_fg_trunc_rules):
                return []
            else:
                return self.m_fg_trunc_rules[fg_id]

    ## call algorithm to compute the rules for a single flow gorup
    def __compute_svip_rules(self,
                             weights,
                             eval):
        self.m_single_solver.set_input(weights,
                                       eval,
                                       self.m_default_rules,
                                       self.m_eps)
        if (not self.m_single_solver.solve()):
            return None

        rules, _ = self.m_single_solver.get_output()
        return rules

    ## call algorithm to compute the rules for a single flow gorup
    def __compute_mvip_rules(self):
        self.m_multiple_solver.set_input(self.m_fg_popularity,
                                         self.m_rule_limit,
                                         self.m_fg_rules,
                                         self.m_default_rules)
        if (not self.m_multiple_solver.solve()):
            return None
        rules = self.m_multiple_solver.get_output()
        return rules


## manage all the flow groups and ecmp groups
## store rules and push flow mod
class RoutingTable(Lockable):

    def __init__(self,
                 logger,
                 sw_id,
                 rule_limit = 100):
        Lockable.__init__(self)
        self.m_rule_id = 1
        self.m_fg_table = FlowGroupTable()
        self.m_policy = EcmpPolicy()
        ## hard-coded 
        self.m_engine = RuleEngine(rule_limit)

        self.m_fg2msr = dict()

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

        flow_group = self.m_fg_table.create_flow_group(match,
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

            ## Hard-coded
            self.m_fg2msr[fg_id] = FGMeasurement()
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


    def __append_update(self, fg_ids, new_ecmp_id):
        for fg_id in fg_ids:
            with self.m_lock:
                if ((fg_id not in self.m_fg2ecmp) or
                    (new_ecmp_id not in self.m_ecmp2fg)):
                    continue

                ecmp_group = self.m_policy[new_ecmp_id]
                fg_msr = self.m_fg2msr[fg_id]
                self.m_engine.add_or_change_flow_group(fg_id,
                                                       ecmp_group,
                                                       fg_msr)

        ## currently we re-compute the table whenever ecmp<->fg changes
        with self.m_lock:
            if (not self.m_engine.compute_rules()):
                msg = "Cannot compute new rules"
                raise CommandFailure(msg = msg)
                return

            for fg_id in self.m_fg2msr:
                store = self.m_fg2store[fg_id]
                fg = self.m_fg_table[fg_id]
                ecmp_id = self.m_fg2ecmp[fg_id]
                rules = self.m_engine.get_rules(fg_id)
                if (rules == None):
                    continue

                applied_rules = self.m_policy.apply(ecmp_id,
                                                    rules,
                                                    match = fg.m_match,
                                                    action = fg.m_action)

                rule_count = len(applied_rules)
                rule_id_beg = self.m_rule_id
                self.m_rule_id += rule_count
                rule_id_end = self.m_rule_id
                fg_rules = zip(range(rule_id_beg, rule_id_end),
                               applied_rules)
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



