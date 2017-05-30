from abc import ABCMeta
from entity import Entity
from sql_wrapper import SQLWrapper


## The basic manager class
## All the methods should be private, only available to its sub-class
## Read/Write to tables
class BaseManager(Entity):
 
  DEFAULT = "__default"
  TRANS_ID = "__transaction_id"

  DEFAULT_VALUE = "default"


  ACTION_DICT = {"REDIRECT_TO": 0,
                 0 : "REDIRECT_TO",
                 "SEND_TO" : 1,
                 1 : "SEND_TO",
                 "DROP" : 2,
                 2 : "DROP", 
                 "REJECT" : 3,
                 3 : "REJECT",
                 "NAT2SW" : 4,
                 4 : "NAT2SW",
                 "NAT2BE" : 5, 
                 5 : "NAT2BE"}


  def __init__(self, wrapper):
    Entity.__init__(self, wrapper)
    pass


  ## init table
  def init_info(self, config, trans_id):

    def element_to_str(i):
      if i == BaseManager.DEFAULT:
        return BaseManager.DEFAULT_VALUE
      elif i == BaseManager.TRANS_ID:
        return repr(trans_id)
      else:
        return repr(i)

    def entry_to_tuple(t):
      return map(element_to_str, t)
    
    for tbname in config:
      # clear entries
      self.clear_info(tbname)

      # insert
      entries = config[tbname]
      tuples = map(entry_to_tuple, entries)
      self.insert_info(tbname, tuples, trans_id)
