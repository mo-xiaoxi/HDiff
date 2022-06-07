import re
import os
import pandas as pd
import graphviz
import spacy
import string
import copy
from spacy import displacy
from spacy.matcher import DependencyMatcher, PhraseMatcher, Matcher
from config import SR_DIR, ROLE_DIR, TMP_DIR, CORE, TE_THRESHOLD, KEYWORDS_PATH, ROLES, KEYWORDS, CLEANED_RFC_DIR
from config import logger
from src.util import save_json, read_data
from src.clause_analyzer import ClauseAnalyzer

NLP = spacy.load(CORE)


def clean_keys(data):
    """
     将两个单词的字符转换成一个,spacy匹配时，是按单词来匹配的
    """
    results = []
    for d in data:
        doc = NLP(d)
        for i in doc:
            token = i.lemma_.lower()
            results.append(token)
    results = list(set(results))
    return results


def clean_s(s):
    """
    替换字符串，把不必要的空格删除
    :param s:
    :return:
    """

    for c in string.punctuation:
        s = s.replace(" " + c, c)
        if c == '-':
            s = s.replace(c + " ", c)
    return s.strip()


def expand_role_behavior(sent):
    roles = clean_keys(ROLES)
    matcher = DependencyMatcher(NLP.vocab)
    description = 'role-behavior'  # 仅用于作为唯一描述
    # 一些关键的表达
    keywords = clean_keys(KEYWORDS)
    pattern = [
        {
            "RIGHT_ID": "role",
            "RIGHT_ATTRS": {"LEMMA": {"IN": roles}, "DEP": "nsubj"}
        },
        {
            "LEFT_ID": "role",
            "RIGHT_ID": "emotional-verb",
            "RIGHT_ATTRS": {},
            "REL_OP": "<"
        },
        {
            "LEFT_ID": "emotional-verb",
            "RIGHT_ID": "verb",
            "RIGHT_ATTRS": {"LEMMA": {"IN": keywords}, "DEP": "aux"},
            "REL_OP": ">"
        }
    ]
    matcher.add(description, [pattern])
    # keywords = clean_keys(OTHERS)
    # pattern = [
    #     {
    #         "RIGHT_ID": "role",
    #         "RIGHT_ATTRS": {"LEMMA": {"IN": roles}, "DEP": "nsubj"}
    #     },
    #     {
    #         "LEFT_ID": "role",
    #         "RIGHT_ID": "verb",
    #         "RIGHT_ATTRS": {},
    #         "REL_OP": "<"
    #     },
    #     {
    #         "LEFT_ID": "verb",
    #         "RIGHT_ID": "emotional-verb",
    #         "RIGHT_ATTRS": {"LEMMA": {"IN": keywords}, "DEP": "aux"},
    #         "REL_OP": ">"
    #     },
    #     {
    #         "LEFT_ID": "verb",
    #         "RIGHT_ID": "neg",
    #         "RIGHT_ATTRS": {"DEP": "neg"},
    #         "REL_OP": ">"
    #     }
    # ]
    # matcher.add(description, [pattern])
    # print(pattern)
    return matcher(sent)


def analyze_role_behavior(data):
    """
    检查句子是否满足 role must/should/may, 返回results [] 表征提取出来的句子
    """
    doc = NLP(data)
    results = []
    for sent in doc.sents:
        flag = expand_role_behavior(sent)
        if len(flag):
            # print(sent[flag[0][1][0]], sent[flag[0][1][1]], sent[flag[0][1][2]])
            results.append(str(sent).strip())
    return results


def split_clause(token):
    """
    返回一个句子的子句
    :param token: 以 token 为根的子树
    """
    exclude = [
        'mark',  # if, when
        'punct',  # 符号， 比如逗号之类
        'advcl',  # 状语从句
        'advmod',  # 状语修饰语, 如then
    ]
    ret = list(token.subtree)
    for child in token.children:
        if child.dep_ in exclude:
            for ex_token in child.subtree:
                if ex_token in ret:
                    ret.remove(ex_token)
    s = ' '.join(map(lambda x: str(x), ret))
    result = clean_s(s)
    return result


