import sys
import re
import hashlib
import string
import random
import traceback
from config import logger
from src.parser import Rule
from optparse import OptionParser
from src.builder import ABNFGrammarNodeBuilder
from src.util import format_abnf, banner, read_data, read_json, save_json
from config import TEST_CASE_DIR, BGrammar_PATH, SR_PATH, HCONFIG_PATH


"""
将发现的行为规范翻译到测试数据包里
1. 基于普通语法树生成正常的数据包
2. 定义一系列描述方法，用来翻译关系描述，即变异正常数据包
3. auto_fix 自动将一些template完成替换
4. 生成最后的测试样例
"""

# 基础grammar。
# {{xxx}}会在auto_fix中修复 {x}会在发包的时候 自动修复
Bgrammar = read_data(BGrammar_PATH)

# 从RFC中提取的SR配置
SRconfig = read_json(SR_PATH)

# 描述header关系 进行翻译
HConfig = read_json(HCONFIG_PATH)


# todo 检查SRconfig是否编写正确
def check_SRconfig(sr):
    # 表明只是一个sr
    if 'sentence' in sr:
        sr = {'default': sr}
    for k, v in sr.items():
        assert 'sentence' in v, 'Key "sentence" must be in sr, {}'.format(k)
        assert len(v['role']) > 0
        assert 'message' in v, 'Key "message" must be in sr, {}'.format(k)
        assert 'message' in v, 'Key "assertion" must be in sr, {}'.format(k)


# 接受一个SR值，然后进行构建测试样例
def SRbuild(sr):
    sent = sr['sentence']
    role = sr['role']
    message = sr['message']
    assertion = sr['assertion']
    results = []
    grammar = update_grammar(Bgrammar, message['new_grammar'])
    common = generator(grammar)
    for req in common:
        target = get_target(req, message['name'])
        assert target is not None
        for relation in message['relation']:
            results += generate_header(req, message['name'], target, relation)
    results = list(set(results))
    # for example
    if not results:
        results = common
    results = auto_fix(results)
    logger.info('Generate Test Cases: {}'.format(len(results)))
    # save data to file
    tmp = assertion['comment']
    outpath = TEST_CASE_DIR + str(hashlib.md5(sent.encode()).hexdigest())[:5] + '_' + tmp + '.json'
    data = sr
    data['reqs'] = results
    save_json(data, outpath)
    return results


def generator(grammar, target='HTTP-message'):
    """
    基于ABNF语法生成目标HTTP请求
    """
    Rule.from_txt(grammar)
    rule = Rule(target)
    assert rule.children is not None
    builder = ABNFGrammarNodeBuilder(rule)
    results = builder.build(rule.children)
    return results


def gen_testid():
    salt = ''.join(random.sample(string.digits, 8)) + ''.join(random.sample(string.digits, 8))
    testid = "testid{}idhere".format(salt)
    return testid


def gen_requestid(req):
    salt = str(hashlib.md5(req.encode()).hexdigest())
    return salt


# 针对一些关键模版进行自动字符串修复
def auto_fix(results):
    """
    basicid 用来标记该请求的基础请求是什么，所有后置位的请求都是由基础请求变异生成而来。 后续主要要观察变异请求和基础请求的区别
    CT_value 用于自动计算Content-Length的长度
    testid 用于随机生成16位数据，用于标记唯一的请求
    """
    results = list(set(results))
    for i in range(len(results)):
        results[i] = results[i].replace('{{CT_value}}', cacu_valid_CT(results[i])).replace('{{basicid}}', gen_requestid(
            results[i])).replace('{{testid}}', gen_testid())
    return results


def get_target(req, name):
    """
    req 请求包
    name 要修改的header

    """
    node, start = Rule('HTTP-message').parse(req)
    queue = [node]
    tmp = ''
    flag = 0
    while queue:
        n, queue = queue[0], queue[1:]
        # ABNF直接定义的节点
        if n.name == name:
            return n.value
        # ABNF中是一个字符串 e.g., 'Host:{{host}}\r\nConnection:close\r\n'
        # note: 针对第一行请求，理论上直接会从n.name阶段获取
        elif n.name == 'literal' and name in n.value:
            tmp = n.value
            # 有时候header和value分开定义的，需要同时获取。获取到CRLF位置
            flag = 1
        elif flag == 1:
            if n.name == 'literal' or n.name == 'OWS':
                tmp += n.value
            elif n.name == 'CRLF':
                tmp += n.value
                # 获取完毕
                return tmp
        queue.extend(n.children)

    return None


