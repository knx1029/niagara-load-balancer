import time
import heapq
from Queue import PriorityQueue
from operator import itemgetter
import math

from suffix_forest import *
from utils import *

BITS = 32 #48
IMB_FALL_INDEX = 2

## generate rules for a single VIP
class SVipSolver:
    ## make an entry for priority queue, which ranks max weight first
    def __make_entry(self, n):
        return (-self.traffic_eval.weight(n.root), n)

    ## unmake an entry
    def __unmake_entry(self, e):
        return -e[0], e[1]

    ## calculate the new imbalance after moving x from a to b
    @staticmethod
    def __delta_imb(a, b, x):
        return min(a, x) + min(b, x) - x

    ## find the biggest drop in imbalance (delta_imb)
    ## Let a = vj - wj, b = wi - vi, q = vj.nodes
    ## pop out node from q until delta_imb stops increasing
    ## when a node is popped, its left and right children are pushed to q
    def __find_biggest_delta_imb(self, q, a, b, old_x = None, old_y = None):
        ## try to use previous result, a short-cut
        if (len(q) == 0):
            return None
        x, nodex = self.__unmake_entry(q[0])
        if (old_x != None):
            if (double_cmp(x - old_x) == 0):
                dx = self.__delta_imb(a, b, x)
                y = old_y
                dy = self.__delta_imb(a, b, y)
                if (double_cmp(dy - dx) <= 0) and (double_cmp(y - x) <= 0):
                    return x, y

        tlist = []
        y = 0.0
        z = 0.0
        while (len(q) > 0):
            ## evaluate the biggest node
            x, nodex = self.__unmake_entry(q[0])
            dx = self.__delta_imb(a, b, x)

            ## pick the second largest
            y = 0.0
            if (len(q) > 1):
                y = max(y, self.__unmake_entry(q[1])[0])
            if (len(q) > 2):
                y = max(y, self.__unmake_entry(q[2])[0])
            if (nodex.left == None):
                nodex.expand_left()
            if (nodex.right == None):
                nodex.expand_right()
            ## z records the biggest weights of children of nodes in tlist
            ## if nothing to expand
            if (nodex.left != None):
                cl = self.traffic_eval.weight(nodex.left.root)
                cr = self.traffic_eval.weight(nodex.right.root)
                if (double_cmp(cl - x) == 0):
                    heapq.heappop(q)
                    heapq.heappush(q, self.__make_entry(nodex.left))
                    continue
                elif (double_cmp(cr - x) == 0):
                    heapq.heappop(q)
                    heapq.heappush(q, self.__make_entry(nodex.right))
                    continue
                z = max(z, max(cl, cr))

            y = max(z, y)

            ## we skip the nodes with equal weights
            ## save them into a temp list
            if (double_cmp(y - x) == 0):
                tlist.append(heapq.heappop(q))
                continue

            ## compute the delta_imb of the second largest value
            dy = self.__delta_imb(a, b, y)
            
            ## if the second largest does not achieve a bigger 
            ## imbalance reduction, then we push nodes in the
            ## temp list to the heap and break;
            ## otherwise, we push CHILDREN of nodes in the temp
            ## list to the heap
