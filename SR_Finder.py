import re
import os
import pandas as pd
import graphviz
import stanza
import spacy
from spacy import displacy
from spacy.matcher import DependencyMatcher, PhraseMatcher
from config import ANALYSIS_DIR, REFIEND_RFC_DIR, TMP_DIR, CORE, TE_THRESHOLD, KEYWORDS_PATH
# from clause_analyzer import ClauseAnalyzer
from tree2rules import generate_rule_tree, expand_rule_tree

# senders, recipients, clients, servers, user agents,
# intermediaries, origin servers, proxies, gateways, or caches,
# RFC 中定义的HTTP角色
ROLES = [
    "server", "origin server", "recipient", "response",
    "message", "request",  "header",
    "client", "user agent", "sender",

    "accelerator", "gateway", "tunnel", "cache",
    "inbound", "outbound", "upstream", "downstream",
    "proxy", "reverse proxy", "interception proxy",
    "intermediary",
]

KEYWORDS = [
    "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
    "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", "OPTIONAL"
]

OTHERS = ['will', 'would', "can", 'might', 'could', 'ought to']


# 其他的情感动词, will（would），shall（should），can（could），may（might），must，need，dare，ought to，used to，had better

def clean_keys(data):
    """
     将两个单词的字符转换成一个,spacy匹配时，是按单词来匹配的
    """
    nlp = spacy.load(CORE)
    results = []
    for d in data:
        doc = nlp(d)
        for i in doc:
            token = i.lemma_.lower()
            results.append(token)
    results = list(set(results))
    return results


def analyze_key_words(data):
    """
    检查句子是否满足 带有must类似的关键词，返回results [] 表征提取出来的句子
    """
    nlp = spacy.load(CORE)
    doc = nlp(data)
    matcher = PhraseMatcher(nlp.vocab)
    description = 'RFC-keywords'
    pattern = [nlp.make_doc(text) for text in KEYWORDS]
    matcher.add(description, pattern)
    results = []
    for sent in doc.sents:
        flag = matcher(sent)
        if len(flag):
            results.append(str(sent).strip())
    return results


def analyze_role_behavior(data):
    """
    检查句子是否满足 role must/should/may，返回results [] 表征提取出来的句子
    """
    nlp = spacy.load(CORE)
    doc = nlp(data)
    matcher = DependencyMatcher(nlp.vocab)
    description = 'role-behavior'  # 仅用于作为唯一描述
    roles = clean_keys(ROLES)
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
    results = []
    for sent in doc.sents:
        if 'generate' in str(sent):
            # print(sent)
            continue
        flag = matcher(sent)
        if len(flag):
            # print(sent[flag[0][1][0]], sent[flag[0][1][1]], sent[flag[0][1][2]])
            results.append(str(sent).strip())
    return results


def subtree(token, exclude=None):
    """
    返回排除了部分依赖关系的子树
    :param token: 以 token 为根的子树
    :param exclude: list, 每个元素为 str，表示排除的依赖关系
    """
    if exclude is None:
        exclude = []
    ret = list(token.subtree)
    for child in token.children:
        if child.dep_ in exclude:
            for ex_token in child.subtree:
                if ex_token in ret:
                    ret.remove(ex_token)
    return ret


def subtree2str(subtree):
    """ 将 [Token, ...] 格式的列表转为字符串 """
    ret = ' '.join(map(lambda x: str(x), subtree))
    return ret.replace(' - ', '-').replace('( ', '(').replace(' )', ')')


def recursive_prepend(clause, prefix, sep=' '):
    """
    为 clause 表示的三元组树状结构递归添加前缀，返回添加完毕之后的元组
    :param clause: 三元组树状结构的根
    :param prefix: 要添加的前缀
    :param sep: 字符串拼接时的间隔符
    """
    if isinstance(clause, tuple):
        return (recursive_prepend(clause[0], prefix),
                recursive_prepend(clause[1], prefix), clause[2])
    else:
        return prefix + sep + clause


def cut_clause(token):
    """
    切割 and / or 等子句，返回格式形如 ret_clause := (clause, clause, 'and'/'or') 或者单个最小子句
    :param token: 以 token 为根的子树开始切割
    """

    AND = 'and'
    OR = 'or'
    CUT_TARGET = [AND, OR]
    # prep/pcomp 用于特殊处理 with/with 后的子句这类结构
    # 其余用于找到当前小子句，其中 preconj 用于筛去 either 这类词，mark 用于筛去 if 这类词，cc 用于筛去 and/or 这类词，advmod 用于筛去 then 这类词等等
    CUT_EXCLUDE = ['mark', 'punct', 'cc', 'conj', 'advcl', 'ccomp', 'prep', 'pcomp', 'preconj', 'advmod']
    cc = None
    sub_root = None  # 子句的 root
    nsubj = None
    prep = None
    pcomp = None  # token、prep 和 pcomp 都可能出现 cc 儿子，此时需要进行递归切割
    for child in token.children:
        if child.dep_ == 'cc' and child.lemma_ in CUT_TARGET:
            assert cc is None, '理应不会出现两个 cc'
            cc = child.lemma_
        if child.dep_ == 'conj':
            assert sub_root is None, '理应不会出现两个 conj'
            sub_root = child
        if child.dep_ == 'nsubj':
            assert nsubj is None, '理应不会出现两个 nsubj'
            nsubj = child
        # prep: with/without
        if child.dep_ == 'prep':
            assert prep is None, '理应不会出现两个 prep'
            prep = child
        if child.dep_ == 'pcomp':
            assert pcomp is None, '理应不会出现两个 pcomp'
            pcomp = child
        # 当不存在 prep、pcomp 时，clause1 为第一个子句或整个句子（取决于 token 子依赖中是否存在 cc）
        # 当存在 prep 或 pcomp 时，clause1 为需要递归添加的前缀
    clause1 = subtree(token, exclude=CUT_EXCLUDE)
    clause1 = subtree2str(clause1)

    if cc is None:
        if prep is not None:
            return recursive_prepend(cut_clause(prep), clause1)
        elif pcomp is not None:
            return recursive_prepend(cut_clause(pcomp), clause1)
        else:
            return clause1
    else:
        assert sub_root is not None, '出现 and/or 时理应有 conj'
        clause2 = cut_clause(sub_root)

        # 考虑是否传递 clause1 的主语给 clause2
        nsubj_sent = subtree2str(subtree(nsubj)) if nsubj is not None else None
        need_pass_nsubj = True
        for child in sub_root.children:
            if child.dep_ == 'nsubj':
                need_pass_nsubj = False  # clause2 有主语，不需要传递
        if need_pass_nsubj and nsubj_sent is not None:
            clause2 = recursive_prepend(clause2, nsubj_sent)

        return (clause1, clause2, cc)


