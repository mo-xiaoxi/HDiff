import hashlib
import copy
import ssl
import numpy as np
import string
import docker
import socket
import time
import re
import os
import html
import json
import random
import requests
import itertools
import difflib
from config import logger
from config import ABNF_DIR, RFC_DIR, CLEANED_RFC_DIR


def find_pair(left_idx, right_char, string):
    """ 从 string 的 left_idx 位置开始，找到与其匹配的右端位置
    :param left_idx: 左端下标
    :param right_char: 右端字符
    :param string: 字符串
    :return: 匹配的右端下标
    """

    left_char = string[left_idx]
    curr_idx = left_idx + 1

    # note(yangyr17): 合并了下面的三个 if

    if right_char in [" ", "*", "\""]:  # 注意不允许存在双引号嵌套
        curr_idx = string.find(right_char, left_idx + 1)
        # assert curr_idx != -1
        # todo(yangyr17): <">            = <US-ASCII double-quote mark (34)> 时错误
        if curr_idx == -1:
            curr_idx = len(string)
    else:  # 类似括号匹配
        left_count = 0
        while curr_idx < len(string):
            curr_char = string[curr_idx]
            if curr_char == right_char:  # 不允许存在类似< "<s" >
                if left_count == 0:
                    break
                else:
                    left_count -= 1
            elif curr_char == left_char:
                left_count += 1

            curr_idx += 1

    return curr_idx


# read the abnf list from a given file
def read_rule(path):
    """
    解析指定路径下文件的ABNF规则
    """
    logger.debug('Get ABNF list from file {}'.format(path))
    rule_list = {}
    key = ''
    f = open(path, 'rb')
    for line in f:
        line = line.decode().strip()
        # 截断到第一个未被引号包围的分号
        i = 0
        while i < len(line):
            if line[i] == ';':
                line = line[:i]
                break
            if line[i] == '"':
                i = find_pair(i, '"', line)
            i = i + 1

        if len(line) == 0:
            continue

        # 找到第一个未被引号包围的等号，其下标为 i
        i = 0
        while i < len(line):
            if line[i] == '=':
                break
            if line[i] == '"':
                i = find_pair(i, '"', line)
            i = i + 1

        if i < len(line):
            if len(line[i + 1:].strip()) <= 1:
                continue
            key = line[:i].strip()
            rule_list[key] = line[i + 1:].strip()
        else:
            rule_list[key] = rule_list[key] + " " + line
    f.close()
    logger.debug("ABNF rules:{}".format(rule_list))
    return rule_list


def random_case_string(s):
    """
    输入一个字符串，随机返回大小写变异的字符串
    """
    result = ''
    for i in s:
        flag = random.randint(0, 1)
        if flag:
            result += i.upper()
        else:
            result += i.lower()
    return result


def random_repeat(min_num, max_num, data):
    """
    返回一个列表中min-max的重复 全集重复
    1,3 ['a','b']
    返回
    ['a','b','ab','ba','aab','aba','abb','baa','bab','bba','bbb']
    1,1 ['a','b']
    """
    min_num = min_num if min_num is not None else 0
    # todo 最大重复次数为最小的重复次数+3
    max_num = max_num if max_num is not None else min_num + 3
    # 1 char 这类语法，上下重复一致 定量重复 n规则

    results = []
    if min_num == max_num:
        args = max_num * [data]
        res = cartesian(*args)
        results.append(res)
        results = flatten(results)
        return results

    for i in range(min_num, max_num):
        args = i * [data]
        res = cartesian(*args)
        results.append(res)
    results = flatten(results)
    return results


def flatten(*L):
    """Takes an item, or a list of items, of which some items may be lists, and returns a list; e.g.
    flatten(1) returns [1]
    flatten([1] returns [1]
    flatten([1, 2, 3], 4, [5]) returns [1, 2, 3, 4, 5].
    """
    flat_list = []
    for item in L:
        if isinstance(item, list):
            flat_list.extend(flatten(*item))
        else:
            flat_list.append(item)
    return flat_list


def cartesian(*L):
    """列表笛卡尔积计算
    [['HTTP'], ['/'], ['0.9', '1.0', '1.1', '2.0']]
    =>
    ['HTTP/0.9', 'HTTP/1.0', 'HTTP/1.1', 'HTTP/2.0']
    """
    result = []
    for i in itertools.product(*L):
        result.append(''.join(i))
    return result


