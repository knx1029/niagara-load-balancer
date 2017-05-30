from sql_wrapper import SQLWrapper

class Field:

   # type
   MATCH_STRING = "varchar(512)"
   LONG_STRING = "varchar(128)"
   SHORT_STRING = "varchar(16)"
   IP_STRING = "varchar(64)"
   ID_STRING = "varchar(64)"
   TIMESTAMP = "timestamp"
   INT = "int"
   REAL = "real"

   # comment
   NOT_NULL = "NOT NULL"
   CAN_NULL = None

   # fields
   SPEC = {}


   # ---------- Device -----------#

   DEVICE_SPEC_ID = "device_spec_id"
   SPEC[DEVICE_SPEC_ID] = (INT, NOT_NULL)

   DEVICE_TYPE = "device_type"
   SPEC[DEVICE_TYPE] = (LONG_STRING, NOT_NULL)

   DEVICE_CLASS = "device_class"
   SPEC[DEVICE_CLASS] = (SHORT_STRING, NOT_NULL)

   DEVICE_RULE_LIMIT = "device_rule_limit"
   SPEC[DEVICE_RULE_LIMIT] = (INT, NOT_NULL)

   DEVICE_SPEC_DESC = "device_spec_desc"
   SPEC[DEVICE_SPEC_DESC] =(LONG_STRING, NOT_NULL)

#   DEVICE_TYPE_DESC = "device_type_desc"
#   SPEC[DEVICE_TYPE_DESC] = (LONG_STRING, CAN_NULL)

