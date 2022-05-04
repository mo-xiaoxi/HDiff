"""
检测目标环境是否正常
"""
from src.util import read_json, send, extract_proxy_send
from config import CONFIG_PATH, logger
# import HackRequests


payload = "POST /?testid=testid0569314796802745idhere HTTP/1.1\r\nHost: {host}\r\nConnection:close\r\nX-Basic-ID: 85a058c56554d9a780457a1043af6683\r\nContent-Length: 6\r\n\r\ntest=1"
default_host = '127.0.0.1'


def run():
    conf = read_json(CONFIG_PATH)
    targets = conf['proxy_targets']
    for i in targets:
        targets[i].setdefault('host', default_host)
        port = targets[i]['port']
        host = targets[i]['host']
        host_string = '{}:{}'.format(host, port)
        data_send = payload.replace('{host}', host_string).encode('latin-1')
        try:
            res = send(host, port, data_send)
        except Exception as e:
            logger.error(e)
            logger.warning("host:{}\tport:{}\t".format(host, port))
            continue
        data = res.decode('latin-1')
        proxy_send = extract_proxy_send(data)
        status_code = data.split(' ')[1]
        version = data.split(' ')[0]
        logger.info("{}\t{}\t{}\t{}\t{}".format(i, status_code, version, host, port))
        # print(proxy_send)
        if status_code != "200":
            logger.error("ERROR? ")
            logger.warning("DATA SEND:")
            print(data_send)
            logger.warning("DATA RECV:")
            print(data)
            logger.warning("Proxy Send:")
            print(proxy_send)
    targets = conf['server_targets']
    for i in targets:
        targets[i].setdefault('host', default_host)
        port = targets[i]['port']
        host = targets[i]['host']
        host_string = '{}:{}'.format(host, port)
        data_send = payload.replace('{host}', host_string).encode('latin-1')
        try:
            res = send(host, port, data_send)
        except Exception as e:
            print(e)
            print("host:{}\tport:{}\t".format(host, port))
            continue
        data = res.decode('latin-1')
        status_code = data.split(' ')[1]
        version = data.split(' ')[0]
        logger.info("{}\t{}\t{}\t{}\t{}".format(i, status_code, version, host, port))
        if status_code != "200":
            logger.error("ERROR? ")
            logger.warning("DATA SEND:")
            print(payload)
            logger.warning("DATA RECV:")
            print(data)


if __name__ == '__main__':
    run()
