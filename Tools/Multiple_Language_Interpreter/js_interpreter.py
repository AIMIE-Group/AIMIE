from base_interpreter import BaseInterpreter
import os
import pandas as pd
from log import Log
import sys
from util import load_keyword

logger = Log()
aimie_dir = '../AIMIE_Backup'
end_keywords = load_keyword('source_end')


def js_repos():
    aimie_lang = pd.read_csv("./doc/aimie_language.csv")
    js_aimie = aimie_lang[aimie_lang['language']=='js']['full_name'].tolist()
    return js_aimie

def get_js_file(full_name):
    js_files = []
    for root, dirs, files in os.walk(f"{aimie_dir}/{full_name}"):
        if 'static' in dirs:
            dirs.remove('static')
        for file in files:
            # file size > 50KB
            if os.path.getsize(os.path.join(root, file)) > 50*1024:
                continue
            if file.endswith('.js') and not file.endswith('min.js'):
                js_files.append(os.path.join(root, file))
    return js_files

class JS_Interpreter(BaseInterpreter):
    def __init__(self, js_file):
        self.read_file(js_file)
        self.set_language('js')
        self.tree = self.parser.parse(self.source_byte)
        self.string_dict = dict()
        self.upload_urls = set()
        self.if_value = dict()
    
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

        if second_child.type == 'string':
            string_value = self.process_string_only(second_child)
        elif second_child.type == 'binary_expression':
            string_value = self.process_binary_expression(second_child)
        else:
            logger.warning(f"other type in variable_declarator: {second_child.type}")
            return
        self.string_dict[identifier] = string_value
        if self.check_urls(string_value+'#'+identifier):
            logger.info(f"operation: {identifier} = {string_value}")

    def process_binary_expression(self, parent_node):
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
                elif child.type == 'binary_expression':
                    values.append(self.process_binary_expression(child))
                elif child.type == 'call_expression' and self.get_node_byte(child).startswith('$'):
                    value_list = self.process_call_value(child)
                    values.append(value_list)
                else:
                    logger.warning(f"other type in binary_expression: {child.type}")
                    return ""
            
            
            if type(values[0]) == list and type(values[1]) == list:
                return [i+j for i in values[0] for j in values[1]]
            elif type(values[0]) == list:
                return [i+values[1] for i in values[0]]
            elif type(values[1]) == list:
                return [values[0]+i for i in values[1]]
            else:
                return ''.join(values)
            
        elif op.type == '==':
            if first_child.type == 'identifier' and second_child.type == 'string':
                identifier = self.get_node_byte(first_child)
                print("identifier:", identifier)
                string_value = self.process_string_only(second_child)
                self.append_to_if_value(identifier, string_value)
                print(f"if: {identifier} == {string_value}, now {identifier}: {self.if_value[identifier]}")
            else:
                logger.warning(f"other type in binary_expression: {first_child.type} == {second_child.type}")
                return ""
        elif op.type == '|':
            for child in [first_child, second_child]:
                if child.type == 'binary_expression':
                    self.process_binary_expression(child)
                else:
                    logger.warning(f"other type in binary_expression | : {child.type}")
                    return
            return ""
        else:
            logger.warning(f"other type in binary_expression: {op.type}")
            return ""

    def process_member_expression(self, parent_node):
        if parent_node.child_count == 1:
            return self.get_node_byte(parent_node.children[0])
        elif parent_node.child_count == 3:
            return self.get_node_byte(parent_node.children[0]) + '.' + self.get_node_byte(parent_node.children[2])
        else:
            logger.warning(f"other type in member_expression: {parent_node.child_count}")
            return ""

    def process_call(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[1]
        
        if first_child.type == 'identifier':
            identifier = self.get_node_byte(first_child)
        elif first_child.type == 'member_expression':
            identifier = self.process_member_expression(first_child)
        else:
            logger.warning(f"other type in call: {first_child.type}")
            return
        
        if second_child.type == 'arguments':
            if second_child.child_count == 0:
                return
            arguments = second_child.children[1:-1:2]
            for argument in arguments:
                if argument.type == 'string':
                    string_value = self.process_string_only(argument)
                    if self.check_urls(string_value+'#'+identifier):
                        logger.info(f"call: {identifier}({string_value})")
                elif argument.type == 'identifier':
                    identifier = self.get_node_byte(argument)
                    string_value = self.get_string_value(identifier)
                    if self.check_urls(string_value+'#'+identifier):
                        logger.info(f"call: {identifier}({string_value})")
                elif argument.type == 'object':
                    continue
                else:
                    logger.warning(f"other type in call: {argument.type}")
                    return
        else:
            logger.warning(f"other type in call: {second_child.type}")
            return

    def process_call_value(self, parent_node):
        first_child = parent_node.children[0]
        
        if first_child.type == 'member_expression':
            first_member = first_child.children[0]
            second_member = first_child.children[2]
            if first_member.type == 'call_expression' and self.get_node_byte(first_member.children[0]) == '$' and self.get_node_byte(second_member) == 'val':
                identifier = self.get_node_byte(first_member.children[1])[3:-2]
                string_value = self.get_string_value(identifier)
                return string_value
            else:
                logger.warning(f"other type in call_value: {first_member.type} {second_member.type}")
                return ""
        else:
            logger.warning(f"other type in call_value: {first_child.type}")
            return ""


    def process_pair(self, parent_node):
        first_child = parent_node.children[0]
        second_child = parent_node.children[2]
        pair_op = self.get_node_byte(parent_node.children[1])
        print(f"pair type: {first_child.type} {pair_op} {second_child.type}")
        
        if first_child.type == 'string':
            key = self.process_string_only(first_child)
        elif first_child.type == 'property_identifier':
            key = self.get_node_byte(first_child)
        else:
            logger.warning(f"other type in pair: {first_child.type}")
            return
        
        if second_child.type == 'string':
            value = self.process_string_only(second_child)
            if self.check_urls(value+'#'+key):
                logger.info(f"pair: {key} {pair_op} {value}")
        elif second_child.type == 'identifier':
            value = self.get_string_value(self.get_node_byte(second_child))
        else:
            logger.warning(f"other type in pair: {second_child.type}")
            return
        
        if first_child.type == 'property_identifier':
            self.string_dict[key] = value

    def process_if_statement(self, parent_node):
        parenthesized_expression = parent_node.children[1]
        self.if_value = dict()

        if parenthesized_expression.children[1].type == 'binary_expression':
            self.process_binary_expression(parenthesized_expression.children[1])
        else:
            logger.warning(f"other type in if_statement: {parenthesized_expression.children[1].type}")
            return

    def process_return_statement(self, parent_node):
        return_child = parent_node.children[1]
        if return_child.type == 'string':
            string_value = self.process_string_only(return_child)
            if self.check_urls(string_value):
                logger.info(f"return string: {string_value}")
        elif return_child.type == 'binary_expression':
            string_value = self.process_binary_expression(return_child)
            if self.check_urls(string_value):
                logger.info(f"return string: {string_value}")
        else:
            logger.warning(f"other type in return_statement: {return_child.type}")
            return

    def process_string_only(self, string_node):
        string_value = self.get_node_byte(string_node)
        return string_value[1:-1]

    def process_string(self, cursor):
        if cursor.node.type == 'string':
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
                    self.process_return_statement(cursor.node)
                    return
                elif cursor.node.type == 'pair':
                    self.process_pair(cursor.node)
                    return
                elif cursor.node.type == 'binary_expression':
                    print("binary_expression pass")
                    continue
                elif cursor.node.type == 'call_expression':
                    self.process_call(cursor.node)
                    return
                elif cursor.node.type == 'arguments':
                    print("arguments pass")
                    continue
                elif cursor.node.type == 'parenthesized_expression':
                    print("parenthesized_expression pass")
                    continue
                elif cursor.node.type == 'if_statement':
                    self.process_if_statement(cursor.node)
                    cursor.goto_first_child()
                    print(f"pass child: {cursor.node.type}")
                    cursor.goto_next_sibling()
                    print(f"pass child: {cursor.node.type}")
                    return
                else:
                    logger.warning(f"other type for cursor: {cursor.node.type}")
                    return

    def dfs_walk(self, cursor):
        if not cursor:
            return
        if cursor.node.type == 'string':
            self.process_string(cursor)
            return
        elif cursor.node.type == 'else_clause':
            self.if_value = dict()
        elif cursor.node.type == 'function_declaration':
            self.get_method(cursor)
        if cursor.goto_first_child():
            self.dfs_walk(cursor)
            while cursor.goto_next_sibling():
                self.dfs_walk(cursor)
            cursor.goto_parent()

    def check_urls(self, urls):
        if type(urls) == list:
            for u in urls:
                self.check_url(u)
            return True
        elif type(urls) == str:
            if len(urls.split('#')) == 2:
                url, info = urls.split('#')
            else:
                url, info = urls, ''
            if url.endswith('=') and 'type' in self.if_value.keys():
                urls = [url+t+'#'+info for t in self.if_value['type']]
                return self.check_urls(urls)
            return self.check_url(urls)

    def get_method(self, cursor):
        first_child = cursor.node.children[1]
        second_child = cursor.node.children[2]

        values = []
        if first_child.type == 'identifier':
            values.append(self.get_node_byte(first_child))
        if second_child.type == 'formal_parameters':
            for child in second_child.children[1:-1:2]:
                if child.type == 'identifier':
                    values.append(self.get_node_byte(child))
        self.method = '#'.join(values)
        
if __name__ == "__main__":
    tmp_file = open('js_tree.tmp','w')

    if len(sys.argv) > 1:
        test_files = sys.argv[1:]
        for test_file in test_files:
            js_parser = JS_Interpreter(test_file)
            js_parser.print_tree(tmp_file)
            js_parser.start_walk()
            print(test_file,js_parser.get_upload_urls())
    else:
        res_file = open('js_res.txt','w')
        repos = js_repos()
        for repo in repos:
            files = get_js_file(repo)
            if len(files) == 0:
                res_file.write(f"{repo} no js file")
                continue
            upload_urls = set()
            for file in files:
                try:
                    js_parser = JS_Interpreter(file)
                    js_parser.print_tree(tmp_file)
                    js_parser.start_walk()
                    upload_urls |= js_parser.get_upload_urls()
                except Exception as e:
                    logger.error(f"error in {file}: {e}")

            print(repo,upload_urls)
            
        res_file.close()

    tmp_file.close()