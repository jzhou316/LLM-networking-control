import libyang
from libyang.context import Context
from libyang.schema import SNode, Module
from tree_structures import Node, Tree


class YangChunker:
    def __init__(self, yang_dir: str="tests/libyang-python-tests/sample-yang-models"):
        self.ctx = Context(yang_dir)

    def extract_node_text(self, node: SNode) -> str:
        result = dict()
        # All nodes have a name, description, and schema path
        result["name"] = node.name()
        if node.description():
            result["description"] = node.description()
        if node.schema_path():
            result["schema_path"] = node.schema_path()
        # Fields that depend on the node type
        if node.nodetype() == SNode.CONTAINER:
            result["type"] = "container"
        elif node.nodetype() == SNode.LEAF:
            result["type"] = "leaf"
            if node.units():
                result["units"] = node.units()
            if node.default():
                result["default"] = node.default()
            result["is_key"] = node.is_key()
        elif node.nodetype() == SNode.LEAFLIST:
            result["type"] = "leaf-list"
            if node.units():
                result["units"] = node.units()
            if node.defaults() and len(list(node.defaults())) > 0:
                result["defaults"] = [default for default in node.defaults()]
            result["ordered"] = node.ordered()
            if node.min_elements():
                result["min_elements"] = node.min_elements()
            if node.max_elements():
                result["max_elements"] = node.max_elements()
        return str(result)


    def chunk_yang_module(self, module: str) -> list:
        chunks = []
        module = self.ctx.load_module(module)
        tree_root = Node("", 0, set(), None)

        def extract_chunks(ptr: Node, node: SNode):
            ptr.text = self.extract_node_text(node)
            # if len(current_chunk) + len(node_text) > chunk_size:
            #     chunks.append("".join(current_chunk))
            # current_chunk.clear()
            # current_chunk.append(node_text)

            if node.nodetype() == SNode.LEAF or node.nodetype() == SNode.LEAFLIST:
                return

            for child in node.children():
                child_node = Node("", len(chunks), set(), None)
                ptr.children.append(len(chunks))
                extract_chunks(child)
        
        tree_ptr = tree_root
        for node in module:
            extract_chunks(tree_ptr, node)
        
        return chunks

def main():
    yc = YangChunker()
    chunks = yc.chunk_yang_module("sonic-acl")
    print(chunks)
    print(len(chunks))

if __name__ == "__main__":
    main()




"""
chunks = []

def print_tree(node, indent=0):
    # print("  " * indent + str(node.name()))
    # print("  " * indent + str(node.description()))
    # print("  " * indent + str(node.nodetype()))
    if node.nodetype() == SNode.CONTAINER:
        container_dict = dict()
        container_dict["type"] = "container"
        container_dict["name"] = node.name()
        if node.description():
            container_dict["description"] = node.description()
        if node.presence():
            container_dict["presence"] = node.presence()
        container_dict["schema_path"] = node.schema_path()
        container_dict["mandatory"] = node.mandatory()
        chunks.append(container_dict)
    elif node.nodetype() == SNode.LEAF:
        leaf_dict = dict()
        leaf_dict["type"] = "leaf"
        leaf_dict["name"] = node.name()
        if node.description():
            leaf_dict["description"] = node.description()
        if node.units():
            leaf_dict["units"] = node.units()
        if node.default():
            leaf_dict["default"] = node.default()
        leaf_dict["is_key"] = node.is_key()
        leaf_dict["schema_path"] = node.schema_path()
        leaf_dict["mandatory"] = node.mandatory()
        leaf_dict["config_set"] = node.config_set()
        chunks.append(leaf_dict)
    elif node.nodetype() == SNode.LEAFLIST:
        leaf_list_dict = dict()
        leaf_list_dict["type"] = "leaf-list"
        leaf_list_dict["name"] = node.name()
        if node.description():
            leaf_list_dict["description"] = node.description()
        if node.units():
            leaf_list_dict["units"] = node.units()
        if node.defaults():
            leaf_list_dict["defaults"] = node.defaults()
        leaf_list_dict["ordered"] = node.ordered()
        if node.min_elements():
            leaf_list_dict["min_elements"] = node.min_elements()
        if node.max_elements():
            leaf_list_dict["max_elements"] = node.max_elements()
            
        print("  " * indent + "Leaf-list: ")
        print("  " * indent + str(node.type()))
        if node.units():
            print("  " * indent + str(node.units()))
        if node.defaults():
            for default in node.defaults():
                print("  " * indent + str(default))
        print("  " * indent + str(node.ordered()))
        if node.min_elements():
            print("  " * indent + str(node.min_elements()))
        if node.max_elements():
            print("  " * indent + str(node.max_elements()))

    print("  " * indent + str(node.mandatory()))
    print("  " * indent + str(node.config_set()))
    print("  " * indent + str(node.schema_path()))
    for must in node.musts():
        print("MUST STATEMENT")
        print("  " * indent + str(must.condition()))
        if must.error_message():
            print("  " * indent + str(must.error_message()))
    if node.nodetype() == SNode.LEAF:
        return
    if node.nodetype() == SNode.LEAFLIST:
        return
    for child in node.children():
        print_tree(child, indent + 1)

def main():
    ctx = libyang.Context("tests/libyang-python-tests/sample-yang-models")
    module = ctx.load_module("sonic-acl")
    module_dict = dict()
    module_dict["type"] = "module"
    module_dict["name"] = module.name()
    module_dict["prefix"] = module.prefix()
    module_dict["description"] = module.description()
    chunks.append(module_dict)

    for revision in module.revisions():
        print(revision.date())
        print(revision.description())

    for imprt in module.imports():
        import_dict = dict()
        import_dict["type"] = "import"
        import_dict["name"] = imprt.name()
        import_dict["prefix"] = imprt.prefix()
        chunks.append(import_dict)
    
    for typedef in module.typedefs():
        typedef_dict = dict()
        typedef_dict["type"] = "typedef"
        typedef_dict["name"] = typedef.name()
        typedef_dict["description"] = typedef.description()
        typedef_dict["units"] = typedef.units()
    
    for child in module.children():
        print_tree(child)
    print(chunks)

if __name__ == "__main__":
    main()
"""