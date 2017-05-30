from suffix_forest import *
import math

## suffixes are not equally weighted in the forest
class WSuffixForest(SuffixForest):

    def __init__(self, id, list):
        SuffixForest.__init__(self, id, list)
        pass

    ## it returns a suffix node with largest weight <= v
    ## eval is the object that evaluates weights of nodes
    def get_lower_bound_node(self, v, eval):
        best_bound = 0.0
        best_result = None
        for tree in self.tree_list:
            if (eval.equal(best_bound, v)):
                break
            result = tree.get_lower_bound_node(v, eval, best_bound)
            if (result):
                best_result = result
                _, best_bound = best_result
        return best_result


    ## it returns a suffix node with smallest weight >= v
    ## eval is the object that evaluates weights of nodes
    def get_upper_bound_node(self, v, eval):
        best_bound = 1.0
        best_result = None
        for tree in self.tree_list:
            if (eval.equal(best_bound, v)):
                break
            result = tree.get_upper_bound_node(v, eval, best_bound)
            if (result):
                best_result = result
                _, best_bound = best_result
        return best_result


class WSuffixTree(SuffixTree):

    @staticmethod
    def new_tree(str, id = 0):
        return WSuffixTree(str, id)

    def __init__(self, str, id = 0):
        SuffixTree.__init__(self, str, id)

    ## it returns a suffix node with largest weight <= v
    ## eval is the object that evaluates weights of nodes
    def get_lower_bound_node(self, w, eval, best_bound = 0):
        return self._get_lower_bound_node(w, eval, self.owner_id, best_bound)

    def _get_lower_bound_node(self, w, eval, id, best_bound):

        if (eval.equal(best_bound, w)):
            return None

        if (self.owner_id != id):
            return None

        ## evaluate node itself
        if (not self.subowner_exist):
            v = eval.weight(self.root)
            if (v <= w):
                if (w > best_bound):
                    return (self, v)
                else:
                    return None

        current = None

        ## search left
        self.expand_left()
        left_result = self.left._get_lower_bound_node(w, eval, id, best_bound)
        if (left_result):
            current = left_result
            _, best_bound = current

        ## search right
        self.expand_right()
        right_result = self.right._get_lower_bound_node(w, eval, id, best_bound)
        if (right_result):
            current = right_result

        return current



    ## it returns a suffix node with smallest weight >= v
    ## eval is the object that evaluates weights of nodes
    def get_upper_bound_node(self, w, eval, best_bound = 1.0):
        return self._get_upper_bound_node(w, eval, self.owner_id, best_bound)

    def _get_upper_bound_node(self, w, eval, id, best_bound = 1.0):
        if (eval.equal(w, best_bound)):
            return None

        if (self.owner_id == id):
            return None

        ## evaluate the node itself
        current = None
        if (not self.subowner_exist):
            v = eval.weight(self.root)
            if (v < w):
                return None
            if (v < best_bound):
                best_bound = v
                current = (self, v)

        ## search left
        self.expand_left()
        left_result = self.left._get_upper_bound_node(w, eval, id, best_bound)
        if (left_result):
            current = left_result
            _, best_bound = current

        ## search right
        self.expand_right()
        right_result = self.right._get_upper_bound_node(w, eval, id, best_bound)
        if (right_result):
            current = right_result

        return current
            


class SuffixEval():

    def __init__(self, eps):
        print "?????"
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
            if (str[-1] == '0'):
                return 0.7 * math.pow(0.5, k - 1)
            else:
                return 0.3 * math.pow(0.5, k - 1)

    def weight2(self, str):
        a = str.count('0')
        b = str.count('1')
        return math.pow(0.5, a) * math.pow(0.5, b)


def approximate_weights(ws):
    vs = zip(ws, [0.0] * len(ws))

    while True:
        biggest = 1.0
        biggest_wv = None
        for wv in vs:
            w, v = wv
            if (math.abs(w - v) > biggest):
                biggest = math.abs(w - v)
                biggest_wv = wv


def example():
    root_str = "********"
    left_str = "*******0"
    right_str = "*******1"
    
    a = WSuffixForest(0, [])
    b = WSuffixForest(1, [])
    a.add_tree(WSuffixTree(root_str))

    eval = SuffixEval(1e-3)
    
    w = 0.3

    print eval.weight("101")
    node, v =  a.get_lower_bound_node(w, eval)
    str = node.root
    print str, v
    a.remove_node(node)
    b.add_tree(node)
    
    a.tree_list[0].show()