def split_phrase(sent):
    """
    切分短语，将条件和结果的句子切分成一个个清晰的短语
    :param sent:
    :return:
    """
    doc = NLP(sent)
    root = None
    for token in doc:
        if token.dep_ == 'ROOT':
            root = token
    data = result_handle(subtree(root))
    return data


def concat_prepend(clause, prefix, sep=' '):
    """
    为 clause 表示的三元组树状结构递归添加前缀，返回添加完毕之后的元组
    :param clause: 三元组树状结构的根
    :param prefix: 要添加的前缀
    :param sep: 字符串拼接时的间隔符
    """
    if isinstance(clause, list):
        assert len(clause) == 3
        return [concat_prepend(clause[0], prefix),
                concat_prepend(clause[1], prefix), clause[2]]
    elif isinstance(prefix, list):
        assert len(prefix) == 3
        return [concat_prepend(clause, prefix[0]),
                concat_prepend(clause, prefix[1]), prefix[2]]
    else:
        return clean_s(prefix + sep + str(clause))


def result2string(data):
    """
    将结果转换成string
    :param data:
    :return:
    """
    result = ""
    for token in data:
        result = concat_prepend(token, result)
    return result


def result_handle(result):
    """
    返回结果callback函数
    :param result:
    :return:
    """
    data, cc = result
    if cc:
        c1 = result2string(data[0])
        c2 = result2string(data[1])
        return [c1, c2, cc]
    else:
        s = result2string(data)
        return s


def subtree(root):
    """
     基于根节点进行切割
    :param root:
    :return:
    """
    children = list(root.children)
    cc = None
    if not children:
        return [root], cc

    # 正常， left + root + right
    # 存在cc, left + root+ right  以cc位置切开， [left, root, :cc], [cc+1:end], cc
    left_clause = []
    right_clause = []
    i = 0
    index = 0
    for l in root.lefts:
        left = result_handle(subtree(l))
        left_clause.append(left)
        i += 1
    for r in root.rights:
        right = result_handle(subtree(r))
        right_clause.append(right)
        i += 1
        if r.dep_ == 'cc' and r.lower_ in ["or", "and"]:
            index = i
    # print(index)
    # 存在cc
    clause = left_clause + [root] + right_clause
    if index:
        clause1 = clause[:index]
        clause2 = clause[index + 1:]
        cc = clause[index]
        return [clause1, clause2], cc
    return clause, cc


def dereference(data, rfc_number):
    rfc_path = "{}/{}.txt".format(CLEANED_RFC_DIR, rfc_number)
    rfc_data = NLP(read_data(rfc_path))
    lib = [
        "this is a request message",
        "this is a response message",
        "this message",
        "such message",
        "such request",
    ]
    sents = list(map(lambda x: str(x), rfc_data.sents))
    for l in lib:
        for i in range(len(data)):
            if l in data[i]:
                r = pre_find(data[i], sents)
                if r:
                    data[i] = data[i].replace(l, r)
                break
    return data


def pre_find(data, sents, maxstep=5):
    flag = [
        "request is",
        "message is"
    ]
    index = sents.index(data)
    for j in range(index - 1, index - maxstep, -1):
        for f in flag:
            if f in sents[j]:
                r = sents[j][sents[j].find(f):].split(',')[0].split('.')[0]
                return r
    logger.warning("Not Found...")
    return None


