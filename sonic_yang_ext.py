from __future__ import print_function
import libyang as ly
import syslog
from json import dump, dumps, loads
from xmltodict import parse, unparse
from glob import glob
from collections import OrderedDict

Type_1_list_maps_model = [
    'DSCP_TO_TC_MAP_LIST',
    'DOT1P_TO_TC_MAP_LIST',
    'TC_TO_PRIORITY_GROUP_MAP_LIST',
    'TC_TO_QUEUE_MAP_LIST',
    'MAP_PFC_PRIORITY_TO_QUEUE_LIST',
    'PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_LIST',
    'DSCP_TO_FC_MAP_LIST',
    'EXP_TO_FC_MAP_LIST',
    'CABLE_LENGTH_LIST',
    'MPLS_TC_TO_TC_MAP_LIST'
]

# Workaround for those fields who is defined as leaf-list in YANG model but have string value in config DB.
# Dictinary structure key = (<table_name>, <field_name>), value = seperator
LEAF_LIST_WITH_STRING_VALUE_DICT = {
    ('MIRROR_SESSION', 'src_ip'): ',',
    ('NTP', 'src_intf'): ';',
    ('BGP_ALLOWED_PREFIXES', 'prefixes_v4'): ',',
    ('BGP_ALLOWED_PREFIXES', 'prefixes_v6'): ',',
    ('BUFFER_PORT_EGRESS_PROFILE_LIST', 'profile_list'): ',',
    ('BUFFER_PORT_INGRESS_PROFILE_LIST', 'profile_list'): ',',
    ('PORT', 'adv_speeds'): ',',
    ('PORT', 'adv_interface_types'): ',',
}

"""
This is the Exception thrown out of all public function of this class.
"""
class SonicYangException(Exception):
    pass

