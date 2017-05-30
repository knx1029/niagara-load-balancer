import mysql.connector
from mysql.connector import errorcode

CREATE_DB = "CREATE DATABASE IF NOT EXISTS {};"
USE_DB = "USE {};"
DROP_DB  = "DROP DATABASE IF EXISTS {};"
SHOW_DB = "SHOW DATABASES;"

CREATE_TABLE_WO_PK = "CREATE TABLE IF NOT EXISTS {} ({});"
CREATE_TABLE_W_PK = "CREATE TABLE IF NOT EXISTS {} ({}, PRIMARY KEY ({}));"
DROP_TABLE = "DROP TABLE IF EXISTS {}; "
SHOW_TABLE = "SHOW TABLES;"
CLEAR_TABLE = "DELETE FROM {};"

INSERT_TUPLE = "INSERT INTO {} VALUES ({});"
DELETE_TUPLE = "DELETE FROM {} WHERE {};"

QUERY_TUPLE = "SELECT {} FROM {}"
QUERY_TUPLE_CRITERIA = " WHERE {}"
QUERY_TUPLE_GROUP = " GROUP BY {}"
QUERY_TUPLE_ORDER = " ORDER BY {}"

UPDATE_TUPLE = "UPDATE {} SET {}"
UPDATE_TUPLE_CRITERIA = " WHERE {}"

### Utils
def eq_str((x, y)):
  return "{} = {}".format(x, y)


### START
class SQLWrapper:

  def __init__(self, config):
    self.__cnx = mysql.connector.connect(**config)
    self.__cursor = self.__cnx.cursor()

  def close(self):
    self.__cursor.close()
    self.__cnx.close()

  def run(self, cmd):
    try: 
#      print "Running : ", cmd
      self.__cursor.execute(cmd)
    except mysql.connector.Error as err:
      print("Failed operation:{}".format(err))
      return 1
    return 0

  def query(self, cmd):
    self.run(cmd)
    return __cursor.copy()

  # ----------- database ------------ #
  def create_db(self, db_name):
    self.run(CREATE_DB.format(db_name))

  def change_db(self, db_name):
    self.run(USE_DB.format(db_name))

  def drop_db(self, db_name):
    self.run(DROP_DB.format(db_name))


  # ---------- table ---------- #
  def create_table(self, tb_name, fields, pk):
    if (pk == None):
      fstr = ", ".join(fields)
      self.run(CREATE_TABLE_WO_PK.format(tb_name, fstr))
    else:
      fstr = ", ".join(fields)
      pkstr = ", ".join(pk)    
      self.run(CREATE_TABLE_W_PK.format(tb_name, fstr, pkstr))


  def drop_table(self, tb_name):
    self.run(DROP_TABLE.format(tb_name))

  def clear_table(self, tb_name):
    self.run(CLEAR_TABLE.format(tb_name))


  # --------------- tuple ----------------- #
  def insert_tuple(self, tb_name, tuple):
    tuple_str = ",".join(tuple)
    insert = INSERT_TUPLE.format(tb_name, tuple_str)
    self.run(insert)

  
  def query_one_tuple(self, fields, tb_name, criteria, group, order):
    self.__query_tuple(fields, tb_name, criteria, group, order)
    return self.__cursor.fetchone()

  def query_tuple(self, fields, tb_name, criteria, group, order):
    self.__query_tuple(fields, tb_name, criteria, group, order)
    return self.__cursor.fetchall()

  def __query_tuple(self, fields, tb_name, criteria, group, order):

    field_str = ", ".join(fields)
    query = QUERY_TUPLE.format(field_str, tb_name)
    
    if (criteria != None):
      criteria_str = " AND ".join(map(eq_str,criteria))
      query = query + QUERY_TUPLE_CRITERIA.format(criteria_str)
    if (group != None):
      group_str = ", ".join(group)
      query = query + QUERY_TUPLE_GROUP.format(group_str)
    if (order != None):
      order_str = ", ".join(order)
      query = query + QUERY_TUPLE_ORDER.format(order_str) 
    query = query + ";"
    self.run(query)

  def delete_tuple(self, tb_name, criteria):
    delete = CLEAR_TABLE.format(tb_name)

    if (criteria != None):
      criteria_str = " AND ".join(map(eq_str,criteria))
      delete = DELETE_TUPLE.format(tb_name, criteria_str)
    print delete
    self.run(delete)


  # update
  def update_tuple(self, tb_name, values, criteria):
    value_str = ", ".join(map(eq_str, values))
    update = UPDATE_TUPLE.format(tb_name, value_str)

    if (criteria != None):
      criteria_str = " AND ".join(map(eq_str,criteria))
      update = update + UPDATE_TUPLE_CRITERIA.format(criteria_str)

    update = update + ";"
    self.run(update)


  def commit(self):
    self.__cnx.commit()    
