import sys
from tree_sitter import Parser, Language
from log import Log
from util import load_keyword, is_gateway
import re
from urllib.parse import urlparse, parse_qs

logger = Log()
end_keywords = load_keyword('source_end')
exclude_keywords = load_keyword('exclude')
pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

Language.build_library(
    # Store the library in the `build` directory
    'build/my-languages.so',
    [
        'vendor/tree-sitter-python',
        'vendor/tree-sitter-javascript',
        'vendor/tree-sitter-go',
        'vendor/tree-sitter-java',
        'vendor/tree-sitter-php',
    ]
)

PY_LANGUAGE = Language('build/my-languages.so', 'python')
JS_LANGUAGE = Language('build/my-languages.so', 'javascript')
GO_LANGUAGE = Language('build/my-languages.so', 'go')
JAVA_LANGUAGE = Language('build/my-languages.so', 'java')
PHP_LANGUAGE = Language('build/my-languages.so', 'php')

class BaseInterpreter():
    language = "base"
    filename = ""
    parser = Parser()
    source_code = None
    source_byte = None
    tree = None
    f_out = sys.stdout
    string_dict = dict()
    upload_urls = set()
    if_value = dict()
    method = ""

    def __init__(self,input_file):
        self.read_file(input_file)

    def set_language(self, language):
        self.language = language
        if language == 'py':
            self.parser.set_language(PY_LANGUAGE)
        elif language == 'js':
            self.parser.set_language(JS_LANGUAGE)
        elif language == 'go':
            self.parser.set_language(GO_LANGUAGE)
        elif language == 'java':
            self.parser.set_language(JAVA_LANGUAGE)
        elif language == 'php':
            self.parser.set_language(PHP_LANGUAGE)
        else:
            logger.error(f"ERROR: {language} not supported.")
            return

    def read_file(self,input_file):
        self.filename = input_file
        with open(input_file, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        self.source_byte = bytes(self.source_code, 'utf8')

    def dfs(self, node ,i):
        if (len(node.children) == 0 and len(node.type) > 2) or node.type in ['identifier', 'string', 'number', 'name', 'encapsed_string', 'interpreted_string_literal']:
            self.f_out.write('  '*i + node.type + ' ' + self.get_node_byte(node) + '\n')
        else:
            self.f_out.write('  '*i + node.type + '\n')
        for child in node.children:
            self.dfs(child, i+1)

    def print_tree(self,f_out=sys.stdout):
        self.f_out = f_out
        self.dfs(self.tree.root_node, 0)

    def get_node_byte(self, node):
        return self.source_byte[node.start_byte:node.end_byte].decode('utf-8')
    
    def append_to_if_value(self, key, value):
        if key in self.if_value.keys():
            self.if_value[key].append(value)
        else:
            self.if_value[key] = [value]

    def get_string_value(self, indentifier):
        if  indentifier in  self.string_dict.keys():
            return self.string_dict[indentifier]
        elif indentifier in self.if_value.keys():
            return self.if_value[indentifier]
        else:
            logger.error(f"ERROR: {indentifier} not defined.")
            return ""

    def start_walk(self):
        cursor = self.tree.walk()
        self.dfs_walk(cursor)

    def dfs_walk(self, cursor):
        if not cursor:
            return
        if cursor.goto_first_child():
            self.dfs_walk(cursor)
            while cursor.goto_next_sibling():
                self.dfs_walk(cursor)
            cursor.goto_parent()

    def check_url(self, url):
        if len(url.split('#')[0]) < 12:
            return False
        if re.findall(r'[\u4e00-\u9fa5]', url) != []:   # delete chinese character
            return False
        url = url + '#' + self.method
        print(f"checking url: {url}")
        if any(x in url for x in exclude_keywords):
            return False
        url_list = re.findall(pattern, url)
        if url_list == []:
            return False
        url = url_list[0]
        self.upload_urls.add(url)
        return True
    
    def get_upload_urls(self):
        # delete prefix
        new_urls = set()
        for url in sorted(self.upload_urls,reverse=True):
            is_prefix = False
            for long_url in new_urls:
                if long_url.startswith(url):
                    is_prefix = True
                    break
            if not is_prefix:
                new_urls.add(url)
        self.upload_urls = new_urls
        
        # params: type only
        final_urls = set()
        for url in new_urls:
            u = urlparse(url)
            raw_url = f"{u.scheme}://{u.netloc}{u.path}"
            if is_gateway(url):
                params = parse_qs(u.query)
                type_flag = 0
                for type_pattern in ['type', 'apiType']:
                    if type_pattern in params.keys():
                        if params[type_pattern][0] == 'multipart': 
                            break
                        final_urls.add(f"{raw_url}?{type_pattern}={params[type_pattern][0]}")
                        type_flag = 1
                        break
                if not type_flag:
                    final_urls.add(raw_url)
            else:
                final_urls.add(raw_url)
        return final_urls
    
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