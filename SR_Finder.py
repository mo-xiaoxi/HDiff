import os
import sys
import stanza
import pandas as pd
import traceback
import nltk
from config import CLEANED_RFC_DIR, SR_DIR
from nltk.corpus import wordnet
from optparse import OptionParser
from config import logger, BASE_DIR
from src.util import banner, download_rfc, read_data


def init():
    stanza.download('en')
    nltk.download('wordnet')


# 得到情感强烈的句子
def get_high_sentiment_sentences(s):
    nlp = stanza.Pipeline(lang='en', processors='tokenize,sentiment')
    doc = nlp(s)
    result = []
    for i, sentence in enumerate(doc.sentences):
        if sentence.sentiment != 1:
            result.append(sentence.text)
    return result


def get_result(input_path, output_path):
    data = read_data(input_path)
    result = get_high_sentiment_sentences(data)
    # list转dataframe
    df = pd.DataFrame(result, columns=['sentences'])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # 保存到本地excel
    df.to_csv(output_path, index=False, encoding='utf-8')


# 扩展同义词和反义词
def expand_words(words=['refuse']):
    synonyms = []
    antonyms = []
    for w in words:
        for syn in wordnet.synsets(w):
            for l in syn.lemmas():
                synonyms.append(l.name())
                if l.antonyms():
                    antonyms.append(l.antonyms()[0].name())
        print(set(synonyms))
        print(set(antonyms))
    return


def debug():
    s = 'In particular, the Host and Connection header fields ought to be implemented by all HTTP/1.x implementations whether or not they advertise conformance with HTTP/1.1'
    nlp = stanza.Pipeline(lang='en', processors='tokenize,sentiment')
    doc = nlp(s)
    print(doc)


def parse_options():
    parser = OptionParser()
    parser.add_option("-r", "--rfc", dest="rfc", default=None,
                      help="The RFC number")
    parser.add_option("-p", "--path", dest="path", default=None, help="The RFC file to load.")
    (options, args) = parser.parse_args()
    return options


def run_error(errmsg):
    logger.error(("Usage: python " + sys.argv[0] + " [Options] use -h for help"))
    logger.error(("Error: " + errmsg))
    sys.exit()


def run():
    options = parse_options()

    if options.path is not None:
        input_path = BASE_DIR + '/' + options.path
        file_name = os.path.basename(input_path)
        output_path = '{}/{}.csv'.format(SR_DIR, file_name).replace('.txt', '')
    elif options.rfc is not None:
        rfc_number = str(options.rfc)
        download_rfc(rfc_number)
        input_path = "{}/{}.txt".format(CLEANED_RFC_DIR, rfc_number)
        output_path = "{}/{}.csv".format(SR_DIR, rfc_number)
    else:
        init()
        errmsg = "You must set the parameters (--rfc or --inpath)."
        run_error(errmsg)
        sys.exit()
    logger.debug("input:{}, output:{}".format(input_path, output_path))
    get_result(input_path, output_path)
    logger.info("All Task Done! :)")


def main():
    banner()
    try:
        run()
    except Exception as e:
        traceback.print_exc()
        run_error(errmsg=str(e))


if __name__ == '__main__':
    # init()
    # expand_words()
    main()