def update_grammar(old, new):
    """
    更新语法
    new 可以跨多行
    """
    new = format_abnf(new)
    old = format_abnf(old)
    result = old
    nn = new.split('\r\n')
    for n in nn:
        if len(n) == 0:
            continue
        name = n.split('=')[0]
        pattern = "{}\s?=.*\r\n".format(name)
        ts = re.search(pattern, result, re.I)
        if ts is None:
            # 新规则，直接添加
            result += n + '\r\n'
        else:
            target = ts.group()
            result = result.replace(target, n + '\r\n')
    return result


def spchar():
    """
    得到特殊char取值
    """
    data = list(string.whitespace + string.punctuation)
    data += [
        # '\x00',
        # '\xff',
        '\u00ff',
        '\u0000',
        '\uff00',
        '\uffff',
        '\u001f',
        '\u202e',
    ]
    data = list(set(data))
    data.sort()
    return data


# spchar TODO The current method is very violent and needs to be modified later
def gen_spchar(value):
    # value ='[]Ho[]st[]:[]localhost[]\r\n'
    pos = -1
    result = []
    sps = spchar()
    while True:
        pos = value.find('[]', pos + 1)
        if pos == -1:
            break
        for s in sps:
            tmp = value[:pos] + s + value[pos + 2:]
            result.append(tmp.replace('[]', ''))
    return result


# header 关系描述
def repeat_header(req, name, target):
    """
    req 原始请求
    name 要替换的header name
    target 目标在数据包中的值
    return results  列表，表示最后结果
    """
    results = []
    for v in HConfig[name]['repeat']:
        if isinstance(v, dict):
            if v['type'] == 'spchar':
                value = v['value']
                data = gen_spchar(value)
            else:
                logger.error('Undefined...')
                raise
        else:
            data = [v]
        for d in data:
            results.append(req.replace(target, target + d))  # 前序
            results.append(req.replace(target, d + target))  # 后序
    return results


def generate_header(req, name, target, relation):
    """
    req 原始请求
    name 要替换的header name
    target 目标在数据包中的值
    return results  列表，表示最后结果
    """
    results = []
    for v in HConfig[name][relation]:
        if isinstance(v, dict):
            value = v['value']
            if v['type'] == 'spchar':
                data = gen_spchar(value)
            elif v['type'] == 'abnf':
                # 通过ABNF生成
                grammar = update_grammar(Bgrammar, value)
                data = generator(grammar, target=name)
            else:
                logger.error('Undefined...')
                raise
        else:
            data = [v]
        for d in data:
            if relation == 'repeat':
                results.append(req.replace(target, target + d))  # 前序
                results.append(req.replace(target, d + target))  # 后序
            elif relation in ['valid', 'invalid', 'empty']:
                results.append(req.replace(target, d))
            else:
                logger.error('Undefined...')
                raise
    return results


def invalid_header(req, name, target):
    """
    req 原始请求
    name 要替换的header name
    target 目标在数据包中的值
    return results  列表，表示最后结果
    """
    results = []
    for v in HConfig[name]['invalid']:
        results.append(req.replace(target, v))
    return results


def long_header(req, name, target):
    results = []
    for v in HConfig[name]['long']:
        results.append(req.replace(target, v))
    return results


def valid_header(req, name, target):
    """
    header 标记目标header的名字
    req 原始请求
    return results  列表，表示最后结果
    """
    results = []
    for v in HConfig[name]['invalid']:
        results.append(req.replace(target, v))
    return results


def cacu_valid_CT(req):
    data = req.split('\r\n\r\n')[1]
    return str(len(data))



def parse_options():
    parser = OptionParser()
    parser.add_option("-t", "--target", dest="target", default=None,
                      help="The target is defined in the SR.json")
    (options, args) = parser.parse_args()
    return options


def run_error(errmsg):
    logger.error(("Usage: python " + sys.argv[0] + " [Options] use -h for help"))
    logger.error(("Error: " + errmsg))
    sys.exit()


def run():
    options = parse_options()
    if options.target is not None:
        key = options.target
        logger.info('Generate Specification Requirements: {}'.format(key))
        sr = SRconfig[key]
        check_SRconfig(sr)
        SRbuild(sr)
    else:
        errmsg = "You must set the parameters (-t or --target)."
        run_error(errmsg)
        sys.exit()
    logger.info("All Task Done! :)")


def main():
    banner()
    try:
        run()
    except Exception as e:
        traceback.print_exc()
        run_error(errmsg=str(e))


if __name__ == '__main__':
    run()
