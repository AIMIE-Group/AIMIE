from base_interpreter import BaseInterpreter
import os
import pandas as pd
from log import Log
import sys
from util import load_keyword

logger = Log()
aimie_dir = '../AIMIE_Backup'
end_keywords = load_keyword('source_end')

def java_repos():
    aimie_lang = pd.read_csv("./doc/aimie_language.csv")
    java_aimie = aimie_lang[aimie_lang['language']=='java']['full_name'].tolist()
    return java_aimie

def get_java_file(full_name):
    java_files = []
    for root, dirs, files in os.walk(f"{aimie_dir}/{full_name}"):
        for file in files:
            if file.endswith('.java'):
                java_files.append(os.path.join(root, file))
    return java_files

class JAVA_Interpreter(BaseInterpreter):
    def __init__(self, java_file):
        self.read_file(java_file)
        self.set_language('java')
        self.tree = self.parser.parse(self.source_byte)
        self.string_dict = dict()
        self.upload_urls = set()
        self.if_value = dict()
    
    def process_string_only(self, string_node):
        string_value = self.get_node_byte(string_node)
        return string_value[1:-1]
    
    def process_binary_expression(self, parent_node):
        first_child = parent_node.children[0]
        op = parent_node.children[1]
        second_child = parent_node.children[2]
        print('binary')
        if op.type == '+':
            values = []
            for child in [first_child, second_child]:
                if child.type == 'identifier':
                    identifier = self.get_node_byte(child)
                    print("identifier:", identifier)
                    values.append(self.get_string_value(identifier))
                elif child.type == 'string_literal':
                    string_value = self.process_string_only(child)
                    values.append(string_value)
                elif child.type == 'binary_expression':
                    values.append(self.process_binary_expression(child))
                elif child.type == 'call_expression' and self.get_node_byte(child).startswith('$'):
                    value_list = self.process_call_value(child)
                    values.append(value_list)
                else:
                    logger.warning(f"other type in binary_expression: {child.type}")
                    return ""
            
            print(values)
            if type(values[0]) == list and type(values[1]) == list:
                return [i+j for i in values[0] for j in values[1]]
            elif type(values[0]) == list:
                return [i+values[1] for i in values[0]]
            elif type(values[1]) == list:
                return [values[0]+i for i in values[1]]
            else:
                return ''.join(values)

    def process_variable_declarator(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[2]
        print(f"variable_declarator type: {first_child.type} <- {second_child.type}")

        if first_child.type == 'identifier':
            identifier = self.get_node_byte(first_child)
            print("identifier:", identifier)
        else:
            logger.warning(f"other type in variable_declarator: {first_child.type}")
            return

        if second_child.type == 'string_literal':
            string_value = self.process_string_only(second_child)
        elif second_child.type == 'binary_expression':
            string_value = self.process_binary_expression(second_child)
        else:
            logger.warning(f"other type in variable_declarator: {second_child.type}")
            return
        self.string_dict[identifier] = string_value
        if self.check_url(string_value+'#'+identifier):
            logger.info(f"operation: {identifier} = {string_value}")
    
    def process_creation_call(self, parent_node):
        first_child = parent_node.children[1]
        second_child = parent_node.children[2]

        if first_child.type == 'type_identifier':
            identifier = self.get_node_byte(first_child)
        
        if second_child.type == 'argument_list':
            if second_child.child_count == 0:
                return
            arguments = second_child.children[1:-1:2]
            for argument in arguments:
                if argument.type == 'string_literal':
                    string_value = self.process_string_only(argument)
                    if self.check_url(string_value+'#'+identifier):
                        logger.info(f"call: {identifier}({string_value})")

    def process_string(self, cursor):
        if cursor.node.type == 'string_literal':
            string_node = cursor.node
            string_value = self.process_string_only(string_node)
            print(f"find string: {string_value} in {self.filename}: {string_node.start_point}, {string_node.end_point}")
            
            if any(string_value.endswith(x) for x in end_keywords):
                return
            
            while cursor.goto_parent():
                if cursor.node.type == 'variable_declarator':
                    self.process_variable_declarator(cursor.node)
                    return
                elif cursor.node.type == 'return_statement':
                    print(string_value)
                    if self.check_url(string_value):
                        logger.info(f"return string: {string_value}")
                    return
                elif cursor.node.type == 'binary_expression':
                    continue
                elif cursor.node.type == 'argument_list':
                    continue
                elif cursor.node.type == 'object_creation_expression':
                    self.process_creation_call(cursor.node)
                    return
                else:
                    logger.warning(f"other type in string_op: {cursor.node.type}")
                    break
    
    def get_method(self, cursor):
        first_child = cursor.node.children[2]
        second_child = cursor.node.children[3]

        values = []
        if first_child.type == 'identifier':
            identifier = self.get_node_byte(first_child)
            values.append(identifier)
        if second_child.type == 'formal_parameters':
            parameters = second_child.children[1:-1:2]
            for parameter in parameters:
                if parameter.type == 'formal_parameter':
                    identifier = self.get_node_byte(parameter.children[1])
                    values.append(identifier)
        self.method = '#'.join(values)
    
    def dfs_walk(self, cursor):
        if not cursor:
            return
        if cursor.node.type == 'method_declaration':
            self.get_method(cursor)
        if cursor.node.type == 'string_literal':
            self.process_string(cursor)
            return
        if cursor.goto_first_child():
            self.dfs_walk(cursor)
            while cursor.goto_next_sibling():
                self.dfs_walk(cursor)
            cursor.goto_parent()

if __name__ == "__main__":
    tmp_file = open('java_tree.tmp','w')

    if len(sys.argv) > 1:
        test_files = sys.argv[1:]
        for test_file in test_files:
            java_parser = JAVA_Interpreter(test_file)
            java_parser.print_tree(tmp_file)
            java_parser.start_walk()
            print(test_file,java_parser.get_upload_urls())
    else:
        res_file = open('java_res.txt','w')
        repos = java_repos()
        for repo in repos:
            files = get_java_file(repo)
            if len(files) == 0:
                res_file.write(f"{repo} no java file")
                continue
            upload_urls = set()
            for file in files:
                try:
                    java_parser = JAVA_Interpreter(file)
                    java_parser.print_tree(tmp_file)
                    java_parser.start_walk()
                    upload_urls |= java_parser.get_upload_urls()
                except Exception as e:
                    logger.error(f"error in {file}: {e}")

            print(repo,upload_urls)

        res_file.close()

    tmp_file.close()