import os
import re
import spacy
from spacy import displacy
from spacy.matcher import DependencyMatcher
from spacy.symbols import ORTH
import graphviz
from config import TMP_DIR, CORE, KEYWORDS_PATH
from config import logger

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class DependencyAnalyzer:
    """
    自定义的依赖分析器，封装 spacy 接口以便使用
    """
    AND = 'and'
    OR = 'or'
    CUT_TARGET = [AND, OR]
    # prep/pcomp 用于特殊处理 with/with 后的子句这类结构
    # 其余用于找到当前小子句，其中 preconj 用于筛去 either 这类词，mark 用于筛去 if 这类词，cc 用于筛去 and/or 这类词，advmod 用于筛去 then 这类词等等
    CUT_EXCLUDE = ['mark', 'punct', 'cc', 'conj', 'advcl', 'ccomp', 'prep', 'pcomp', 'preconj', 'advmod']

    def __init__(self, core, keywords_path=None):
        """
        初始化依赖分析器
        :param core: spacy 使用的 core
        :param keywords_path: 仅用于 tokenize 方便，为 None 表示不处理
        """
        self._nlp = spacy.load(core)
        self._matcher = DependencyMatcher(self._nlp.vocab)
        self.doc = None

        with open(keywords_path, 'r') as f:
            keywords = list(filter(lambda x: x != '', map(lambda x: x.strip(), f.readlines())))
            for keyword in keywords:
                self._nlp.tokenizer.add_special_case(keyword, [{ORTH: keyword}])

    def analyze_line(self, line):
        """
        传入一个句子进行分析。
        再次调用此函数会分析新的句子，但注意 patterns 并不会因此重置，重置需要使用 clear_patterns()。
        """
        self.doc = self._nlp(line)

    def add_patterns(self, key, patterns):
        """ 添加要搜索的 patterns """
        self._matcher.add(key, patterns)

    def clear_patterns(self):
        """ 清空 patterns """
        self._matcher = DependencyMatcher(self._nlp.vocab)

    def search_patterns(self):
        """ 在当前分析的句子中进行模板匹配 """
        assert self.doc is not None, 'You need call analyze_line(line) before searching.'
        return self._matcher(self.doc)

    def draw_dependency_tree(self, use_graphviz=True, filename='dp.gv'):
        """
        绘制依赖分析树
        :param use_graphviz: 为 True 时使用 graphviz 绘制，False 时使用 displacy 绘制
        :param filename: 使用 graphviz 绘制时的文件名
        """
        if not use_graphviz:
            displacy.serve(self.doc, style='dep')
        else:
            filepath = os.path.join(TMP_DIR, filename)
            dot = graphviz.Digraph()
            for ent in self.doc:
                dot.node(str(ent.idx), ent.text)
                if ent.head != ent:
                    dot.edge(str(ent.head.idx), str(ent.idx), ent.dep_)
            dot.render(filepath, view=True)

    def subtree(self, token, exclude=None):
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

    def subtree2str(self, subtree):
        """ 将 [Token, ...] 格式的列表转为字符串 """
        ret = ' '.join(map(lambda x: str(x), subtree))
        return ret.replace(' - ', '-').replace('( ', '(').replace(' )', ')')

    def recursive_prepend(self, clause, prefix, sep=' '):
        """
        为 clause 表示的三元组树状结构递归添加前缀，返回添加完毕之后的元组
        :param clause: 三元组树状结构的根
        :param prefix: 要添加的前缀
        :param sep: 字符串拼接时的间隔符
        """
        if isinstance(clause, tuple):
            return (self.recursive_prepend(clause[0], prefix),
                    self.recursive_prepend(clause[1], prefix), clause[2])
        else:
            return prefix + sep + clause

    def cut_clause(self, token):
        """
        切割 and / or 等子句，返回格式形如 ret_clause := (clause, clause, 'and'/'or') 或者单个最小子句
        :param token: 以 token 为根的子树开始切割
        """
        cc = None
        sub_root = None  # 子句的 root
        nsubj = None
        prep = None
        pcomp = None  # token、prep 和 pcomp 都可能出现 cc 儿子，此时需要进行递归切割
        for child in token.children:
            if child.dep_ == 'cc' and child.lemma_ in DependencyAnalyzer.CUT_TARGET:
                assert cc is None, '理应不会出现两个 cc'
                cc = child.lemma_
            if child.dep_ == 'conj':
                assert sub_root is None, '理应不会出现两个 conj'
                sub_root = child
            if child.dep_ == 'nsubj':
                assert nsubj is None, '理应不会出现两个 nsubj'
                nsubj = child
            # if child.dep_ == 'prep':
            #     assert prep is None, '理应不会出现两个 prep'
            #     prep = child
            if child.dep_ == 'pcomp':
                assert pcomp is None, '理应不会出现两个 pcomp'
                pcomp = child
        # 当不存在 prep、pcomp 时，clause1 为第一个子句或整个句子（取决于 token 子依赖中是否存在 cc）
        # 当存在 prep 或 pcomp 时，clause1 为需要递归添加的前缀
        clause1 = self.subtree(token, exclude=DependencyAnalyzer.CUT_EXCLUDE)
        clause1 = self.subtree2str(clause1)

        if cc is None:
            if prep is not None:
                return self.recursive_prepend(self.cut_clause(prep), clause1)
            elif pcomp is not None:
                return self.recursive_prepend(self.cut_clause(pcomp), clause1)
            else:
                return clause1
        else:
            assert sub_root is not None, '出现 and/or 时理应有 conj'
            clause2 = self.cut_clause(sub_root)

            # 考虑是否传递 clause1 的主语给 clause2
            nsubj_sent = self.subtree2str(self.subtree(nsubj)) if nsubj is not None else None
            need_pass_nsubj = True
            for child in sub_root.children:
                if child.dep_ == 'nsubj':
                    need_pass_nsubj = False  # clause2 有主语，不需要传递
            if need_pass_nsubj and nsubj_sent is not None:
                clause2 = self.recursive_prepend(clause2, nsubj_sent)

            return (clause1, clause2, cc)


