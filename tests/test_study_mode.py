from app import app
import json
import pytest
from services import feedback_learning, study_mode


def test_off_never_calls_learner_and_keeps_manual_correction(monkeypatch):
    monkeypatch.setattr(feedback_learning, 'enabled', lambda: True)
    def forbidden(*args):
        raise AssertionError('AI off must not invoke the learner')
    monkeypatch.setattr(feedback_learning, 'suggestions', forbidden)
    data=app.test_client().post('/api/parse', json={'text':'risperidnoe 2mg QD','study_ai':'off'}).json
    assert data['study']['ai_invocation_count']==0
    assert data['items'][0]['learned_suggestions']==[]
    assert data['items'][0]['correction_suffix']
    assert 'feedback_token' not in data['items'][0]


@pytest.mark.parametrize('mode', ['gemma', 'nemotron', 'xing', 'lfm', 'qwen'])
def test_models_use_same_prompt_and_require_human_confirmation(monkeypatch, mode):
    output=json.dumps({'status':'candidate_found','candidates':[{'standard_name':'risperidone','confidence':'high','reason':'철자 후보'}]})
    seen=[]
    def infer(messages, *args):
        seen.append(messages)
        return output, {'returned_model':'test-model'}
    monkeypatch.setattr(study_mode,'_cloud',infer)
    monkeypatch.setattr(study_mode,'_qwen',infer)
    monkeypatch.setattr(study_mode,'capabilities',lambda:{'qwen':{'available':True,'model':'qwen2.5:7b'}})
    data=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode,'study_api_key':'TEST_SECRET_ONLY'}).json
    assert data['study']['ai_invocation_count']==1
    assert data['study']['ai_candidate_count']==1
    assert data['study']['ai_success_count']==1
    assert len(data['study']['calls'][0]['prompt_hash'])==64
    assert data['items'][0]['status']=='unknown_drug'
    assert 'feedback_token' not in data['items'][0]
    assert not data['items'][0]['learned_suggestions'][0]['auto_accepted']
    assert 'TEST_SECRET_ONLY' not in json.dumps(data)
    assert '2mg' not in json.dumps(seen)
    assert 'QD' not in json.dumps(seen)


def test_modes_preserve_conversion_and_reject_invalid_mode():
    client=app.test_client()
    outputs=[client.post('/api/parse',json={'text':'risperidone 2mg QD','study_ai':m}).json for m in ['off','gemma','nemotron','xing','lfm']]
    assert all(o['totals']==outputs[0]['totals'] for o in outputs)
    assert client.post('/api/parse',json={'text':'risperidone 2mg QD','study_ai':True}).status_code==400


def test_missing_key_and_failed_inference_never_look_successful(monkeypatch):
    client=app.test_client()
    data=client.post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':'gemma'}).json
    assert data['study']['ai_available'] is False
    assert data['study']['calls'][0]['status']=='unavailable'
    def failure(*args):
        raise RuntimeError('SECRET must not be returned')
    monkeypatch.setattr(study_mode,'_cloud',failure)
    response=client.post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':'gemma','study_api_key':'TEST_SECRET_ONLY'})
    assert response.json['study']['calls'][0]['status']=='error'
    assert response.json['study']['ai_success_count']==0
    assert 'SECRET' not in response.get_data(as_text=True)
    assert response.headers['Cache-Control']=='no-store'


def test_cloud_transport_uses_only_fixed_destination(monkeypatch):
    observed={}
    class Reply:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,n): return json.dumps({'choices':[{'message':{'content':'{}'}}], 'model':'example'}).encode()
    class Transport:
        def open(self,req,timeout):
            observed.update(url=req.full_url,body=json.loads(req.data),auth=req.get_header('Authorization'),timeout=timeout)
            return Reply()
    monkeypatch.setattr(study_mode,'build_opener',lambda *args:Transport())
    output,meta=study_mode._cloud([],study_mode.MODELS['lfm'],'TEST_KEY')
    assert observed['url']=='https://openrouter.ai/api/v1/chat/completions'
    assert observed['body']['model']=='liquid/lfm-2.5-2.6b:free'
    assert observed['body']['provider']['allow_fallbacks'] is False
    assert observed['body']['provider']['max_price']=={'prompt':0,'completion':0,'request':0}
    assert observed['body']['provider']['require_parameters'] is True
    assert observed['body']['reasoning']=={'enabled':False}
    assert 'models' not in observed['body']
    assert observed['auth']=='Bearer TEST_KEY'
    assert meta['returned_model']=='example'


@pytest.mark.parametrize('model', ['openai/gpt-5.4', 'openrouter/free', 'google/gemma-4-31b-it', 'unlisted/model:free'])
def test_non_selected_or_paid_model_is_rejected_before_transport(monkeypatch, model):
    def forbidden(*args):
        raise AssertionError('Disallowed model reached transport')
    monkeypatch.setattr(study_mode, 'build_opener', forbidden)
    with pytest.raises(ValueError, match='free_model_required'):
        study_mode._cloud([],model,'TEST_KEY')


@pytest.mark.parametrize('mode', ['gpt','claude','gemini','deepseek',{},[]])
def test_old_paid_modes_are_rejected(mode):
    response=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode})
    assert response.status_code==400


def test_free_catalog_and_protocol_are_explicit():
    data=app.test_client().get('/api/study-status').json
    assert data['protocol']=='ap-study-3-free'
    assert data['cost_policy']=='free_cloud_only'
    assert len(data['cloud_models'])==4
    assert all(m.endswith(':free') for m in data['cloud_models'].values())


def test_rate_limit_is_recorded_without_exposing_error_body(monkeypatch):
    from urllib.error import HTTPError
    def failure(*args):
        raise HTTPError('https://openrouter.ai/api/v1/chat/completions',429,'SECRET_MESSAGE',{},None)
    monkeypatch.setattr(study_mode,'_cloud',failure)
    r=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':'gemma','study_api_key':'TEST_SECRET_ONLY'})
    call=r.json['study']['calls'][0]
    assert call['status']=='error' and call['http_status']==429
    assert r.json['study']['ai_success_count']==0
    assert 'SECRET' not in r.get_data(as_text=True)
