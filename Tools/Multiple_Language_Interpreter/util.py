import tldextract
from log import Log
import json

log = Log()
public_platform_path = '../Public_Image_Hosting_Platform_List.txt'

def extract_sld(domain):
    return  '.'.join(tldextract.extract(domain)[1:3])

def load_second_list():
    with open("./doc/upload_second_list.txt",'r') as f:
        white_list = [x.strip() for x in f.readlines()]
    return white_list

def is_gateway(url):
    second_list = load_second_list()
    if any(x in url for x in second_list):
        return True
    return False

def load_white_list():
    with open(public_platform_path,'r') as f:
        white_list = [x.strip() for x in f.readlines()]
    return white_list

def is_public_platform(url):
    white_list = load_white_list()
    if any(x in url for x in white_list):
        return True
    return False

def get_tranco_rank_map():
    rank = {}
    with open('./doc/tranco-500K.csv') as fin:
        for line in fin:
            domain_rank, domain = line.split(',')
            rank[domain.strip()] = int(domain_rank.strip())
    return rank

def load_keyword(keyword_type):
    with open('./doc/keyword.json','r') as f:
        keyword = json.load(f)
        exclude = keyword['link'][keyword_type]
    return exclude