## CHANGED
            CHANGED = True

            if (CHANGED):
                if ((double_cmp(dy - dx) < 0) or
                    ((double_cmp(dy - dx) == 0) and 
                      double_cmp(math.fabs(x - b) - math.fabs(y - b)) < 0)):
                    while (len(tlist) > 0):
                        heapq.heappush(q, tlist.pop())
                    break
                else:
                    tlist.append(heapq.heappop(q))
                    while (len(tlist) > 0):
                        _, nodex = self.__unmake_entry(tlist.pop())
                        if (nodex.left != None):
                            heapq.heappush(q, self.__make_entry(nodex.left))
                            heapq.heappush(q, self.__make_entry(nodex.right))
                    z = 0.0
            else:
                if (double_cmp(dy - dx) <= 0) and (double_cmp(y - x) <= 0):
                    while (len(tlist) > 0):
                        heapq.heappush(q, tlist.pop())
                    break
                else:
                    tlist.append(heapq.heappop(q))
                    while (len(tlist) > 0):
                        _, nodex = self.__unmake_entry(tlist.pop())
                        if (nodex.left != None):
                            heapq.heappush(q, self.__make_entry(nodex.left))
                            heapq.heappush(q, self.__make_entry(nodex.right))
                    z = 0.0

        return x, y


    def __init__(self):
        ## input
        self.weights = None
        self.traffic_eval = None
        self.eps = -1
        self.default_rules = None

        ## output
        self.value_map = None
        self.rules = None

        ## intermediate
        self.pqueue = None
        self.old_xy = None

        pass


    ## compute the suffix forest map from rules
    def __init_vmap_pqueue(self):
        ## if rules is None, pick the biggest weight as pool
        if (self.default_rules == None) or (len(self.default_rules) == 0):
            pool_idx = 0
            pool_weight = -1
            for (i, w) in self.weights:
                if (w > pool_weight):
                    pool_weight = w
                    pool_idx = i
            ## set the default rules
            root = "*" * BITS
            self.rules = [(root, pool_idx)]
        else:
            ## rules cannot overlap
            for ki in range(0, len(self.default_rules)):
                (si, i) = self.default_rules[ki]
                for kj in reversed(range(0, ki)):
                    (sj, j) = self.default_rules[kj]
                    if (overlap(si, sj) == CONTAINED):
                        return False
            self.rules = self.default_rules[:]

        ## create all data structure
        self.value_map = {}
        self.pqueue = {}
        for (i, _) in self.weights:
            self.pqueue[i] = []
            self.value_map[i] = 0.0

        for ki in range(0, len(self.rules)):
            (si, i) = self.rules[ki]
            tree = SuffixTree(si)
            e = self.__make_entry(tree)
            heapq.heappush(self.pqueue[i], e)
            self.value_map[i] += self.traffic_eval.weight(si)

        return True


    ## set input. weights: [(idx, w)], traffic_eval.weight(str), eps
    def set_input(self, weights, traffic_eval, default_rules = None, eps = 1e-3):
        if (weights == None) or (traffic_eval == None):
            return None

        self.eps = eps
        self.weights = weights[:]
        self.traffic_eval = traffic_eval
        if (default_rules != None):
            self.default_rules = default_rules[:]
        else:
            self.default_rules = None

        ## init intermediate and output results
        self.rules = None
        if (not self.__init_vmap_pqueue()):
            return None
        self.old_xy = {}

    ## get output
    def get_output(self):
        ## finish
        return self.rules, self.value_map


    ## find the next value pair to transfer weights
    def next_transfer(self):
        ## find the biggest and second biggest w-v
        best_b_idx, best_b = -1, 0.0
        for (i, w) in self.weights:
            v = self.value_map[i]
#            print i, "w=",w, "v=",v, "w-v=",w-v
            if (w - v >= best_b):
                best_b_idx, best_b = i, w - v
                    
 #       print "best_b", best_b_idx, best_b
        ## we choose the v-w, which gives the maximum gain in reducing
        ## imbalance, a.k.a., delta_imb
        best_fall, best_x = -1.0, -1.0
        best_a, best_a_idx = -1.0, -1
        for (j, w) in self.weights:
            v = self.value_map[j]
            aj = v - w
            if aj <= 0:
                continue
            qj = self.pqueue[j]
            if (j in self.old_xy):
                old_x, old_y = self.old_xy[j]
                res = self.__find_biggest_delta_imb(qj,
                                                    aj,
                                                    best_b,
                                                    old_x,
                                                    old_y)
            else:
                res = self.__find_biggest_delta_imb(qj, aj, best_b)
            if (res == None):
                continue
            xj, yj = res

            self.old_xy[j] = (xj, yj)
            dj = self.__delta_imb(aj, best_b, xj)
#            print "best_a", j, w, v, aj, dj
#            print xj, yj
            
            if (dj > best_fall):
                best_fall = dj
                best_a = aj
                best_a_idx = j
                best_x = xj

        return best_fall, best_a_idx, best_b_idx, best_x


    ## transfer x from a to b
    def exec_transfer(self, best):
        best_fall, best_a_idx, best_b_idx, best_x = best
        if (best_fall <= 0):
            return False
        qa = self.pqueue[best_a_idx]
        qb = self.pqueue[best_b_idx]
        self.value_map[best_b_idx] += best_x
        self.value_map[best_a_idx] -= best_x
        best_item = heapq.heappop(qa)
        heapq.heappush(qb, best_item)
        _, best_node = self.__unmake_entry(best_item)
        self.rules.append((best_node.root, best_b_idx, best_fall))
        if (best_b_idx in self.old_xy):
            del self.old_xy[best_b_idx]
#        print "imbalance reduced b", best_delta_imb
#        print "transfer {0} from {1}({3}) to {2}({4})".format(best_x,
#                                                              best_a_idx,
#                                                              best_b_idx,
#                                                              value_map[best_a_idx],
#                                                              value_map[best_b_idx])

        return True


    ## check if the approximation accuray <= eps
    def check_within_eps(self, eps):
        ## compute accuracy
        accuracy = max(map(lambda((i, w)):math.fabs(w - self.value_map[i]),
                           self.weights))
        return (double_cmp(accuracy - eps) <= 0)


    ## approximate a list of weights ws till the accuracy < eps
    ## eval gives the fraction of every suffix pattern
    def solve(self):
        if (double_cmp(self.eps) <= 0):
            return False

        while (not self.check_within_eps(self.eps)):
            best = self.next_transfer()
            if (not self.exec_transfer(best)):
                return False
        return True


