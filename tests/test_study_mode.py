from app import app
import json
import pytest
from services import feedback_learning, study_mode

KEYS = {'google': 'AIza'+'TEST_ONLY_'*4, 'groq': 'gsk_'+'TEST_ONLY_'*4}
CANDIDATE = json.dumps({'status':'candidate_found','candidates':[{'standard_name':'risperidone','confidence':'high','reason':'철자 후보'}]})


def credentials(mode):
    return dict(study_api_key=KEYS[study_mode.PROVIDERS[mode]],study_free_tier_confirmed=True) if mode in study_mode.MODELS else {}


def test_off_never_calls_learner_and_keeps_manual_correction(monkeypatch):
    monkeypatch.setattr(feedback_learning, 'enabled', lambda: True)
    def forbidden(*args): raise AssertionError('AI off must not invoke the learner')
    monkeypatch.setattr(feedback_learning,'suggestions',forbidden)
    monkeypatch.setattr(study_mode,'_cloud',forbidden)
    data=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':'off'}).json
    assert data['study']['ai_invocation_count']==0
    assert data['items'][0]['learned_suggestions']==[]
    assert data['items'][0]['correction_suffix']
    assert 'feedback_token' not in data['items'][0]


@pytest.mark.parametrize('mode', [*study_mode.MODELS,'qwen'])
def test_models_use_same_prompt_and_require_human_confirmation(monkeypatch,mode):
    seen=[]
    def infer(messages,*args):
        seen.append(messages)
        return CANDIDATE,{'returned_model':'test-model'}
    monkeypatch.setattr(study_mode,'_cloud',infer)
    monkeypatch.setattr(study_mode,'_qwen',infer)
    monkeypatch.setattr(study_mode,'capabilities',lambda:{'qwen':{'available':True,'model':'qwen2.5:7b'}})
    data=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode,**credentials(mode)}).json
    assert data['study']['ai_invocation_count']==1
    assert data['study']['ai_candidate_count']==1
    assert data['study']['ai_success_count']==1
    assert len(data['study']['calls'][0]['prompt_hash'])==64
    assert data['items'][0]['status']=='unknown_drug'
    assert 'feedback_token' not in data['items'][0]
    assert not data['items'][0]['learned_suggestions'][0]['auto_accepted']
    assert 'TEST_ONLY' not in json.dumps(data)
    assert '2mg' not in json.dumps(seen) and 'QD' not in json.dumps(seen)


def test_modes_preserve_conversion():
    client=app.test_client()
    outputs=[client.post('/api/parse',json={'text':'risperidone 2mg QD','study_ai':m}).json for m in ['off',*study_mode.MODELS]]
    assert all(o['totals']==outputs[0]['totals'] for o in outputs)


@pytest.mark.parametrize('mode',list(study_mode.MODELS))
@pytest.mark.parametrize('confirmed',[None,False,'true',1])
def test_unconfirmed_account_never_reaches_transport(monkeypatch,mode,confirmed):
    def forbidden(*args): raise AssertionError('Unconfirmed account made an AI request')
    monkeypatch.setattr(study_mode,'_cloud',forbidden)
    data=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode,**credentials(mode),'study_free_tier_confirmed':confirmed}).json
    assert data['study']['ai_available'] is False
    assert data['study']['ai_invocation_count']==0
    assert data['study']['calls'][0]['reason']=='free_tier_not_confirmed'


@pytest.mark.parametrize('mode',[*study_mode.MODELS,'qwen'])
def test_preview_never_calls_any_ai_even_with_valid_credentials(monkeypatch,mode):
    def forbidden(*args): raise AssertionError('Preview made an AI request')
    monkeypatch.setattr(study_mode,'_cloud',forbidden)
    monkeypatch.setattr(study_mode,'_qwen',forbidden)
    data=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode,'study_preview':True,**credentials(mode)}).json
    assert data['study']['preview'] is True
    assert data['study']['ai_invocation_count']==0
    assert data['study']['calls'][0]['reason']=='preview_no_requests'


