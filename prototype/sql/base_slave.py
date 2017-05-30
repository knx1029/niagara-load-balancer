from abc import ABCMeta
from sql_wrapper import SQLWrapper
from entity import Entity

## The basic slave class
## Can only read
class BaseSlave(Entity):

#  __metaclass__ = ABCMeta
 
  DEFAULT = "__default"
  TRANS_ID = "__transaction_id"

  ACTION_DICT = {"REDIRECT_TO": 0, 0 : "REDIRECT_TO","SEND_TO" : 1, 1 : "SEND_TO", "DROP" : 2, 2 : "DROP", 
         "REJECT" : 3, 3 : "REJECT", "NAT2SW" : 4, 4 : "NAT2SW", "NAT2BE" : 5,  5 : "NAT2BE"}


  def __init__(self, device_id, wrapper):
    self.device_id = device_id
    Entity.__init__(self, wrapper)
    pass

