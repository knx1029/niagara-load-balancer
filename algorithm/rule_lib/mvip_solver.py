from svip_solver import *

class MVipSolver:

    def __init__(self, eps):
        self.eps = eps
        self.vips = None
        self.rule_capacity = 0
        self.default_rules = None
        self.rules = None
        pass

    ## vips = [(vip_idx, weights, traffic_eval, volume)]
    def set_input(self, vips, rule_capacity, default_rules = None):
        self.vips = vips
        self.rule_capacity = rule_capacity
        self.default_rules = default_rules
        self.rules = None

    ## compute the rules for multiple VIPs based on SVipSolver
    def solve(self):
        solvers = {}
        stairsteps = []
        ## create solver for every vip
        ## initialize the stairstep
        for (vip_idx, weights, traffic_eval, popularity) in self.vips:
            svip_solver = SVipSolver()
            svip_solver.set_input(weights,
                                  traffic_eval,
                                  self.default_rules,
                                  self.eps)
            solvers[vip_idx] = svip_solver
            fall = svip_solver.next_transfer()
            heapq.heappush(stairsteps,
                           (-fall[0] * popularity,
                            vip_idx,
                            fall,
                            popularity))

        ## intialize num of rules to be allocated
        num_rules = 0
        if (self.default_rules == None):
            num_rules = len(self.vips)
            self.rules = []
        else:
            num_rules = len(self.default_rules)
            self.rules = self.default_rules[:]
        if (num_rules > self.rule_capacity):
            return False

        ## in each iteration, we allocate 1 rule
        ## to the VIP with best vip_fall
        while (num_rules < self.rule_capacity) and (len(stairsteps) > 0):
            (_, best_vip_idx, best_vip_fall, popularity) = heapq.heappop(stairsteps)
            svip_solver = solvers[best_vip_idx]
            svip_solver.exec_transfer(best_vip_fall)
            if (not svip_solver.check_within_eps(self.eps)):
                fall = svip_solver.next_transfer()
                heapq.heappush(stairsteps,
                               (-fall[0] * popularity,
                                best_vip_idx,
                                fall,
                                popularity))
            num_rules = num_rules + 1
            

        if (self.default_rules == None):
            vip_rule_start_index = 0
            self.rules = []
        else:
            vip_rule_start_index = len(self.default_rules)
            self.rules = [(None, self.default_rules)]
        self.values = {}

        for vip_idx, svip_solver in solvers.items():
            svip_rules, svip_values = svip_solver.get_output()
            self.rules.append((vip_idx, svip_rules[vip_rule_start_index:]))
            self.values[vip_idx] = svip_values
        return True


    def get_output(self):
        return self.rules, self.values


## A simplified multi-VIP solver based on rules
class SMVipSolver:

    def __init__(self):
        self.vip_popularity = None
        self.rule_map = None
        self.default_rules = None
        self.rules = None

    def set_input(self, vip_popularity, rule_capacity, rule_map, default_rules):
        self.vip_popularity = vip_popularity
        self.rule_capacity = rule_capacity
        self.rule_map = rule_map
        self.default_rules = default_rules
        self.rules = None
        
    ## compute the rules for multiple VIPs based on SVipSolver
    def solve(self):
        if (self.vip_popularity == None or self.rule_map == None):
            return False

        ## intialize num of rules to be allocated
        rule_idx = 1
        if (self.default_rules != None):
            rule_idx = len(self.default_rules)
            num_rules = len(self.default_rules)
        else:
            rule_idx = 1
            num_rules = 0

        stairsteps = []
        ## create solver for every vip
        ## initialize the stairstep
        for (vip_idx, popularity) in self.vip_popularity.items():
            ## find the starting rule point
            vip_rules = self.rule_map[vip_idx]
            if (len(vip_rules) == 0):
                continue
            if (self.default_rules == None):
                num_rules = num_rules + 1

            if (len(vip_rules) == rule_idx):
                heapq.heappush(stairsteps,
                               (0,
                                vip_idx,
                                rule_idx,
                                popularity))
            else:
                rule = vip_rules[rule_idx]
                if (len(rule) <= IMB_FALL_INDEX):
                    return False
                heapq.heappush(stairsteps,
                               (-rule[IMB_FALL_INDEX] * popularity,
                                vip_idx,
                                rule_idx,
                                popularity))

        


        ## in each iteration, we allocate 1 rule
        ## to the VIP with best vip_fall
        while ((num_rules < self.rule_capacity)
               and (double_cmp(stairsteps[0][0]) != 0)):
            (best_vip_fall, best_vip_idx, best_rule_idx, popularity) = heapq.heappop(stairsteps)
            vip_rules = self.rule_map[best_vip_idx]
            num_rules = num_rules + 1
            if (best_rule_idx + 1 < len(vip_rules)):
                rule = vip_rules[best_rule_idx + 1]
                if (len(rule) <= IMB_FALL_INDEX):
                    return False
                heapq.heappush(stairsteps,
                               (-rule[IMB_FALL_INDEX] * popularity,
                                best_vip_idx,
                                best_rule_idx + 1,
                                popularity))
            else:
                heapq.heappush(stairsteps,
                               (0,
                                best_vip_idx,
                                best_rule_idx + 1,
                                popularity))

        if (self.default_rules == None):
            rule_start_idx = 0
            self.rules = []
        else:
            rule_start_idx = len(self.default_rules)
            self.rules = [(None, self.default_rules)]
        for (_, vip_idx, rule_idx, _) in stairsteps:
            svip_rules = self.rule_map[vip_idx][rule_start_idx:rule_idx]
            self.rules.append((vip_idx, svip_rules))
        return True

    def get_output(self):
        return self.rules


## Unit test of SVipSolver
class MVipUTest():

    def __init__():
        pass

    @staticmethod
    def validate(rules, values, vips, rule_capacity, eps):
        ## retrive the default rules
        default_rules = None
        num_rules = 0
        for (vip_idx, vip_rules) in rules:
            if (vip_idx == None):
                if (default_rules != None):
                    print "multiple default rules?"
                    return False
                default_rules = vip_rules
            num_rules = num_rules + len(vip_rules)

        ## check number of rules
        if (num_rules > rule_capacity):
            print "rule capacity exceeded", num_rules, rule_capacity
            return False
        elif (num_rules == rule_capacity):
            loosen_eps = 1.0
        else:
            loosen_eps = eps

        ## Skip checking value if is None
        if (values == None):
            return True

        ## check vip's value one by one
        for (vip_idx, vip_rules) in rules:
            if (vip_idx == None):
                continue

            if (not (vip_idx in values)):
                return False
            vip_values = values[vip_idx]
            ## find corresponding weights, traffic_eval
            weights = None
            traffic_eval = None
            for (i, ws, eval, vol) in vips:
                if (i == vip_idx):
                    weights = ws
                    traffic_eval = eval
                    break
            if (weights == None):
                return False

            if (default_rules == None):
                rules = vip_rules
            else:
                rules = default_rules + vip_rules
            if (not SVipUTest.validate(rules,
                                       vip_values,
                                       weights,
                                       traffic_eval,
                                       loosen_eps)):
                return False

        return True