#   DEVICE_CLASS_DESC = "device_class_desc"
#   SPEC[DEVICE_CLASS_DESC] = (SHORT_STRING, NOT_NULL)

   DEVICE_ID = "device_id"
   SPEC[DEVICE_ID] =(INT, NOT_NULL)

   DEVICE_ADDRESS_TYPE = "device_address_type"
   SPEC[DEVICE_ADDRESS_TYPE] = (SHORT_STRING, NOT_NULL)

   DEVICE_ADDRESS = "device_address"
   SPEC[DEVICE_ADDRESS] = (IP_STRING, NOT_NULL)

   NORTH_BOUND_DEVICE_ID = "north_bound_device_id"
   SPEC[NORTH_BOUND_DEVICE_ID] = (INT, NOT_NULL)

   DEVICE_COMMENT = "device_comment"
   SPEC[DEVICE_COMMENT] = (LONG_STRING, CAN_NULL)

   # ---------- VIPs -----------#

   SERVICE_DESC = "service_desc"
   SPEC[SERVICE_DESC] = (LONG_STRING, NOT_NULL)

   VIP = "vip"
   SPEC[VIP] = (IP_STRING, NOT_NULL)

   PORT = "port"
   SPEC[PORT] = (INT, CAN_NULL)

   PROTO = "proto"
   SPEC[PROTO] = (INT, CAN_NULL)

   VIP_ID = "vip_id"
   SPEC[VIP_ID] = (ID_STRING, NOT_NULL)

   SERVICE = "service"
   SPEC[SERVICE] = (LONG_STRING, NOT_NULL)

   VIP_LABEL = "vip_label"
   SPEC[VIP_LABEL] = (ID_STRING, NOT_NULL)

   WEIGHT = "weight"
   SPEC[WEIGHT] = (INT, NOT_NULL)

   TRAFFIC_VOLUME = "traffic_volume"
   SPEC[TRAFFIC_VOLUME] = (REAL, NOT_NULL)

   # ---------- Rules -----------#

   VERSION = "version"
   SPEC[VERSION] = (INT, NOT_NULL)

   INSTALLED_VERSION = "installed_version"
   SPEC[INSTALLED_VERSION] = (INT, NOT_NULL)

   MARKING_VERSION = "marking_version"
   SPEC[MARKING_VERSION] = (INT, NOT_NULL)

   ACTION = "action"
   SPEC[ACTION] = (SHORT_STRING, NOT_NULL)

   TO_DEVICE_ID = "to_device_id"
   SPEC[TO_DEVICE_ID] = (INT, NOT_NULL)

   PRIORITY = "priority"
   SPEC[PRIORITY] = (INT, NOT_NULL)

   PKT_MATCH = "pkt_match"
   SPEC[PKT_MATCH] = (MATCH_STRING, NOT_NULL)

   # ---------- Health Checking -----------#

   HEALTH_CHECK_ID = "health_check_id"
   SPEC[HEALTH_CHECK_ID] = (INT, NOT_NULL)

   CHECK_SPEC = "check_spec"
   SPEC[CHECK_SPEC] = (LONG_STRING, NOT_NULL)

   FREQUENCY_PER_HOUR = "frequency_per_hour"
   SPEC[FREQUENCY_PER_HOUR] = (REAL, NOT_NULL)

   FREQUENCY_ON_FAILURE = "frequency_on_failure"
   SPEC[FREQUENCY_ON_FAILURE] = (REAL, NOT_NULL)

   FAIL_HEALTH_ON_NUM_FAILURE = "fail_health_on_num_failure"
   SPEC[FAIL_HEALTH_ON_NUM_FAILURE] = (INT, NOT_NULL)


   # ---------- Health Checking -----------#

   SERVICE_NET_LOAD = "service_net_load"
   SPEC[SERVICE_NET_LOAD] = (REAL, CAN_NULL)

   SERVICE_CPU_LOAD = "service_cpu_load"
   SPEC[SERVICE_CPU_LOAD] = (REAL, CAN_NULL)

   SERVICE_IO_LOAD = "service_io_load"
   SPEC[SERVICE_IO_LOAD] = (REAL, CAN_NULL)

   SERVICE_MEM_LOAD = "service_mem_load"
   SPEC[SERVICE_MEM_LOAD] = (REAL, CAN_NULL)

   SYS_NET_LOAD = "sys_net_load"
   SPEC[SYS_NET_LOAD] = (REAL, CAN_NULL)

   SYS_CPU_LOAD = "sys_cpu_load"
   SPEC[SYS_CPU_LOAD] = (REAL, CAN_NULL)

   SYS_IO_LOAD = "sys_io_load"
   SPEC[SYS_IO_LOAD] = (REAL, CAN_NULL)

   SYS_MEM_LOAD = "sys_mem_load"
   SPEC[SYS_MEM_LOAD] = (REAL, CAN_NULL)

   DEVICE_STATUS = "device_status"
   SPEC[DEVICE_STATUS] = (SHORT_STRING, NOT_NULL)

   HEALTH_STATUS = "health_status"
   SPEC[HEALTH_STATUS] = (SHORT_STRING, NOT_NULL)

   HEALTH_CHECKER_ID = "health_checker_id"
   SPEC[HEALTH_CHECKER_ID] = (INT, NOT_NULL)

   HEALTH_CHECK_ID = "health_check_id"
   SPEC[HEALTH_CHECK_ID] = (INT, NOT_NULL)

   HEALTH_COMMENT = "health_comment"
   SPEC[HEALTH_COMMENT] = (LONG_STRING, NOT_NULL)

   # ---------- System Logs -----------#

   TS = "ts"
   SPEC[TS] = (TIMESTAMP, NOT_NULL)

   TRANSACTION_ID = "transaction_id"
   SPEC[TRANSACTION_ID] = (ID_STRING, NOT_NULL)


class Table:

  def __init__(self, tb_name, fields, pk):
    self.tb_name = tb_name
    self.__fields = fields
    self.__primary_key = pk

  def add_field(self, field_name):
    self.__fields.append(field_name)

  def set_pk(self, pk):
    self.__primary_key = pk

  # retrun a list of field string
  def fields2str(self, field_spec):
    def field2str(field_name):
      field_type, comment = field_spec[field_name]
      if (comment != None):
        return "{} {} {}".format(field_name, field_type, comment)
      else:
        return "{} {}".format(field_name, field_type)

    if (self.__fields == None):
      return None
    else:
      return map(field2str, self.__fields)

  # return a list of primary key string
  def pk2str(self):
    return self.__primary_key


  def desc(self, field_spec):
    fields_str = self.field2str(field_spec)
    pk_str = self.pk2str()
    desc =  ", ".join(fields_str)
    if pk_str != None:
      desc = desc + ", PRIMARY KEY(" + ", ".join(pk_str) + ")"
    return desc


class TableSchema:

  SCHEMA = {}

  # --------------  Devices ---------------- #

  DEVICE_SPEC_TBNAME = "device_spec"
  DEVICE_SPEC_TABLE = Table(DEVICE_SPEC_TBNAME,
       [Field.DEVICE_SPEC_ID,
        Field.DEVICE_TYPE,
        Field.DEVICE_CLASS,
        Field.DEVICE_RULE_LIMIT,
        Field.DEVICE_SPEC_DESC],
       [Field.DEVICE_SPEC_ID])
  SCHEMA[DEVICE_SPEC_TBNAME] = DEVICE_SPEC_TABLE
  

