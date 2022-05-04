import os
import sys
import traceback
from config import logger
from src.parser import Rule
from src.builder import ABNFGrammarNodeBuilder
from src.util import banner, get_abnf_rule, save_json
from optparse import OptionParser
from config import BASE_DIR



"""
ABNF gengerator
"""


def generator(target):
    rule = Rule(target)
    assert rule.children is not None
    builder = ABNFGrammarNodeBuilder(rule)
    results = builder.build(rule.children)
    return results


def parse_options():
    parser = OptionParser()
    parser.add_option("-r", "--rfc", dest="rfc", default=None,
                      help="The RFC number of the ABNF rule to be extracted.")
    parser.add_option("-i", "--inpath", dest="inpath", default=None, help="The ABNF file to load.")
    parser.add_option("-t", "--target", dest="target", default="HTTP-version",
                      help="The field to be fuzzed in ABNF rules.")
    parser.add_option("-d", "--dir", dest="dir", default=BASE_DIR + "/data/fuzz_data/",
                      help="Write output files to directory <dir>")
    (options, args) = parser.parse_args()
    return options


def run_error(errmsg):
    logger.error(("Usage: python " + sys.argv[0] + " [Options] use -h for help"))
    logger.error(("Error: " + errmsg))
    sys.exit()


def run():
    options = parse_options()
    if options.inpath is not None:
        path = BASE_DIR + '/' + options.inpath
        logger.info(path)
        Rule.from_file(path)
    elif options.rfc is not None:
        rule_source = get_abnf_rule(str(options.rfc))
        Rule.from_txt(rule_source)
    else:
        errmsg = "You must set the parameters (--rfc or --inpath)."
        run_error(errmsg)
    target = options.target
    results = generator(target)
    logger.info(results)
    data = {target: results}
    outpath = "{}/{}.json".format(options.dir, target)
    save_json(data, outpath)
    logger.info("All Task Done! :)")


def main():
    banner()
    try:
        run()
    except Exception as e:
        traceback.print_exc()
        run_error(errmsg=str(e))


if __name__ == '__main__':
    main()
