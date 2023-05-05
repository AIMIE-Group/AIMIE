from bert_serving.client import BertClient
import re
from db import DB
import json
import requests
import random
from hashlib import md5
from scipy.spatial import distance


appid = ''
appkey = ''
from_lang = 'auto'
to_lang = 'en'
endpoint = 'http://api.fanyi.baidu.com'
path = '/api/trans/vip/translate'
url = endpoint + path

keywords = json.load(open('./keywords.json'))
kws = list(keywords['context'].keys())
stopwords = keywords['stopwords']


def trans_foreign_lang(query):
    # Generate salt and sign
    def make_md5(s, encoding='utf-8'):
        return md5(s.encode(encoding)).hexdigest()
    salt = random.randint(32768, 65536)
    sign = make_md5(appid + query + str(salt) + appkey)
    # Build request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}
    # Send request
    result = requests.post(url, params=payload, headers=headers).json()
    # Show response
    print(" to :", result['trans_result'][0]['dst'])
    return result['trans_result'][0]['dst']


def has_foreign_lang(word):
    pattern = re.compile('^[a-z0-9]+$')
    if pattern.fullmatch(word):
        return False
    else:
        print("from:", word)
        return True


def str_filter(string):
    pattern = re.compile('[0-9!"#$%&\'()*+,\-./:;<=>?@[\\]^_`{|}~～–…—：、，；【】｜¥·。？！（）《〈〉》‘’“”×\t\n\r]')
    new_string = pattern.sub(' ', string.lower())
    words = list(filter(None, re.split('[\s]+', new_string)))
    return words


def str_preprocess(string):
    words = str_filter(string)
    words_new = []
    for word in words:
        if '\\' in word:
            continue
        elif has_foreign_lang(word):
            words_tmp = trans_foreign_lang(word)
            words_tmp = str_filter(words_tmp)
            words_new.extend(words_tmp)
        else:
            words_new.append(word)
    for stopword in stopwords:
        while stopword in words_new:
            words_new.remove(stopword)
    return ' '.join(words_new)


def ou_dist(vec1, vec2):
    return distance.euclidean(vec1, vec2)


db = DB()
my_mongo_collection = db.get_mongo()
base_records = my_mongo_collection.fraud_detection['input_collection']
bc = BertClient(port=5777, port_out=5778, check_length=False)

correctss0 = []
correctss1 = []
thresholds = [0.3, 0.34, 0.38, 0.42, 0.46]
for threshold in thresholds:
    wordss = []
    base_tasks = base_records.find({"threshold": threshold, "real": 1}).limit(100)
    for base_task in base_tasks:
        if 'words' not in base_task.keys():
            words = str_preprocess(base_task['context'])
            base_records.update_one({'url': base_task['url'], "threshold": threshold}, {'$set': {'words': words}})
        else:
            words = base_task['words']
        wordss.append(words)
    base_vecs = bc.encode(wordss)

    dist_thresholds = [4.5, 5, 5.5, 6, 6.5]

    # Image Hosting Modules
    corrects1 = [0, 0, 0, 0, 0]
    for i in range(50, 100):
        min_dist = 10000
        for j in range(50):
            dist = ou_dist(base_vecs[i], base_vecs[j])
            if dist < min_dist:
                min_dist = dist

        for m in range(len(dist_thresholds)):
            if min_dist <= dist_thresholds[m]:
                corrects1[m] += 1

    correctss1.append(corrects1)

    # Other Modules
    corrects0 = [0, 0, 0, 0, 0]
    context_tasks = base_records.find({"threshold": threshold, "real": 0}).limit(50)
    for context_task in context_tasks:
        if 'words' not in context_task.keys():
            words = str_preprocess(context_task['context'])
            base_records.update_one({'url': context_task['url'], "threshold": threshold}, {'$set': {'words': words}})
        else:
            words = context_task['words']
        vec = bc.encode([words])[0]

        min_dist = 10000
        for base_vec in base_vecs[:50]:
            dist = ou_dist(base_vec, vec)
            if dist < min_dist:
                min_dist = dist

        for d in range(len(dist_thresholds)):
            if min_dist >= dist_thresholds[d]:
                corrects0[d] += 1

    correctss0.append(corrects0)

print(correctss0)
print()
print(correctss1)
print()


f1 = [[0] * len(correctss0[0]) for i in range(len(correctss0))]
press = [[0] * len(correctss0[0]) for i in range(len(correctss0))]
recss = [[0] * len(correctss0[0]) for i in range(len(correctss0))]
for i in range(len(correctss0)):
    for j in range(len(correctss0[0])):
        TP = correctss0[i][j]
        FN = 50 - correctss0[i][j]
        TN = correctss1[i][j]
        FP = 50 - correctss1[i][j]
        pre = TP / (TP + FP)
        rec = TP / (TP + FN)
        press[i][j] = pre
        recss[i][j] = rec
        f1[i][j] = 2 * pre * rec / (pre + rec)

print(press)
print()
print(recss)
print()
print(f1)
