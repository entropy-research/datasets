import json
import libcst as cst
from libcst import FunctionDef, ClassDef, Module, parse_module, Call, Comment
from typing import Dict, Union
import pprint

"""
    CST Parse:
    1. Each node should be a "Callable" (class, function, method etc)
    2. The model will use language modeling to track dependencies across functions
    3. Each node has a purpose
    4. Each node is given a salt to be put into a hashtable 

    Given the callable subnodes + the target callable,
        should be able to identify nodes where they are present in the local file.

    This must then generate a call tree for each function containing code for each subnode.
    Calls should map to callables.
    This code should then be converted to AST. 
    Then walk the ast to identify references from hashtable.
    If there is a name match in the hash table -> insert <call>, if none do nothing.
    Reformat calls to be <call>call</call>

    Requirements for the parser:
    1. must yield raw code
    2. must yield a function call tree with code on a function by function basis
    3. must generate the 
"""


class CodeExtractorVisitor(cst.CSTTransformer):
    def __init__(self, module):
        self.code_elements = {"__data__": {"name": "root"}, "__children__": []}
        self.ancestor_stack = []
        self.callSet = {}
        self.nodeSet = {}
        self.module = module

    def get_call_set(self):
        return self.callDict

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        treeNode = {}

        func_name = node.name.value

        params = [param.name.value for param in node.params.params]
        func_body = self.module.code_for_node(node)

        treeNode["__data__"] = {"name": func_name, "params": params, "body": func_body, "type": "func"}
        treeNode["__children__"] = []

        if len(self.ancestor_stack) == 0:
            self.code_elements["__children__"].append(treeNode)
        else:
            self.ancestor_stack[-1]["__children__"].append(treeNode)

        self.ancestor_stack.append(treeNode)

        self.callSet[func_name] = 0
        self.nodeSet[func_name] = treeNode["__data__"]
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> None:
        # if original_node != updated_node:
        #     self.ancestor_stack[-1]["__data__"]["body"] = self.module.code_for_node(updated_node.body).strip()
        self.ancestor_stack.pop()
        return updated_node

    def visit_Lambda(self, node: cst.Lambda) -> bool:
        treeNode = {}

        params = [param.name.value for param in node.params.params]
        func_body = self.module.code_for_node(node)

        treeNode["__data__"] = {"params": params, "body": func_body, "type": "lambda"}
        treeNode["__children__"] = []

        if len(self.ancestor_stack) == 0:
            self.code_elements["__children__"].append(treeNode)
        else:
            self.ancestor_stack[-1]["__children__"].append(treeNode)

        self.ancestor_stack.append(treeNode)
        return True

    def leave_Lambda(self, original_node: cst.Lambda, updated_node: cst.Lambda) -> None:
        self.ancestor_stack.pop()
        return updated_node


class CallSetVisitor(cst.CSTTransformer):

    def __init__(self, module, call_set, nodes):
        self.call_set = call_set
        self.module = module
        self.current = []
        self.callTree = {}
        self.nodes = nodes

    def _add_count(self, funcName, callName):
        if funcName not in self.callTree:
            self.callTree[funcName] = {}

        if callName not in self.callTree:
            self.callTree[callName] = {}

        if callName not in self.callTree[funcName]:
            self.callTree[funcName][callName] = 0

        self.callTree[funcName][callName] += 1
        self.call_set[callName] += 1

    def visit_FunctionDef(self, node: "FunctionDef"):
        name = node.name.value
        self.current.append(name)
        return True

    def leave_FunctionDef(self, oldnode, node):
        name = self.current.pop()
        self.nodes[name]["emb_repr"] = self.module.code_for_node(node)
        return node

    # def visit_ClassDef(self, node: "FunctionDef"):
    #     self.current.append(node.name.value)
    #
    #     return True
    #
    # def leave_ClassDef(self, oldnode, node):
    #     name = self.current.pop()
    #     return node
    def visit_Call(self, node):
        call = self.module.code_for_node(node).strip().split("(")[0].split(".")[-1]

        #To run on all calls, remove call_set requirement
        if call in self.call_set:
            if len(self.current) > 0:
                self._add_count(self.current[-1], call)

        return True

    def leave_Call(self, oldnode, updated):
        call = self.module.code_for_node(updated)
        callname = call.strip().split("(")[0].split(".")[-1]

        # To run on all calls, remove call_set requirement
        if callname in self.call_set:
            updated = Comment(value=('#<call>' + call.replace("\n", "") + '</call>'))

        return updated

def extract_code_elements(code: str) -> Dict[
    str, Union[cst.BaseCompoundStatement, Dict[str, cst.BaseCompoundStatement]]]:

    module = cst.parse_module(code)

    codeExtractor = CodeExtractorVisitor(module)
    callset = CallSetVisitor(module, codeExtractor.callSet, codeExtractor.nodeSet)
    module.visit(codeExtractor)
    module.visit(callset)

    return codeExtractor.code_elements, callset.callTree, codeExtractor.nodeSet, codeExtractor.callSet

def stringify_code_elements(
        code_elements: Dict[str, Union[cst.BaseCompoundStatement, Dict[str, cst.BaseCompoundStatement]]],
        module: Module) -> Dict[str, Union[str, Dict[str, str]]]:
    result = {}
    return result


def parse_code(code):

    code_elements, callTree, nodes, callSet = extract_code_elements(code)
    return {"code": code_elements, "call_tree": callTree, "node_set": nodes, "call_set":callSet}


def main():
    code = """
                def func1(a, b):

                    def nested_func1(b, c):
                        return c

                    return a + b

                def func2(x, y):
                    return x * y

                class MyClass:
                    def method1(self, p):
                        return p * 2
            """
    code = open("cst_parser.py", "rb").read()
    extract_code_elements(code)
    # dict = {"code": code_elements, "call_set": str(callSet)}
    # pprint.pprint(dict)

    # with open("./test.json", "w+") as f:
    #     json.dump(dict, f)


if __name__ == "__main__":
    main()
