import time
import heapq
from Queue import PriorityQueue
from operator import itemgetter
import math

from suffix_forest import *
from weighted_suffix_forest import *
from single_vip import *

BITS = 32

## approximate a list of weights ws till the accuracy < eps
## eval gives the fraction of every suffix pattern
def approximate(ws, eps, eval, CHOOSE_SLOPE):

    ## find the biggest drop in imbalance (delta_imb)
    ## a = vj - wj, b = wi - vi
    ## the idea is to pop out node from q until delta_imb stops increasing
    ## when a node is popped, its left and right chilren are pushed to q
    def find_biggest_delta_imb(q, a, b):
        ## we pop out nodes until delta_imb stops increasing
        tlist = []
        z = 0.0
        while (True):
            ## evaluate the biggest
            x, nodex = unmake_entry(q[0])
            dx = delta_imb(a, b, x)

            ## pick the second largest
            y = 0.0
            if (len(q) > 1):
                y = max(y, unmake_entry(q[1])[0])
            if (len(q) > 2):
                y = max(y, unmake_entry(q[2])[0])

            if (nodex.left == None):
                nodex.expand_left()
            if (nodex.right == None):
                nodex.expand_right()
            ## z records the biggest weights of children of nodes in tlist
            z = max(z, max(eval.weight(nodex.left.root),
                           eval.weight(nodex.right.root)))
            y = max(z, y)

            ## we pre-save the nodes with equal weights to a list
            if (y == x):
                tlist.append(heapq.heappop(q))
                continue

            dy = delta_imb(a, b, y)
            
            ## if the second largest does not achieve a bigger 
            ## imbalance reduction, then we break
            ## otherwise, we update the heap
            if (dy <= dx and y < x):
                break
            else:
                tlist.append(heapq.heappop(q))
                while (len(tlist) > 0):
                    _, nodex = unmake_entry(tlist.pop())
                    heapq.heappush(q, make_entry(nodex.left))
                    heapq.heappush(q, make_entry(nodex.right))
                z = 0.0

        while (len(tlist) > 0):
            heapq.heappush(q, tlist.pop())

        return x, y


    ## compute imbalance
    def imb_map(a):
        idx, w = a
        return math.fabs(w - weight_map[idx])

    ## calculate imbalance
    def delta_imb(a, b, x):
        return min(a, x) + min(b, x) - x

    ## make an entry for priority queue, which ranks max weight first
    def make_entry(n):
        return (-eval.weight(n.root), n)

    ## unmake an entry
    def unmake_entry(e):
        return -e[0], e[1]


    ## create all data structure
    weight_map = {}
    pqueue = {}
    forest = {}

    weights = ws[:]
    weights.sort(key = itemgetter(1), reverse = True)
    pool_idx = weights[0][0]

    for (idx, _) in weights:
      weight_map[idx] = 0.0
      pqueue[idx] = []
      forest[idx] = SuffixForest(idx, [])

    ## initialize
    weight_map[pool_idx] = 1.0
    root = "*" * BITS
    tree = SuffixTree(root)
    heapq.heappush(pqueue[pool_idx], make_entry(tree))
    forest[pool_idx].add_tree(tree)

    rules = [(root, pool_idx)]

    while (True):
        accuracy = max(map(imb_map, weights))
        if (accuracy <= eps):
            break

        ## find the biggest and second biggest w-v
        best_b_idx, best_b = -1, 0.0
        second_b = -1.0
        for (idx, w) in weights:
            v = weight_map[idx]
            if (w - v >= best_b):
                second_b = best_b
                best_b_idx, best_b = idx, w - v

        ## we choose the v-w, which gives the maximum gain in reducing
        ## imbalance.
        ## specifically, we first find out the biggest imbalance reduction
        ## a.k.a. delta_imb, for every v-w, given best_b; second, we
        ## examine how much the biggest delta_imb is going to fall, if
        ## best_b becomes second_b; the gap between these two delta_imb
        ## represents the gain of matching up best_b with the v-w
        ##  among these v-w, the one having the biggest delta_imb fall is
        ## chosen. In this way, we are not looking at the absolute value
        ## of imbalance reduced, but the gain of reducing the imbalance
        best_fall, best_x = -1.0, -1.0
        best_a, best_a_idx = -1.0, -1
        for (idx, w) in weights:
            v = weight_map[idx]
            aj = v - w
            if aj <= 0:
                continue
            qj = pqueue[idx]
            xj, yj = find_biggest_delta_imb(qj, aj, best_b)

            dj = delta_imb(aj, best_b, xj)
            dj_ = max(delta_imb(aj, second_b, xj),
                      delta_imb(aj, second_b, yj))

