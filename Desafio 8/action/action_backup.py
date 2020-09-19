from cgi import parse_multipart, parse_header
from io import BytesIO
from base64 import b64decode
from ibm_watson import NaturalLanguageUnderstandingV1, SpeechToTextV1, ApiException
from ibm_cloud_sdk_core.authenticators import BasicAuthenticator, IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, EmotionOptions, SentimentOptions

import json, os
import uuid;


general_sentiment = 0

recommendations = [
    { 'entity': 'SEGURANCA', 'car': 'Toro' },
    { 'entity': 'CONSUMO', 'car': 'Fiat 500' }, #definido
    { 'entity': 'DESEMPENHO', 'car': 'Marea' },
    { 'entity': 'MANUTENCAO', 'car': 'Fiorino' }, #definido
    {'entity': 'CONFORTO', 'car': 'Cronos'}, #definido
    {'entity': 'DESIGN', 'car': 'Renegade'},
    {'entity': 'ACESSORIOS', 'car': 'Argo'},
]

def getEntities(model_id, natural_language_understanding, text):
    global general_sentiment
    response = natural_language_understanding.analyze(
        text=text,
        features=Features(
            entities=EntitiesOptions(
                model=model_id,
                sentiment=True,
                emotion=True),
            sentiment=SentimentOptions()
        )
    ).get_result()
    python_obj = json.loads(json.dumps(response, indent=2))
    #return { 'transcript': python_obj }
    entities = []
    if len(python_obj['entities']) > 0:
        general_sentiment = python_obj['sentiment']['document']['score']
        for entity in python_obj['entities']:
            entities.append({ 'entity': entity['type'], 'sentiment': entity['sentiment']['score'], 'mention': entity['text'] })
        return entities
    else:
        return {}

#def removeElement(nums, min_sentiment):
#    new = []
#    for i, n in enumerate(nums):
#        if n != min_sentiment and i < len(nums):
#            new.append(n)
#    return new

def main(args):

    model_id = '956978fa-b5e6-4108-96ad-3367bde3478b';

    #NLU
    authenticatorNLU = IAMAuthenticator('bbTi93KoBLq60M_Lj5fMpXInVoYI_CJFp66VBBTtsmhE')
    natural_language_understanding = NaturalLanguageUnderstandingV1(version='2020-08-01',authenticator=authenticatorNLU)
    natural_language_understanding.set_service_url('https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/340adba1-4277-46f0-aca3-412077e9b53d')

    _c_type, p_dict = parse_header(
        args['__ow_headers']['content-type']
    )
    
    decoded_string = b64decode(args['__ow_body'])

    p_dict['boundary'] = bytes(p_dict['boundary'], "utf-8")
    p_dict['CONTENT-LENGTH'] = len(decoded_string)

    multipart_data = parse_multipart(BytesIO(decoded_string), p_dict)

    name_audio = uuid.uuid4().hex.upper()[0:50]+'.flac'

    try:
        fo = open(name_audio, 'wb')
        fo.write(multipart_data.get('audio')[0])
        fo.close()
    except:
        fo = False

    if fo: # file audio
        stt_authenticator = BasicAuthenticator(
            'apikey',
            'MaKHsSDKPKgfvQRPDfbFhXSMfvY-JtogeRyQIZn6WPem'
        )
        stt = SpeechToTextV1(authenticator=stt_authenticator)
        stt.set_service_url('https://api.us-south.speech-to-text.watson.cloud.ibm.com')
        with open(
            os.path.join(
                os.path.dirname(__file__), './.',
                name_audio
            ), 'rb'
        ) as audio_file:
            stt_result = stt.recognize(
                audio=audio_file,
                content_type='audio/flac',
                model='pt-BR_BroadbandModel'
            ).get_result()
        # print(json.dumps(stt_result, indent=2))
        transcript_audio = stt_result['results'][0]['alternatives'][0]['transcript']
        entities = getEntities(model_id, natural_language_understanding, transcript_audio)
    else:
        text = multipart_data.get('text')[0]
        entities = getEntities(model_id, natural_language_understanding, text)

    #entities[1]['sentiment'] = -0.92
    #entities[2]['sentiment'] = -0.98
    #entities[3]['sentiment'] = -0.92
    #entities[4]['sentiment'] = -0.96

    if general_sentiment > 0:
        return { "recommendation": "", "entities": entities }
    elif general_sentiment < 0:
        nums = []
        repetidos = []
        definidos = []
        for i, item in enumerate(entities):
            nums.append(item['sentiment'])
        min_sentiment = min(nums)
        if len(nums) == len(set(nums)):
            definidos.append(min_sentiment)
        else:
            for idx,sentiment in enumerate(nums):
                if sentiment == min_sentiment:
                    repetidos.append(idx)

            if len(repetidos) > 1:
                definidos.append(entities[min(repetidos)])
            elif len(repetidos) == 1:
                definidos.append(entities[repetidos[0]]) #min_sentiment
                #vector_new = removeElement(nums, min_sentiment)
                #second_min_sentiment = min(vector_new)
                #difference = vector_new - second_min_sentiment
                #if difference < 0.1:
                #    definidos.append(min_sentiment)
                #else:
                #    definidos.append(min_sentiment)
                #definidos.append(min_sentiment)
                #definidos.append(min(vector_new))

        recommendation = ""
        for item in recommendations:
            if item['entity'] == definidos[0]['entity']:
                recommendation = item['car']
        return {
            'recommendation': recommendation, #entities[3]['sentiment']
            'entities': entities
        }

    #return entities
    return {
        "recommendation": "",
        #"general_sentiment": general_sentiment,
        "entities": entities
    }
