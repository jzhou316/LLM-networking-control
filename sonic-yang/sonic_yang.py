import libyang as ly
import syslog

from json import dump
from glob import glob

from sonic_yang_ext import SonicYangExtMixin, SonicYangException

"""
Yang schema and data tree python APIs based on libyang python
Here, sonic_yang_ext_mixin extends funtionality of sonic_yang,
i.e. it is mixin not parent class.
"""
class SonicYang(SonicYangExtMixin):
    def __init__(self, yang_dir, debug=False, print_log_enabled=True, sonic_yang_options=0):
        self.yang_dir = yang_dir
        self.ctx = None
        self.module = None
        self.root = None

        # logging vars
        self.SYSLOG_IDENTIFIER = "sonic_yang"
        self.DEBUG = debug
        self.print_log_enabled = print_log_enabled

        # yang model files, need this map it to module
        self.yangFiles = list()
        # map from TABLE in config DB to container and module
        self.confDbYangMap = dict()
        # JSON format of yang model [similar to pyang conversion]
        self.yJson = list()
        # config DB json input, will be cropped as yang models
        self.jIn = dict()
        # YANG JSON, this is traslated from config DB json
        self.xlateJson = dict()
        # reverse translation from yang JSON, == config db json
        self.revXlateJson = dict()
        # below dict store the input config tables which have no YANG models
        self.tablesWithOutYang = dict()
        # below dict will store preProcessed yang objects, which may be needed by
        # all yang modules, such as grouping.
        self.preProcessedYang = dict()
        # element path for CONFIG DB. An example for this list could be:
        # ['PORT', 'Ethernet0', 'speed']
        self.elementPath = []
        try:
            self.ctx = ly.Context(yang_dir, sonic_yang_options)
        except Exception as e:
            self.fail(e)

        return
    
    def __del__(self):
        pass
    
    def sysLog(self, debug=syslog.LOG_INFO, msg=None, doPrint=False):
        # log debug only if enabled
        if self.DEBUG == False and debug == syslog.LOG_DEBUG:
            return
        if doPrint and self.print_log_enabled:
            print("{}({}):{}".format(self.SYSLOG_IDENTIFIER, debug, msg))
        syslog.openlog(self.SYSLOG_IDENTIFIER)
        syslog.syslog(debug, msg)
        syslog.closelog()

        return

    def fail(self, e):
        self.sysLog(msg=e, debug=syslog.LOG_ERR, doPrint=True)
        raise e

    """
    load_schema_module(): load a Yang model file
    input:    yang_file - full path of a Yang model file
    returns:  Exception if error
    """
    def _load_schema_module(self, yang_file):
        try:
            with open(yang_file, 'r') as f:
                yang_file_str = f.read()
            return self.ctx.parse_module_str(yang_file_str)
        except Exception as e:
            self.sysLog(msg="Failed to load yang module file: " + yang_file, debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)

    """
    load_schema_module_list(): load all Yang model files in the list
    input:    yang_files - a list of Yang model file full path
    returns:  Exception if error
    """
    def _load_schema_module_list(self, yang_files):
        for file in yang_files:
             try:
                 self._load_schema_module(file)
             except Exception as e:
                 self.fail(e)

    """
    load_schema_modules(): load all Yang model files in the directory
    input:    yang_dir - the directory of the yang model files to be loaded
    returns:  Exception if error
    """
    def _load_schema_modules(self, yang_dir):
        py = glob(yang_dir+"/*.yang")
        for file in py:
            try:
                self._load_schema_module(file)
            except Exception as e:
                self.fail(e)

    """
    load_schema_modules_ctx(): load all Yang model files in the directory to context: ctx
    input:    yang_dir,  context
    returns:  Exception if error, returrns context object if no error
    """
    def _load_schema_modules_ctx(self, yang_dir=None):
        if not yang_dir:
            yang_dir = self.yang_dir

        ctx = ly.Context(yang_dir)

        py = glob(yang_dir+"/*.yang")
        for file in py:
            try:
                with open(file, 'r') as f:
                    yang_str = f.read()
                ctx.parse_module_str(yang_str)
            except Exception as e:
                self.sysLog(msg="Failed to parse yang module file: " + file, debug=syslog.LOG_ERR, doPrint=True)
                self.fail(e)

        return ctx

    """
    load_data_file(): load a Yang data json file
    input:    data_file - the full path of the yang json data file to be loaded
    returns:  Exception if error
    """
    def _load_data_file(self, data_file, fmt="json"):
        try:
            with open(data_file, 'r') as f:
                data_node = self.ctx.parse_data_file(f, fmt)
        except Exception as e:
            self.sysLog(msg="Failed to load data file: " + str(data_file), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            self.root = data_node

    """
    get module name from xpath
    input:    path
    returns:  module name
    """
    def _get_module_name(self, schema_xpath):
        module_name = schema_xpath.split(':')[0].strip('/')
        return module_name

    """
    get_module(): get module object from Yang module name
    input:   yang module name
    returns: Schema_Node object
    """
    def _get_module(self, module_name):
        mod = self.ctx.get_module(module_name)
        return mod
    
    """
    print_data_mem():  print the data tree
    input:  option:  "JSON" or "XML"
    """
    def _print_data_mem(self, option):
        if (option == "XML"):
            mem = self.root.print_mem(fmt="json")
        else:
            mem = self.root.print_mem(fmt="xml")

        return mem

    """
    get_module_tree(): get yang module tree in JSON or XMAL format
    input:   module name
    returns: JSON or XML format of the input yang module schema tree
    """
    def _get_module_tree(self, module_name, format):
        result = None

        try:
            module = self.ctx.get_module(str(module_name))
        except Exception as e:
            self.sysLog(msg="Cound not get module: " + str(module_name), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            if (module is not None):
                if (format == "XML"):
                    #libyang bug with format
                    result = module.print_mem(fmt="yin")
                else:
                    result = module.print_mem(fmt="yang")

        return result
    
    """
    validate_data(): validate data tree
    input:
           node:   root of the data tree
           ctx:    context
    returns:  Exception if failed
    """
    def _validate_data(self, node=None, ctx=None):
        if not node:
            node = self.root

        if not ctx:
            ctx = self.ctx

        try:
            node.validate()
        except Exception as e:
            self.fail(e)

    """
    validate_data_tree(): validate the data tree. (Public)
    returns: Exception if failed
    """
    def validate_data_tree(self):
        try:
            self._validate_data(self.root, self.ctx)
        except Exception as e:
            self.sysLog(msg="Failed to validate data tree\n{", debug=syslog.LOG_ERR, doPrint=True)
            raise e

    """
    find_parent_data_node():  find the parent node object
    input:    data_xpath - xpath of the data node
    returns:  parent node
    """
    def _find_parent_data_node(self, data_xpath):
        if (self.root is None):
            self.sysLog(msg="data not loaded", debug=syslog.LOG_ERR, doPrint=True)
            return None
        try:
            data_node = self._find_data_node(data_xpath)
        except Exception as e:
            self.sysLog(msg="Failed to find data node from xpath: " + str(data_xpath), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            if data_node is not None:
                return data_node.parent()

        return None
    
    """
    get_parent_data_xpath():  find the parent data node's xpath
    input:    data_xpath - xpathof the data node
    returns:  - xpath of parent data node
              - Exception if error
    """
    def _get_parent_data_xpath(self, data_xpath):
        path=""
        try:
            data_node = self._find_parent_data_node(data_xpath)
        except Exception as e:
            self.sysLog(msg="Failed to find parent node from xpath: " + str(data_xpath), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            if data_node is not None:
                path = data_node.path()
        return path

    """
    new_data_node(): create a new data node in the data tree
    input:
           xpath: xpath of the new node
           value: value of the new node
    returns:  new Data_Node object if success,  Exception if falied
    """
    def _new_data_node(self, xpath, value):
        val = str(value)
        try:
            data_node = self.root.new_path(self.ctx, xpath, val, 0, 0)
        except Exception as e:
            self.sysLog(msg="Failed to add data node for path: " + str(xpath), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            return data_node
        
    """
    new_data_node(): create a new data node in the data tree
    input:
           xpath: xpath of the new node
           value: value of the new node
    returns:  new Data_Node object if success,  Exception if falied
    """
    def _new_data_node(self, xpath, value):
        val = str(value)
        try:
            data_node = self.root.new_path(xpath, val, 0, 0)
        except Exception as e:
            self.sysLog(msg="Failed to add data node for path: " + str(xpath), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            return data_node

    """
    find_data_node():  find the data node from xpath
    input:    data_xpath: xpath of the data node
    returns   - Data_Node object if found
              - None if not exist
              - Exception if there is error
    """
    def _find_data_node(self, data_xpath):
        try:
            set = self.root.find_path(data_xpath)
        except Exception as e:
            self.sysLog(msg="Failed to find data node from xpath: " + str(data_xpath), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)
        else:
            if set is not None:
                # print(set.value())
                return set
            return None
        
    """
    merge_data(): merge a data file to the existing data tree
    input:    yang model directory and full path of the data json file to be merged
    returns:  Exception if failed
    """
    def _merge_data(self, data_file):
        try:
           #source data node
            with open(data_file, 'r') as f:
                source_node = self.ctx.parse_data_file(f, fmt="json")

            #merge
            self.root.merge(source_node, 0)
        except Exception as e:
            self.fail(e)

    """
    add_node(): add a node to Yang schema or data tree
    input:    xpath and value of the node to be added
    returns:  Exception if failed
    """
    def _add_data_node(self, data_xpath, value):
        try:
            self._new_data_node(data_xpath, value)
            #check if the node added to the data tree
            self._find_data_node(data_xpath)
        except Exception as e:
            self.sysLog(msg="add_node(): Failed to add data node for xpath: " + str(data_xpath), debug=syslog.LOG_ERR, doPrint=True)
            self.fail(e)