@pytest.mark.parametrize('mode',list(study_mode.MODELS))
@pytest.mark.parametrize('key',[None,'https://openrouter.ai/settings/keys','sk-or-v1-'+'x'*40,'x'*30])
def test_missing_wrong_provider_or_openrouter_key_is_blocked(monkeypatch,mode,key):
    def forbidden(*args): raise AssertionError('Invalid key reached transport')
    monkeypatch.setattr(study_mode,'_cloud',forbidden)
    data=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode,'study_api_key':key,'study_free_tier_confirmed':True}).json
    assert data['study']['ai_available'] is False
    assert data['study']['calls'][0]['status']=='unavailable'


@pytest.mark.parametrize('mode',list(study_mode.MODELS))
def test_transport_fixed_provider_and_model_no_fallback_or_retry(monkeypatch,mode):
    observed=[]
    model=study_mode.MODELS[mode];provider=study_mode.PROVIDERS[mode]
    class Reply:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,n): return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'{}'}}],'model':model}).encode()
    class Transport:
        def open(self,req,timeout):
            observed.append((req.full_url,json.loads(req.data),req.get_header('Authorization'),timeout))
            return Reply()
    monkeypatch.setattr(study_mode,'build_opener',lambda *args:Transport())
    output,meta=study_mode._cloud([],model,KEYS[provider],True)
    assert len(observed)==1
    url,body,auth,timeout=observed[0]
    assert url==study_mode.ENDPOINTS[provider]
    assert body['model']==model and body['max_tokens']==1000
    assert not {'models','provider','tools','plugins'}&body.keys()
    if mode=='google_gemma': assert 'reasoning_effort' not in body
    else: assert body['reasoning_effort']==('low' if mode.startswith('groq_oss') else 'none')
    assert auth=='Bearer '+KEYS[provider]
    assert meta['provider']==provider and meta['cost_usd'] is None


@pytest.mark.parametrize('model',['openai/gpt-5.4','openrouter/free','google/gemma-4-31b-it:free','arbitrary/model'])
def test_unlisted_model_rejected_before_transport(monkeypatch,model):
    def forbidden(*args): raise AssertionError('Unlisted model reached transport')
    monkeypatch.setattr(study_mode,'build_opener',forbidden)
    with pytest.raises(ValueError,match='selected_model_required'):
        study_mode._cloud([],model,KEYS['groq'],True)


@pytest.mark.parametrize('mode',['gemma','nemotron','xing','lfm','gpt','claude','gemini','deepseek',True,{},[]])
def test_legacy_modes_rejected(mode):
    assert app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD','study_ai':mode}).status_code==400


def test_status_discloses_account_verification_limit():
    data=app.test_client().get('/api/study-status').json
    assert data['protocol']=='ap-study-4-direct-free'
    assert data['cost_policy']=='free_tier_account_required'
    assert len(data['cloud_models'])==5
    assert set(data['cloud_providers'].values())=={'google','groq'}
    assert data['billing_verification']=='researcher_attestation_not_provider_verified'
    assert data['preview_ai_calls'] is False and data['paid_fallback'] is False


@pytest.mark.parametrize('code',[401,402,429,503])
def test_error_stops_remaining_items_and_never_exposes_secret(monkeypatch,code):
    from urllib.error import HTTPError
    calls=[]
    def failure(*args):
        calls.append(1)
        raise HTTPError('https://api.groq.com/openai/v1/chat/completions',code,'SECRET_MESSAGE',{},None)
    monkeypatch.setattr(study_mode,'_cloud',failure)
    r=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD; queiapine 100mg QD','study_ai':'groq_oss20',**credentials('groq_oss20')})
    assert len(calls)==1
    meta=r.json['study']
    assert meta['calls'][0]['status']=='error' and meta['calls'][0]['http_status']==code
    assert meta['calls'][1]['reason']=='stopped_after_error'
    assert meta['ai_success_count']==0 and meta['ai_invocation_count']==1
    assert 'SECRET' not in r.get_data(as_text=True) and 'TEST_ONLY' not in r.get_data(as_text=True)
    assert r.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('change',[{'model':'different-model'},{'finish_reason':'length'}])
