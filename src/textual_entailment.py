from allennlp_models import pretrained
import logging
from config import logger

# 忽略无关logging
logging.getLogger('allennlp.common.params').disabled = True
logging.getLogger('allennlp.nn.initializers').disabled = True
logging.getLogger('allennlp.modules.token_embedders.embedding').setLevel(logging.DEBUG)
logging.getLogger('urllib3.connectionpool').disabled = True
logging.getLogger('allennlp.common.file_utils').disabled = True
logging.getLogger('allennlp.common.plugins').disabled = True
logging.getLogger('allennlp.models.archival').disabled = True
logging.getLogger('allennlp.data.vocabulary ').disabled = True

te_model = "pair-classification-roberta-mnli"
logger.debug("Loading TE Model:{}".format(te_model))
predictor = pretrained.load_predictor(te_model)
logger.debug("Loading Succ!")

if __name__ == '__main__':
    print(predictor.predict(
        premise="A server MUST respond with a 400 (Bad Request) status code to any request message that contains a Host header field with an invalid field-value.",
        hypothesis="HTTP version is 1.1"
    ))