#  DEVICE_CLASS_TBNAME = "device_class"
#  DEVICE_CLASS_TABLE = Table(DEVICE_CLASS_TBNAME,
#       [Field.DEVICE_CLASS,
#        Field.DEVICE_CLASS_DESC],
#       [Field.DEVICE_CLASS])
#  SCHEMA[DEVICE_CLASS_TBNAME] = DEVICE_CLASS_TABLE

#  DEVICE_TYPE_TBNAME = "device_type"
#  DEVICE_TYPE_TABLE = Table(DEVICE_TYPE_TBNAME,
#       [Field.DEVICE_TYPE,
#        Field.DEVICE_TYPE_DESC],
#       [Field.DEVICE_TYPE])
#  SCHEMA[DEVICE_TYPE_TBNAME] = DEVICE_TYPE_TABLE

  DEVICE_ID_TBNAME = "device_id"
  DEVICE_ID_TABLE = Table(DEVICE_ID_TBNAME,
       [Field.DEVICE_ID,
        Field.DEVICE_ADDRESS_TYPE,
        Field.DEVICE_ADDRESS,
        Field.DEVICE_SPEC_ID,
        Field.NORTH_BOUND_DEVICE_ID,
        Field.DEVICE_COMMENT,
        Field.TS,
        Field.TRANSACTION_ID],
       [Field.DEVICE_ID])
  SCHEMA[DEVICE_ID_TBNAME] = DEVICE_ID_TABLE

  # --------------  VIPs ---------------- #
  SERVICE_DESC_TBNAME = "service_desc"
  SERVICE_DESC_TABLE = Table(SERVICE_DESC_TBNAME,
        [Field.VIP,
         Field.PORT,
         Field.PROTO,
         Field.VIP_ID,
         Field.SERVICE,
         Field.TS,
         Field.TRANSACTION_ID],
        [Field.VIP_ID])
  SCHEMA[SERVICE_DESC_TBNAME] = SERVICE_DESC_TABLE

  VIP_LABEL_TBNAME = "vip_label"
  VIP_LABEL_TABLE = Table(VIP_LABEL_TBNAME,
        [Field.VIP_ID,
         Field.VIP_LABEL,
         Field.TRANSACTION_ID],
        [Field.VIP_ID])
  SCHEMA[VIP_LABEL_TBNAME] = VIP_LABEL_TABLE

  VIP_WEIGHT_TBNAME = "vip_weight"
  VIP_WEIGHT_TABLE = Table(VIP_WEIGHT_TBNAME,
        [Field.VIP_ID,
         Field.DEVICE_ID,
         Field.WEIGHT,
         Field.TS,
         Field.TRANSACTION_ID],
        [Field.VIP_ID,
         Field.DEVICE_ID,
         Field.TRANSACTION_ID])
  SCHEMA[VIP_WEIGHT_TBNAME] = VIP_WEIGHT_TABLE

  VIP_TRAFFIC_TBNAME = "vip_traffic"
  VIP_TRAFFIC_TABLE = Table(VIP_TRAFFIC_TBNAME,
        [Field.VIP_ID,
         Field.TRAFFIC_VOLUME, 
         Field.TS,
         Field.TRANSACTION_ID],
        [Field.VIP_ID,
         Field.TRANSACTION_ID])
  SCHEMA[VIP_TRAFFIC_TBNAME] = VIP_TRAFFIC_TABLE

  # --------------  Health Check ---------------- #

  HEALTH_CHECK_TBNAME = "health_check"
  HEALTH_CHECK_TABLE = Table(HEALTH_CHECK_TBNAME,
        [Field.HEALTH_CHECK_ID,
         Field.VIP_LABEL,
         Field.CHECK_SPEC,
         Field.FREQUENCY_PER_HOUR,
         Field.FREQUENCY_ON_FAILURE,
         Field.FAIL_HEALTH_ON_NUM_FAILURE,
         Field.TRANSACTION_ID],
        [Field.HEALTH_CHECK_ID])
  SCHEMA[HEALTH_CHECK_TBNAME] = HEALTH_CHECK_TABLE

  # --------------  Rules ---------------- #

  ACTIVE_VERSION_TBNAME = "active_version"
  ACTIVE_VERSION_TABLE = Table(ACTIVE_VERSION_TBNAME,
         [Field.VERSION,
          Field.VIP_ID,
          Field.TS, Field.TRANSACTION_ID],
         [Field.VIP_ID])
  SCHEMA[ACTIVE_VERSION_TBNAME] = ACTIVE_VERSION_TABLE

  MARKING_VERSION_TBNAME = "marking_version"
  MARKING_VERSION_TABLE = Table(MARKING_VERSION_TBNAME,
          [Field.VIP_ID,
           Field.DEVICE_ID,
           Field.INSTALLED_VERSION,
           Field.MARKING_VERSION,
           Field.TS,
           Field.TRANSACTION_ID],
          [Field.VIP_ID,
           Field.DEVICE_ID])
  SCHEMA[MARKING_VERSION_TBNAME] = MARKING_VERSION_TABLE

  RULE_TABLE_TBNAME = "rule_table"
  RULE_TABLE_TABLE = Table(RULE_TABLE_TBNAME,
          [Field.VERSION,
           Field.VIP_LABEL,
           Field.DEVICE_ID,
           Field.PKT_MATCH,
           Field.ACTION,
           Field.TO_DEVICE_ID,
           Field.PRIORITY,
           Field.TS,
           Field.TRANSACTION_ID],
          [Field.VERSION,
           Field.DEVICE_ID,
           Field.VIP_LABEL,
           Field.PRIORITY])
  SCHEMA[RULE_TABLE_TBNAME] = RULE_TABLE_TABLE

  ABSTRACT_RULE_TABLE_TBNAME = "abstract_rule_table"
  ABSTRACT_RULE_TABLE_TABLE = Table(ABSTRACT_RULE_TABLE_TBNAME,
          [Field.VERSION,
           Field.VIP_LABEL,
           Field.DEVICE_ID,
           Field.PKT_MATCH,
           Field.TO_DEVICE_ID,
           Field.PRIORITY,
           Field.TS,
           Field.TRANSACTION_ID],
          [Field.VERSION,
           Field.DEVICE_ID,
           Field.VIP_LABEL,
           Field.PRIORITY])
  SCHEMA[ABSTRACT_RULE_TABLE_TBNAME] = ABSTRACT_RULE_TABLE_TABLE


  # --------------  Local Status ---------------- #

  DEVICE_STATUS_TBNAME = "device_status"
  DEVICE_STATUS_TABLE = Table(DEVICE_STATUS_TBNAME,
           [Field.VIP_ID,
            Field.DEVICE_ID,
            Field.SERVICE_NET_LOAD,
            Field.SERVICE_CPU_LOAD,
            Field.SERVICE_IO_LOAD,
            Field.SERVICE_MEM_LOAD,
            Field.SYS_NET_LOAD,
            Field.SYS_CPU_LOAD,
            Field.SYS_IO_LOAD,
            Field.SYS_MEM_LOAD,
            Field.DEVICE_STATUS,
            Field.TS,
            Field.TRANSACTION_ID],
           [Field.DEVICE_ID,
            Field.VIP_ID,
            Field.TRANSACTION_ID])
  SCHEMA[DEVICE_STATUS_TBNAME] = DEVICE_STATUS_TABLE

  HEALTH_STATUS_TBNAME = "health_status"
  HEALTH_STATUS_TABLE = Table(HEALTH_STATUS_TBNAME,
           [Field.DEVICE_ID,
            Field.VIP_ID,
            Field.HEALTH_STATUS,
            Field.HEALTH_CHECKER_ID,
            Field.HEALTH_CHECK_ID,
            Field.HEALTH_COMMENT,
            Field.TS,
            Field.TRANSACTION_ID],
           [Field.DEVICE_ID,
            Field.VIP_ID,
            Field.HEALTH_CHECKER_ID,
            Field.HEALTH_CHECK_ID,
            Field.TRANSACTION_ID]) 
  SCHEMA[HEALTH_STATUS_TBNAME] = HEALTH_STATUS_TABLE

## Create tables
class TableOwner:

  

######### STATIC INFO FINISH ############

  def __init__(self, wrapper):
    self.__wrapper = wrapper

  def create_table(self):
    for tbname, tbschema in TableSchema.SCHEMA.items():
      print "drop", tbname
      self.__wrapper.drop_table(tbname)

      print "create", tbname
      fields = tbschema.fields2str(Field.SPEC)
      pk = tbschema.pk2str()
      self.__wrapper.create_table(tbname, fields, pk)

      print ""



  def close(self):
    pass
