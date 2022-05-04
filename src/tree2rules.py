import copy
from src.dp_analyzer import DependencyAnalyzer


def generate_rule_tree(ca, clause_tree, type):
    """
    遍历 DependencyAnalyzer 得到的 clause 树状结构，并使用 ClauseAnalyzer 进行处理
    :param ca: ClauseAnalyzer object，用于对每个子句进行处理
    :param clause_tree: tuple，由子句组成的三元组树状结构的根
    :return rule_tree: tuple，由准模板项组成的三元组树状结构的根
    """
    if isinstance(clause_tree, tuple):
        rule_tree = (
            generate_rule_tree(ca, clause_tree[0], type), generate_rule_tree(ca, clause_tree[1], type), clause_tree[2])
    elif isinstance(clause_tree, str):
        rule_tree = ca.analyze_clause(clause_tree, type)
    else:
        assert False, 'clause_tree 类型错误：%s，必须为 tuple/str' % str(type(clause_tree))
    return rule_tree


def expand_rule_tree(rule_tree, rule_sets):
    """
    展开准模板树，生成准模板列表
    :param rule_tree: tuple，由准模板项组成的三元组树状结构的根
    :param rule_sets: list，需要对这个列表中的每一项附加上当前子树对应的规则，最外层传入时应为 [{}]
    :ret ret_rule_sets: list，更新后的规则集列表
    """
    ret_rule_sets = []
    if isinstance(rule_tree, tuple):
        if rule_tree[2] == DependencyAnalyzer.OR:
            ret_rule_sets.extend(expand_rule_tree(rule_tree[0], rule_sets))
            ret_rule_sets.extend(expand_rule_tree(rule_tree[1], rule_sets))
        elif rule_tree[2] == DependencyAnalyzer.AND:
            ret_rule_sets = expand_rule_tree(rule_tree[0], rule_sets)
            ret_rule_sets = expand_rule_tree(rule_tree[1], ret_rule_sets)
        else:
            assert False, '逻辑类型错误，%s' % str(rule_tree[2])
    elif isinstance(rule_tree, dict):
        ret_rule_sets = copy.deepcopy(rule_sets)
        for rule_set in ret_rule_sets:
            rule_set.update(rule_tree)
    else:
        assert False, 'rule_tree 类型错误：%s，必须为 tuple/str' % str(type(rule_tree))
    return ret_rule_sets