def test_incomplete_or_different_model_cannot_be_accepted(monkeypatch,change):
    class Reply:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,n):
            return json.dumps({'model':change.get('model',study_mode.MODELS['groq_oss20']),'choices':[{'finish_reason':change.get('finish_reason','stop'),'message':{'content':'{}'}}]}).encode()
    class Transport:
        def open(self,*args,**kwargs): return Reply()
    monkeypatch.setattr(study_mode,'build_opener',lambda *args:Transport())
    with pytest.raises(ValueError):
        study_mode._cloud([],study_mode.MODELS['groq_oss20'],KEYS['groq'],True)


def test_audit_records_full_prompt_time_settings_and_independent_repeat_labels(monkeypatch):
    seen=[]
    def infer(messages,*args):
        seen.append(messages)
        return CANDIDATE, {'returned_model':study_mode.MODELS['groq_oss20']}
    monkeypatch.setattr(study_mode,'_cloud',infer)
    calls=[]
    for index in range(1,4):
        data=app.test_client().post('/api/parse',json={
            'text':'risperidnoe 2mg QD','study_ai':'groq_oss20',
            **credentials('groq_oss20'),'study_repeat_index':index,'study_repeat_count':3}).json
        calls.append(data['study']['calls'][0])
    assert len(seen)==3 and seen[0]==seen[1]==seen[2]
    assert [c['repeat_index'] for c in calls]==[1,2,3]
    assert len({c['prompt_hash'] for c in calls})==1
    for c in calls:
        assert c['prompt_messages']==seen[0] and c['raw_response']==CANDIDATE
        assert c['started_at_utc']<=c['completed_at_utc']
        assert c['temperature_requested']==0 and c['max_output_tokens_requested']==1000
        assert c['model_revision'] is None and c['model_revision_status']=='not_verified'
        assert c['fresh_conversation'] and not c['application_response_cache']
        assert c['repeat_count']==3
    assert 'TEST_ONLY' not in json.dumps(calls)


@pytest.mark.parametrize('index,count',[(0,3),(4,3),(1,4),(True,3),(1,'3'),(2,1)])
def test_invalid_repeat_settings_rejected_before_any_inference(monkeypatch,index,count):
    def forbidden(*args): raise AssertionError('Invalid repetition called AI')
    monkeypatch.setattr(study_mode,'_cloud',forbidden)
    r=app.test_client().post('/api/parse',json={'text':'risperidnoe 2mg QD',
        'study_ai':'groq_oss20',**credentials('groq_oss20'),
        'study_repeat_index':index,'study_repeat_count':count})
    assert r.status_code==400


def test_user_agent_is_sent_for_every_provider(monkeypatch):
    seen=[]
    class Reply:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self,n): return json.dumps({'model':study_mode.MODELS['groq_oss20'],'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}).encode()
    class T:
        def open(self,req,timeout): seen.append(req.get_header('User-agent')); return Reply()
    monkeypatch.setattr(study_mode,'build_opener',lambda *a:T())
    study_mode._cloud([],study_mode.MODELS['groq_oss20'],KEYS['groq'],True)
    assert seen and 'python-urllib' not in seen[0].lower()


@pytest.mark.parametrize('raw,expected',[('<thought>plan</thought>{"status":"unknown","candidates":[]}','{"status":"unknown","candidates":[]}'),
    ('```json\n{"a":1}\n```','{"a":1}'),('{"a":1}','{"a":1}')])
def test_gemma_thought_and_fence_are_removed(raw,expected):
    assert study_mode._strip_thought(raw)==expected
