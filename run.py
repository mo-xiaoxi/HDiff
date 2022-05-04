import os
import sys
import copy
import json
import shutil
import tarfile
import platform
from multiprocessing import Pool
import threading
import ast
import docker
import traceback
from config import logger
from src.util import send, merge_dict, read_json, save_json, get_all_files, extract_proxy_send, extract_testid, \
    get_status_code, easy_encode, easy_decode, extract_response_data, get_container_by_name, extract_container_file
from config import CONFIG_PATH, PAYLOAD_DIR, RESULT_LOGS_DIR, RESULT_STAGE_1_DIR, \
    RESULT_STAGE_2_DIR, TMP_TAR_PATH, TMP_DIR, PROGRESS_INTERVAL, PROXY_PROCESSES, \
    DIRECT_RESULT_DIR, DATA_NUM_WHEN_TRY, SINGLE_SERVER_PAYLOAD_NUMS, SERVER_PROCESSES


def error_callback(e):
    """ 发生 error 时的 callback """
    logger.error(e)
    traceback.print_exc()


def run_single(key, host, port, data_send_list, use_ssl=False, client_wait_time=0.5, recv_buf_size=4096):
    """ 多进程测试调用的单次函数，将对单个 (host, port) 进行测试
    :param key: str, 测试结果将放入 global_results[key] 中，且格式为 {<key>: {<testid>: <res>, ...}, ...}，这里取 key 为 container_name
    :param host: str, 目标主机
    :param port: int, 目标端口
    :param data_send_list: list, 要发送的数据列表，每一项为 bytes
    :param use_ssl: bool, 是否使用 SSL
    :param client_wait_time: float, 客户端发包后等待时间（单位为秒）
    :param recv_buf_size: int, 接收响应时的 buffer 大小，即最多接收字节数
    :return ret: dict, 返回形如 {<testid>: <res>, ...} 的格式
    """
    ret = {}
    cnt = 0
    for data_send in data_send_list:
        if cnt % PROGRESS_INTERVAL == 0:
            logger.info('%s: %d/%d %.4f%%' % (key, cnt, len(data_send_list), cnt / len(data_send_list) * 100))

        testid = extract_testid(easy_decode(data_send))
        assert testid is not None, 'testid for "%s" is None' % easy_decode(data_send)
        host_string = "{}:{}".format(host, port)
        data_send = data_send.replace(b'{host}', easy_encode(host_string))
        res = send(host, port, data_send, use_ssl, client_wait_time, recv_buf_size)
        ret[testid] = res
        cnt += 1
    logger.info('%s: %d/%d %.4f%%' % (key, len(data_send_list), len(data_send_list), 100))
    return key, ret


def post_run_single(ret):
    """
    run_single 完毕之后调用的 callback 函数，用于对结果进行存储和分析等，加上了 try-except 用于显示异常
    :param ret: tuple, 包含 testid (str 类型) 表示测试包的 id，以及 res (bytes 类型) 表示返回包
    """
    try:
        key, ret = ret
        global global_results, global_lock
        with global_lock:
            global_results[key] = ret

    except Exception as e:
        logger.error('Exception in post_test_target: %s' % e.__str__())


def get_proxy_targets(cli, conf):
    """
    根据配置文件和目前的容器生成 stage 1 所需要的 targets，注意 stage 2 并不需要从容器中提取 log，所以不需要此操作
    :param cli: docker client 对象
    :param conf: dict，载入的配置文件
    :return: targets: 返回配置文件对应的 targets，并向每个 target 中添加了运行主要 proxy 的 main_container 和存放 log 的 log_container
    """
    prefix = conf['proxy_prefix']
    targets = {}
    for name, target in conf['proxy_targets'].items():
        main_container = get_container_by_name(cli, prefix, name)
        log_container = main_container
        if target.get('log_container_name') is not None:
            log_container = get_container_by_name(cli, prefix, target['log_container_name'])
        targets[name] = target
        targets[name]['main_container'] = main_container
        targets[name]['log_container'] = log_container
    return targets