# download the RFC data and abnf list from a given rfc-number
def download_rfc(rfc_number):
    # html_content = requests.get('https://tools.ietf.org/html/rfc' + rfc_number).content
    res = requests.get('https://datatracker.ietf.org/doc/html/rfc' + rfc_number)
    assert res.status_code == 200
    real_html = res.text
    pattern = re.compile(r'<.+?>', re.S)
    content = pattern.sub('', real_html)
    content = html.unescape(content)
    # logger.debug(content)
    path = os.path.join(RFC_DIR, rfc_number + '.txt')
    save_data(content, path)
    logger.debug("Save RFC {} to {}.".format(rfc_number, path))
    clean_data = clean_rfc(content)
    path = os.path.join(CLEANED_RFC_DIR, rfc_number + '.txt')
    save_data(clean_data, path)
    logger.debug("Save Cleaned RFC {} to {}.".format(rfc_number, path))

    if 'Collected ABNF' in content:
        content = 'Collected ABNF\n' + content.split('Collected ABNF')[2]
    content_list = content.split('\n')

    if 'Collected ABNF' in content:
        while ' = ' not in content_list[0]:
            content_list.pop(0)
        i = 0
        while i < len(content_list):
            if '[Page ' in content_list[i]:
                content_list.pop(i)
            elif content_list[i].startswith('RFC '):
                content_list.pop(i)
            elif len(content_list[i]) < 3:  # white space line
                content_list.pop(i)
            elif not content_list[i].startswith('   '):
                break
            else:
                i = i + 1
        while i < len(content_list):
            content_list.pop(i)
    else:
        i = 0
        while i < len(content_list):
            if '[Page ' in content_list[i]:
                content_list.pop(i)
            elif content_list[i].startswith('RFC '):
                content_list.pop(i)
            else:
                i = i + 1

        i = 0
        while True:
            while i < len(content_list):
                reg = re.compile('[ ]*[a-zA-Z0-9-]*[ ]* = .*')
                match = reg.match(content_list[i])
                if match == None:
                    content_list.pop(i)
                else:
                    break

            if i >= len(content_list):
                break

            while len(content_list[i]) > 3:  # not white space line
                i = i + 1
    content = '\r\n'.join(content_list)

    path = os.path.join(ABNF_DIR, rfc_number + '.txt')  # note (yangyr17)
    content = format_abnf(content)
    save_data(content, path)
    logger.debug("Save ABNF {} to {}.".format(rfc_number, path))
    return content


def get_abnf_rule(rfc_number):
    """ 解析 rfc 的 abnf 文件,  """
    logger.debug('Get ABNF list from RFC' + rfc_number)
    file_path = os.path.join(ABNF_DIR, rfc_number + '.txt')  # note(yangyr17)
    if not os.path.exists(file_path):
        logger.debug('Cache miss! download RFC{}'.format(rfc_number))
        return download_rfc(rfc_number)
    logger.debug('Cache Hit! RFC{}'.format(rfc_number))
    with open(file_path, 'r') as f:
        data = f.read()
    data = expand_abnf(data)
    return data


# 对ABNF文法进行样式格式化
def format_abnf(rule_source):
    rule_source = rule_source.strip()
    if '\r\n' not in rule_source:
        lines = rule_source.split('\n')
    else:
        lines = rule_source.split('\r\n')

    result = ''
    last_index = 0
    for line in lines:
        index = line.find('=')
        if index != -1 and line[index - 1] != '"' and line[index + 1] != '"':
            result += line.strip() + '\r\n'
            last_index = index - 1
        else:
            result += ' ' * last_index + line.strip() + '\r\n'
    return result


