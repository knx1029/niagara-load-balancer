import math

# suffix forest, i.e, a list of suffix tree
class BasicSuffixForest:

  # tree_list = []
  def __init__(self, id, list):
    self.id = id
    self.tree_list = list
    for tree in self.tree_list:
      tree.set_owner(id)
    pass

  # find a node of level k
  def find_node(self, k):
    # try removing the node from a tree
    for tree in self.tree_list:
      node = tree.find_node(k)
      if (node):
        return node
      
    return None

  def remove_node(self, node):
    if (node in self.tree_list):
      self.tree_list.remove(node)
    node.mark_subowner()

  # remove node matching str
  def remove_matching_nodes(self, str):
    # try removing the node from a tree
    for tree in self.tree_list:
      tree.remove_matching_nodes(str)


  # add a new tree to the forest
  def add_tree(self, tree):
    tree.set_owner(self.id)
    self.tree_list.append(tree)

  def __str__(self):
    return '[ {} ]'.format(','.join('{}'.format(k.root)
                                    for k in self.tree_list))

# suffix tree data structure
class BasicSuffixTree:

   @staticmethod
   def new_tree(str, id = 0):
     return BasicSuffixTree(str, id)


   def __init__(self, str, id = 0):
     self.root = str
     self.owner_id = id
     self.subowner_exist = False
     self.left = None
     self.right = None
     self.father = None

     # level = #non-* bits
     self.level = get_level(self.root)

   def show(self):
     print self.root, self.owner_id, self.subowner_exist
     if (self.subowner_exist):
       if (self.left):
         self.left.show()
       if (self.right):
         self.right.show()

   def set_owner(self, id):
     self.owner_id = id

   ## create the left child
   def expand_left(self):
     if (self.left == None):
       idx = self.root.index('*')
       self.left = self.new_tree(self.root[:idx] + '0' + self.root[idx + 1:],
                                 self.owner_id)
       self.left.father = self


   # create the right child
   def expand_right(self):
     if (self.right == None):
       idx = self.root.index('*')
       self.right = self.new_tree(self.root[:idx] + '1' + self.root[idx + 1:],
                                  self.owner_id)
       self.right.father = self
    
   ## mark subowner_exist of all ancestors as True
   def mark_subowner(self):
     node = self.father
     while (node):
       node.subowner_exist = True
       node = node.father


   ## recursively search for a node of level k
   def find_node(self, k):
     node = self._find_node(k, self.owner_id)
     return node

   ## recursively search for a node of level k with givne owner
   def _find_node(self, k, id):
     if (self.owner_id != id or self.level > k):
       return None
     elif self.level == k:
       if (self.subowner_exist):
         return None
       else:
         return self
     else:
       self.expand_left()
       self.expand_right()
       node = self.left._find_node(k, id)
       if node:
         self.subowner_exist = True
         return node

       node = self.right._find_node(k, id)
       if node:
         self.subowner_exist = True
         return node

     return None


   # recursively remove all nodes contained in str
   def remove_matching_nodes(self, str):
     return self._remove_matching_nodes(str, self.owner_id)

   def _remove_matching_nodes(self, str, id):
     # main logic starts
     if (self.owner_id != id):
       return 

     sign = overlap(self.root, str)
     if (sign == NONE):
       pass
     elif (sign == CONTAINED):
       self.owner_id = -1
       return
     elif (sign == OVERLAP):
       self.subowner_exist = True
       idx = self.root.index('*')
       self.expand_left()
       self.left._remove_matching_nodes(str, id)

       self.expand_right()
       self.right._remove_matching_nodes(str, id)



## define overlap, s1 contained/overlap/none in s2
MISC, NONE, CONTAINED, OVERLAP = -1, 0, 1, 2
def overlap(s1, s2):
  if (len(s1) != len(s2)):
    return MISC
  conj = ""
  for i in range(0, len(s1)):
    if (s1[i] != s2[i] and s1[i] != '*' and s2[i] != '*'):
      return NONE
    elif (s1[i] == '*'):
      conj = conj + s2[i]
    else:
      conj = conj + s1[i]
  if (s1 == conj):
    return CONTAINED
  else:
    return OVERLAP


## return the join of s1 and s2
def join(s1, s2):
  if (len(s1) != len(s2)):
    return None
  conj = ""
  for i in range(0, len(s1)):
    if (s1[i] != s2[i] and s1[i] != '*' and s2[i] != '*'):
      return None
    elif (s1[i] == '*'):
      conj = conj + s2[i]
    else:
      conj = conj + s1[i]
  return conj


def get_unit(k):
  return 1.0 / (1 << k)

def get_level(str):
  return len(str) - str.count('*')


## suffixes are not equally weighted in the forest
class WSuffixForest(BasicSuffixForest):

    def __init__(self, id, list):
        BasicSuffixForest.__init__(self, id, list)
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


class WSuffixTree(BasicSuffixTree):

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
        return math.pow(0.6, a) * math.pow(0.4, b)


SuffixTree = BasicSuffixTree
SuffixForest = BasicSuffixForest
