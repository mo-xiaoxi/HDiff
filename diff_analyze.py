import os
import copy
import re
import sys
import json
from src.parser import Rule
from src.util import read_json, save_json, get_all_files, get_status_code, easy_encode, easy_decode, get_diff
from config import RESULT_STAGE_1_DIR, RESULT_STAGE_2_DIR, DIRECT_RESULT_DIR, logger


def show_info(data, name):
    sentence = data['sentence']
    req = data['req']
    assertion = data['HMetrics']
    try:
        result = data['proxy_result']
    except Exception as e:
        result = data['server_result']
    print("*" * 100)
    print("name:\t{}".format(name))
    print("sentence:\t{}".format(sentence))
    print("assertion:\n{}".format(assertion))
    print("req:\n{}".format(req))
    print("proxy_result:\n{}".format(result[name]))
    get_diff(req, result[name]['proxy_send'])
    print("*" * 100)


def stage_1(single_file):
    """
    分析并统计 ALL_RESULTS_DIR 下的结果。
    payload_statistics 为以 payload(即 send 内容) 作为 key，
      且 value 形如 {'expected': "[['200',], ['200','400'], ...], '(200,400)': ['Nginx1_19_3', ...], ..."} 的统计信息
    :param filenames: 文件名列表，均为 ALL_RESULTS_DIR 下的文件名
    """

    file_names = get_all_files(RESULT_STAGE_1_DIR, ends='.json')
    for file_name in file_names:
        if single_file is not None and single_file not in file_name:
            continue
        logger.info("Analysis stage 1:{}".format(file_name))
        results = read_json(file_name)
        deviation = []
        risk_data = {}
        info = {}
        for i in results:
            data = results[i]
            sentence = data['sentence']
            req = data['req']
            assertion = data['HMetrics']
            proxy_result = data['proxy_result']
            for name in proxy_result:
                # 直接忽略proxy拒绝的数据包
                if 'proxy_send' not in proxy_result[name]:
                    logger.debug("{}\t{}\t{}\t".format("proxy send is none!!!", i, name, ))
                    continue
                proxy_send = proxy_result[name]['proxy_send']
                semantic = proxy_result[name]['semantic']
                # 暴力提取下状态码
                response = proxy_result[name]['response']
                if not response:
                    status_code = 'error'
                else:
                    status_code = response.split(' ')[1]

                if 'host' in semantic:
                    host = semantic['host']
                else:
                    logger.debug("{}\t{}\t{}\t".format("Host is none!!!", i, name))
                    host = ''
                flag = False
                if assertion['comment'] == 'example':
                    if str(status_code) != '200':
                        show_info(data, name)
                        flag = True
                # handle assertion 状态码断言
                if 'status_code' in assertion:
                    code = assertion['status_code']
                    if code[0] == '!':
                        code = code[1:]
                        if str(status_code) != str(code):
                            # logger.info('God Product! {}'.format(name))
                            pass
                        else:
                            flag = True
                            # show_info(data, name)
                    else:
                        codes = code.split('|')
                        if str(status_code) in codes:
                            # logger.info('God Product! {}'.format(name))
                            pass
                        else:
                            # print(status_code)
                            flag = True

                    # import string
                    # if test not in list(string.whitespace):
                    #     flag = False
                    # if test != ' ':
                    #     flag = False
                    # flag = False
                    # try:
                    #     test = proxy_send.split('\r\n')[1][0]
                    #     print(test)
                    #     if test in list(string.whitespace):
                    #         print(proxy_send.encode())
                    # except Exception as e:
                    #     # print(e)
                    #     pass
                    # flag = False
                    # if proxy_send and 'User-Agent: helloworld' in proxy_send:
                    #     test = req.split('User')[0].split('\r\n')[1]
                    #     if test in list(string.whitespace):
                    #         flag = True
                if assertion["comment"] == "CL-CL":
                    flag = False
                    if status_code == '200' and proxy_send:
                        flag = True
                        cl_count = proxy_send.lower().count('content-length')
                        if cl_count > 1:
                            # print(11)
                            flag = True
                        lines = proxy_send.split('\r\n')
                        for l in lines:
                            if 'content-length' in l.lower() and '40' in l.lower():
                                print(name, l.encode())

                # 对proxy转发的要求
                if 'proxy_version' in assertion:
                    if status_code == '200':
                        origin_version = req.split('idhere')[1].split('\r\n')[0]
                        version = proxy_send.split('idhere')[1].split('\r\n')[0]
                        if version != ' HTTP/1.1' and version != ' HTTP/1.0':
                            logger.warning(version)
                            flag = True
                            if name not in info:
                                info[name] = {}
                            if origin_version in info[name] and version not in info[name][origin_version]:
                                info[name][origin_version].append(version)
                            else:
                                info[name][origin_version] = [version]
                        # show_info(data,name)

                if flag == True:
                    logger.debug('RFC deviation: {}\t testid:{}'.format(name, i))
                    deviation.append(name)
                    if i not in risk_data:
                        tmp = copy.deepcopy(data)
                        tmp['proxy_result'] = {}
                        tmp['proxy_result'][name] = data['proxy_result'][name]
                        risk_data[i] = tmp
                    else:
                        risk_data[i]['proxy_result'][name] = data['proxy_result'][name]

        logger.warning(info)
        path = file_name.replace('.json', '.risk')
        save_json(risk_data, path)
        logger.warning(len(risk_data))
        deviation = list(set(deviation))
        logger.warning(deviation)


