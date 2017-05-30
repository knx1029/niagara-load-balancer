import math
from utils import *

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

  def remove_tree(self, tree):
    if (tree in self.tree_list):
      self.tree_list.remove(tree)
    tree.mark_subowner()

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
       try:
         idx = self.root.rindex('*')
       except Exception:
         return
       self.left = self.new_tree(self.root[:idx] + '0' + self.root[idx + 1:],
                                 self.owner_id)
       self.left.father = self


   # create the right child
   def expand_right(self):
     if (self.right == None):
       try:
         idx = self.root.rindex('*')
       except Exception:
         return
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


SuffixTree = BasicSuffixTree
SuffixForest = BasicSuffixForest