def analyze_if_clauses(data):
    """
    检查句子是否满足 条件子句, 返回results [] 表征提取出来的句子
    """
    doc = NLP(data)
    matcher = DependencyMatcher(NLP.vocab)
    description = 'if-result'  # 仅用于作为唯一描述
    pattern = [
        {
            "RIGHT_ID": "if",
            "RIGHT_ATTRS": {"LEMMA": "if", "DEP": "mark"}
        },
        {
            "LEFT_ID": "if",
            "RIGHT_ID": "if-verb",
            "RIGHT_ATTRS": {"DEP": "advcl"},
            "REL_OP": "<"
        }
    ]
    matcher.add(description, [pattern])
    for sent in doc.sents:
        flag = matcher(sent)
        if len(flag) > 0:
            if_verb = sent[flag[0][1][1]]
            result_verb = if_verb.head
            ret = {'if': split_clause(if_verb), 'result': split_clause(result_verb)}

            # TODO ccomp — 从句补语，一般由两个动词构成，中心语引导后一个动词所在的从句(IP) （出现，纳入）
            # if result_verb.dep_ == 'ccomp':  # ccomp — 从句补语，一般由两个动词构成，中心语引导后一个动词所在的从句(IP) （出现，纳入）
            #     ret['result'] = [ret['result'], split_clause(result_verb.head), 'and']
            return ret
    return None


def find_key_words(data):
    """
    寻找RFC中 ""包裹的单词
    """
    pattern = re.compile(r'"(.*?)"')
    m = pattern.findall(data)
    result = m
    # result = list(set(m))
    return result


def extract_role_behavior_from_rfc(input_path, output_path):
    df = pd.read_csv(input_path)
    data = df['sentences'].drop_duplicates().values.tolist()
    data = '\n'.join(data)
    results = analyze_role_behavior(data)
    logger.debug(len(results))
    # rfc_num, len(data),
    # list转dataframe
    df = pd.DataFrame(results, columns=['sentences'])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # 保存到本地excel
    df.to_csv(output_path, index=False, encoding='utf-8')


def draw_dependency_tree(sent, use_graphviz=True, filename='dp.gv'):
    """
    绘制依赖分析树
    :param use_graphviz: 为 True 时使用 graphviz 绘制, False 时使用 displacy 绘制
    :param filename: 使用 graphviz 绘制时的文件名
    """
    doc = NLP(sent)
    if not use_graphviz:
        displacy.serve(doc, style='dep')
    else:
        filepath = os.path.join(TMP_DIR, filename)
        dot = graphviz.Digraph()
        for ent in doc:
            dot.node(str(ent.idx), ent.text)
            if ent.head != ent:
                dot.edge(str(ent.head.idx), str(ent.idx), ent.dep_)
        dot.render(filepath, view=True)


def generate_rule_tree(ca, phrase_tree, type):
    """
    遍历 DependencyAnalyzer 得到的 clause 树状结构，并使用 ClauseAnalyzer 进行处理
    :param ca: ClauseAnalyzer object，用于对每个子句进行处理
    :param phrase_tree: tuple，由子句组成的三元组树状结构的根
    :return rule_tree: tuple，由准模板项组成的三元组树状结构的根
    """
    if isinstance(phrase_tree, list):
        assert len(phrase_tree) == 3
        rule_tree = [generate_rule_tree(ca, phrase_tree[0], type), generate_rule_tree(ca, phrase_tree[1], type),
                     phrase_tree[2]]
    elif isinstance(phrase_tree, str):
        rule_tree = ca.analyze_clause(phrase_tree, type)
    else:
        assert False, 'phrase_tree 类型错误：%s，必须为 list/str' % str(type(phrase_tree))
    return rule_tree


def expand_rule_tree(rule_tree, rule_sets):
    """
    展开准模板树，生成准模板列表
    :param rule_tree: tuple，由准模板项组成的三元组树状结构的根
    :param rule_sets: list，需要对这个列表中的每一项附加上当前子树对应的规则，最外层传入时应为 [{}]
    :ret ret_rule_sets: list，更新后的规则集列表
    """
    ret_rule_sets = []
    if isinstance(rule_tree, list):
        assert len(rule_tree) == 3
        if rule_tree[2].lower() == "or":
            ret_rule_sets.extend(expand_rule_tree(rule_tree[0], rule_sets))
            ret_rule_sets.extend(expand_rule_tree(rule_tree[1], rule_sets))
        elif rule_tree[2].lower() == "and":
            ret_rule_sets = expand_rule_tree(rule_tree[0], rule_sets)
            ret_rule_sets = expand_rule_tree(rule_tree[1], ret_rule_sets)
        else:
            assert False, '逻辑类型错误，%s' % str(rule_tree[2])
    elif isinstance(rule_tree, dict):
        # TODO 相同规则，多个属性 不能重复更新，需要变成列表 比如header_exists a, header_exists b。 当前算法只能保留一个语义
        ret_rule_sets = copy.deepcopy(rule_sets)
        for rule_set in ret_rule_sets:
            rule_set.update(rule_tree)
    else:
        assert False, 'rule_tree 类型错误：%s，必须为 list/str' % str(type(rule_tree))
    return ret_rule_sets