def special_char(filename):
    """
    分析并统计 ALL_RESULTS_DIR 下的结果。
    payload_statistics 为以 payload(即 send 内容) 作为 key，
      且 value 形如 {'expected': "[['200',], ['200','400'], ...], '(200,400)': ['Nginx1_19_3', ...], ..."} 的统计信息
    :param filenames: 文件名列表，均为 ALL_RESULTS_DIR 下的文件名
    """
    file_names = get_all_files(RESULT_STAGE_1_DIR, ends='.json')
    file_name = ''
    for file_name in file_names:
        if filename in file_name:
            break
    file_path = os.path.join(RESULT_STAGE_1_DIR, file_name)
    logger.info("Analysis special_char {}".format(file_path))
    results = read_json(file_path)
    risk_data = {}
    deviation = []
    for i in results:
        data = results[i]
        sentence = data['sentence']
        req = data['req']
        assertion = data['HMetrics']
        proxy_result = data['proxy_result']
        for name in proxy_result:
            semantic = proxy_result[name]['semantic']
            response = proxy_result[name]['response']
            if 'status_code' in semantic and semantic['status_code'] != '200':  # 不关心直接被proxy拒绝的请求
                continue
            if 'proxy_send' not in proxy_result[name]:
                # logger.warning('Proxy not send anything.')
                continue
            proxy_send = proxy_result[name]['proxy_send']
            flag = False
            if assertion['comment'] == 'special_byte_header':
                pattern = re.compile("(?P<before>.?)X-h(?P<between>.?)eader(?P<after>.?): X-value\r\n", re.I)
                if name not in risk_data:
                    risk_data[name] = {"before": [], "between": [], "after": []}
            elif assertion['comment'] == 'special_byte_uri_query':
                pattern = re.compile("quer(?P<query_key>.?)y=12(?P<query_value>.?)345", re.I)
                if name not in risk_data:
                    risk_data[name] = {"query_key": [], "query_value": []}
            elif assertion['comment'] == 'special_byte_uri_path':
                pattern = re.compile("index(?P<path>.?)php", re.I)
                if name not in risk_data:
                    risk_data[name] = {"path": []}
            elif assertion['comment'] == 'special_byte_value':
                # {'value': 'X-header:[]X-v[]alue[]\r\n', 'type': 'spchar'}
                pattern = re.compile("X-header:(?P<before>.?)X-v(?P<between>.?)alue(?P<after>.?)\r\n", re.I)
                if name not in risk_data:
                    risk_data[name] = {"before": [], "between": [], "after": []}
            else:
                pattern = re.compile(
                    '(?P<first>.?)Ho(?P<second>.?)st(?P<third>.?):(?P<fourth>.?)localhost(?P<fifth>.?)\r\n', re.I)

            match = pattern.search(proxy_send)
            if match is None:
                continue
            res = match.groupdict()
            for k, v in res.items():
                if v and v not in risk_data[name][k]:
                    risk_data[name][k].append(v)
    path = file_path.replace('stage_1', 'spchar')
    save_json(risk_data, path)
    logger.warning(risk_data)


