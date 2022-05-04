import re
import spacy
from spacy.symbols import ORTH
from config import CORE, KEYWORDS_PATH, TE_THRESHOLD
from src.textual_entailment import predictor


class ClauseAnalyzer:
    """
    用于对简单的子句进行 TE 等分析并生成准模板
    targets 规则：
        * 首先 targets 为一个 list，每一个元素为一个 dict，注意 dict 之间 `name` 不能重复；
        * 每个 dict 中必须包含 `name`、`hypothesis`、`param_types` 这几个 key，`name` 对应这个 target 的名字，`hypothesis` 对应
         这个 target 在 TE 中的 hypothesis，而 `param_types` 为一个列表，用于处理 `hypothesis` 中的参数占位符（如 `%d` 等）；
        * PARAM_KEYWORD 用文本中出现过的且在 keywords 中的关键词进行代参；PARAM_REGEX 为正则表达式类型，用文本中出现过的且满足
         `param_regex` 这个 pattern 的串进行代入，注意 param_regex 需要与 param_types 中的所有 PARAM_REGEX 一一对应。
          另外提醒一下正则表达式书写时可能需要加入单词边界 (\b) 或者进行前瞻后顾，例如 '(?<=123)456(?=789)' 这样来匹配 '456'
    """
    # PARAM_NONE = 0  # 由于换为了列表，所以并不需要该选项
    PARAM_KEYWORD = 1
    PARAM_REGEX = 2

    # note: 负向语义不能通过第二个参数来获取，会有误报。所以，只能通过人工指定正负语义，然后文本蕴含
    condition = [
        # example:
        {'name': 'header_exists', 'hypothesis': 'include %s header', 'param_types': [PARAM_KEYWORD]},  # exist, represent, in, is
        {'name': 'header_not_exists', 'hypothesis': 'not include %s header', 'param_types': [PARAM_KEYWORD]},
        {'name': "multiple_header", 'hypothesis': 'with multiple %s header', 'param_types': [PARAM_KEYWORD]},
        {'name': "invalid_header", 'hypothesis': '%s header field having an invalid value', 'param_types': [PARAM_KEYWORD]},
        {'name': 'assign', 'hypothesis': '%s header field should be "%s"', 'param_types': [PARAM_KEYWORD, PARAM_REGEX],
         'param_regex': [r'(?<=").*?(?=")']},
        {'name': 'not implement', 'hypothesis': '%s is not implemented', 'param_types': [PARAM_KEYWORD]},  # 与定义不符合
        {'name': 'final', 'hypothesis': '%s is final', 'param_types': [PARAM_KEYWORD]},
        {'name': 'not final', 'hypothesis': '%s is not final', 'param_types': [PARAM_KEYWORD]},  # 不是最后
        {'name': 'first', 'hypothesis': '%s is first', 'param_types': [PARAM_KEYWORD]},  # 第一个数据包
        {'name': 'not first', 'hypothesis': '%s is not first', 'param_types': [PARAM_KEYWORD]},  # 非第一个数据包
        {'name': 'twice', 'hypothesis': '%s is applied twice', 'param_types': [PARAM_KEYWORD]},  # repeat, 重复  两次等等
        {'name': 'chunked not twice', 'hypothesis': 'chunked should not be applied twice', 'param_types': []},
        {'name': 'not both Transfer-Encoding and Content-Length',
         'hypothesis': 'not both Transfer-Encoding and Content-Length', 'param_types': []},
    ]
    result = [
        # example
        {'name': 'close_connection', 'hypothesis': 'close the connection', 'param_types': []},  # 关闭请求
        # {'name': 'reject', 'hypothesis': 'reject the request', 'param_types': []},  # 拒绝请求
        {'name': 'status_code', 'hypothesis': 'respond %s code', 'param_types': [PARAM_REGEX],
         'param_regex': [r'\b\d\d\d\b']},  # 以什么状态码回复
        {'name': 'error_status', 'hypothesis': 'treat as an error', 'param_types': []},  # 认为为错误 !200 状态码返回
    ]

    def __init__(self, core, keywords_path, threshold):
        """
        初始化 ClauseAnalyzer 实例
        :param core: str，spacy 使用的 core
        :param keywords_path: str，关键词列表的路径，注意文件内容格式为每行一个关键词
        :param threshold: float，TE 的阈值，大于该 threshold 认为 TE 成立
        """
        self._nlp = spacy.load(core)
        self.threshold = threshold
        with open(keywords_path, 'r') as f:
            self.keywords = list(filter(lambda x: x != '', map(lambda x: x.strip(), f.readlines())))
        for keyword in self.keywords:
            self._nlp.tokenizer.add_special_case(keyword, [{ORTH: keyword}])

    def analyze_clause(self, clause, type='then'):
        """
        用于对简单的子句进行分析，生成准模板。
        :return: 返回形如 {target_name1: [keyword_list1, keyword_list2, ...], ...} 的字典
        注意无参的 target 满足时对应空列表
        """
        doc = self._nlp(clause)
        ret = {}
        # 预处理关键词参数类型中的参数
        clause_keywords = []
        for keywords in self.keywords:
            if keywords in clause:
                clause_keywords.append(keywords)

        # 优化条件和结果搜寻
        if type == 'if':
            targets = self.condition
        elif type == 'then':
            targets = self.result
        else:
            print('ERROR type:{}'.format(type))
            return None

        # 再用 TE 进行条例判断
        for target in targets:
            assert target['hypothesis'].count('%s') == len(
                target['param_types']), '%s: %s 个数必须与 target["param_types"]列表长度匹配'.replace('%s', str(target), 1)
            # 无参类型，直接判断
            if len(target['param_types']) == 0:
                probs = predictor.predict(premise=clause, hypothesis=target['hypothesis'])['probs']
                # 正向语义
                if probs[0] > self.threshold:
                    ret[target['name']] = True
                # # 负向语义
                # elif probs[1] > self.threshold:
                #     ret[target['name']] = False
                else:
                    # print('Not match:{}, {}'.format(clause,target['hypothesis']))
                    pass
            else:
                hypothesis_list = [target['hypothesis']]
                params_list = [[]]  # 存储 hypothesis_list 中每一项对应的参数列表
                regex_cnt = 0  # 当前处理了几个 PARAM_REGEX 类型的参数
                for param_types in target['param_types']:
                    params = []
                    # 关键词参数类型
                    if param_types == self.PARAM_KEYWORD:
                        params = clause_keywords
                    # 正则表达式参数类型
                    elif param_types == self.PARAM_REGEX:
                        params = re.findall(target['param_regex'][regex_cnt], clause)
                    # 代入最靠前的第一个参数
                    new_hypothesis_list = []
                    new_params_list = []
                    for param in params:
                        for i in range(len(hypothesis_list)):
                            new_hypothesis_list.append(hypothesis_list[i].replace('%s', param, 1))
                            tmp_params = params_list[i].copy()
                            tmp_params.append(param)
                            new_params_list.append(tmp_params)
                    hypothesis_list = new_hypothesis_list
                    params_list = new_params_list
                    if param_types == self.PARAM_REGEX:
                        regex_cnt += 1

                for i in range(len(hypothesis_list)):
                    probs = predictor.predict(premise=clause, hypothesis=hypothesis_list[i])['probs']
                    # 正向语义
                    if probs[0] > self.threshold:
                        ret[target['name']] = params_list[i][0]
                        break
                    else:
                        # print('Not match:{}, {}'.format(clause,hypothesis_list[i]))
                        pass

        return ret


if __name__ == '__main__':
    ca = ClauseAnalyzer(CORE, KEYWORDS_PATH, TE_THRESHOLD)
    clause = 'If a Transfer-Encoding header field is present in a request and the chunked transfer coding is not the final encoding, the message body length cannot be determined reliably; the server MUST respond with the 400 (Bad Request) status code and then close the connection.'
    print(ca.analyze_clause(clause, type='if'))
