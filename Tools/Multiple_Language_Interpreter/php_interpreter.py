from base_interpreter import BaseInterpreter
import os
import pandas as pd
from log import Log
import sys
from util import load_keyword

logger = Log()
aimie_dir = '../AIMIE_Backup'
end_keywords = load_keyword('source_end')
string_type_names = ['string', 'encapsed_string']

def php_repos():
    aimie_lang = pd.read_csv("./doc/aimie_language.csv")
    php_aimie = aimie_lang[aimie_lang['language'] == 'php']['full_name'].tolist()
    return php_aimie


def get_php_file(full_name):
    php_files = []
    for root, dirs, files in os.walk(f"{aimie_dir}/{full_name}"):
        for file in files:
            if os.path.getsize(os.path.join(root, file)) > 50*1024:
                continue
            if file.endswith('.php'):
                php_files.append(os.path.join(root, file))
    return php_files


class PHP_Interpreter(BaseInterpreter):
    def __init__(self, php_file):
        self.read_file(php_file)
        self.set_language('php')
        self.tree = self.parser.parse(self.source_byte)
        self.string_dict = dict()
        self.upload_urls = set()

    def process_assignment(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[2]
        print(f"assignment type: {first_child.type} = {second_child.type}")

        if first_child.type == 'variable_name':
            identifier = self.get_node_byte(first_child)[1:]
            print(f"variable_name: {identifier}")
        elif first_child.type == 'subscript_expression':
            identifier = self.get_node_byte(first_child.children[0])[1:]
            print(f"subscript_expression: {identifier}")
        else:
            logger.warning(f"other type in assignment: {first_child.type}")
            return

        if second_child.type in string_type_names:
            string_value = self.process_string_only(second_child)
        elif second_child.type == 'binary_expression':
            string_value = self.process_binary_op(second_child)
        else:
            logger.warning(f"other type in assignment: {second_child.type}")
            return

        self.string_dict[identifier] = string_value
        if self.check_url(string_value+'#'+identifier):
            logger.info(f"assignment operation: {identifier} = {string_value}")

    def process_property_element(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[1]
        print(f"property_element type: {first_child.type} {second_child.type}")

        if first_child.type == 'variable_name':
            identifier = self.get_node_byte(first_child)[1:]
            print(f"variable_name: {identifier}")
        elif first_child.type == 'subscript_expression':
            identifier = self.get_node_byte(first_child.children[0])[1:]
            print(f"subscript_expression: {identifier}")
        else:
            logger.warning(f"other type in property_element: {first_child.type}")
            return

        if second_child.type == 'property_initializer' and len(second_child.children) == 2:
            op = self.get_node_byte(second_child.children[0])
            value_node = second_child.children[1]
            if value_node.type in string_type_names:
                string_value = self.process_string_only(value_node)
            elif value_node.type == 'binary_expression':
                string_value = self.process_binary_op(value_node)
            else:
                logger.warning(f"other type in property_element: {value_node.type}")
                return
    
        else:
            logger.warning(f"other type in property_element: {second_child.type}")
            return

        self.string_dict[identifier] = string_value
        if self.check_url(string_value+'#'+identifier):
            logger.info(f"property_element operation: {identifier} = {string_value}")    

    def process_binary_op(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[2]
        op = self.get_node_byte(parent_node.children[1])
        print(f"binary_expression type: {first_child.type} {op} {second_child.type}")
        
        if op == '.':
            values = []
            for child in [first_child, second_child]:
                if child.type == 'variable_name':
                    identifier = self.get_node_byte(child)[1:]
                    print(f"variable_name: {identifier}")
                    values.append(self.get_string_value(identifier))
                elif child.type in string_type_names:
                    values.append(self.process_string_only(child))
                elif child.type == 'binary_expression':
                    values.append(self.process_binary_op(child))
                elif child.type == 'function_call_expression':
                    values.append("")
                else:
                    logger.warning(f"other type in binary_expression: {child.type}")
                    return ""
            return ''.join(values)
        else:
            logger.warning(f"other op in binary_expression: {op}")
            return ""

    def process_return(self, parent_node):
        first_child = parent_node.children[1]
        print(f"return type: {first_child.type}")

        if first_child.type in string_type_names:
            string_value = self.process_string_only(first_child)
        elif first_child.type == 'binary_expression':
            string_value = self.process_binary_op(first_child)
        else:
            logger.warning(f"other type in return: {first_child.type}")
            return

        if self.check_url(string_value):
            logger.info(f"return string: {string_value}")    
    
    def process_call(self, parent_node):
        call_name = self.get_node_byte(parent_node.children[0])
        arguments = parent_node.children[1]
        print(f"call_name: {call_name}, arguments: {arguments.type}")

        for child in arguments.children[1:-1:2]:
            argument = child.children[0]
            if argument.type in string_type_names:
                string_value = self.process_string_only(argument)
            elif argument.type == 'binary_expression':
                string_value = self.process_binary_op(argument)
            elif argument.type == 'variable_name':
                identifier = self.get_node_byte(argument)[1:]
                print(f"variable_name: {identifier}")
                string_value = self.get_string_value(identifier)
            elif argument.type == 'name':
                print(f"argument name: {self.get_node_byte(argument)}")
            else:
                logger.warning(f"other type in argument: {argument.type}")
                return
            if self.check_url(string_value+'#'+call_name):
                logger.info(f"call function: {call_name}({string_value})")

    def process_member_call(self, parent_node):
        first_child = parent_node.children[0]
        op = self.get_node_byte(parent_node.children[1])
        second_child = parent_node.children[2]
        arguments = parent_node.children[3]
        print(f"member_call type: {first_child.type} {op} {second_child.type}")

        if first_child.type == 'variable_name' and second_child.type == 'name':
            identifier = self.get_node_byte(first_child)[1:]
            method = self.get_node_byte(second_child)
            call_name = f"{identifier}->{method}"
            print(f"member_call: {call_name}")
        else:
            logger.warning(f"other type in member_call: {first_child.type}")
            return
        
        for child in arguments.children[1:-1:2]:
            argument = child.children[0]
            if argument.type in string_type_names:
                string_value = self.process_string_only(argument)
            elif argument.type == 'binary_expression':
                string_value = self.process_binary_op(argument)
            elif argument.type == 'variable_name':
                identifier = self.get_node_byte(argument)[1:]
                print(f"variable_name: {identifier}")
                string_value = self.get_string_value(identifier)
            elif argument.type == 'name':
                print(f"argument name: {self.get_node_byte(argument)}")
            else:
                logger.warning(f"other type in argument: {argument.type}")
                return
            if self.check_url(string_value+'#'+call_name):
                logger.info(f"call function: {call_name}({string_value})")

    def process_array_element(self, parent_node):
        if len(parent_node.children) == 1:
            if parent_node.children[0].type in string_type_names:
                string_value = self.process_string_only(parent_node.children[0])
                if self.check_url(string_value):
                    logger.info(f"array_element: {string_value}")
            else:
                logger.warning(f"other type in array_element: {parent_node.children[0].type}")
            return
        
        elif len(parent_node.children) == 3:
            first_child = parent_node.children[0]
            second_child = parent_node.children[2]
            print(f"array_element type: {first_child.type} => {second_child.type}")

            if first_child.type in string_type_names:
                key = self.process_string_only(first_child)
            elif first_child.type == 'variable_name':
                identifier = self.get_node_byte(first_child)[1:]
                print(f"variable_name: {identifier}")
                key = self.get_string_value(identifier)
                if not key:
                    key = identifier
            else:
                logger.warning(f"other type in array_element: {first_child.type}")
                return

            if second_child.type in string_type_names:
                value = self.process_string_only(second_child)
                if self.check_url(value+'#'+key):
                    logger.info(f"array_element: {key} => {value}")
            elif second_child.type == 'array_creation_expression':
                self.process_array_creation(second_child)
                return
            else:
                logger.warning(f"other type in array_element: {second_child.type}")
                return

    def process_array_creation(self, parent_node):
        for child in parent_node.children[1:-1:2]:
            if child.type == 'array_element_initializer':
                self.process_array_element(child)

    def process_string_only(self, string_node):
        string_value = self.get_node_byte(string_node)
        return string_value[1:-1]

    def process_string(self, cursor):
        if cursor.node.type in string_type_names:
            string_node = cursor.node
            string_value = self.process_string_only(string_node)
            print(f"find string: {string_value} in {self.filename}: {string_node.start_point}, {string_node.end_point}")

            if any(string_value.endswith(x) for x in end_keywords):
                return
            
            while cursor.goto_parent():
                if cursor.node.type == 'assignment_expression':
                    self.process_assignment(cursor.node)
                    return
                elif cursor.node.type == 'return_statement':
                    self.process_return(cursor.node)
                    return
                elif cursor.node.type == 'binary_expression':
                    continue
                elif cursor.node.type == 'argument':
                    continue
                elif cursor.node.type == 'arguments':
                    continue
                elif cursor.node.type == 'subscript_expression':
                    continue
                elif cursor.node.type == 'function_call_expression':
                    self.process_call(cursor.node)
                    return
                elif cursor.node.type == 'member_call_expression' or cursor.node.type == 'scoped_call_expression':
                    self.process_member_call(cursor.node)
                elif cursor.node.type == 'array_element_initializer':
                    self.process_array_element(cursor.node)
                    return
                elif cursor.node.type == 'property_initializer':
                    continue
                elif cursor.node.type == 'property_element':
                    self.process_property_element(cursor.node)
                    return
                else:
                    logger.warning(f"other type in string_op: {cursor.node.type}")
                    break    

    def dfs_walk(self, cursor):
        if not cursor:
            return
        if cursor.node.type in string_type_names:
            self.process_string(cursor)
            return
        elif cursor.node.type in 'text':
            return
        elif cursor.node.type in ['function_definition','method_declaration']:
            self.get_method(cursor)
        if cursor.goto_first_child():
            self.dfs_walk(cursor)
            while cursor.goto_next_sibling():
                self.dfs_walk(cursor)
            cursor.goto_parent()

    def get_method(self, cursor):
        if cursor.node.type == 'method_declaration':
            first_child = cursor.node.children[2]
            second_child = cursor.node.children[3]
        elif cursor.node.type == 'function_definition':
            first_child = cursor.node.children[1]
            second_child = cursor.node.children[2]

        values = []
        if first_child.type == 'name':
            values.append(self.get_node_byte(first_child))
        if second_child.type == 'formal_parameters':
            for child in second_child.children[1:-1:2]:
                if child.type == 'variable_name':
                    values.append(self.get_node_byte(child)[1:])
        self.method = '#'.join(values)

if __name__ == "__main__":
    tmp_file = open('php_tree.tmp','w')

    if len(sys.argv) > 1:
        test_files = sys.argv[1:]
        for test_file in test_files:
            php_parser = PHP_Interpreter(test_file)
            php_parser.print_tree(tmp_file)
            php_parser.start_walk()
            print(test_file,php_parser.get_upload_urls())
    else:
        res_file = open('php_res.txt','w')
        repos = php_repos()
        for repo in repos:
            files = get_php_file(repo)
            if len(files) == 0:
                res_file.write(f"{repo} no php file")
                continue
            upload_urls = set()
            for file in files:
                try:
                    php_parser = PHP_Interpreter(file)
                    php_parser.print_tree(tmp_file)
                    php_parser.start_walk()
                    upload_urls |= php_parser.get_upload_urls()
                except Exception as e:
                    logger.error(f"error in {file}: {e}")

            print(repo,upload_urls)
        
        res_file.close()
    
    tmp_file.close()