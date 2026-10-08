"""Offline regrade plus native-trace consistency checks for the separate follow-up.
No SDK, network, credentials, or inference. Saved traces are not signed attestation.
"""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,json,sys
from pathlib import Path,PurePosixPath

HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent/'research'
if not FROZEN.is_dir():FROZEN=HERE.parent/'submission/FechamentoBR_PublicEvidenceSite/research'
sys.path.insert(0,str(FROZEN))
from fechamento_core import score_response
from final_contract import build_final_prompt,digest,sha256_text
from confirmation_analysis import diagnose
MODELS=('google/gemini-3.8-flash','anthropic/claude-sonnet-4-6@default','google/gemma-4-26b-a4b')
PHASE='confirmation-v1-20261008'

def require(condition,message):
    if not condition:raise ValueError(message)

def model_key(name):
    require(isinstance(name,str),'Missing native model identity')
    return name.removesuffix('@default')

def collect_all_trace_requests(native):
    # Parent/child references may repeat. Equal repeated references are harmless;
    # new requests or conflicting references must never disappear from accounting.
    conversations={};requests={}
    def walk(node):
        require(isinstance(node,dict),'Invalid native trace node')
        for conv in node.get('conversations',[]):
            require(isinstance(conv,dict),'Invalid native conversation')
            reqs=conv.get('requests',[])
            if not reqs:
                continue  # An unused context did not call a model.
            cid=conv.get('id');require(isinstance(cid,str) and bool(cid),'Missing conversation ID')
            canonical=json.dumps(reqs,sort_keys=True,separators=(',',':'))
            require(cid not in conversations or conversations[cid]==canonical,'Conflicting native conversation references')
            conversations[cid]=canonical
            for req in reqs:
                rid=req.get('id');require(isinstance(rid,str) and bool(rid),'Missing request ID')
                value=(cid,json.dumps(req,sort_keys=True,separators=(',',':')))
                require(rid not in requests or requests[rid]==value,'Conflicting native request references')
                requests[rid]=value
        for child in node.get('subruns',[]):
            walk(child)
    walk(native)
    return set(conversations),set(requests)

def match_native_trace(native,records,cases,model):
    byid={c['id']:c for c in cases}
    require(set(records)==set(byid),'Native match requires complete local case coverage')
    require(native.get('state')=='BENCHMARK_TASK_RUN_STATE_COMPLETED','Native parent incomplete')
    require(model_key(native.get('modelVersion',{}).get('slug'))==model_key(model),'Wrong native parent model')
    children=native.get('subruns',[])
    require(len(children)==len(cases),'Native child coverage mismatch')
    nums=[r['numericResult']['value'] for r in native.get('results',[]) if 'numericResult' in r]
    correct=sum(bool(score_response(records[c['id']]['raw_response'],c['expected'])['overall_correct']) for c in cases)
    require(len(nums)==1 and nums[0]==correct/len(cases),'Native parent score differs from strict regrade')
    ids=set();chats=set();requests=set();cost=0
    for child in children:
        require(child.get('state')=='BENCHMARK_TASK_RUN_STATE_COMPLETED','Native child incomplete')
        require(model_key(child.get('modelVersion',{}).get('slug'))==model_key(model),'Wrong native child model')
        values=[r['dictResult'] for r in child.get('results',[]) if 'dictResult' in r]
        require(len(values)==1,'Native child result missing/duplicated')
        cid=values[0].get('case_id')
        require(cid in byid and cid not in ids,'Native case unknown or duplicated');ids.add(cid)
        require(values[0].get('correct') is bool(records[cid]['grade']['overall_correct']),'Native child grade differs')
        convs=child.get('conversations',[]);require(len(convs)==1,'One isolated conversation required')
        conv=convs[0];chat=conv.get('id')
        require(bool(chat) and chat not in chats,'Native conversation reused');chats.add(chat)
        reqs=conv.get('requests',[]);require(len(reqs)==1,'Exactly one native request per case required')
        req=reqs[0];rid=req.get('id')
        require(bool(rid) and rid not in requests,'Native request ID reused');requests.add(rid)
        contents=req.get('contents',[])
        require(len(contents)==2 and contents[0].get('role')=='CONTENT_ROLE_USER' and contents[1].get('role')=='CONTENT_ROLE_ASSISTANT','Native message roles changed')
        prompt=''.join(p.get('text','') for p in contents[0].get('parts',[]))
        answer=''.join(p.get('text','') for p in contents[1].get('parts',[]))
        require(prompt==build_final_prompt(byid[cid])==records[cid]['prompt'],'Native prompt mismatch')
        require(answer==records[cid]['raw_response'],'Native response mismatch')
        metrics=req.get('metrics',{})
        cost+=int(metrics.get('inputTokensCostNanodollars',0))+int(metrics.get('outputTokensCostNanodollars',0))
    all_trace_chats,all_trace_requests=collect_all_trace_requests(native)
    require(all_trace_chats==chats and all_trace_requests==requests,'Extra or unaccounted native conversations/requests')
    return {'native_children':len(ids),'native_conversations':len(chats),'native_quota_nanodollars':cost,
            'conversation_ids':sorted(chats),'request_ids':sorted(requests),'native_py_run_id':native.get('pyRunId')}

