from src.util import random_case_string, flatten, cartesian, random_repeat
from src.parser import GrammarError

MAX_TRY = 3


# TODO For high-complexity generation, easy to run out of memory. Need to support random generation in later stage
class NodeBuilder():
    """An external visitor class."""

    def __init__(self):
        self._node_method_cache = {}

    def __call__(self, node):
        return self.build(node)

    def build(self, node):
        """build node.  This method invokes the appropriate method for the node type."""
        return self._node_method(node)(node)

    @staticmethod
    def _dont_build(node):  # pylint: disable=unused-argument
        """ Skip node visit."""
        node_name = node.__class__.__name__.casefold()
        raise GrammarError("The {} form is not yet supported".format(node_name))
        # return None

    def _node_method(self, node):
        """Looks up method for node using node.name."""
        node_name = node.__class__.__name__.casefold()
        try:
            node_method = self._node_method_cache[node_name]
        except KeyError:
            try:
                node_method = getattr(self, "build_%s" % node_name.replace("-", "_"))
            except AttributeError:
                node_method = self._dont_build

            self._node_method_cache[node_name] = node_method

        return node_method


class ABNFGrammarNodeBuilder(NodeBuilder):
    def __init__(self, rule_cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rule_cls = rule_cls

    def build_alternation(self, node):
        """Creates an Alternation object from alternation node."""
        args = list(filter(None, map(self.build, node.parsers)))
        return flatten(args) if len(args) > 1 else args[0]

    def build_literal(self, node):
        if isinstance(node.value, tuple):
            first_char, last_char = node.value
            result = []
            for i in range(ord(first_char), ord(last_char) + 1):
                result.append(chr(i))
            return result
        if node.case_sensitive:
            return [node.value]
        # todo more elegant random variant case return
        result = []
        for i in range(MAX_TRY):
            result.append(random_case_string(node.value))
        result = list(set(result))
        return result

    def build_concatenation(self, node):
        """Creates a Concatention object from concatenation node."""
        args = list(filter(None, map(self.build, node.parsers)))
        return cartesian(*args) if len(args) > 1 else args[0]

    def build_rule(self, node):
        """Visits a rule node, returning a Rule results."""
        args = list(filter(None, map(self.build, [node.children])))
        # print(args)
        return flatten(args) if len(args) > 1 else args[0]

    def build_option(self, node):
        """
        构建 option
        """
        args = list(filter(None, map(self.build, [node.alternation])))
        result = flatten(args)
        if '' not in result:
            result.append('')
        return result

    def build_repetition(self, node):
        """Creates a Repetition object from repetition node."""
        data = self.build(node.element)
        res = random_repeat(node.repeat.min, node.repeat.max, data)
        return res

    def build_element(self, node):
        """Creates an Alternation object from elements node."""
        return next(filter(None, map(self.build, node.parsers)))

    def build_elements(self, node):
        """Creates an Alternation object from elements node."""
        raise GrammarError("The elements form is not yet supported")

    def build_group(self, node):
        """Returns an Alternation object from group node."""
        raise GrammarError("The group form is not yet supported")

    def build_prose_val(self, node):
        """
         uri-host = <host, see [RFC3986], Section 3.2.2>
         prose_val
        """
        raise GrammarError("The prose_val form is not yet supported")