def direct(filename):
    """
    分析并统计 ALL_RESULTS_DIR 下的结果。
    payload_statistics 为以 payload(即 send 内容) 作为 key，
      且 value 形如 {'expected': "[['200',], ['200','400'], ...], '(200,400)': ['Nginx1_19_3', ...], ..."} 的统计信息
    :param filenames: 文件名列表，均为 ALL_RESULTS_DIR 下的文件名
    """
    file_names = get_all_files(DIRECT_RESULT_DIR, ends='.json')
    file_path = filename

    for file_name in file_names:
        if filename is not None and filename in file_name:
            file_path = os.path.join(DIRECT_RESULT_DIR, file_name)
            break
    results = read_json(file_path)
    logger.info(file_path)
    deviation = []
    risk_data = {}
    info = {}
    for i in results:
        data = results[i]
        sentence = data['sentence']
        req = data['req']
        assertion = data['HMetrics']
        server_result = data['server_result']
        for name in server_result:
            semantic = server_result[name]['semantic']
            # 暴力提取下状态码
            response = server_result[name]['response']
            status_code = semantic['status_code'] if semantic else ''
            if status_code != '200':  # 不关心直接被proxy拒绝的请求
                continue
            flag = False
            if 'status_code' in assertion:
                code = assertion['status_code']
                if code[0] == '!':
                    code = code[1:]
                    if str(status_code) != str(code):
                        # logger.info('God Product! {}'.format(name))
                        pass
                    else:
                        flag = True
                else:
                    # print(code)
                    # print(status_code)
                    codes = status_code.split('|')
                    # print(codes)
                    if str(code) in codes:
                        # logger.info('God Product! {}'.format(name))
                        pass
                    else:
                        flag = True
                # flag = False
                # if 'Host' in req and str(status_code) == '200':
                #     import string
                #     test = req.split("Host:")[1].split('\r\n')[0]
                #     if test in list(string.whitespace):
                #         print(test)
                #         flag=True
                #         show_info(data, name)

            if assertion['comment'] == 'method_test':
                origin_method = req.split('/?testid=')[0].strip()
                if origin_method in """'GET'/'HEAD'/'POST'/'PUT'/'DELETE'/'CONNECT'/'OPTIONS'/'TRACE'/'PATCH'""":
                    continue
                if name not in info:
                    info[name] = []
                if origin_method not in info[name]:
                    info[name].append(origin_method)
                flag = True
            elif assertion['comment'] == 'special_byte_value':
                # TODO后面要分析一下 这些畸形的头部是怎么理解的
                flag = True
                # {'value': 'X-header:[]X-v[]alue[]\r\n', 'type': 'spchar'}
                pattern = re.compile("X-header:(?P<before>.?)X-v(?P<between>.?)alue(?P<after>.?)\r\n", re.I)
                if name not in info:
                    info[name] = {"before": [], "between": [], "after": []}
                match = pattern.search(req)
                if match is None:
                    continue
                res = match.groupdict()
                # print(res)
                for k, v in res.items():
                    if v and v not in info[name][k]:
                        info[name][k].append(v)
            elif assertion['comment'] == 'special_byte_header':
                pattern = re.compile("(?P<before>.?)X-h(?P<between>.?)eader(?P<after>.?): X-value\r\n", re.I)
                if name not in info:
                    info[name] = {"before": [], "between": [], "after": []}
                match = pattern.search(req)
                if match is None:
                    continue
                res = match.groupdict()
                print(res)
                for k, v in res.items():
                    if v and v not in info[name][k]:
                        info[name][k].append(v)
            elif assertion['comment'] == 'common_repeat_host':
                print(name)
                print(req)
                print(semantic)
                flag = True
            elif assertion['comment'] == 'repeat_host':
                if semantic and semantic['Host'] and 'localhost' in semantic['Host']:
                    # print(semantic)
                    if name not in info:
                        info[name] = {"first": [], "second": [], "third": [], "fourth": [], "fifth": []}
                    pattern = re.compile(
                        '(?P<first>.?)Ho(?P<second>.?)st(?P<third>.?):(?P<fourth>.?)localhost(?P<fifth>.?)\r\n', re.I)

                    match = pattern.search(req)
                    if match is None:
                        continue
                    res = match.groupdict()
                    if res['fifth'] == '-':
                        print(name)
                        print(req.encode())
                        print(semantic['Host'])
                    for k, v in res.items():
                        if v and v not in info[name][k]:
                            info[name][k].append(v)
                    flag = True
                # if semantic['Host'] and '127.0.0.1' not in semantic['Host'] and '202.112.51.130' not in semantic['Host'] and '101.35.109.235' not in semantic['Host']:
                #     print(name)
                #     print(req.encode())
                #     print(semantic)
                #     flag=True
            elif assertion['comment'] == 'repeat_content_length':
                if 'test=123456789' not in response and 'test=1' in response:
                    print(req, response)
            if flag:
                # 初始化i进入risk_data
                if i not in risk_data:
                    tmp = copy.deepcopy(data)
                    tmp['server_result'] = {}
                    tmp['server_result'][name] = data['server_result'][name]
                    risk_data[i] = tmp
                else:
                    risk_data[i]['server_result'][name] = data['server_result'][name]
                deviation.append(name)

    path = file_path.replace('.json', '.risk')
    save_json(risk_data, path)
    deviation = list(set(deviation))
    logger.error(deviation)
    # for i in info:
    #     info[i] = list(set(info[i]))
    path = path.replace('.risk', '.info')
    save_json(info, path)