def analyze_if_clauses(data):
    """
    检查句子是否满足 条件子句，返回results [] 表征提取出来的句子
    """
    nlp = spacy.load(CORE)
    doc = nlp(data)
    matcher = DependencyMatcher(nlp.vocab)
    description = 'if-then'  # 仅用于作为唯一描述
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
            then_verb = if_verb.head
            ret = {'if': cut_clause(if_verb), 'then': cut_clause(then_verb)}
            if then_verb.dep_ == 'ccomp':
                ret['then'] = (ret['then'], cut_clause(then_verb.head), 'and')
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


def run_one_rfc_key_words(inputFile='../data/refined_rfc/7230.txt', outFile='../data/analysis/key_words/7230.csv'):
    data = open(inputFile).read()
    results = analyze_key_words(data)
    # list转dataframe
    df = pd.DataFrame(results, columns=['sentences'])
    # 保存到本地excel
    df.to_csv(outFile, index=False, encoding='utf-8')


def read_rfc(rfc_name):
    file_path = '{}/{}.txt'.format(REFIEND_RFC_DIR, rfc_name)
    data = open(file_path, 'r').read()
    return data


def run_one_rfc_role_behavior(inputFile='../data/refined_rfc/7230.txt',
                              outFile='../data/analysis/role_behavior/7230.csv'):
    data = open(inputFile).read()
    # results = analyze_key_words(data)
    results = analyze_role_behavior(data)
    rfc_num = inputFile.split('/')[-1].split('.')[0]
    print(len(results))
    # rfc_num, len(data),
    # list转dataframe
    df = pd.DataFrame(results, columns=['sentences'])
    # 保存到本地excel
    df.to_csv(outFile, index=False, encoding='utf-8')


def run_rfcs():
    for i in range(6):
        rfc_name = '723{}'.format(i)
        inputFile = '{}/{}.txt'.format(REFIEND_RFC_DIR, rfc_name)
        outputFile = '{}/role_behavior/{}.txt'.format(ANALYSIS_DIR, rfc_name).replace('.txt', '.csv')
        run_one_rfc_role_behavior(inputFile, outputFile)
        # print(inputFile,outputFile)


def draw_dependency_tree(sent, use_graphviz=True, filename='dp.gv'):
    """
    绘制依赖分析树
    :param use_graphviz: 为 True 时使用 graphviz 绘制，False 时使用 displacy 绘制
    :param filename: 使用 graphviz 绘制时的文件名
    """
    nlp = spacy.load(CORE)
    doc = nlp(sent)
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


# 分析两个结果的差集
def diff_analysis():
    data = open('../data/refined_rfc/7230.txt').read()
    result1 = analyze_role_behavior(data)
    result2 = analyze_key_words(data)
    # key_words的结果包含了role_behavior的结果
    # for r in result1:
    #     if r not in result2:
    #         print(r)
    for r in result2:
        if r not in result1:
            print(r)


# def analysis(sent):
#     """ 给入一个句子，从依赖树分析开始走到准模板生成 """
#     clause_tree = analyze_if_clauses(sent)
#     print(clause_tree)
#     if clause_tree is None:
#         print('Not If-Then.')
#         return None
#     ca = ClauseAnalyzer(CORE, KEYWORDS_PATH, TE_THRESHOLD)
#     results = {}
#     results['if'] = generate_rule_tree(ca, clause_tree['if'], type='if')
#     results['then'] = generate_rule_tree(ca, clause_tree['then'], type='then')
#     print(results)
#     return results


def analysis():
    nlp = stanza.Pipeline(lang='en', processors='tokenize')
    for i in range(6):
        rfc_num = '723{}'.format(i)
        data = read_rfc(rfc_num)
        doc = nlp(data)
        # print(doc)
        role_behavior = analyze_role_behavior(data)
        print("RFC:{}\tTokens:{}\tSentences:{}\t BS:{}".format(rfc_num, doc.num_tokens, len(doc.sentences),
                                                               len(role_behavior)))


# 子句进行文本蕴含
def debug():
    # print(clause_tree)
    sent = "If a message is received without Transfer-Encoding and with either multiple Content-Length header fields having differing field-values or a single Content-Length header field having an invalid value, then the message framing is invalid and the recipient MUST treat it as an unrecoverable error."
    draw_dependency_tree(sent)
    # res = analysis(sent)
    # res = analyze_role_behavior(sent)
    # print(res)
    # diff_analysis()


if __name__ == '__main__':
    debug()
    # run_one_rfc_role_behavior()
    # diff_analysis()
    # read_rfc('7231')
    # analysis()
    # run_rfcs()