def stage_1(single_file=None, is_try=False):
    """
    stage 1 的主要工作代码，用于测试 proxy，记录 response 和容器 log 中的 host 语义，并将结果输出到 RESULT_STAGE_1_DIR 目录下，与数据文件同名，输出格式参考：
    :param is_try: boolean，是否仅尝试一下测试，为 True 时将只会测试开头的部分数据
    """
    host = "127.0.0.1"

    # 读入配置文件
    cli = docker.from_env()
    conf = read_json(CONFIG_PATH)
    targets = get_proxy_targets(cli, conf)
    logger.debug('targets: ' + str(targets))
    proxy_prefix = conf['proxy_prefix']

    # 创建结果文件夹
    os.makedirs(RESULT_LOGS_DIR, exist_ok=True)
    os.makedirs(RESULT_STAGE_1_DIR, exist_ok=True)

    file_names = get_all_files(PAYLOAD_DIR, ends='.json')
    for file_name in file_names:
        if single_file is not None and single_file not in file_name:
            continue
        data = read_json(file_name)
        logger.info('Stage 1: %s' % file_name)
        sentence = data['sentence']
        payloads = list(map(lambda x: easy_encode(x), data['reqs']))
        assertion = data['assertion']

        result_path = file_name.replace('payload', 'result/stage_1')
        # 临时存储进度，用于进度恢复
        # tmp_path = result_path.replace(".json", '.tmp1').replace('stage_1', 'tmp')
        # 初始化 result 字典
        # result = read_json(tmp_path)
        result = {}
        for payload in payloads:
            testid = extract_testid(easy_decode(payload))
            assert testid is not None
            if testid not in result:
                result[testid] = {'sentence': sentence, 'req': easy_decode(payload), 'assertion': assertion,
                                  'proxy_result': {}}
                for container_name, target in targets.items():
                    result[testid]['proxy_result'][container_name] = {'response': None, 'semantic': {}}

        logger.info('Testing payload file %s' % file_name)
        # 枚举所有 target，多进程测试
        with Pool(processes=PROXY_PROCESSES) as pool:
            global global_results, global_lock
            global_results = {}
            global_lock = threading.Lock()

            # 清空容器内日志，并用每个容器作为一个进程进行测试
            for container_name, target in targets.items():
                port = target['port']
                log_path = target['log_path']
                main_container = target['main_container']
                log_container = target['log_container']
                echo_server_name = target['echo_container_name']
                echo_container = get_container_by_name(cli, proxy_prefix, echo_server_name)
                echo_log_path = target['echo_log_path']

                log_container.exec_run('truncate -s 0 ' + log_path)
                logger.info('%s: Truncated the log file in container' % container_name)
                echo_container.exec_run('truncate -s 0 ' + echo_log_path)
                logger.info('%s: Truncated the log file in container' % echo_server_name)

                tested_payloads = payloads

                if is_try:
                    logger.warning('You are testing using is_try on, this program will not test all the payloads.')
                    tested_payloads = tested_payloads[:DATA_NUM_WHEN_TRY]

                pool.apply_async(run_single, (container_name, host, port, tested_payloads), error_callback=error_callback, callback=post_run_single)

            pool.close()
            pool.join()

        logger.info('Done test for payload file %s, extracting logs and generating stage 1 result' % file_name)

        for container_name, target in targets.items():
            port = target['port']
            log_path = target['log_path']
            main_container = target['main_container']
            log_container = target['log_container']
            echo_server_name = target['echo_container_name']
            echo_container = get_container_by_name(cli, proxy_prefix, echo_server_name)
            echo_log_path = target['echo_log_path']

            # 提取容器 log 文件
            outside_log_path = os.path.join(RESULT_LOGS_DIR, container_name + '.log')
            extract_container_file(log_container, log_path, outside_log_path)
            outside_echo_log_path = os.path.join(RESULT_LOGS_DIR, container_name + '_echo.log')
            extract_container_file(echo_container, echo_log_path, outside_echo_log_path)

            # 合并容器 log 到 result 中
            with open(outside_log_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    testid = extract_testid(line)
                    if testid is None:
                        continue
                    semantic_host = line.split('"')[1]
                    if len(semantic_host) == 0 or semantic_host[0] == '-':
                        semantic_host = ""
                    elif semantic_host[0] == '{':
                        semantic_host = semantic_host[1:-1]
                    result[testid]['proxy_result'][container_name]['semantic']['host'] = semantic_host
            # 合并 echo log 到 result 中
            with open(outside_echo_log_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = easy_decode(ast.literal_eval(line))
                    testid = extract_testid(line)
                    try:
                        result[testid]['proxy_result'][container_name]['response'] = line
                        result[testid]['proxy_result'][container_name]['proxy_send'] = extract_proxy_send(line)
                        status_code = line.split(' ')[1]
                        result[testid]['proxy_result'][container_name]['semantic']["status_code"] = status_code
                    except Exception as e:
                        logger.error(e)
                        logger.error("{}\t{}".format(container_name, testid))
                        logger.error(line)
                        continue

        save_json(result, result_path)
        logger.warning("A file was done, outpath:{}".format(result_path))


def stage_2(single_file=None, is_try=False):
    """
    stage 2 的主要工作代码，用于读入 stage 1 得到的输出，将其中的 json 文件补充上重放的结果以及直接发送 payload 的结果后，
    输出到 RESULT_STAGE_2_DIR 目录下，与 stage 1 输出文件同名。输出格式参考：

    :param is_try: boolean，是否仅尝试一下测试，为 True 时将只会测试开头的部分数据
    """
    # 读入配置文件
    conf = read_json(CONFIG_PATH)
    server_targets = conf['server_targets']
    proxy_targets = conf['proxy_targets']
    logger.info('conf: ' + str(server_targets))

    # 创建结果文件夹
    os.makedirs(RESULT_LOGS_DIR, exist_ok=True)
    os.makedirs(RESULT_STAGE_2_DIR, exist_ok=True)
    file_names = get_all_files(RESULT_STAGE_1_DIR, ends='.json')
    for file_name in file_names:
        if single_file is not None and single_file not in file_name:
            continue
        # 读入 stage 1 JSON 文件，并在此基础上修改得到结果
        result = read_json(file_name)
        result_path = file_name.replace('stage_1', 'stage_2')
        logger.info('Stage 2: %s' % file_name)

        # 初始化 replay_result
        for testid in result.keys():
            result[testid]['replay_result'] = {server_name: {proxy_name: None for proxy_name in conf['proxy_targets'].keys()}
                                               for server_name in server_targets.keys()}

        # 枚举每一个 proxy
        for proxy_name in proxy_targets.keys():
            logger.info('Testing proxy %s for all servers' % proxy_name)

            # 枚举每一个 server，多进程测试
            with Pool(processes=PROXY_PROCESSES) as pool:
                global global_results, global_lock
                global_results = {}
                global_lock = threading.Lock()
                for server_name, target in server_targets.items():
                    target.setdefault('host', '127.0.0.1')
                    port = target['port']
                    host = target['host']
                    payloads = []
                    cnt = 0
                    # 枚举每一个 testid
                    for testid in result.keys():
                        proxy_result_single = result[testid]['proxy_result'].get(proxy_name)
                        assert proxy_result_single is not None
                        proxy_send = proxy_result_single.get('proxy_send')
                        if proxy_send is not None:
                            payloads.append(easy_encode(proxy_send))
                            # replay_response = send(host, port, easy_encode(proxy_send))
                            # result[testid]['replay_result'][server_name][proxy_name] = easy_decode(replay_response)
                        cnt += 1
                        if cnt > DATA_NUM_WHEN_TRY and is_try:
                            logger.warning('You are testing using is_try on, this program will not test all the payloads.')
                            break
                    pool.apply_async(run_single, (server_name, host, port, payloads), callback=post_run_single, error_callback=error_callback)
                pool.close()
                pool.join()

                # 记录 result
                logger.info('Done test proxy %s for all servers, generating stage 2 result')
                for server_name, target in server_targets.items():
                    for testid in result.keys():
                        res = global_results[server_name].get(testid)
                        if res is not None:
                            result[testid]['replay_result'][server_name][proxy_name] = easy_decode(res)
                save_json(result, result_path)

        logger.warning("A file was replayed successfully done, outpath:{}".format(result_path))


def direct(single_file=None, is_try=False):
    """
    stage 3 - direct 的主要工作代码，用于读入 stage 2 得到的输出，将其中的 json 文件补充上直接向 server 发送 payload 的结果后，
    输出到 DIRECT_RESULT_DIR 目录下，与 stage 2 输出文件同名。
    :param is_try: boolean，是否仅尝试一下测试，为 True 时将只会测试开头的部分数据
    """
    # 读入配置文件
    conf = read_json(CONFIG_PATH)
    server_targets = conf['server_targets']
    logger.info('conf: ' + str(server_targets))

    # 创建结果文件夹
    os.makedirs(RESULT_LOGS_DIR, exist_ok=True)
    os.makedirs(DIRECT_RESULT_DIR, exist_ok=True)
    file_names = get_all_files(PAYLOAD_DIR, ends='.json')
    for file_name in file_names:
        if single_file is not None and single_file not in file_name:
            continue
        data = read_json(file_name)
        logger.info('Direct : %s' % file_name)
        sentence = data['sentence']
        payloads = list(map(lambda x: easy_encode(x), data['reqs']))
        assertion = data['assertion']

        if is_try:
            payloads = payloads[:DATA_NUM_WHEN_TRY]
            logger.warning('You are testing using is_try on, this program will not test all the payloads.')

        result_path = file_name.replace('payload', 'result/direct')

        # 初始化 result 字典
        result = {}
        for payload in payloads:
            testid = extract_testid(easy_decode(payload))
            assert testid is not None
            if testid not in result:
                result[testid] = {'sentence': sentence, 'req': easy_decode(payload), 'assertion': assertion,
                                  'server_result': {}}
                for container_name, target in server_targets.items():
                    result[testid]['server_result'][container_name] = {'response': None, 'semantic': {}}

        # 枚举每一个 server，多进程测试
        logger.info('Testing direct for all servers')
        with Pool(processes=PROXY_PROCESSES) as pool:
            global global_results, global_lock
            global_results = {}
            global_lock = threading.Lock()
            for server_name, target in server_targets.items():
                target.setdefault('host', '127.0.0.1')
                port = target['port']
                host = target['host']
                pool.apply_async(run_single, (server_name, host, port, payloads), callback=post_run_single, error_callback=error_callback)
            pool.close()
            pool.join()

            # 记录 result
            logger.info('Done test direct for all servers, generating direct result')
            for server_name, target in server_targets.items():
                for testid, res in global_results[server_name].items():
                    data = easy_decode(res)
                    result[testid]['server_result'][server_name]['response'] = data
                    status_code = get_status_code(data)
                    d = extract_response_data(data)
                    _uri = d['URI'] if 'URI' in d else None
                    _host = d['Host'] if 'Host' in d else None
                    result[testid]['server_result'][server_name]['semantic'] = {"status_code": status_code,
                                                                                'URI': _uri, "Host": _host}

        # 保存最终结果
        save_json(result, result_path)
        logger.warning("A file was done, outpath:{}".format(result_path))


# 通过输入参数来调试对应的函数
def run():
    # example: python run.py stage_1/stage_2/direct example
    func = sys.argv[1]
    param = sys.argv[2]
    if func == 'all':
        stage_1()
        stage_2()
    else:
        filename = "{}".format(param)
        is_try = False
        try:
            if sys.argv[3] is not None:
                is_try = True
        except Exception as e:
            pass
        print('Func: {} filename:{}'.format(func, filename))
        eval(func)(filename, is_try)
        # proxy + echo server
        # run_stage_1(single_file, is_try)
        # replay to server + direct send payload to server
        # run_stage_2(single_file, is_try)
        # run_risk_2(single_file, is_try)


if __name__ == '__main__':
    run()