def analyze_proxy(filename):
    """
    分析并统计 ALL_RESULTS_DIR 下的结果。
    payload_statistics 为以 payload(即 send 内容) 作为 key，
      且 value 形如 {'expected': "[['200',], ['200','400'], ...], '(200,400)': ['Nginx1_19_3', ...], ..."} 的统计信息
    :param filenames: 文件名列表，均为 ALL_RESULTS_DIR 下的文件名
    """
    file_names = get_all_files(RESULT_STAGE_1_DIR, ends='.json')
    file_path = filename
    for file_name in file_names:
        if filename is not None and filename in file_name:
            file_path = os.path.join(RESULT_STAGE_1_DIR, file_name)
            break
    results = read_json(file_path)
    deviation = []
    risk_data = {}
    info = {}
    test = {}
    for i in results:
        data = results[i]
        sentence = data['sentence']
        req = data['req']
        assertion = data['HMetrics']
        proxy_result = data['proxy_result']
        for name in proxy_result:
            semantic = proxy_result[name]['semantic']
            # 暴力提取下状态码
            response = proxy_result[name]['response']
            if response is None:
                status_code = 'error'
            else:
                status_code = response.split(' ')[1]
            if 'host' in semantic:
                host = semantic['host']
            else:
                host = ''
            if 'status_code' in semantic and semantic['status_code'] != '200':  # 不关心直接被proxy拒绝的请求
                continue
            if 'proxy_send' not in proxy_result[name]:
                # logger.warning('Proxy not send anything.')
                continue
            proxy_send = proxy_result[name]['proxy_send']
            flag = False
            if 'host' in assertion:
                assertion['comment'] = assertion['host']
            if assertion['comment'] == 'repeat_host':
                # []Ho[]st[]:[]localhost[]\r\n
                if 'localhost' not in proxy_send:
                    continue
                if '127.0.0.1' not in proxy_send and 'echo' not in proxy_send:
                    continue
                if name not in info:
                    info[name] = {"first": [], "second": [], "third": [], "fourth": [], "fifth": []}
                pattern = re.compile(
                    '(?P<first>.?)Ho(?P<second>.?)st(?P<third>.?):(?P<fourth>.?)localhost(?P<fifth>.?)\r\n', re.I)

                match = pattern.search(proxy_send)
                if match is None:
                    continue
                flag = True
                res = match.groupdict()
                # key = 'fifth'
                # if len(res[key]):# and 'localhost' not in semantic['host'] :
                #     # print(name)
                #     # print(req.encode())
                #     # print(proxy_send.encode())
                #     if res[key] not in test:
                #         test[res[key]] =[]
                #     host = semantic['host'] if 'host' in semantic else ''
                #     host = host.split('/?testid')[0]
                #     if host not in test[res[key]]:
                #         test[res[key]].append(host)
                key = 'fifth'
                if True:
                    if res[key] not in test:
                        test[res[key]] = []
                    host = semantic['host'] if 'host' in semantic else ''
                    host = host.split('/?testid')[0]
                    if '127.0.0.1' in host and 'localhost' in proxy_send:
                        print(host)
                        print(name)
                        print(req.encode())
                        print(proxy_send.encode())

                for k, v in res.items():
                    if v and v not in info[name][k]:
                        info[name][k].append(v)

            elif assertion['comment'] == 'method_test':
                origin_method = req.split('/?testid=')[0].strip()
                method = proxy_send.split('/?testid=')[0].strip()
                if name not in info:
                    info[name] = []
                if method not in """'GET'/'HEAD'/'POST'/'PUT'/'DELETE'/'CONNECT'/'OPTIONS'/'TRACE'/'PATCH'""":
                    if method not in info[name]:
                        info[name].append(method)
                    flag = True
                elif origin_method != method:
                    print(name, origin_method, method)
                    flag = True
            elif assertion['comment'] == 'common_repeat_host':
                # print(name)
                print(req)
                print(proxy_send)
                pattern = re.compile('.?Host.?:.*', re.I)
                host = pattern.findall(proxy_send)
                proxy_host = proxy_result[name]["semantic"]["host"]
                print(host, proxy_host)
                flag = True
            elif assertion['comment'] == 'absolute_uri_host':
                pattern = re.compile('.?Host.?:.*', re.I)
                host = pattern.findall(proxy_send)
                forwarded_host_count = proxy_send.count('X-Forwarded-Host:')
                if len(host) > 1 + forwarded_host_count:
                    # 发出多个host，这里排除一下X-Forwarded-Host 字段
                    # 发出两个host包
                    # print(req)
                    # print(proxy_send)
                    # print(name, i)
                    # flag = True
                    pass
                elif forwarded_host_count > 0 and len(host) > 0:
                    # X-forwarder-Host 歧义, 同时具有host和X-forwarder-Host
                    # flag = True
                    # print(req)
                    # print(proxy_send)
                    # print(name, i)
                    pass
                # TODO X-forwarder-Host 歧义 直接构造X-forwarder-Host字段
                elif len(proxy_send.split(' ')[1].split('/?id')[0]):
                    # uri没有替换，直接发送。可能造成后端歧义
                    # print(proxy_send.encode())
                    # # print(req)
                    # print(name, i)
                    # proxy_host = proxy_result[name]["semantic"]["host"]
                    # print(proxy_host)
                    flag = True
                else:
                    pass
                    # # 发出的host header 字段内容非法
                    # pattern = re.compile('.*Host.?:.*', re.I)
                    # cc = pattern.findall(proxy_send)
                    # for c in cc:
                    #     c = c.rstrip('\r')
                    #     node, start = Rule('host-header').parse(c)
                    #     if start < len(c):
                    #         # print(c)
                    #         print(req)
                    #         print(proxy_send)
                    #         print(name, i)
                    #         flag = True
            elif assertion['comment'] == 'repeat_content_length':
                ct = 'Content-Length'.lower()
                c = proxy_send.lower().count(ct)
                if c > 1:
                    flag = True
                    print(name, proxy_send)

            else:
                logger.error('Not found comment:{}'.format(assertion['comment']))
            if flag:
                # logger.warning('Host Of Troubles! {}\t testid:\t{}'.format(name, i))
                # print(proxy_send)
                # 初始化i进入risk_data
                if i not in risk_data:
                    tmp = copy.deepcopy(data)
                    tmp['proxy_result'] = {}
                    tmp['proxy_result'][name] = data['proxy_result'][name]
                    risk_data[i] = tmp
                else:
                    risk_data[i]['proxy_result'][name] = data['proxy_result'][name]
                deviation.append(name)
    print(test)
    path = file_path.replace('.json', '.risk')
    save_json(risk_data, path)
    deviation = list(set(deviation))
    logger.warning(deviation)
    # for i in info:
    #     info[i] = list(set(info[i]))
    path = path.replace('.risk', '.info')
    save_json(info, path)


