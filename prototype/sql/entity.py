from abc import ABCMeta
from sql_wrapper import SQLWrapper


## The basic manager class
## All the methods should be private, only available to its sub-class
## Read/Write to tables
class Entity:

  def __init__(self, wrapper):
    self.__wrapper = wrapper

  # Not implemented
  def rollback_op(self):
    pass

  # Not implemented
  def start_op(self):
    pass

  def end_op(self):
    self.__wrapper.commit()

  ## clear table
  def clear_info(self, tbname):
    self.__wrapper.clear_table(tbname)

  ## insert tuples
  def insert_info(self, tbname, tuples, trans_id):
    for tuple in tuples:
      self.__wrapper.insert_tuple(tbname, tuple)


  ## query tuples
  def query_info(self, fields, tbname, criteria, group, order):
    return self.__wrapper.query_tuple(fields, tbname, criteria, group, order)


  ## query tuples
  def query_one_info(self, fields, tbname, criteria, group, order):
    return self.__wrapper.query_one_tuple(fields, tbname, criteria, group, order)

  ## update tuples
  def update_info(self, tbname, values, criteria):
    self.__wrapper.update_tuple(tbname, values, criteria)

  ## delete tuples
  def delete_info(self, tbname, criteria):
    self.__wrapper.delete_tuple(tbname, criteria)