# class sonic_yang methods, use mixin to extend sonic_yang
class SonicYangExtMixin:

    """
    load all YANG models, create JSON of yang models. (Public function)
    """
    def loadYangModel(self):
        try:
            # get all files
            self.yangFiles = glob(self.yang_dir +"/*.yang")
            # load yang modules
            for file in self.yangFiles:
                m = self._load_schema_module(file)
                if m is not None:
                    self.sysLog(msg="module: {} is loaded successfully".format(m.name()))
                else:
                    raise(Exception("Could not load module {}".format(file)))

            # keep only modules name in self.yangFiles
            self.yangFiles = [f.split('/')[-1] for f in self.yangFiles]
            self.yangFiles = [f.split('.')[0] for f in self.yangFiles]
            self.sysLog(syslog.LOG_DEBUG,'Loaded below Yang Models')
            self.sysLog(syslog.LOG_DEBUG,str(self.yangFiles))

            # # load json for each yang model
            self._loadJsonYangModel()
            # # create a map from config DB table to yang container
            self._createDBTableToModuleMap()
        except Exception as e:
            self.sysLog(msg="Yang Models Load failed:{}".format(str(e)), \
                debug=syslog.LOG_ERR, doPrint=True)
            raise SonicYangException("Yang Models Load failed\n{}".format(str(e)))

        return True

    def get_simplified_schema(self, module, max_depth):
        def extract_hierarchy(data, current_depth=0):
            """
            Extract a hierarchical representation of the keys and their names from an OrderedDict,
            limited by a specified depth. Include a single ellipsis for content beyond the depth limit.
            """
            # Check if the current depth exceeds the maximum allowed depth
            if current_depth > max_depth:
                return "..."  # Use a single ellipsis to indicate more depth

            if not isinstance(data, (OrderedDict, dict, list)):
                return data  # Base case: directly return non-container data

            if isinstance(data, (OrderedDict, dict)):
                result = {}
                name = data.get('@name', None)
                if name:  # If this is a named entity, start building its representation.
                    result['name'] = name

                for key, value in data.items():
                    if key in ['@name', 'name']:  # Skip the name key to avoid repetition.
                        continue
                    if key not in ['module', 'container', 'list', 'leaf', 'leaf-list', 'typedef', 'grouping', 'type', 'choice', 'uses']:
                        continue  # Only process recognized YANG elements
                    
                    # Recursively process each item, incrementing depth for child elements
                    child = extract_hierarchy(value, current_depth + 1)
                    if isinstance(child, list) and len(child) > 1 and all(c == "..." for c in child):
                        # If the child is a list of ellipses, replace it with a single ellipsis
                        result[key] = ["..."]
                    else:
                        result[key] = child

            elif isinstance(data, list):
                # Process list items only up to the depth limit, then insert a single ellipsis
                processed_items = [extract_hierarchy(item, current_depth + 1) for item in data]
                if all(item == "..." for item in processed_items):
                    return ["..."]  # Replace multiple ellipses with a single entry
                return processed_items

            return result
        
        xml_dict = parse(self._get_module_tree(module.name(), "XML"))
        return extract_hierarchy(data=xml_dict, current_depth=0)


    """
    load JSON schema format from yang models
    """
    def _loadJsonYangModel(self):

        try:
            for f in self.yangFiles:
                m = self.ctx.get_module(f)
                if m is not None:
                    xml = m.print_mem(fmt="yin")
                    self.yJson.append(parse(xml))
                    self.sysLog(msg="Parsed Json for {}".format(m.name()))
        except Exception as e:
            self.sysLog(msg="JSON schema Load failed:{}".format(str(e)), \
                debug=syslog.LOG_ERR, doPrint=True)
            raise e

        return
    
    def _preProcessYangGrouping(self, moduleName, module):
        '''
            PreProcess Grouping Section of YANG models, and store it in
            self.preProcessedYang['grouping'] as
            {'<moduleName>':
                {'<groupingName>':
                    [<List of Leafs>]
                }
            }

            Parameters:
                moduleName (str): name of yang module.
                module (dict): json format of yang module.

            Returns:
                void
        '''
        try:
            # create grouping dict
            if self.preProcessedYang.get('grouping') is None:
                self.preProcessedYang['grouping'] = dict()
            self.preProcessedYang['grouping'][moduleName] = dict()

            # get groupings from yang module
            groupings = module['grouping']

            # if grouping is a dict, make it a list for common processing
            if isinstance(groupings, dict):
                groupings = [groupings]

            for grouping in groupings:
                gName = grouping["@name"]
                gLeaf = grouping["leaf"]
                self.preProcessedYang['grouping'][moduleName][gName] = gLeaf

        except Exception as e:
            self.sysLog(msg="_preProcessYangGrouping failed:{}".format(str(e)), \
                debug=syslog.LOG_ERR, doPrint=True)
            raise e
        return
    
    # preProcesss Generic Yang Objects
    def _preProcessYang(self, moduleName, module):
        '''
            PreProcess Generic Section of YANG models by calling
            _preProcessYang<SectionName> methods.

            Parameters:
                moduleName (str): name of yang module.
                module (dict): json format of yang module.

            Returns:
                void
        '''
        try:
            # preProcesss Grouping
            if module.get('grouping') is not None:
                self._preProcessYangGrouping(moduleName, module)
        except Exception as e:
            self.sysLog(msg="_preProcessYang failed:{}".format(str(e)), \
                debug=syslog.LOG_ERR, doPrint=True)
            raise e
        return
    
    """
    Create a map from config DB tables to container in yang model
    This module name and topLevelContainer are fetched considering YANG models are
    written using below Guidelines:
    https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md.
    """
    def _createDBTableToModuleMap(self):

        for j in self.yJson:
            # get module name
            moduleName = j['module']['@name']
            # preProcesss Generic Yang Objects
            self._preProcessYang(moduleName, j['module'])
            # get top level container
            topLevelContainer = j['module'].get('container')
            # if top level container is none, this is common yang files, which may
            # have definitions. Store module.
            if topLevelContainer is None:
                self.confDbYangMap[moduleName] = j['module']
                continue

            # top level container must exist for rest of the yang files and it should
            # have same name as module name.
            if topLevelContainer['@name'] != moduleName:
                raise(SonicYangException("topLevelContainer mismatch {}:{}".\
                    format(topLevelContainer['@name'], moduleName)))

            # Each container inside topLevelContainer maps to a sonic config table.
            container = topLevelContainer['container']
            # container is a list
            if isinstance(container, list):
                for c in container:
                    self.confDbYangMap[c['@name']] = {
                        "module" : moduleName,
                        "topLevelContainer": topLevelContainer['@name'],
                        "container": c,
                        "yangModule": j['module']
                        }
            # container is a dict
            else:
                self.confDbYangMap[container['@name']] = {
                    "module" : moduleName,
                    "topLevelContainer": topLevelContainer['@name'],
                    "container": container,
                    "yangModule": j['module']
                    }
        return
    
    """
    Get module, topLevelContainer(TLC) and json container for a config DB table
    """
    def _getModuleTLCcontainer(self, table):
        cmap = self.confDbYangMap
        m = cmap[table]['module']
        t = cmap[table]['topLevelContainer']
        c = cmap[table]['container']
        return m, t, c
    
    """
    Crop config as per yang models,
    This Function crops from config only those TABLEs, for which yang models is
    provided. The Tables without YANG models are stored in
    self.tablesWithOutYangModels.
    """
    def _cropConfigDB(self, croppedFile=None):

        tables = list(self.jIn.keys())
        for table in tables:
            if table not in self.confDbYangMap:
                # store in tablesWithOutYang
                self.tablesWithOutYang[table] = self.jIn[table]
                del self.jIn[table]

        if len(self.tablesWithOutYang):
            self.sysLog(msg=f"Note: Below table(s) have no YANG models: {', '.join(self.tablesWithOutYang)}", doPrint=True)

        if croppedFile:
            with open(croppedFile, 'w') as f:
                dump(self.jIn, f, indent=4)

        return
    
    """
    Extract keys from table entry in Config DB and return in a dict

    Input:
    tableKey: Config DB Primary Key, Example tableKey = "Vlan111|2a04:5555:45:6709::1/64"
    keys: key string from YANG list, i.e. 'vlan_name ip-prefix'.

    Return:
    KeyDict = {"vlan_name": "Vlan111", "ip-prefix": "2a04:5555:45:6709::1/64"}
    """
    def _extractKey(self, tableKey, keys):
        keyList = keys.split()
        # get the value groups
        value = tableKey.split("|")
        # match lens
        if len(keyList) != len(value):
            raise Exception("Value not found for {} in {}".format(keys, tableKey))
        # create the keyDict
        keyDict = dict()
        for i in range(len(keyList)):
            keyDict[keyList[i]] = value[i].strip()
            
        # I ADDED THIS TO CONVERT VLANID TO NUM
        if 'vlanid' in keyDict:
            keyDict['vlanid'] = int(keyDict['vlanid'])

        return keyDict

    """
    Fill the dict based on leaf as a list or dict @model yang model object
    """
    def _fillLeafDict(self, leafs, leafDict, isleafList=False):

        if leafs is None:
            return

        # fill default values
        def _fillSteps(leaf):
            leaf['__isleafList'] = isleafList
            leafDict[leaf['@name']] = leaf
            return

        if isinstance(leafs, list):
            for leaf in leafs:
                #print("{}:{}".format(leaf['@name'], leaf))
                _fillSteps(leaf)
        else:
            #print("{}:{}".format(leaf['@name'], leaf))
            _fillSteps(leafs)

        return

    def _createLeafDict(self, model, table):
        '''
            create a dict to map each key under primary key with a leaf in yang model.
            This is done to improve performance of mapping from values of TABLEs in
            config DB to leaf in YANG LIST.

            Parameters:
                module (dict): json format of yang module.
                table (str): config DB table, this table is being translated.

            Returns:
                 leafDict (dict): dict with leaf(s) information for List\Container
                    corresponding to config DB table.
        '''
        leafDict = dict()
        #Iterate over leaf, choices and leaf-list.
        self._fillLeafDict(model.get('leaf'), leafDict)

        #choices, this is tricky, since leafs are under cases in tree.
        choices = model.get('choice')
        if choices:
            for choice in choices:
                cases = choice['case']
                for case in cases:
                    self._fillLeafDict(case.get('leaf'), leafDict)

        # leaf-lists
        self._fillLeafDict(model.get('leaf-list'), leafDict, True)

        # uses should map to grouping,
        if model.get('uses') is not None:
            self._fillLeafDictUses(model.get('uses'), table, leafDict)

        return leafDict
    
    def _findYangTypedValue(self, key, value, leafDict):

        # convert config DB string to yang Type
        def _yangConvert(val):
            # Convert everything to string
            val = str(val)
            # find type of this key from yang leaf
            type = leafDict[key]['type']['@name']

            if 'uint' in type:
                vValue = int(val, 10)
            # TODO: find type of leafref from schema node
            elif 'leafref' in type:
                vValue = val
            #TODO: find type in sonic-head, as of now, all are enumeration
            elif 'stypes:' in type:
                vValue = val
            else:
                vValue = val
            return vValue

        # if it is a leaf-list do it for each element
        if leafDict[key]['__isleafList']:
            vValue = list()
            if isinstance(value, str) and (self.elementPath[0], self.elementPath[-1]) in LEAF_LIST_WITH_STRING_VALUE_DICT:
                # For field defined as leaf-list but has string value in CONFIG DB, need do special handling here. For exampe:
                # port.adv_speeds in CONFIG DB has value "100,1000,10000", it shall be transferred to [100,1000,10000] as YANG value here to
                # make it align with its YANG definition.
                value = (x.strip() for x in value.split(LEAF_LIST_WITH_STRING_VALUE_DICT[(self.elementPath[0], self.elementPath[-1])]))
            for v in value:
                vValue.append(_yangConvert(v))
        else:
            vValue = _yangConvert(value)

        return vValue

    """
    Xlate a Type 1 map list
    This function will xlate from a dict in config DB to a Yang JSON list
    using yang model. Output will be go in self.xlateJson

    Note: Exceptions from this function are collected in exceptionList and
    are displayed only when an entry is not xlated properly from ConfigDB
    to sonic_yang.json.

    Type 1 Lists have inner list, which is diffrent from config DB.
    Each field value in config db should be converted to inner list with
    key and value.
    Example:

    Config DB:
    "DSCP_TO_TC_MAP": {
       "Dscp_to_tc_map1": {
          "1": "1",
          "2": "2"
       }
    }

    YANG Model:
    module: sonic-dscp-tc-map
     +--rw sonic-dscp-tc-map
     +--rw DSCP_TO_TC_MAP
        +--rw DSCP_TO_TC_MAP_LIST* [name]
           +--rw name              string
           +--rw DSCP_TO_TC_MAP* [dscp]
              +--rw dscp    string
              +--rw tc?     string

    YANG JSON:
    "sonic-dscp-tc-map:sonic-dscp-tc-map": {
        "sonic-dscp-tc-map:DSCP_TO_TC_MAP": {
             "DSCP_TO_TC_MAP_LIST": [
                   {
                        "name": "map3",
                        "DSCP_TO_TC_MAP": [
                            {
                                "dscp": "64",
                                "tc": "1"
                            },
                            {
                                "dscp":"2",
                                "tc":"2"
                            }
                        ]
                    }
                ]
            }
    }
    """
    def _xlateType1MapList(self, model, yang, config, table, exceptionList):

        #create a dict to map each key under primary key with a dict yang model.
        #This is done to improve performance of mapping from values of TABLEs in
        #config DB to leaf in YANG LIST.
        inner_clist = model.get('list')
        if inner_clist:
            inner_listKey = inner_clist['key']['@value']
            inner_leafDict = self._createLeafDict(inner_clist, table)
            for lkey in inner_leafDict:
                if inner_listKey != lkey:
                    inner_listVal = lkey

        # get keys from YANG model list itself
        listKeys = model['key']['@value']
        self.sysLog(msg="xlateList keyList:{}".format(listKeys))
        primaryKeys = list(config.keys())
        for pkey in primaryKeys:
            try:
                vKey = None
                self.sysLog(syslog.LOG_DEBUG, "xlateList Extract pkey:{}".\
                    format(pkey))
                # Find and extracts key from each dict in config
                keyDict = self._extractKey(pkey, listKeys)

                if inner_clist:
                   inner_yang_list = list()
                   for vKey in config[pkey]:
                      inner_keyDict = dict()
                      self.sysLog(syslog.LOG_DEBUG, "xlateList Key {} vkey {} Val {} vval {}".\
                          format(inner_listKey, str(vKey), inner_listVal, str(config[pkey][vKey])))
                      inner_keyDict[inner_listKey] = str(vKey)
                      inner_keyDict[inner_listVal] = str(config[pkey][vKey])
                      inner_yang_list.append(inner_keyDict)

                keyDict[inner_clist['@name']] = inner_yang_list
                yang.append(keyDict)
                # delete pkey from config, done to match one key with one list
                del config[pkey]

            except Exception as e:
                # log debug, because this exception may occur with multilists
                self.sysLog(msg="xlateList Exception:{}".format(str(e)), \
                    debug=syslog.LOG_DEBUG, doPrint=True)
                exceptionList.append(str(e))
                # with multilist, we continue matching other keys.
                continue
        return

    """
    Xlate a list
    This function will xlate from a dict in config DB to a Yang JSON list
    using yang model. Output will be go in self.xlateJson

    Note: Exceptions from this function are collected in exceptionList and
    are displayed only when an entry is not xlated properly from ConfigDB
    to sonic_yang.json.
    """
    def _xlateList(self, model, yang, config, table, exceptionList):
        # Type 1 lists need special handling because of inner yang list and
        # config db format.
        if model['@name'] in Type_1_list_maps_model:
            self.sysLog(msg="_xlateType1MapList: {}".format(model['@name']))
            self._xlateType1MapList(model, yang, config, table, exceptionList)
            return

        #create a dict to map each key under primary key with a dict yang model.
        #This is done to improve performance of mapping from values of TABLEs in
        #config DB to leaf in YANG LIST.

        leafDict = self._createLeafDict(model, table)
        # get keys from YANG model list itself
        listKeys = model['key']['@value']
        self.sysLog(msg="xlateList keyList:{}".format(listKeys))
        primaryKeys = list(config.keys())
        for pkey in primaryKeys:
            try:
                self.elementPath.append(pkey)
                vKey = None
                self.sysLog(syslog.LOG_DEBUG, "xlateList Extract pkey:{}".\
                    format(pkey))
                # Find and extracts key from each dict in config
                keyDict = self._extractKey(pkey, listKeys)
                # fill rest of the values in keyDict
                for vKey in config[pkey]:
                    self.elementPath.append(vKey)
                    self.sysLog(syslog.LOG_DEBUG, "xlateList vkey {}".format(vKey))
                    try:
                        keyDict[vKey] = self._findYangTypedValue(vKey, \
                                            config[pkey][vKey], leafDict)
                    finally:
                        self.elementPath.pop()
                yang.append(keyDict)
                # delete pkey from config, done to match one key with one list
                del config[pkey]

            except Exception as e:
                # log debug, because this exception may occur with multilists
                self.sysLog(msg="xlateList Exception:{}".format(str(e)), \
                    debug=syslog.LOG_DEBUG, doPrint=True)
                exceptionList.append(str(e))
                # with multilist, we continue matching other keys.
                continue
            finally:
                self.elementPath.pop()

        return

    """
    Process list inside a Container.
    This function will call xlateList based on list(s) present in Container.
    """
    def _xlateListInContainer(self, model, yang, configC, table, exceptionList):
        clist = model
        yang[clist['@name']] = list()
        self.sysLog(msg="xlateProcessListOfContainer: {}".format(clist['@name']))
        self._xlateList(clist, yang[clist['@name']], configC, table, exceptionList)
        # clean empty lists
        if len(yang[clist['@name']]) == 0:
            del yang[clist['@name']]

        return

    """
    Process container inside a Container.
    This function will call xlateContainer based on Container(s) present
    in outer Container.
    """
    def _xlateContainerInContainer(self, model, yang, configC, table):
        ccontainer = model
        ccName = ccontainer['@name']
        yang[ccName] = dict()
        if ccName not in configC:
            # Inner container doesn't exist in config
            return

        if len(configC[ccName]) == 0:
            # Empty container, clean config and return
            del configC[ccName]
            return
        self.sysLog(msg="xlateProcessListOfContainer: {}".format(ccName))
        self.elementPath.append(ccName)
        self._xlateContainer(ccontainer, yang[ccName], \
        configC[ccName], table)
        self.elementPath.pop()

        # clean empty container
        if len(yang[ccName]) == 0:
            del yang[ccName]
        # remove copy after processing
        del configC[ccName]

        return

    """
    Xlate a container
    This function will xlate from a dict in config DB to a Yang JSON container
    using yang model. Output will be stored in self.xlateJson
    """
    def _xlateContainer(self, model, yang, config, table):

        # To Handle multiple Lists, Make a copy of config, because we delete keys
        # from config after each match. This is done to match one pkey with one list.
        configC = config.copy()
        exceptionList = list()
        clist = model.get('list')
        # If single list exists in container,
        if clist and isinstance(clist, dict) and \
           clist['@name'] == model['@name']+"_LIST" and bool(configC):
                self._xlateListInContainer(clist, yang, configC, table, \
                    exceptionList)
        # If multi-list exists in container,
        elif clist and isinstance(clist, list) and bool(configC):
            for modelList in clist:
                self._xlateListInContainer(modelList, yang, configC, table, \
                    exceptionList)

        # Handle container(s) in container
        ccontainer = model.get('container')
        # If single list exists in container,
        if ccontainer and isinstance(ccontainer, dict) and bool(configC):
            self._xlateContainerInContainer(ccontainer, yang, configC, table)
        # If multi-list exists in container,
        elif ccontainer and isinstance(ccontainer, list) and bool(configC):
            for modelContainer in ccontainer:
                self._xlateContainerInContainer(modelContainer, yang, configC, table)

        ## Handle other leaves in container,
        leafDict = self._createLeafDict(model, table)
        vKeys = list(configC.keys())
        for vKey in vKeys:
            #vkey must be a leaf\leaf-list\choice in container
            if leafDict.get(vKey):
                self.elementPath.append(vKey)
                self.sysLog(syslog.LOG_DEBUG, "xlateContainer vkey {}".format(vKey))
                yang[vKey] = self._findYangTypedValue(vKey, configC[vKey], leafDict)
                self.elementPath.pop()
                # delete entry from copy of config
                del configC[vKey]

        # All entries in copy of config must have been parsed.
        if len(configC):
            self.sysLog(msg="All Keys are not parsed in {}\n{}".format(table, \
                configC.keys()), debug=syslog.LOG_ERR, doPrint=True)
            self.sysLog(msg="exceptionList:{}".format(exceptionList), \
                debug=syslog.LOG_ERR, doPrint=True)
            raise(Exception("All Keys are not parsed in {}\n{}\nexceptionList:{}".format(table, \
                configC.keys(), exceptionList)))

        return
    
    """
    xlate ConfigDB json to Yang json
    """
    def _xlateConfigDBtoYang(self, jIn, yangJ):

        # find top level container for each table, and run the xlate_container.
        for table in jIn.keys():
            cmap = self.confDbYangMap[table]
            # create top level containers
            key = cmap['module']+":"+cmap['topLevelContainer']
            subkey = cmap['topLevelContainer']+":"+cmap['container']['@name']
            # Add new top level container for first table in this container
            yangJ[key] = dict() if yangJ.get(key) is None else yangJ[key]
            yangJ[key][subkey] = dict()
            self.sysLog(msg="xlateConfigDBtoYang {}:{}".format(key, subkey))
            self.elementPath.append(table)
            self._xlateContainer(cmap['container'], yangJ[key][subkey], \
                                jIn[table], table)
            self.elementPath = []

        return
    
    """
    Read config file and crop it as per yang models
    """
    def _xlateConfigDB(self, xlateFile=None):

        jIn= self.jIn
        yangJ = self.xlateJson
        # xlation is written in self.xlateJson
        self._xlateConfigDBtoYang(jIn, yangJ)

        if xlateFile:
            with open(xlateFile, 'w') as f:
                dump(self.xlateJson, f, indent=4)

        return
    
    """
    create config DB table key from entry in yang JSON
    """
    def _createKey(self, entry, keys):

        keyDict = dict()
        keyList = keys.split()
        keyV = ""

        for key in keyList:
            val = entry.get(key)
            if val:
                #print("pair: {} {}".format(key, val))
                keyDict[key] = sval = str(val)
                keyV += sval + "|"
                #print("VAL: {} {}".format(regex, keyV))
            else:
                raise Exception("key {} not found in entry".format(key))
        #print("kDict {}".format(keyDict))
        keyV = keyV.rstrip("|")

        return keyV, keyDict
    
    """
    Convert a string from Config DB value to Yang Value based on type of the
    key in Yang model.
    @model : A List of Leafs in Yang model list
    """
    def _revFindYangTypedValue(self, key, value, leafDict):

        # convert yang Type to config DB string
        def _revYangConvert(val):
            # config DB has only strings, thank god for that :), wait not yet!!!
            return str(val)

        # if it is a leaf-list do it for each element
        if leafDict[key]['__isleafList']:
            if isinstance(value, list) and (self.elementPath[0], self.elementPath[-1]) in LEAF_LIST_WITH_STRING_VALUE_DICT:
                # For field defined as leaf-list but has string value in CONFIG DB, we need do special handling here:
                # e.g. port.adv_speeds is [10,100,1000] in YANG, need to convert it into a string for CONFIG DB: "10,100,1000"
                vValue = LEAF_LIST_WITH_STRING_VALUE_DICT[(self.elementPath[0], self.elementPath[-1])].join((_revYangConvert(x) for x in value))
            else:
                vValue = list()
                for v in value:
                    vValue.append(_revYangConvert(v))
        elif leafDict[key]['type']['@name'] == 'boolean':
            vValue = 'true' if value else 'false'
        else:
            vValue = _revYangConvert(value)

        return vValue
    
    """
    Rev xlate from <TABLE>_LIST to table in config DB
    Type 1 Lists have inner list, each inner list key:val should
    be mapped to field:value in Config DB.
    Example:

    YANG:
    module: sonic-dscp-tc-map
    +--rw sonic-dscp-tc-map
     +--rw DSCP_TO_TC_MAP
        +--rw DSCP_TO_TC_MAP_LIST* [name]
           +--rw name              string
           +--rw DSCP_TO_TC_MAP* [dscp]
              +--rw dscp    string
              +--rw tc?     string

    YANG JSON:
    "sonic-dscp-tc-map:sonic-dscp-tc-map": {
            "sonic-dscp-tc-map:DSCP_TO_TC_MAP": {
                "DSCP_TO_TC_MAP_LIST": [
                    {
                        "name": "map3",
                        "DSCP_TO_TC_MAP": [
                            {
                                "dscp": "64",
                                "tc": "1"
                            },
                            {
                                "dscp":"2",
                                "tc":"2"
                            }
                        ]
                    }
                ]
            }
        }

    Config DB:
    "DSCP_TO_TC_MAP": {
       "Dscp_to_tc_map1": {
          "1": "1",
          "2": "2"
       }
    }
    """

    def _revXlateType1MapList(self, model, yang, config, table):
        # get keys from YANG model list itself
        listKeys = model['key']['@value']
        # create a dict to map each key under primary key with a dict yang model.
        # This is done to improve performance of mapping from values of TABLEs in
        # config DB to leaf in YANG LIST.

        # Gather inner list key and value from model
        inner_clist = model.get('list')
        if inner_clist:
            inner_listKey = inner_clist['key']['@value']
            inner_leafDict = self._createLeafDict(inner_clist, table)
            for lkey in inner_leafDict:
                if inner_listKey != lkey:
                    inner_listVal = lkey

        # list with name <NAME>_LIST should be removed,
        if "_LIST" in model['@name']:
            for entry in yang:
                # create key of config DB table
                pkey, pkeydict = self._createKey(entry, listKeys)
                self.sysLog(syslog.LOG_DEBUG, "revXlateList pkey:{}".format(pkey))
                config[pkey]= dict()
                # fill rest of the entries
                inner_list = entry[inner_clist['@name']]
                for index in range(len(inner_list)):
                    self.sysLog(syslog.LOG_DEBUG, "revXlateList fkey:{} fval {}".\
                         format(str(inner_list[index][inner_listKey]),\
                             str(inner_list[index][inner_listVal])))
                    config[pkey][str(inner_list[index][inner_listKey])] = str(inner_list[index][inner_listVal])
        return

    """
    Rev xlate from <TABLE>_LIST to table in config DB
    """
    def _revXlateList(self, model, yang, config, table):

        # special processing for Type 1 Map tables.
        if model['@name'] in Type_1_list_maps_model:
           self._revXlateType1MapList(model, yang, config, table)
           return

        # get keys from YANG model list itself
        listKeys = model['key']['@value']
        # create a dict to map each key under primary key with a dict yang model.
        # This is done to improve performance of mapping from values of TABLEs in
        # config DB to leaf in YANG LIST.
        leafDict = self._createLeafDict(model, table)

        # list with name <NAME>_LIST should be removed,
        if "_LIST" in model['@name']:
            for entry in yang:
                # create key of config DB table
                pkey, pkeydict = self._createKey(entry, listKeys)
                self.sysLog(syslog.LOG_DEBUG, "revXlateList pkey:{}".format(pkey))
                self.elementPath.append(pkey)
                config[pkey]= dict()
                # fill rest of the entries
                for key in entry:
                    if key not in pkeydict:
                        self.elementPath.append(key)
                        config[pkey][key] = self._revFindYangTypedValue(key, \
                            entry[key], leafDict)
                        self.elementPath.pop()
                self.elementPath.pop()

        return
    
    """
    Rev xlate a list inside a yang container
    """
    def _revXlateListInContainer(self, model, yang, config, table):
        modelList = model
        # Pass matching list from Yang Json if exist
        if yang.get(modelList['@name']):
            self.sysLog(msg="revXlateListInContainer {}".format(modelList['@name']))
            self._revXlateList(modelList, yang[modelList['@name']], config, table)
        return

    """
    Rev xlate a container inside a yang container
    """
    def _revXlateContainerInContainer(self, model, yang, config, table):
        modelContainer = model
        # Pass matching list from Yang Json if exist
        if yang.get(modelContainer['@name']):
            config[modelContainer['@name']] = dict()
            self.sysLog(msg="revXlateContainerInContainer {}".format(modelContainer['@name']))
            self.elementPath.append(modelContainer['@name'])
            self._revXlateContainer(modelContainer, yang[modelContainer['@name']], \
                config[modelContainer['@name']], table)
            self.elementPath.pop()
        return

    """
    Rev xlate from yang container to table in config DB
    """
    def _revXlateContainer(self, model, yang, config, table):

        # IF container has only one list
        clist = model.get('list')
        if isinstance(clist, dict):
            self._revXlateListInContainer(clist, yang, config, table)
        # IF container has lists
        elif isinstance(clist, list):
            for modelList in clist:
                self._revXlateListInContainer(modelList, yang, config, table)

        ccontainer = model.get('container')
        # IF container has only one inner container
        if isinstance(ccontainer, dict):
            self._revXlateContainerInContainer(ccontainer, yang, config, table)
        # IF container has only many inner container
        elif isinstance(ccontainer, list):
            for modelContainer in ccontainer:
                self._revXlateContainerInContainer(modelContainer, yang, config, table)

        ## Handle other leaves in container,
        leafDict = self._createLeafDict(model, table)
        for vKey in yang:
            #vkey must be a leaf\leaf-list\choice in container
            if leafDict.get(vKey):
                self.sysLog(syslog.LOG_DEBUG, "revXlateContainer vkey {}".format(vKey))
                self.elementPath.append(vKey)
                config[vKey] = self._revFindYangTypedValue(vKey, yang[vKey], leafDict)
                self.elementPath.pop()

        return

    """
    rev xlate ConfigDB json to Yang json
    """
    def _revXlateYangtoConfigDB(self, yangJ, cDbJson):

        yangJ = self.xlateJson
        cDbJson = self.revXlateJson

        # find table in config DB, use name as a KEY
        for module_top in yangJ.keys():
            # module _top will be of from module:top
            for container in yangJ[module_top].keys():
                # the module_top can the format
                # moduleName:TableName or
                # TableName
                names = container.split(':')
                if len(names) > 2:
                    raise SonicYangException("Invalid Yang data file structure")
                table = names[0] if len(names) == 1 else names[1]
                #print("revXlate " + table)
                cmap = self.confDbYangMap[table]
                cDbJson[table] = dict()
                #print(key + "--" + subkey)
                self.sysLog(msg="revXlateYangtoConfigDB {}".format(table))
                self.elementPath.append(table)
                self._revXlateContainer(cmap['container'], yangJ[module_top][container], \
                    cDbJson[table], table)
                self.elementPath = []

        return

    """
    load_data: load Config DB, crop, xlate and create data tree from it. (Public)
    input:    data
              debug Flag
    returns:  True - success   False - failed
    """
    def loadData(self, configdbJson, debug=True, print=False):
        try:
            # write Translated config in file if debug enabled
            xlateFile = None
            if debug:
                xlateFile = "xlateConfig.json"
            self.jIn = configdbJson
            # reset xlate and tablesWithOutYang
            self.xlateJson = dict()
            self.tablesWithOutYang = dict()
            # self.jIn will be cropped
            self._cropConfigDB()
            # xlated result will be in self.xlateJson
            self._xlateConfigDB(xlateFile=xlateFile)
            # print(self.xlateJson)
            self.sysLog(msg="Try to load Data in the tree")
            if print:
                return self.xlateJson
            # self.root = self.ctx.parse_data_mem(dumps(self.xlateJson), fmt="json")

        except Exception as e:
            self.root = None
            self.sysLog(msg="Data Loading Failed:{}".format(str(e)), \
            debug=syslog.LOG_ERR, doPrint=True)
            raise SonicYangException("Data Loading Failed\n{}".format(str(e)))

        return True
    
    """
    Get data from Data tree, data tree will be assigned in self.xlateJson. (Public)
    """
    def getData(self, debug=False):

        try:
            # write reverse Translated config in file if debug enabled
            revXlateFile = None
            if debug:
                revXlateFile = "revXlateConfig.json"
            self.xlateJson = loads(self._print_data_mem('JSON'))
            # reset reverse xlate
            self.revXlateJson = dict()
            # result will be stored self.revXlateJson
            self._revXlateConfigDB(revXlateFile=revXlateFile)

        except Exception as e:
            self.sysLog(msg="Get Data Tree Failed:{}".format(str(e)), \
             debug=syslog.LOG_ERR, doPrint=True)
            raise SonicYangException("Get Data Tree Failed\n{}".format(str(e)))

        return self.revXlateJson
    
    def XlateYangToConfigDB(self, yang_data):
        config_db_json = dict()
        self.xlateJson = yang_data
        self.revXlateJson = config_db_json
        self._revXlateYangtoConfigDB(yang_data, config_db_json)
        return config_db_json