# 分析host of troubles问题
def host_of_troubles_1(filename):
    """
    分析并统计 ALL_RESULTS_DIR 下的结果。
    payload_statistics 为以 payload(即 send 内容) 作为 key，
      且 value 形如 {'expected': "[['200',], ['200','400'], ...], '(200,400)': ['Nginx1_19_3', ...], ..."} 的统计信息
    :param filenames: 文件名列表，均为 ALL_RESULTS_DIR 下的文件名
    """
    file_names = get_all_files(RESULT_STAGE_1_DIR, ends='.json')
    file_path = filename
    for file_name in file_names:
        if filename is not None and filename in file_name:
            file_path = os.path.join(RESULT_STAGE_1_DIR, file_name)
            break
    # file_path = os.path.join(RESULT_STAGE_1_DIR, filename)
    results = read_json(file_path)
    risk_data = {}
    deviation = []
    grammar = """
            host-header = "Host" ":" [ SP ] host [ SP ]
            host = uri-host [ ":" port ]
            port = *DIGIT
            uri-host = 1*token
            token = DIGIT / ALPHA
            OWS = *( SP / HTAB )
            """
    Rule.from_txt(grammar)
    for i in results:
        data = results[i]
        sentence = data['sentence']
        req = data['req']
        assertion = data['HMetrics']
        proxy_result = data['proxy_result']
        for name in proxy_result:
            semantic = proxy_result[name]['semantic']
            response = proxy_result[name]['response']
            if 'status_code' in semantic and semantic['status_code'] != '200':  # 不关心直接被proxy拒绝的请求
                continue
            if 'proxy_send' not in proxy_result[name]:
                # logger.warning('Proxy not send anything.')
                continue
            proxy_send = proxy_result[name]['proxy_send']
            flag = False
            pattern = re.compile('.?Host.?:.*', re.I)
            host = pattern.findall(proxy_send)
            forwarded_host_count = proxy_send.count('X-Forwarded-Host:')
            if assertion['host'] == 'absolute_uri_host' or assertion['host'] == 'X-Forwarded-Host':
                if len(host) > 1 + forwarded_host_count:
                    # 发出多个host，这里排除一下X-Forwarded-Host 字段
                    # 发出两个host包
                    # print(req)
                    # print(proxy_send)
                    # print(name, i)
                    # flag = True
                    pass
                elif forwarded_host_count > 0 and len(host) > 0:
                    # X-forwarder-Host 歧义, 同时具有host和X-forwarder-Host
                    # flag = True
                    # print(req)
                    # print(proxy_send)
                    # print(name, i)
                    pass
                # TODO X-forwarder-Host 歧义 直接构造X-forwarder-Host字段
                elif len(proxy_send.split(' ')[1].split('/?id')[0]):
                    # uri没有替换，直接发送。可能造成后端歧义
                    # print(proxy_send)
                    # print(req)
                    # print(name, i)
                    flag = True
                else:
                    # 发出的host header 字段内容非法
                    pattern = re.compile('.*Host.?:.*', re.I)
                    cc = pattern.findall(proxy_send)
                    for c in cc:
                        c = c.rstrip('\r')
                        node, start = Rule('host-header').parse(c)
                        if start < len(c):
                            # print(c)
                            print(req)
                            print(proxy_send)
                            print(name, i)
                            flag = True

            elif assertion['host'] == 'repeat_host':
                if 'localhost' in proxy_send:
                    pass
                    flag = True
                else:
                    # print(proxy_send)
                    pass
            else:
                raise

            if flag:
                # logger.warning('Host Of Troubles! {}\t testid:\t{}'.format(name, i))
                # print(proxy_send)
                # 初始化i进入risk_data
                if i not in risk_data:
                    tmp = copy.deepcopy(data)
                    tmp['proxy_result'] = {}
                    tmp['proxy_result'][name] = data['proxy_result'][name]
                    risk_data[i] = tmp
                else:
                    risk_data[i]['proxy_result'][name] = data['proxy_result'][name]
                deviation.append(name)
    path = file_path.replace('.json', '.risk')
    save_json(risk_data, path)
    deviation = list(set(deviation))
    logger.error(deviation)


