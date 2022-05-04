from allennlp_models import pretrained
import logging
# 忽略无关logging
logging.getLogger('allennlp.common.params').disabled = True
logging.getLogger('allennlp.nn.initializers').disabled = True
logging.getLogger('allennlp.modules.token_embedders.embedding').setLevel(logging.DEBUG)
logging.getLogger('urllib3.connectionpool').disabled = True
logging.getLogger('allennlp.common.file_utils').disabled = True
logging.getLogger('allennlp.common.plugins').disabled = True
logging.getLogger('allennlp.models.archival').disabled = True
logging.getLogger('allennlp.data.vocabulary ').disabled = True

predictor = pretrained.load_predictor('pair-classification-roberta-mnli')


if __name__ == '__main__':
    print(predictor.predict(
        premise="A server MUST respond with a 400 (Bad Request) status code to any request message that contains a Host header field with an invalid field-value.",
        hypothesis="HTTP version is 1.1"
    ))