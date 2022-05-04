import os
from loguru import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + '/'
DATA_DIR = BASE_DIR + '/data/'
TMP_DIR = BASE_DIR + '/data/tmp/'

os.makedirs(TMP_DIR, exist_ok=True)

# RFC 原文
RFC_DIR = os.path.join(DATA_DIR, 'rfc/')
# 预处理完后的RFC文档
CLEANED_RFC_DIR = os.path.join(DATA_DIR, 'cleaned_rfc/')
# ABNF保存位置
ABNF_DIR = os.path.join(DATA_DIR, 'abnf/')
# 中间分析结果保存位置
SR_DIR = os.path.join(DATA_DIR, 'SR/')

ROLE_DIR = os.path.join(DATA_DIR, "role_behavior/")
# 关键左值保存目录
KEYWORDS_DIR = os.path.join(DATA_DIR, 'keywords/')

KEYWORDS_PATH = os.path.join(KEYWORDS_DIR, 'keywords.txt')
KEYWORDS_DICT_PATH = os.path.join(KEYWORDS_DIR, 'keywords_dict.json')

LOG_PATH = os.path.join(TMP_DIR, 'log.txt')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data/')

FUZ_DATA_DIR = os.path.join(DATA_DIR, "fuzz_data/")

ABNF_DIFF_PATH = os.path.join(DATA_DIR, 'abnf_difference.json')
RESULTS_DIR = os.path.join(DATA_DIR, "results/")
PAYLOAD_DIR = os.path.join(DATA_DIR, "payload/")
RESULT_DIR = os.path.join(DATA_DIR, "result/")
RESULT_LOGS_DIR = os.path.join(DATA_DIR, "proxy_logs/")
RESULT_STAGE_1_DIR = os.path.join(RESULT_DIR, "stage_1/")
RESULT_STAGE_2_DIR = os.path.join(RESULT_DIR, "stage_2/")
DIRECT_RESULT_DIR = os.path.join(RESULT_DIR, "direct/")
REPLAY_LOGS_DIR = os.path.join(DATA_DIR, "replay_logs/")

LOG_FILE_PATH = os.path.join(DATA_DIR, "log/run.log")

CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
TMP_TAR_PATH = os.path.join(DATA_DIR, 'tmp.tar')
TMP_DIR = os.path.join(DATA_DIR, 'tmp')
TEST_CASE_DIR = os.path.join(DATA_DIR, 'payload/')
DEMO_DIR = os.path.join(DATA_DIR, 'demo/')
BGrammar_PATH = os.path.join(DEMO_DIR, 'bgrammar.txt')
SR_PATH = os.path.join(DEMO_DIR, 'SR.json')
HCONFIG_PATH = os.path.join(DEMO_DIR, 'HConfig.json')




# 为容器打上的标签，便于停止容器
DOCKER_LABEL = 'HDiff'
# 随机端口的范围： [PORT_LB, PORT_UB]
PORT_LB = 9000
PORT_UB = 9999

# 发包后等待时长
CLIENT_WAIT_TIME = 0.5
# 容器启动之后的等待时长
CONTAINER_WAIT_TIME = 3
# 接收响应时的 buffer 大小，即最多接收字节数
RECV_BUF_SIZE = 4096
# 每组有多少条数据，**注意更改该值后保存的进度会作废**
GROUP_SIZE = 45
# 每组误报超过该阈值时发出警告，提醒调高 CLIENT_WAIT_TIME
MISJUDGE_WARNING_THRESHOLD = 3

# Proxy 测试中使用的进程数
PROXY_PROCESSES = 16
# 测试中使用的进度打印间隔
PROGRESS_INTERVAL = 50
# 测试中 is_try 开启时使用的数据量
DATA_NUM_WHEN_TRY = 60

SINGLE_SERVER_PAYLOAD_NUMS = 80

SERVER_PROCESSES = 8

# 加载的预置模型
# CORE = 'en_core_web_trf' # 超大型,效果好，NER会好，但是速度慢
CORE = 'en_core_web_sm'  # 小型单词库，但是快
TE_THRESHOLD = 0.5

# log
trace = logger.add(BASE_DIR + '/data/log/runtime.log', rotation="100 MB")