# 分析host of troubles 第二阶段
def host_of_troubles_2(filename):
    """
    """
    file_path = os.path.join(RESULT_STAGE_2_DIR, filename)
    results = read_json(file_path)
    risk_data = {}
    deviation = []
    for i in results:
        data = results[i]
        sentence = data['sentence']
        req = data['req']
        assertion = data['HMetrics']
        proxy_result = data['proxy_result']
        replay_result = data['replay_result']
        for server in replay_result:
            d = replay_result[server]

            for proxy in d:
                # 忽略没有测试的
                if d[proxy] is None:
                    continue
                # TODO 有些服务器直接没有返回
                if d[proxy] == '':
                    continue
                status_code = d[proxy].split(' ')[1]
                if status_code != '200':
                    continue
                response_data = d[proxy].split('\r\n\r\n')[1]
                response_data = response_data[response_data.find("{"):response_data.find("}") + 1]
                # TODO 有些服务器直接没有返回data字段
                if response_data == '':
                    continue
                response_data = json.loads(response_data)
                uri = response_data['URI']
                host = response_data['Host']
                print(proxy_result)
                proxy_host = proxy_result[proxy]["semantic"]["host"]
                # TODO 这里暴力排除目标理解成echo-server. 这会造成漏报
                if proxy_host != host and host != 'echo-server:8001':
                    logger.debug("{}\t{}\t{}\t{}\t{}".format(proxy, server, status_code, host, proxy_host))
                    print(req)
                    print(proxy_result[proxy]['proxy_send'])
                    if i not in risk_data:
                        tmp = copy.deepcopy(data)
                        tmp['replay_result'] = {}
                        tmp['replay_result'][server] = data['replay_result'][server]
                        risk_data[i] = tmp
                    else:
                        risk_data[i]['replay_result'][server] = data['replay_result'][server]
                    deviation.append((proxy, server))
    path = file_path.replace('.risk', '.result')
    save_json(risk_data, path)
    deviation = list(set(deviation))
    logger.error(deviation)

# 通过输入参数来调试对应的函数
def run():
    # exmaple: python diff_analyze.py example
    func = sys.argv[1]
    filename = "{}".format(sys.argv[2])
    logger.info('Call Func: {} filename:{}'.format(func, filename))
    eval(func)(filename)


if __name__ == '__main__':
    run()