def analysis(sent):
    tokens = NLP(sent)
    result = {}

    # ROLE
    flag = expand_role_behavior(tokens)
    role = tokens[flag[0][1][0]]
    verb = tokens[flag[0][1][1]]
    emotional = tokens[flag[0][1][2]]

    # check if-result
    for token in tokens:
        if token.lower_ == 'if':
            result = analysis_if(sent)
            if not result:
                result = {}
                break
            result['role'] = str(role)
            result['origin'] = sent
            logger.debug(result)
            return result

    ca = ClauseAnalyzer(CORE, KEYWORDS_PATH, TE_THRESHOLD)
    # check role MUST 直接TE推导
    result['if'] = ca.analyze_clause(sent, type='if')
    result['result'] = ca.analyze_clause(sent, type='result')
    result['role'] = str(role)
    result['origin'] = sent
    logger.debug(result)
    return result


def analysis_if(sent):
    """
    给入一个句子，从依赖树分析开始走到准模板生成
    :param sent:
    :return:
    """
    logger.debug(sent)
    # 获取一个句子的if-result结果
    clause_tree = analyze_if_clauses(sent)
    if clause_tree is None:
        logger.info('Not If-Result.')
        return None
    logger.debug(clause_tree)
    phrase_tree = {}
    for k in clause_tree:
        phrase = split_phrase(clause_tree[k])
        phrase_tree[k] = phrase
    logger.debug(phrase_tree)
    ca = ClauseAnalyzer(CORE, KEYWORDS_PATH, TE_THRESHOLD)

    rule_tree = {}
    for k in phrase_tree:
        rule_tree[k] = generate_rule_tree(ca, phrase_tree[k], type=k)
    logger.debug(rule_tree)

    rule_sets = {}
    for k in rule_tree:
        rule_sets[k] = expand_rule_tree(rule_tree[k], [{}])
        for rule in rule_sets[k]:
            if rule == {}:
                rule_sets[k].remove(rule)
    logger.debug(rule_sets)

    return rule_sets


def run_analysis(rfc_number):
    input_path = "{}/{}.csv".format(ROLE_DIR, rfc_number)
    ouput_path = "{}/{}.json".format(ROLE_DIR, rfc_number)
    df = pd.read_csv(input_path)
    data = df['sentences'].drop_duplicates().values.tolist()
    results = []
    # 消引用
    data = dereference(data, rfc_number)
    for d in data:
        res = analysis(d)
        if res:
            for k in res:
                if len(res[k]):
                    continue
            results.append(res)
    # print(results)
    save_json(results, ouput_path)


def run_rfcs():
    for i in range(3, 6, 1):
        rfc_number = 7230 + i
        input_path = "{}/{}.csv".format(SR_DIR, rfc_number)
        output_path = "{}/{}.csv".format(ROLE_DIR, rfc_number)
        extract_role_behavior_from_rfc(input_path, output_path)
        run_analysis(rfc_number)


if __name__ == '__main__':
    # sent = "A server MUST reject any received request message that contains whitespace between a header field-name and colon with a response code of 400 (Bad Request)."
    # draw_dependency_tree(sent)
    # rfc_number = '7232'
    # run_analysis(rfc_number)
    # sent = "If terminating the request message body with a line-ending is desired, then the user agent MUST count the terminating CRLF octets as part of the message body length."
    # analysis(sent)
    run_rfcs()