def verify_directory(base,cases,approved_recipe):
    base=Path(base).resolve()
    require((base/'experiment.json').is_file(),'Supplementary experiment file missing')
    exp=json.loads((base/'experiment.json').read_text(encoding='utf-8'))
    require(exp.get('experiment_id')==PHASE and exp.get('original_study') is False,'Wrong experiment identity')
    require(exp.get('state')=='completed' and exp.get('completed_requests')==72,'Incomplete experiment: no complete aggregate')
    require(exp.get('planned_requests')==72 and exp.get('cases')==cases,'Corpus or planned scope changed')
    require(exp.get('recipe')==approved_recipe,'Recipe differs from approved freeze')
    bundle=hashlib.sha256(json.dumps(approved_recipe,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(exp.get('bundle_sha256')==bundle,'Wrong experiment bundle')
    require(sha256_text(exp['protocol_text'])==approved_recipe['protocol_text_sha256'],'Recorded protocol changed')
    schedule=exp.get('schedule',[])
    require([(r.get('repetition'),r.get('model')) for r in schedule]==[(rep,m) for rep in (1,2) for m in MODELS],'Schedule changed or duplicated')
    require(all(r.get('state')=='completed' for r in schedule),'A planned attempt is not complete')
    byid={c['id']:c for c in cases};dataset=digest(cases)
    natives=defaultdict(list)
    for path in (base/'native').glob('*.run.json'):
        native=json.loads(path.read_text(encoding='utf-8'))
        key=model_key(native.get('modelVersion',{}).get('slug'))
        require(key in {model_key(m) for m in MODELS},'Unexpected native model')
        natives[key].append(native)
    require(set(natives)=={model_key(m) for m in MODELS} and all(len(v)==2 for v in natives.values()),'Exactly six native parent traces required')
    for runs in natives.values():runs.sort(key=lambda n:str(n['startTime']))
    reports=[];all_chats=set();all_requests=set();parents=set();runids=set();cost=0
    for item in schedule:
        rel=PurePosixPath(item['relative_folder'])
        require(not rel.is_absolute() and '..' not in rel.parts and rel.parts[0]=='repetition_'+str(item['repetition']),'Unsafe or wrong repetition path')
        folder=(base/str(rel)).resolve();require(folder.is_relative_to(base),'Path escapes experiment')
        read=lambda n:json.loads((folder/n).read_text(encoding='utf-8'))
        manifest=read('manifest.json');summary=read('summary.json');status=read('status.json')
        require(manifest.get('phase')==PHASE and manifest.get('original_study') is False and manifest.get('evidence_kind')=='kaggle_model_run','Wrong manifest evidence origin')
        require(manifest.get('model')==item['model'] and manifest.get('dataset_sha256')==dataset and manifest.get('planned_cases')==12,'Wrong model or coverage')
        require(manifest.get('repetition')==item['repetition'],'Wrong manifest repetition')
        require(manifest.get('source_hashes')==approved_recipe['source_hashes'],'Wrong original source inventory')
        expected_receipt={'adapter_file_sha256':approved_recipe['confirmation_adapter_file_sha256'],'executed_cell_sha256':approved_recipe['cell_hashes']['confirmation_runner.py']}
        require(manifest.get('confirmation_source_receipt')==expected_receipt,'Wrong supplementary adapter source')
        require(manifest.get('run_id')==item.get('run_id')==summary.get('run_id') and item['run_id'] not in runids,'Attempt ID mismatch/duplicate');runids.add(item['run_id'])
        require(manifest.get('http_timeout_seconds')==120 and manifest.get('http_retries')==0 and manifest.get('sdk_cache') is False,'Execution policy changed')
        require(status.get('state')=='completed' and status.get('completed_cases')==12,'Incomplete stored attempt')
        records={}
        for path in (folder/'records').glob('*.json'):
            rec=json.loads(path.read_text(encoding='utf-8'));cid=rec.get('case_id')
            require(cid in byid and cid==path.stem and cid not in records,'Wrong/duplicate record ID')
            c=byid[cid]
            require(rec.get('phase')==PHASE and rec.get('original_study') is False and rec.get('evidence_kind')=='kaggle_model_run','Wrong record evidence origin')
            require(rec.get('model')==item['model'] and rec.get('dataset_sha256')==dataset,'Wrong record model/corpus')
            require(rec.get('expected')==c['expected'] and rec.get('prompt')==build_final_prompt(c) and rec.get('prompt_sha256')==sha256_text(build_final_prompt(c)),'Frozen gold or prompt mismatch')
            require(type(rec.get('raw_response')) is str and rec.get('grade')==score_response(rec['raw_response'],c['expected']),'Missing raw answer or grade mismatch')
            records[cid]=rec
        require(set(records)==set(byid),'Missing record coverage')
        correct=sum(bool(r['grade']['overall_correct']) for r in records.values())
        require(summary.get('deployment_protocol')==PHASE and summary.get('original_study') is False and summary.get('model')==item['model'] and summary.get('dataset_sha256')==dataset,'Wrong summary identity')
        require(summary.get('primary_correct')==item.get('strict_correct')==correct and summary.get('total_cases')==12 and summary.get('score')==correct/12,'Summary score differs from raw regrade')
        native=natives[model_key(item['model'])][item['repetition']-1]
        proof=match_native_trace(native,records,cases,item['model'])
        require(not (all_chats & set(proof['conversation_ids'])) and not (all_requests & set(proof['request_ids'])),'Conversation/request reused across attempts')
        require(proof['native_py_run_id'] and proof['native_py_run_id'] not in parents,'Native parent ID missing/reused')
        all_chats.update(proof['conversation_ids']);all_requests.update(proof['request_ids']);parents.add(proof['native_py_run_id']);cost+=proof['native_quota_nanodollars']
        categories={c['id']:diagnose(c,records[c['id']]['raw_response']) for c in cases}
        targets=[c for c in cases if c['role']=='contrast'];controls=[c for c in cases if c['role']=='control']
        reports.append({'model':item['model'],'repetition':item['repetition'],'strict_correct':correct,'total':12,
            'target_correct':sum(categories[c['id']]=='strict_pass' for c in targets),'targets':8,
            'controls':{c['id']:categories[c['id']] for c in controls},'diagnostics':dict(Counter(categories.values())),
            'case_diagnostics':categories,'run_id':item['run_id'],'native_py_run_id':proof['native_py_run_id']})
    return {'experiment_id':PHASE,'state':'verified_complete','original_study':False,'responses':72,
        'native_parent_runs':len(parents),'native_individual_conversations':len(all_chats),
        'native_prompts_answers_models_matched':True,'bundle_sha256':bundle,
        'native_included_quota_usd':cost/1e9,'personal_api_payment':False,'results':reports,
        'interpretation':'Targeted authored follow-up; no causal attribution, independent-draw or population-ranking claim.',
        'verified_at_utc':datetime.now(timezone.utc).isoformat()}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python verify_confirmation.py PATH_TO_EXTRACTED_EXPERIMENT_DIRECTORY')
    cases=json.loads((HERE/'cases.json').read_text(encoding='utf-8'))['cases']
    freeze=json.loads((HERE/'FREEZE_RECEIPT.json').read_text(encoding='utf-8'))
    report=verify_directory(Path(sys.argv[1]),cases,freeze['recipe'])
    destination=HERE/'VERIFIED_RESULTS.json'
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if destination.exists() and json.loads(destination.read_text(encoding='utf-8')).get('bundle_sha256')!=report['bundle_sha256']:
        raise RuntimeError('Refusing to replace verification for another experiment')
    destination.write_text(text,encoding='utf-8')
    for row in report['results']:print(row['repetition'],row['model'],str(row['strict_correct'])+'/12',str(row['target_correct'])+'/8 targets',row['diagnostics'])
    print('PASS: 72 raw outputs regraded and matched to 72 distinct native conversations. Model calls: 0.')
