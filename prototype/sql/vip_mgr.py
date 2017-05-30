from sql_wrapper import SQLWrapper
from table_owner import *
from base_mgr import BaseManager


## manage VIP information
class VIPManager(BaseManager):


######### STATIC INFO START ############
  VIP_CONFIG = {}

  VIP_CONFIG[TableSchema.SERVICE_DESC_TBNAME] = [
    ('192.168.124.2', -1, 6, 'vip1', 'test', BaseManager.DEFAULT, BaseManager.TRANS_ID),
    ('10.6.1.1', 80, 6, 'vip2', 'ecmp', BaseManager.DEFAULT, BaseManager.TRANS_ID)
  ]

  VIP_CONFIG[TableSchema.VIP_LABEL_TBNAME] = [
    ('vip1', 'vip1', BaseManager.TRANS_ID),
    ('vip2', 'vip2', BaseManager.TRANS_ID)
  ]

  VIP_CONFIG[TableSchema.VIP_WEIGHT_TBNAME] = [
    ('vip1', 4, 1, BaseManager.DEFAULT, BaseManager.TRANS_ID),
    ('vip1', 5, 1, BaseManager.DEFAULT, BaseManager.TRANS_ID),
    ('vip2', 9, 1, BaseManager.DEFAULT, BaseManager.TRANS_ID),
    ('vip2', 10, 1, BaseManager.DEFAULT, BaseManager.TRANS_ID) 
  ]


  VIP_CONFIG[TableSchema.VIP_TRAFFIC_TBNAME] = [
    ('vip1', 1.0, BaseManager.DEFAULT, BaseManager.TRANS_ID),
    ('vip2', 1.0, BaseManager.DEFAULT, BaseManager.TRANS_ID)
  ]

######### STATIC INFO FINISH ############

  @staticmethod
  def factory():
    if VIP_MGR == None:
      VIP_MGR = VipManager(wrapper)

  def __init__(self, wrapper):
    BaseManager.__init__(self, wrapper)
    pass

  ## init
  def init_vip_info(self, trans_id):
    self.start_op()
    self.init_info(VIPManager.VIP_CONFIG, trans_id)
    self.end_op()

  ## update the weight of device in a vip
  def update_weight(self, vip_id, device_id, weight, trans_id):
    self.start_op()

    criteria = [(Field.VIP_ID, repr(vip_id)),
          (Field.DEVICE_ID, repr(device_id)),] 

    values = [(Field.WEIGHT, repr(weight)),
                  (Field.TRANSACTION_ID, repr(trans_id))]

    self.update_info(TableSchema.VIP_WEIGHT_TBNAME, 
               values, criteria)

    self.end_op()

  def read_vip_traffic(self, vip_id):
    fields = [Field.TRAFFIC_VOLUME]
    criteria = [(Field.VIP_ID, repr(vip_id))]
    entry = self.query_one_info(fields,
                                TableSchema.VIP_TRAFFIC_TBNAME,
                                criteria,
                                None,
                                None)
    traffic = entry[0]
    
    return traffic

  def read_vip_grouped_weights(self, vip_id):
    fields = [Field.NORTH_BOUND_DEVICE_ID, "sum({})".format(Field.WEIGHT)]
    X = TableSchema.VIP_WEIGHT_TBNAME
    Y = TableSchema.DEVICE_ID_TBNAME
    J = Field.DEVICE_ID
    tb_name = "{},{}".format(X, Y)
    criteria = [("{}.{}".format(X, J), "{}.{}".format(Y, J)), 
                (Field.VIP_ID, repr(vip_id))]
    group_by = [Field.NORTH_BOUND_DEVICE_ID]
    list = self.query_info(fields, tb_name, criteria, group_by, None)

    weights = []
    for entry in list:
      weights.append((entry[0], float(entry[1])))
    return weights

  def read_vip_desc(self, vip_id):
    fields = [Field.VIP, Field.PORT, Field.PROTO]
    criteria = [(Field.VIP_ID, repr(vip_id))]
    entry = self.query_one_info(fields,TableSchema.SERVICE_DESC_TBNAME, criteria, None, None)
    return (entry[0], entry[1], entry[2])
  


  def close(self):
    pass
