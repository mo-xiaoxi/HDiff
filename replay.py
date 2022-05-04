import os
import json
import docker
from config import CONFIG_PATH, REPLAY_LOGS_DIR, logger
from src.util import read_json, send, extract_proxy_send, easy_encode, easy_decode, get_status_code, extract_testid, \
    get_container_by_name, extract_container_file, get_diff

# origin_payload = """\
# POST /index.html HTTP/1.1
# Host: abc.com
# Content-Length0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:
# Content-Length: 60

# GET /admin/add_user.py HTTP/1.1
# Host: abc.com
# abc: xyz
# """.replace('\n','\r\n')

# origin_payload = """\
# POST / HTTP/1.1
# Host: 127.0.0.1:8004
# Connection: close
# Transfer-Encoding: chunked

# 3
# abc
# 0

# """.replace('\n','\r\n')
# origin_payload = """\
# POST / HTTP/1.1
# Host: localhost
# Connection: close
# Content-Length: 3,4

# abc

# """.replace('\n','\r\n')
# origin_payload = """\
# POST /?id=testid8605229791513179idhere HTTP/1.1
# Host: localhost
# Connection: close
# Expect: 100-continue
# Content-Length: 5
# Transfer-Encoding: chunked

# 1E
# 4c
# 0

# GET /admin HTTP/1.1
# """.replace('\n','\r\n').replace('localhost','127.0.0.1:8004')
# origin_payload = """\
# POST /?id=testid8605429794523179idhere HTTP/1.1
# Host: localhost
# Transfer-Encoding: chunked

# 000000000000000000000000000ffffffffffffff
# abc
# 0

# """.replace('\n','\r\n').replace('localhost','127.0.0.1:8004')
# origin_payload = """\
# GET /?id=testid8605429794523179idhere HTTP/1.1
# Host: localhost
# Transfer-Encoding: chunked
# Transfer-encoding: identity

# 7;\nxx
# 4c
# 0

# GET /admin HTTP/1.1

# """.replace('\n','\r\n').replace('localhost','127.0.0.1:8004').replace('\r\nxx','\nxx')

# origin_payload = "GET /?id=testid8605429794523178idhere HTTP/0.9\r\nHost: 127.0.0.1:8004\r\nConnection:close\r\n\r\n"
# origin_payload = 'GET /?id=testid8214637024359612idhere HTTP/1.1\r\nHost: h1.com\r\nTrailer: Set-Cookie\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\nConnection: keep-alive\r\n\r\n7\r\nMozilla\r\n0\r\nSet-Cookie: moxiaoxi.com\r\n\r\n'

# origin_payload = """\
# GET /?testid=testid791850644655298idhere HTTP/0.9
# Host: {host}
# Content-Length: 6
# Connection:close

# test=1
# """.replace('{host}','127.0.0.1:8004').replace('\n','\r\n')

origin_payload = """\
POST /?testid=testid791850644655298idhere HTTP/1.0
Host: {host}
Content-Length: 6
Connection:close
Transfer-Encoding: chunked

3
abc
0

""".replace('{host}', '127.0.0.1:8004').replace('\n', '\r\n')

# origin_payload = """\
# POST /?testid=testid791850644655298idhere HTTP/1.0
# Host: {host}
# Content-Length: 6
# Connection: Transfer-Encoding
# Transfer-Encoding: chunked

# 3
# abc
# 0

# """.replace('{host}','127.0.0.1:8004').replace('\n','\r\n')

# origin_payload = """\
# GET /?testid=testid791850644655298idhere HTTP/1.0
# Host: {host}
# Content-length: 5
# Transfer-Encoding: chunked

# 3
# abc
# 0

# """.replace('{host}','127.0.0.1:8004').replace('\n','\r\n')

default_host = '127.0.0.1'


