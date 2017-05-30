import sql
import os, sys, inspect


cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
   print "import directory: ", cmd_folder
   sys.path.insert(0, cmd_folder)

paths = ["./rule_gen", "./sq/"]
for relative_path in paths:
  cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], relative_path)))
  if cmd_subfolder not in sys.path:
     print "import directory: ", cmd_subfolder
     sys.path.insert(0, cmd_subfolder)
