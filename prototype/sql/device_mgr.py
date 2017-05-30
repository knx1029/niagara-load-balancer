from sql_wrapper import SQLWrapper
from table_owner import *
from base_mgr import BaseManager



# manage devices
class DeviceManager(BaseManager):

######### STATIC INFO START ############

  DEV_CONFIG = {}

#  DEV_CONFIG[TableSchema.DEVICE_TYPE_TBNAME] = [(1, "Linux"),
#                                                (2, "Pica8")]

#  DEV_CONFIG[TableSchema.DEVICE_CLASS_TBNAME] = [(1, 'HSW'),
#                                                 (2, 'SSW'),
#                                                 (3, 'BE')]

  DEV_CONFIG[TableSchema.DEVICE_SPEC_TBNAME] = [
   (1, "Linux", "HSW", 1000, "Linux-HSW"),
   (2, "Linux", "SSW", 10000, "Linux-SSW"),
   (3, "Linux", "BE", 0, "Linux-BE"),
   (4, "Pica8", "HSW", 100, "Pica8-HSW"),
   (5, "Pica8", "SSW", 100, "Pica8-HSW"),
   (6, "Linux", "SSW", 100, "Linux-NAT")
  ]

  DEV_CONFIG[TableSchema.DEVICE_ID_TBNAME] = [
    (1, "ipv4", "10.99.88.80", 1, 0, "HSW", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (2, "ipv4", "10.99.88.81", 2, 1, "SSW,Tunnel", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (3, "ipv4", "10.99.88.82", 2, 1, "SSW,Tunnel", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (4, "ipv4", "10.99.88.83", 3, 2, "BE,Link", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (5, "ipv4", "10.99.88.84", 3, 3, "BE,Link", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (6, "ipv4", "192.168.0.1", 4, 0, "HSW", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (7, "ipv4", "192.168.0.2", 5, 6, "HSW,Link", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (8, "ipv4", "192.168.1.2", 5, 6, "HSW,Link", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (9, "ipv4", "10.4.1.1", 6, 7, "SSW,Link", BaseManager.DEFAULT, BaseManager.TRANS_ID),
    (10, "ipv4", "10.5.1.1", 6, 8, "SSW,Link", BaseManager.DEFAULT, BaseManager.TRANS_ID)
  ]


# TABLES['health_check'] = (
#  "health_check_id int NOT NULL, "
#  "vip_label varchar(64) NOT NULL,"
#  "check_spec varchar(128) NOT NULL, "
#  "frequency_per_hour real NOT NULL DEFAULT 60, "
#  "frequency_on_failure real NOT NULL DEFAULT 10,"
#  "fail_health_on_num_failure int NOT NULL DEFAULT 10, "
#  "transaction_id varchar(64) NOT NULL, "
#  "PRIMARY KEY (health_check_id, vip_label)"
# )


### local config
# TABLES['dev_status'] = (
#  "vip_id varchar(64) NOT NULL, "
#  "device_id int NOT NULL, "
#  "service_net_load real, "
#  "service_cpu_load real, "
#  "service_io_load real, "
#  "service_mem_load real, "
#  "sys_net_load real, "
#  "sys_cpu_load real, "
#  "sys_io_load real, "
#  "sys_mem_load real, "
#  "status varchar(64), "
#  "ts timestamp NOT NULL, "
#  "transaction_id varchar(64) NOT NULL, "
#  "PRIMARY KEY (device_id, vip_id, ts)"
# )

# TABLES['health_status'] = (
#   "device_id int NOT NULL, "
#   "vip_id varchar(64) NOT NULL, "
#   "health varchar(16) NOT NULL, "
#   "health_checker_id int NOT NULL, "
#   "health_check_id int NOT NULL, "
#   "detailed_feedback varchar(512) NOT NULL, "
#   "ts timestamp NOT NULL, "
#   "transaction_id varchar(64) NOT NULL"
# )



######### STATIC INFO FINISH ############


  def __init__(self, wrapper):
    BaseManager.__init__(self, wrapper)
    pass

  def init_device_info(self, trans_id):
    self.start_op()
    self.init_info(DeviceManager.DEV_CONFIG, trans_id)
    self.end_op()

  def close(self):
    pass