def get_line_in_file(filepath, testid):
    """
    倒序获得文件中首次包含某 test 的一行
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()
        for line in reversed(lines):
            if line.find('testid%sidhere' % testid) != -1:
                return line.strip()
    return None


def proxy(payload):
    conf = read_json(CONFIG_PATH)
    os.makedirs(REPLAY_LOGS_DIR, exist_ok=True)
    targets = conf['proxy_targets']
    proxys = {}
    cli = docker.from_env()
    prefix = conf['proxy_prefix']
    testid = extract_testid(payload)
    for i in targets:
        targets[i].setdefault('host', default_host)
        port = targets[i]['port']
        host = targets[i]['host']
        host_string = '{}:{}'.format(host, port)
        data_send = payload.replace('{host}', host_string)
        res = send(host, port, easy_encode(data_send))
        data = easy_decode(res)
        proxy_send = extract_proxy_send(data)

        targets[i].setdefault('log_container_name', i)
        log_container = get_container_by_name(cli, prefix, targets[i]['log_container_name'])
        proxy_log_path = targets[i]['log_path']
        outside_proxy_log_path = os.path.join(REPLAY_LOGS_DIR, i + '.log')
        extract_container_file(log_container, proxy_log_path, outside_proxy_log_path)
        outside_echo_log_path = os.path.join(REPLAY_LOGS_DIR, i + '_echo.log')
        echo_container = get_container_by_name(cli, prefix, targets[i]["echo_container_name"])
        echo_log_path = targets[i]["echo_log_path"]
        extract_container_file(echo_container, echo_log_path, outside_echo_log_path)
        echo_log_line = get_line_in_file(outside_echo_log_path, testid)
        proxy_log_line = get_line_in_file(outside_proxy_log_path, testid)
        semantic_host = proxy_log_line.split('"')[1] if proxy_log_line else ''
        if len(semantic_host) == 0 or semantic_host[0] == '-':
            semantic_host = ""
        elif semantic_host[0] == '{':
            semantic_host = semantic_host[1:-1]
        print("*" * 100)
        print("Proxy Name:", i)
        print('\necho_log_line:', echo_log_line)  # echo 日志中对应一行
        print('\nproxy_log_line:', proxy_log_line)  # proxy 日志中对应的一行
        print('\nsemantic_host:', semantic_host)  # 从 proxy 日志提取的 host
        print("*" * 100)

        status_code = get_status_code(data)
        origin_method = data_send.split('/?testid=')[0].strip()
        try:
            version = proxy_send.split('HTTP/')[1].split('\r\n')[0]
            method = proxy_send.split(' ')[0].strip()
        except Exception as e:
            version = ''
            method = ''
        # logger.debug("{}\t{}\t{}\t{}\t{}".format(i, status_code, version, host, port))
        proxys[i] = [
            status_code, version, origin_method, method
        ]
        # if i =='2':
        #     logger.warning("DATA SEND:")
        #     print(data_send)
        #     logger.warning("DATA RECV:")
        #     print(data)
        #     logger.warning("Proxy Send:")
        #     print(proxy_send)

        # if proxy_send is not None and 'h1.cn' in proxy_send and 'h2.cn' in proxy_send:
        #     flag = True
        #     for l in proxy_send.splitlines():
        #         if '.cn' in l and ('X-Forwarded-For'.lower() in l.lower() or 'X-Forwarded-Host'.lower() in l.lower()):
        #             flag = False
        #             break
        #     if flag:
        #         logger.warning("Diff {}".format(i))
        #         get_diff(data_send, proxy_send)
        if proxy_send is not None:
            logger.warning("Diff {}".format(i))
            get_diff(data_send, proxy_send)
    for i in proxys:
        print("{} {}({})".format(i, proxys[i][0], proxys[i][3]))
    # print("{}({})\t{}({})\t{}({})\t{}({})\t{}({})\t{}({})\t".format(proxys['apache'][0], proxys['apache'][1],
    #                                                                         proxys['nginx'][0], proxys['nginx'][1],
    #                                                                         proxys['apache_traffic_server'][0],proxys['apache_traffic_server'][1],
    #                                                                         proxys['squid'][0],proxys['squid'][1],
    #                                                                         proxys['haproxy'][0],proxys['haproxy'][1],
    #                                                                         proxys['varnish'][0],proxys['varnish'][1],
    #                                                                         ))


def server(payload):
    conf = read_json(CONFIG_PATH)
    targets = conf['server_targets']
    servers = {}
    for i in targets:
        targets[i].setdefault('host', default_host)
        port = targets[i]['port']
        host = targets[i]['host']
        host_string = '{}:{}'.format(host, port)
        data_send = easy_encode(payload.replace('{host}', host_string))
        res = send(host, port, data_send)
        data = easy_decode(res)
        status_code = get_status_code(data)
        try:
            version = data.split('HTTP/')[1].split(' ')[0]
        except Exception as e:
            version = ''

        # logger.debug("{}\t{}\t{}\t{}\t{}".format(i, status_code, version, host, port))
        uri = ''
        host = ''
        if status_code == "200":
            logger.warning(i)
            # print(i)
            # logger.error("ERROR? ")
            # logger.warning("DATA SEND:")
            # print(payload)
            logger.warning("DATA RECV:")
            print(data)
            response_data = data.split('\r\n\r\n')[1]
            response_data = response_data[response_data.find("{"):response_data.find("}") + 1]
            # TODO 有些服务器直接没有返回data字段
            try:
                response_data = json.loads(response_data)
                uri = response_data['URI']
                host = response_data['Host']
            except Exception as e:
                logger.error(e)
        elif status_code == '302':
            print(data)
        else:
            # print(i,data)
            pass
        servers[i] = [
            status_code, version, uri, host
        ]
    for i in servers:
        print("{} {}({})".format(i, servers[i][0], servers[i][3]))


if __name__ == '__main__':
    payload = origin_payload
    proxy(payload)
    server(payload)
