from sql_wrapper import SQLWrapper

class View:

  def __init__(self, vw_name, fields):
    self.vw_name = vw_name
    self.__fields = fields


class ViewSchema:

  SCHEMA = {}


  DEVICE_SPEC_VIEW_NAME = "device_spec_view"
  DEVICE_SPEC_VIEW = View(DEVICE_SPEC_VIEW_NAME,
           [Field.DEVICE_SPEC_ID,
            Field.DEVICE_CLASS_DESC,
            Field.DEVICE_TYPE_DESC])
  SCHEMA[DEVICE_SPEC_VIEW_NAME] = DEVICE_SPEC_VIEW

  Local


class ViewOwner:

  def __init__(self, wrapper):
    self.__wrapper = wrapper

  def create_table(self):

    print "drop view", ViewSchema.DEVICE_SPEC_VIEW_NAME
    cmd = "DROP VIEW {0};".format(ViewSchema.DEVICE_SPEC_VIEW_NAME)
    print "create view", ViewSchema.DEVICE_SPEC_VIEW_NAME
    cmd = ("CREATE OR REPLACE VIEW {0} AS SELECT " +
           "A.{4}, B.{5}, C.{6} " + 
           "FROM {1} AS A INNER JOIN {2} AS B " +
           "ON A.{7} = B.{7} " +
           "INNER JOIN {3} AS C " +
           "ON A.{8} = C.{8};").format(ViewSchema.LA_RULE_TABLE_VIEW_NAME,
                                       TableSchema.RULE_TABLE_TBNAME,
                                       TableSchema.DEVICE_ID_TBNAME,
                                       Field.VERSION,
                                       Field.VIP_LABEL,
                                       Field.DEVICE_ID,
                                       Field.PKT_MATCH,
                                       Field.ACTION,
                                       Field.TO_DEVICE_ID,
                                       Field.DEVICE_ADDRESS_TYPE,
                                       Field.DEVICE_ADDRESS,
                                       Field.DEVICE_SPEC_ID,
                                       Field.PRIORITY,
                                       Field.TS,
                                       Field.TRANSACTION_ID)
    self.__wrapper.run(cmd)


    print "drop view", ViewSchema.DEVICE_SPEC_VIEW_NAME
    cmd = "DROP VIEW {0};".format(ViewSchema.DEVICE_SPEC_VIEW_NAME)

    print "create view", ViewSchema.DEVICE_SPEC_VIEW_NAME
    cmd = ("CREATE OR REPLACE VIEW {0} AS SELECT " +
           "A.{3}, A.{4}, A.{5}, A{6}, A{7}, A{8}, B{9}" + 
           "FROM {1} AS A INNER JOIN {2} AS B " +
           "ON A.{3} = B.{3}").format(ViewSchema.DEVICE_SPEC_VIEW_NAME,
                                      TableSchema.DEVICE_SPEC_TBNAME,
                                      TableSchema.DEVICE_TYPE_TBNAME,
                                      TableSchema.DEVICE_CLASS_TBNAME,
                                      Field.DEVICE_SPEC_ID,
                                      Field.DEVICE_TYPE_DESC,
                                      Field.DEVICE_CLASS_DESC,
                                      Field.DEVICE_TYPE,
                                      Field.DEVICE_CLASS)
    self.__wrapper.run(cmd)
