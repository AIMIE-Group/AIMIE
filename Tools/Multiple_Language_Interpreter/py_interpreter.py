from base_interpreter import BaseInterpreter
import os
import pandas as pd
from log import Log
import sys
from util import load_keyword

logger = Log()
aimie_dir = '../AIMIE_Backup'
end_keywords = load_keyword('source_end')
exclude_keywords = load_keyword('exclude')


def py_repos():
    aimie_lang = pd.read_csv("./doc/aimie_language.csv")
    py_aimie = aimie_lang[aimie_lang['language'] == 'py']['full_name'].tolist()
    return py_aimie


def get_py_file(full_name):
    py_files = []
    for root, dirs, files in os.walk(f"{aimie_dir}/{full_name}"):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files


class PY_Interpreter(BaseInterpreter):
    def __init__(self, py_file):
        self.read_file(py_file)
        self.set_language('py')
        self.tree = self.parser.parse(self.source_byte)
        self.string_dict = dict()
        self.upload_urls = set()

    def process_binary_op(self, parent_node):
        first_child = parent_node.children[0]
        op = parent_node.children[1]
        second_child = parent_node.children[2]

        if op.type == '+':
            values = []
            for child in [first_child, second_child]:
                if child.type == 'identifier':
                    identifier = self.get_node_byte(child)
                    print("identifier:", identifier)
                    values.append(self.get_string_value(identifier))
                elif child.type == 'string':
                    string_value = self.process_string_only(child)
                    values.append(string_value)
                elif child.type == 'binary_operator':
                    string_value = self.process_binary_op(child)
                    values.append(string_value)
                else:
                    logger.warning(f"other type in bin_op: {child.type}")
                    return ""
            return values[0] + values[1]
        else:
            logger.warning(f"other type in bin_op: {op.type}")

    def process_assignment(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[2]
        print(f"assignment type: {first_child.type} <- {second_child.type}")

        if first_child.type == 'identifier':
            identifier = self.get_node_byte(first_child)
            print("identifier:", identifier)
        else:
            logger.warning(f"other type in assignment: {first_child.type}")
            return

        if second_child.type == 'string':
            string_value = self.process_string_only(second_child)
        elif second_child.type == 'binary_operator':
            string_value = self.process_binary_op(second_child)
        elif second_child.type == 'call':
            string_value = self.process_call(second_child)
        else:
            logger.warning(f"other type in assignment: {second_child.type}")
            return
        
        self.string_dict[identifier] = string_value
        if self.check_url(string_value+'#'+identifier):
            logger.info(f"operation: {identifier} = {string_value}")

    def process_call(self, parent_node):
        attribute = parent_node.children[0]
        arguments = parent_node.children[1]

        if attribute.type == 'attribute' and arguments.type == 'argument_list':
            if len(attribute.children) == 3 and attribute.children[0].type == 'string':
                string_value = self.process_string_only(attribute.children[0])
                call_type = self.get_node_byte(attribute.children[2])
                print(f"raw string in call {call_type}:", string_value)

                if call_type == 'format':
                    if arguments.children[1].type == 'identifier':
                        identifier = self.get_node_byte(arguments.children[1])
                        string_value = string_value.format(self.get_string_value(identifier))
                        if self.check_url(string_value):
                            logger.info(f"format string: {string_value}")
                        return string_value
                    elif arguments.children[1].type == 'keyword_argument':
                        keyword = self.get_node_byte(arguments.children[1].children[0])
                        if arguments.children[1].children[2].type == 'string':
                            key_value = self.process_string_only(arguments.children[1].children[2])
                        elif arguments.children[1].children[2].type == 'identifier':
                            key_value = self.get_node_byte(arguments.children[1].children[2])
                            key_value = self.get_string_value(key_value)
                        string_value = string_value.format(**{keyword: key_value})
                        if self.check_url(string_value):
                            logger.info(f"format string: {string_value}")
                        return string_value
                    else:
                        logger.warning(f"other type in call_format: {arguments.children[1].type}")
                else:
                    logger.warning(f"other type in call_type: {call_type}")

            elif len(attribute.children) == 3 and attribute.children[0].type == 'identifier':
                call_identifier = self.get_node_byte(attribute)
                call_type = self.get_node_byte(attribute.children[2])
                print("identifier in call:", call_identifier)

                if call_type == 'post':
                    for argument in arguments.children[1:-1:2]:
                        if argument.type == 'string':
                            string_value = self.process_string_only(argument)
                            print("raw string in call_post:", string_value)
                            if self.check_url(string_value+'#'+call_identifier):
                                logger.info(f"post string: {string_value}")
                    return string_value
                else:
                    logger.warning(f"other type in call_type: {call_type}")
            else:
                logger.warning(f"other type in call_atrribute: {self.get_node_byte(attribute)}")
        
        elif attribute.type == 'identifier' and arguments.type == 'argument_list':
            call_identifier = self.get_node_byte(attribute)
            print("identifier in call:", call_identifier)
            info = call_identifier
            for child in arguments.children:
                if child.type == 'string':
                    string_value = self.process_string_only(child)
                    print("raw string in call:", string_value)
                    if self.check_url(string_value+'#'+info):
                        logger.info(f"string in {call_identifier}({string_value})")
                    info += string_value
                elif child.type == 'identifier':
                    identifier = self.get_node_byte(child)
                    string_value = self.get_string_value(identifier)
                    print("identifier in call:", identifier)
                    info += identifier
                    if self.check_url(string_value+'#'+info):
                        logger.info(f"string in {call_identifier}({identifier} = {string_value})")
                elif child.type in ['(', ',', ')']:
                    continue
                else:
                    logger.warning(f"other type in call_argument: {child.type}")
            string_value = ""   
        else:
            logger.warning(f"other type in call: {attribute.type} {arguments.type}")
            return ""           

    def process_dictionary(self, parent_node):
        for child in parent_node.children:
            if child.type == 'pair':
                self.process_pair(child)
            elif child.type in ['{', ',', '}']:
                continue
            else:
                logger.warning(f"other type in dictionary: {child.type}")

    def process_pair(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[2]
        pair_op = self.get_node_byte(parent_node.children[1])
        print(f"pair type: {first_child.type} {pair_op} {second_child.type}")
        
        if first_child.type == 'string':
            first_key = self.process_string_only(first_child)
        else:
            logger.warning(f"other type in pair: {first_child.type}")
            return
        
        if second_child.type == 'string':
            second_value = self.process_string_only(second_child)
            if self.check_url(second_value+'#'+first_key):
                logger.info(f"pair operation: {first_key} {pair_op} {second_value}")
        elif second_child.type == 'identifier':
            second_value = self.get_string_value(self.get_node_byte(second_child))
        elif second_child.type == 'dictionary':
            self.process_dictionary(second_child)
            return
        else:
            logger.warning(f"other type in pair: {second_child.type}")
            return
        
        print(f"pair: {first_key} {second_value}")
        self.string_dict[first_key] = second_value

    def process_string_only(self, node):
        string_value = self.get_node_byte(node)
        if string_value.startswith("f"):
            string_value = string_value[2:-1]
        elif string_value.startswith("r"):
            string_value = string_value[2:-1]
        else:
            string_value = string_value[1:-1]
        
        if len(node.children) > 3:
            middle_node = node.children[1]
            if middle_node.type == 'string_content':
                middle_node = node.children[2]
            if middle_node.type == 'interpolation':
                if middle_node.children[1].type == 'identifier':
                    identifier = self.get_node_byte(middle_node.children[1])
                    print("identifier in interpolation:", identifier)
                    id_value = self.get_string_value(identifier)
                    string_value = string_value.replace(f"{{{identifier}}}", id_value)
                elif middle_node.children[1].type in ['call', 'subscript']:
                    call_value = "#"
                    if 'json' in self.get_node_byte(middle_node.children[1]):
                        call_value += "generate_url"
                    string_value = string_value.replace(f"{{{self.get_node_byte(middle_node.children[1])}}}", call_value)
            else:
                logger.warning(f"other type in string_only: {middle_node.type}")
        return string_value
        
    def process_string(self, cursor):
        if cursor.node.type == 'string':
            string_node = cursor.node
            string_value = self.process_string_only(string_node)
            print(f"find string: {string_value} in {self.filename}")

            if string_value.startswith("r"):
                return
            if any(string_value.endswith(x) for x in end_keywords):
                return
            if "{" in string_value:
                string_value = string_value[:string_value.index("{")]
                
            while cursor.goto_parent():
                if cursor.node.type == 'assignment':
                    self.process_assignment(cursor.node)
                    return
                elif cursor.node.type == 'binary_operator':
                    continue
                elif cursor.node.type == 'return_statement':
                    if self.check_url(string_value):
                        logger.info(f"return string: {string_value}")
                    return
                elif cursor.node.type == 'argument_list':
                    print("arguments pass")
                    continue
                elif cursor.node.type == 'attribute':
                    continue
                elif cursor.node.type == 'call':
                    self.process_call(cursor.node)
                    return
                elif cursor.node.type == 'pair':
                    continue
                elif cursor.node.type == 'dictionary':
                    self.process_dictionary(cursor.node)
                    return
                else:
                    logger.warning(f"other type in string_op: {cursor.node.type}")
                    break

    def dfs_walk(self, cursor):
        if not cursor:
            return
        if cursor.node.type == 'string':
            self.process_string(cursor)
            return
        elif cursor.node.type == 'function_definition':
            self.get_method(cursor)
        if cursor.goto_first_child():
            self.dfs_walk(cursor)
            while cursor.goto_next_sibling():
                self.dfs_walk(cursor)
            cursor.goto_parent()

    def get_method(self, cursor):
        first_child = cursor.node.children[1]
        second_child = cursor.node.children[2]

        values = []
        if first_child.type == 'identifier':
            values.append(self.get_node_byte(first_child))
        if second_child.type == 'parameters':
            for child in second_child.children[1:-1:2]:
                if child.type == 'identifier' and self.get_node_byte(child) != 'self':
                    values.append(self.get_node_byte(child))
        self.method = '#'.join(values)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_files = sys.argv[1:]
        for test_file in test_files:
            py_parser = PY_Interpreter(test_file)
            with open('py_tree.tmp', 'w') as f:
                py_parser.print_tree(f)
            py_parser.start_walk()
            print(test_file,py_parser.get_upload_urls())
    else:
        res_file = open('py_res.txt', 'w')
        repos = py_repos()
        for repo in repos:
            files = get_py_file(repo)
            upload_urls = set()
            for file in files:
                try:
                    py_parser = PY_Interpreter(file)
                    with open('py_tree.tmp', 'w') as f:
                        py_parser.print_tree(f)
                    py_parser.start_walk()
                    upload_urls = upload_urls.union(py_parser.get_upload_urls())
                except Exception as e:
                    print(e)

            print(repo,upload_urls)

        res_file.close()