class TrafficVectorEval():
    def __init__(self, nbits, v):
        self.v = v
        self.nbits = nbits

    def weight(self, str):
        index = 0
        wcount = 0
        for c in str:
            if (c == '1'):
                index = (index << 1) + 1
            elif (c == '0'):
                index = (index << 1)
            else:
                wcount = wcount + 1
        bcount = len(str) - wcount
        if (bcount <= self.nbits):
            bdiff = (self.nbits - bcount)
            pdiff = (1 << bdiff)
            w = 0
            for i in range(pdiff):
                w = w + self.v[(i << bcount) + index]
            return w
        else:
            bdiff = bcount - self.nbits
            pdiff = (1 << bdiff)
            w = self.v[index & ((1 << self.nbits) - 1)] / pdiff
            return w

class TrafficExactEval():
    def __init__(self, vs):
        self.vs = vs

    def weight(self, str):
        value = 0
        mask = 0
        for c in str:
            if (c == '1'):
                value = (value << 1) + 1
                mask = (mask << 1) + 1
            elif (c == '0'):
                value = (value << 1)
                mask = (mask << 1) + 1
            else:
                value = (value << 1)
                mask = (mask << 1)
        we = 0
        for v, w in self.vs:
            if ((v & mask) == value):
                we = we + w
        return we


class TrafficEval():

    def __init__(self, r0 = 0.5):
        self.r0 = r0
        self.r1 = 1.0 - r0
        pass

    def weight(self, str):
#        return self.weight1(str)
        return self.weight2(str)

    def weight1(self, str):
        k = get_level(str)
        if k == 0:
            return 1.0
        else:
            if (str[0] == '0'):
                return self.r0 * math.pow(0.5, k - 1)
            else:
                return self.r1 * math.pow(0.5, k - 1)

    def weight2(self, str):
        a = str.count('0')
        b = str.count('1')
        return math.pow(self.r0, a) * math.pow(self.r1, b)


## Unit test of SVipSolver
class SVipUTest():

    def __init__():
        pass

    ## check if value_map equals value_list
    @staticmethod
    def value_map_equal(vmap, ref_vmap):
        if (len(vmap) > len(ref_vmap)):
            return False
        for (i, v) in ref_vmap.items():
            if (i not in vmap):
                return False
            if (double_cmp(v - vmap[i]) != 0):
                return False
        return True

    ## check if value_map approximate weights within eps
    @staticmethod
    def value_map_fit_weights(vmap, weights, eps):
        if (len(vmap) > len(weights)):
            return False
        for (i, w) in weights:
            if (i not in vmap):
                return False
            if (double_cmp(math.fabs(w - vmap[i]) - eps) > 0):
                return False
        return True

    @staticmethod
    def validate(rules, values, weights, traffic_eval, eps):
        vmap = SVipUTest.get_value_map(rules, traffic_eval, weights)
        if (vmap == None):
            print "vmap = None"
            return False
        if (not SVipUTest.value_map_equal(vmap, values)):
            print "vmap != vlist"
            print "vmap", vmap
            return False
        if (not SVipUTest.value_map_fit_weights(vmap, weights, eps)):
            print "vmap !~ weights"
            return False
        return True

    ## compute the value map from rules and traffic_eval
    @staticmethod
    def get_value_map(rules, traffic_eval, weights):
        value_map = {w[0]:0 for w in weights}

        last_imb = -1
        for ki in range(0, len(rules)):
            ## rules[ki][0] = (si, i) or (si, i, imb_fall)
            si = rules[ki][0]
            i = rules[ki][1]
            if (i not in value_map):
                return None
            v = traffic_eval.weight(si)
            value_map[i] += v
            for kj in reversed(range(0, ki)):
                sj = rules[kj][0]
                j = rules[kj][1]
                if (overlap(si, sj) == CONTAINED):
                    value_map[j] -= v
                    break
            current_imb = sum(map(lambda((i,w)): math.fabs(value_map[i] - w),
                                  weights)) * 0.5
            if (last_imb >= 0 and len(rules[ki]) > IMB_FALL_INDEX):
                imb_fall = rules[ki][IMB_FALL_INDEX]
                if (double_cmp(last_imb - current_imb - imb_fall) != 0):
#                    print rules[ki]
#                    imbs = map(lambda((i,w)):value_map[i] - w,
#                               weights)
#                    print ",".join(str(i) for i in imbs)
#                    print last_imb, current_imb, imb_fall
                    return None
            last_imb = current_imb
                
        return value_map