#            print "delta_imb for {0} is {1},  w={2}".format(idx,
#                                                            dj,
#                                                            xj)
            
            if (CHOOSE_SLOPE and dj - dj_ > best_fall):
                best_fall = dj - dj_
                best_a = aj
                best_a_idx = idx
                best_x = xj
            elif (not CHOOSE_SLOPE) and (dj > best_fall):
                best_fall = dj
                best_a = aj
                best_a_idx = idx
                best_x = xj

        if (best_fall > 0):
            qi = pqueue[best_b_idx]
            qj = pqueue[best_a_idx]
            weight_map[best_b_idx] += best_x
            weight_map[best_a_idx] -= best_x
            best_delta_imb, best_node = unmake_entry(heapq.heappop(qj))
            heapq.heappush(qi, make_entry(best_node))

            rules.append((best_node.root, best_b_idx))
 #           print "imbalance reduced b", best_delta_imb


 #           print "transfer {0} from {1}({3}) to {2}({4})".format(best_x,
 #                                                                 best_a_idx,
 #                                                                 best_b_idx,
 #                                                                 weight_map[best_a_idx],
 #                                                                 weight_map[best_b_idx])
        else:
            break
               
    vs = [(idx, weight_map[idx]) for (idx, w) in ws]

    return vs, rules
        


class TestEval():

    def __init__(self, eps):
        self.eps = eps
        pass

    def equal(self, x, y):
        return (x >= y - self.eps) and (x <= y + self.eps)

    def weight(self, str):
#        return self.weight1(str)
        return self.weight2(str)

    def weight1(self, str):
        k = get_level(str)
        if k == 0:
            return 1.0
        else:
            if (str[0] == '0'):
                return 0.7 * math.pow(0.5, k - 1)
            else:
                return 0.3 * math.pow(0.5, k - 1)

    def weight2(self, str):
        a = str.count('0')
        b = str.count('1')
        return math.pow(0.7, a) * math.pow(0.3, b)

#        return math.pow(0.5, a) * math.pow(0.5, b)


def gen(ntests, nweights):
    ws_list = []
    for i in range(0, ntests):
        ns = [random.random() for j in range(0, nweights)]
        s = sum(ns)
        ws = zip(range(0, nweights), [n / s for n in ns])
        ws_list.append(ws)
    return ws_list

def example():
    eps = 1e-3
    eval = TestEval(eps)
    ntests = 50
    nweights = 16 
    ws_list = gen(ntests, nweights)
    
    skew_win, tie, balance_win = 0, 0, 0
    skew_time = 0.0
    balance_time = 0.0
    for ws in ws_list:
        start = time.time()
        CHOOSE_SLOPE = True
        values, rules = approximate(ws, eps, eval, True)
        skew_time = skew_time + time.time() - start

        if False:
            print values
            print len(rules)
            print "\n".join(str(r) for r in rules)

        skew = len(rules)

        ## None: no default rules
        ecmp_info = None
        algo_mode = HEU ## BF
        start = time.time()
        CHOOSE_SLOPE = False
        values, rules = approximate(ws, eps, eval, False)

#        _, _, rules, values = find_single_vip_w_default(ws,
#                                                        eps,
#                                                        algo_mode,
#                                                        ecmp_info)
        balance_time = balance_time + time.time() - start
        balance = len(rules)

        if skew < balance:
            skew_win = skew_win + 1
        elif balance < skew:
            balance_win = balance_win + 1
        else:
            tie = tie + 1
            
        if False:
            print ",".join("({0},{1})".format(v[0],v[2]) for v in values)
            print len(rules)
            print "\n".join(str(r) for r in rules)
 
    print "skew_win {0}, tie {1}, balance_win {2}".format(skew_win,
                                                          tie,
                                                          balance_win)
    print "skew_time {0}, balance_time {1}".format(skew_time, balance_time)

example()