def analyze_lack_header(sent):
    from textual_entailment import predictor
    """ 检查句子是否满足 if-then，并返回分割的子句，暂时来说满足时返回 True，不满足时返回 False """
    if re.search('header', sent, re.IGNORECASE) is None:
        return False
    return predictor.predict(premise=sent, hypothesis='lack a header')['probs'][0] > 0.55


def analyze_if_then(sent):
    """ 检查句子是否满足 if-then，并返回分割的子句，不满足时返回 None """
    try:
        da = DependencyAnalyzer(CORE, KEYWORDS_PATH)
        da.analyze_line(sent)
        key = 'if-then'  # 仅用于作为唯一描述
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
        da.add_patterns(key, [pattern])
        matches = da.search_patterns()
        if len(matches) > 0:
            if_verb = da.doc[matches[0][1][1]]
            then_verb = if_verb.head
            ret = {'if': da.cut_clause(if_verb), 'then': da.cut_clause(then_verb)}
            if then_verb.dep_ == 'ccomp':
                ret['then'] = (ret['then'], da.cut_clause(then_verb.head), 'and')
            return ret
        else:
            return None
    except AssertionError as e:
        logger.error('AssertionError, sent: ' + sent)
        logger.error('message: ' + e.__str__())
        return None


def analyze_must(sent):
    """ 检查句子是否满足 server must/should，不满足时返回 None，满足时返回切割后的三元组树状结构 """
    try:
        da = DependencyAnalyzer(CORE, KEYWORDS_PATH)
        da.analyze_line(sent)
        key = 'server-must'  # 仅用于作为唯一描述
        pattern = [
            {
                "RIGHT_ID": "server",
                "RIGHT_ATTRS": {"LEMMA": "server", "DEP": "nsubj"}
            },
            {
                "LEFT_ID": "server",
                "RIGHT_ID": "must-verb",
                "RIGHT_ATTRS": {},
                "REL_OP": "<"
            },
            {
                "LEFT_ID": "must-verb",
                "RIGHT_ID": "must",
                "RIGHT_ATTRS": {"LEMMA": {"IN": ["should", "must"]}, "DEP": "aux"},
                "REL_OP": ">"
            }
        ]
        da.add_patterns(key, [pattern])
        matches = da.search_patterns()
        if len(matches) > 0:
            must_verb = da.doc[matches[0][1][1]]
            return da.cut_clause(must_verb)
        else:
            return None
    except AssertionError as e:
        logger.error('AssertionError, sent: ' + sent)
        logger.error('message: ' + e.__str__())
        return None


def analyze_respond_status_code(sent):
    """
    检查句子是否满足 respond xxx code，暂时返回 True/False
    包括 respond with xxx/code/status，
    """
    try:
        if re.search('\d\d\d', sent) is None:
            return False
        da = DependencyAnalyzer(CORE, KEYWORDS_PATH)
        da.analyze_line(sent)
        key = 'respond_status_code'  # 仅用于作为唯一描述
        pattern = [
            {
                "RIGHT_ID": "respond",
                "RIGHT_ATTRS": {"LEMMA": "respond"}
            },
            {
                "LEFT_ID": "respond",
                "RIGHT_ID": "with",
                "RIGHT_ATTRS": {"LEMMA": "with", "DEP": "prep"},
                "REL_OP": ">"
            }
        ]
        da.add_patterns(key, [pattern])
        matches = da.search_patterns()
        for match in matches:
            respond_word = da.doc[match[1][0]]
            with_word = da.doc[match[1][1]]
            for child in respond_word.children:
                if child.dep_ == 'aux' and child.lemma_ == 'may':  # 筛除 may respond 的情况
                    return False
            for child in with_word.children:
                if child.dep_ == 'pobj' and (
                        child.lemma_ in ['code', 'status'] or re.search('\d\d\d', child.lemma_) is not None):
                    return True
        return False
    except AssertionError as e:
        logger.error('AssertionError, sent: ' + sent)
        logger.error('message: ' + e.__str__())
        return False


def test_draw_dependency_tree(sent):
    """ 测例，绘制依赖树 """
    # 初始化 Analyzer
    da = DependencyAnalyzer(CORE, KEYWORDS_PATH)
    # 分析句子
    da.analyze_line(sent)
    # 依赖树绘制
    da.draw_dependency_tree(use_graphviz=True, filename='dp.gv')


def test_if_then(sent):
    """ 测例，检查句子是否满足 if-then，若是则输出分析结果 """
    ret = analyze_if_then(sent)
    if ret is not None:
        print('IF:')
        print(ret['if'])
        print('THEN:')
        print(ret['then'])
    else:
        print('Not if-then.')
    print('Sentence:')
    print(sent)
    print('-' * 100)
    print()



if __name__ == '__main__':
    sent = 'If a Transfer-Encoding header field is present in a request and the chunked transfer coding is not the final encoding, the message body length cannot be determined reliably; the server MUST respond with the 400 (Bad Request) status code and then close the connection.'
    test_if_then(sent)