# 对  prose-val 语法进行自动扩展
def expand_abnf(data):
    """ 查询 rfc_number 对应的 ABNF 中是否引用其他 RFC, 并对被引用的 RFC 进行递归解析
     主要处理prose-val
     URI-reference = <URI-reference, see [RFC3986], Section 4.1>
     path-empty    = 0<pchar>
     """
    data = format_abnf(data)
    lines = data.split('\r\n')
    new_rfcs = {}
    for line in lines:
        c1 = line.find("<")
        c2 = line.find(">")
        # 判定散文格式
        if c1 >= 0 and c2 >= 0 and line[c1 + 1] != '"' and line[c2 - 1] != '"':
            # todo 目前暂未考虑换行散文格式规则
            assert ';' not in line
            reg = re.compile('.*<(?P<name>[^,]*), .*RFC(?P<rfc_num>[0-9]*).*')
            match = reg.match(line)
            # 说明是纯粹的尖括号格式,直接删去尖括号
            if match == None:
                new_line = line.replace('<', '').replace('>', '')
                data = data.replace(line, new_line)
                continue
            res = match.groupdict()
            if res['rfc_num'] not in new_rfcs:
                new_rfcs[res['rfc_num']] = [res['name']]
            else:
                new_rfcs[res['rfc_num']].append(res['name'])
            origin_name = line.split('=')[0].strip()
            if origin_name == res['name']:
                # 删除当前行
                data = data.replace(line + '\r\n', '')
            else:
                new_line = "{} = {}".format(origin_name, res['name'])
                data = data.replace(line, new_line)
    # 暂不考虑RFC之间循环引用，理论上也不会循环引用
    for rfc_num in new_rfcs:
        data += get_abnf_rule(rfc_num)
    return data


def banner():
    my_banner = ("""%s
          o         o    o__ __o         o      o__ __o      o__ __o   
         <|>       <|>  <|     v\      _<|>_   /v     v\    /v     v\  
         < >       < >  / \     <\            />       <\  />       <\ 
          |         |   \o/       \o     o    \o           \o          
          o__/_ _\__o    |         |>   <|>    |>_          |>_        
          |         |   / \       //    / \    |            |          
         <o>       <o>  \o/      /      \o/   <o>          <o>         
          |         |    |      o        |     |            |          
         / \       / \  / \  __/>       / \   / \          / \          \
                                                                    %s%s
                                                        # Version: 1.0
                                                        # Author: moxiaoxi%s
        """ % ('\033[91m', '\033[0m', '\033[93m', '\033[0m'))
    print(my_banner)


# save to json
def save_json(result, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # with open(path, 'w') as f:
    #     json.dump(result, f, cls=MyEncoder, ensure_ascii=False, indent=4)
    with open(path, 'w') as f:
        json.dump(result, f, indent=4)
    logger.info("Save data to {}".format(path))
    return True


# save list to txt
def save_data(result, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(result)
    logger.info("Save data to {}".format(path))
    return


def read_data(path):
    if not os.path.exists(path):
        logger.warning("{} not exist!".format(path))
        return None
    with open(path, 'r') as f:
        data = f.read()
    return data


def read_json(path):
    if not os.path.exists(path):
        logger.warning("{} not exist!".format(path))
        return {}
    with open(path, 'r') as f:
        # data = json.load(f, cls=MyEncoder, ensure_ascii=False, indent=4)
        data = json.loads(f.read())
    return data


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


def merge_dict(dict1, dict2):
    ret = copy.deepcopy(dict1)
    ret.update(dict2)
    return ret


def send(host, port, data_send, use_ssl=False, client_wait_time=0.5, recv_buf_size=4096):
    """ 进行单次发包测试
    :param host: str, 目标主机
    :param port: int, 目标端口
    :param data_send: bytes, 要发送的数据
    :param use_ssl: bool, 是否使用 SSL
    :param client_wait_time: float, 客户端发包后等待时间（单位为秒）
    :param recv_buf_size: int, 接收响应时的 buffer 大小，即最多接收字节数
    :return: str
    """
    try:
        client = socket.socket()
        if use_ssl != 0:
            client = ssl.wrap_socket(client)
    except Exception as e:
        logger.error(e)
        return False
    client.settimeout(client_wait_time * 2)
    client.connect((host, port))
    client.send(data_send)
    time.sleep(client_wait_time)
    try:
        data_recv = client.recv(recv_buf_size)
    except socket.timeout:
        data_recv = b''
    client.close()
    return data_recv


def get_random_port():
    """ 获得 [PORT_LB, PORT_UB] 的一个随机端口 """
    from config import PORT_LB, PORT_UB
    return random.randint(PORT_LB, PORT_UB)


def calc_md5(file_path):
    """ 计算给定路径文件的 MD5 """
    with open(file_path, 'rb') as f:
        data = f.read()
    return hashlib.md5(data).hexdigest()


def is_number(s):
    """ 判断字符串 s 是否为一个数 """
    try:
        tmp = int(s)
        return True
    except ValueError:
        return False


def get_status_code(data):
    """
    获得响应的状态码
    :param data: 接收到的字节串
    :return status_codes: list, 每项为 int 类型，对应状态码列表
    """
    try:
        status_code = str(int(data.split(' ')[1]))
    except Exception as e:
        logger.error(e)
        logger.error(data)
        status_code = None
    return status_code


def check_status_codes(expected_status_codes, status_codes):
    """
    检查获得的 status_codes 是否满足 expected_status_codes
    :param expected_status_codes: list, 每项为一个字符串，特别地，可以用 'any' 表示任意状态码，'!200' 表示除 200 外的状态码
    :param status_codes: list, 每项为一个数字，表示响应状态码
    :return:
    """
    if len(expected_status_codes) != len(status_codes):
        return False
    for i in range(len(expected_status_codes)):
        expected_status_code = expected_status_codes[i]
        status_code = status_codes[i]
        if expected_status_code == 'any':
            continue
        elif expected_status_code[0] == '!':
            if int(expected_status_code[1:]) == status_code:
                return False
        else:
            if int(expected_status_code) != status_code:
                return False
    return True


def is_expected_status_codes_valid(expected_status_codes):
    """
    检查是否为合法的期望响应码列表
    :param expected_status_codes: list, 每项为一个字符串，可以用 'any' 表示任意状态码，'!200' 表示除 200 外的状态码
    :return: True or False
    """
    for code in expected_status_codes:
        if not (code == 'any' or (code[0] == '!' and is_number(code[1:])) or is_number(code)):
            return False
    return True


#
# def load_progress(target_name, data_path, group_size, target, tot_num):
#     """
#     载入进度，若 common 内容与当前不符则进度作废
#     :param target_name: target 名
#     :param data_path: 输入数据文件路径
#     :param group_size: 数据分组大小
#     :param target: target 详细配置
#     :param tot_num: 总数据条数（用于显示恢复进度）
#     :return: 整合后的测试记录 load_results，以及进度完成标记数组 finish_flags
#     """
#     from config import FUZZ_HTTP_DIR, PROGRESS_DIR, COMMON_FILE_NAME
#     load_results = {'irregular': [], 'result': []}
#     group_num = tot_num // group_size + (1 if tot_num % group_size != 0 else 0)
#     finish_flags = [False for _ in range(group_num)]
#     data_name = os.path.basename(data_path).split('.')[0]
#     progress_dir = os.path.join(PROGRESS_DIR, target_name, data_name)
#     common_path = os.path.join(progress_dir, COMMON_FILE_NAME)
#     if os.path.exists(common_path):
#         common = read_data(common_path)
#         if common.get('key') != target_name or common.get('data_name') != data_name or common.get('target') != target \
#                 or common.get('md5') != calc_md5(data_path) or common.get('group_size') != group_size:
#             logger.warning(
#                 'group_size/md5/target has changed, delete the progress dir: %s/%s/' % (target_name, data_name))
#             shutil.rmtree(progress_dir)
#         else:
#             pieces = os.listdir(progress_dir)
#             pieces.remove(COMMON_FILE_NAME)
#             # 保证最终输出有序
#             pieces.sort(key=lambda x: int(x.split('.')[0]))
#             for piece in pieces:
#                 content = read_data(os.path.join(progress_dir, piece))
#                 load_results['irregular'].extend(content['irregular'])
#                 load_results['result'].extend(content['result'])
#                 finish_flags[int(piece.split('.')[0])] = True
#             load_num = len(load_results['result'])
#             logger.info('Recovery progress: %d/%d, %.2f%%' % (load_num, tot_num, load_num / tot_num * 100))
#     return load_results, finish_flags
#
#
# def save_progress(target_name, data_name, group_size, target, results):
#     """
#     保存进度，注意因为会在此之前调用 load_progress，保证了 common 一定同目前符合
#     :param target_name: target 名
#     :param data_name: 输入数据文件名（不含后缀）
#     :param group_size: 数据分组大小
#     :param target: target 详细配置
#     :param results: 要保存的结果
#     :return: None
#     """
#     from config import PROGRESS_DIR, FUZZ_HTTP_DIR, COMMON_FILE_NAME, PREFUZZ_V2_OUTPUT_DIR
#     data_path = os.path.join(PREFUZZ_V2_OUTPUT_DIR, '%s.json' % data_name)
#     progress_dir = os.path.join(PROGRESS_DIR, target_name, data_name)
#     common_path = os.path.join(progress_dir, COMMON_FILE_NAME)
#     if not os.path.exists(progress_dir):
#         os.makedirs(progress_dir)
#         md5 = calc_md5(data_path)
#         common = {'key': target_name, 'data_name': data_name, 'target': target, 'md5': md5, 'group_size': group_size}
#         save_data(common, common_path)
#     tmp_results = {'irregular': results['irregular'], 'result': results['result']}
#     save_data(tmp_results, os.path.join(progress_dir, '%d.json' % results['group_ind']))


def start_container(image_name, inner_port):
    """
    开启一个容器
    :param image_name: 镜像名
    :param inner_port: 容器内开放的端口
    :return: port: 返回容器向外开放的端口
    """
    from config import DOCKER_LABEL
    docker_client = docker.from_env()
    while True:
        outer_port = get_random_port()
        try:
            docker_client.containers.run(image_name, ports={'%d/tcp' % inner_port: outer_port}, tty=True,
                                         stdin_open=True, privileged=True,
                                         remove=True, detach=True, labels=[DOCKER_LABEL])
        except Exception as e:
            if 'port is already allocated' not in e.__str__():
                raise e
            else:
                continue
        break
    logger.info('Start container %s with port %d' % (image_name, outer_port))
    return outer_port


def kill_containers():
    """ 杀死所有带 DOCKER_LABEL 的容器 """
    logger.info('Kill containers.')
    from config import DOCKER_LABEL
    docker_client = docker.from_env()
    for container in docker_client.containers.list(filters={'label': DOCKER_LABEL}):
        container.stop()


# 得到当前目录下所有文件，除了.开头或者.bak结尾的文件
def get_all_files(path, ends=None):
    res = []
    g = os.walk(path)
    for path, dir_list, file_list in g:
        for file_name in file_list:
            if file_name.startswith('.') or file_name.endswith('.bak'):
                continue
            if ends is None or file_name.endswith(ends):
                res.append(os.path.join(path, file_name))
    res.sort()
    return res


def read_origin_http(path):
    data = ''
    with open(path, 'r') as f:
        data = f.read()
        data = data.replace('\n', '\r\n')
    if not data.endswith('\r\n\r\n'):
        data = data.strip() + '\r\n\r\n'
    return data

    # for k in results:
    #     p = k.replace('origin_http', 'fuzz_http').replace('.template', '.json')


def find_same(rules_name):
    tmp = dict()
    index = 0
    for x in rules_name:
        if x in tmp:
            return x
        tmp[x] = index
        index = index + 1


def extract_proxy_send(res):
    """
    从 echo server 的响应中提取 proxy 发出的内容
    :param res: str，echo server 的响应
    """
    if res.find('starthttp1234567890') == -1:
        return None
    ret = res.split('starthttp1234567890')[1]
    ret = '\r\n'.join(ret.split('\r\n')[1:])
    ret = ret.split('endthttp0987654321')[-2]
    return ret


def extract_testid(s):
    """ 提取字符串中 testid<id>idhere 的 <id> 部分 """
    m = re.search("testid(?P<testid>\d{16})idhere", s)
    return None if m is None else m.group('testid')


def gen_ramstr():
    return ''.join(random.sample(
        string.ascii_letters + string.digits + "!" + "#" + "$" + "%" + "&" + "'" + "*" + "+" + "-" + "." + "^" + "_" + "`" + "|" + "~",
        8))


def easy_decode(s):
    try:
        return s.decode('utf-8')
    except Exception as e:
        return s.decode('latin-1')


def easy_encode(s):
    try:
        return s.encode('utf-8')
    except Exception as e:
        return s.encode('latin-1')


# for server
def extract_response_data(res):
    try:
        if get_status_code(res) == '200':
            response_data = res.split('\r\n\r\n')[1]
            response_data = response_data[response_data.find("{"):response_data.find("}") + 1]
            data = json.loads(response_data)
            return data
    except Exception as e:
        logger.warning(e)
        logger.warning(res)
    return {}


# RFC 清洗工作
def clean_rfc(data):
    lines = data.split('\n')
    lines = list(filter(None, lines))
    # 删除目录之前的内容
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].replace(' ', '').find('.....') >= 0:
            lines = lines[i + 1:]
            break

    deleted = [False for _ in range(len(lines))]

    # 删除页眉
    for i in range(len(lines)):
        if re.search(r'\[Page \d+\]', lines[i]) is not None:
            deleted[i] = True
            if i + 1 < len(lines):
                deleted[i + 1] = True
            if i + 2 < len(lines):
                deleted[i + 2] = True
            t = i - 1
            while t >= 0 and lines[t] == '\n':
                deleted[t] = True
                t -= 1
            t = i + 3
            while t < len(lines) and lines[t] == '\n':
                deleted[t] = True
                t += 1
    old_lines = lines
    lines = []
    for i in range(len(old_lines)):
        if not deleted[i]:
            lines.append(old_lines[i])

    # 删除标题
    for i in range(len(lines)):
        if lines[i][0] != ' ' and lines[i][0] != '\n':
            lines[i] = '\n'

    # 删除 ABNF 段(首行包含' =')和 [ 开头的段
    is_middle = False
    need_delete = False
    for i in range(len(lines)):
        if lines[i] == '\n':
            is_middle = False
            need_delete = False
        elif not is_middle:
            if lines[i].find(' =') >= 0 or lines[i].strip().find('[') == 0:
                need_delete = True
            is_middle = True
        if need_delete:
            lines[i] = '\n'

    # 删除各类图示
    special_characters = ['-', '+', '<', '>', '=']
    for i in range(len(lines)):
        # 删除包含特殊字符过多的行
        for c in special_characters:
            if lines[i].count(c) > 5:
                lines[i] = '\n'
        # 删除不含数字和字母的行
        if re.search('\w', lines[i]) is None:
            lines[i] = '\n'
        # 删除引号之外包含 | 的行
        q_cnt = 0
        for c in lines[i]:
            if c == '"':
                q_cnt += 1
            elif c == '|' and q_cnt % 2 == 0:
                lines[i] = '\n'
                break

    # 合并行
    old_lines = lines
    lines = []
    last_line = ''
    for i in range(len(old_lines)):
        cur_line = old_lines[i].strip()
        if len(cur_line) > 0:
            if i > 0 and len(last_line) > 0:
                lines[-1] += ' ' + cur_line
            elif i == 0 or len(last_line) == 0:
                lines.append(cur_line)
        last_line = cur_line

    # 删除结尾非 . 的行
    old_lines = lines
    lines = []
    for i in range(len(old_lines)):
        if old_lines[i].strip()[-1] == '.':
            lines.append(old_lines[i])

    # 删除每行第一个字母之前的部分
    for i in range(len(lines)):
        pos = re.search(r'[A-Za-z]', lines[i]).start()
        lines[i] = lines[i][pos:]
    result = '\n'.join(lines)
    return result




def get_container_by_name(cli, prefix, name, ignore_errors=False):
    """
    使用 prefix_name_1 的形式寻找容器
    :param cli: docker client 对象
    :param prefix: 前缀名
    :param name: docker-compose.yml 中设置的容器名
    :param ignore_errors: 是否忽略未找到容器的错误
    :return: docker container 对象
    """
    containers = cli.containers.list()
    container = None
    # if platform.system() == 'Darwin':
    #     full_name = prefix + '-' + name + '-1'
    # else:
    full_name = prefix + '_' + name + '_1'
    for c in containers:
        if c.name == full_name:
            container = c
            break
    if not ignore_errors:
        assert container is not None, 'Cannot find container %s' % full_name
    return container




def extract_container_file(container, path_in_container, extract_path):
    """
    提取容器中的文件到指定路径
    :param container: docker container 对象
    :param path_in_container: 文件在容器中的路径
    :param extract_path: 提取到的目标路径
    :return:
    """
    command = 'docker cp {}:{} {}'.format(container.name, path_in_container, extract_path)
    # print(command)
    os.system(command)


def get_diff(origin, now):
    d = difflib.Differ()
    diff = d.compare(origin.splitlines(), now.splitlines())
    result = '\n'.join(list(diff))
    print(result)
    return result