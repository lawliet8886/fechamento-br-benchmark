"""Targeted confirmation adapter, derived from reviewed public v2; original study unchanged.

Uses only the three predeclared models for a separate 12-case follow-up.
The frozen dataset, scoring code and original 84 results remain unchanged.
No Kaggle/network import or model call occurs at module import.
"""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import os
from uuid import uuid4

from final_contract import validate_final_cases, build_final_prompt, digest, sha256_text
from fechamento_core import score_response
from final_runner import atomic_json, _preserve_error_write
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextvars import copy_context

CONFIRMATION_PROTOCOL_ID='confirmation-v1-20261008'
CONFIRMATION_MODELS=('google/gemini-3.8-flash','anthropic/claude-sonnet-4-6@default','google/gemma-4-26b-a4b')


def dispatch_confirmation_fail_fast(items, worker):
    """At most two in flight. First failure stops ALL future submissions.

    This is separate from the frozen final-v1 dispatcher. If a provider rejects
    quota/rate limits, no additional queued cases are sent to the provider;
    jobs already started may complete. No retry.
    """
    iterator = iter(items)
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='fechamento-public-v2')
    pending = set()
    returned = []
    try:
        for _ in range(2):
            item = next(iterator, None)
            if item is not None:
                pending.add(pool.submit(copy_context().run, worker, item))
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            failure = None
            for future in done:
                try:
                    future.result()
                    returned.append('returned')
                except BaseException as exc:
                    if failure is None:
                        failure = exc
            if failure is not None:
                for future in pending:
                    future.cancel()
                raise failure
            for _ in done:
                item = next(iterator, None)
                if item is not None:
                    pending.add(pool.submit(copy_context().run, worker, item))
        return returned
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)
def require_native_free_proxy(kbench,fixture_mode):
    if getattr(getattr(kbench,'client',None),'use_cache',None) is not False:
        raise RuntimeError('SDK cache must be explicitly disabled')
    if fixture_mode:
        return
    if not Path('/kaggle/working').is_dir() or os.environ.get('KAGGLE_USE_MODEL_PROXY','').lower()!='true':
        raise RuntimeError('Kaggle native included proxy only; no paid fallback')

def concrete_return(tp):
    def annotate(fn):
        fn.__annotations__['return']=tp
        return fn
    return annotate

def register_confirmation_task(kbench,cases,source_hashes,output_root,*,fixture_mode=False,confirmation_source_receipt=None):
    """Return a single task. Registration does not execute the model."""
    if not fixture_mode:
        if not isinstance(confirmation_source_receipt,dict) or set(confirmation_source_receipt)!={'adapter_file_sha256','executed_cell_sha256'}:
            raise RuntimeError('Approved public source receipt required before model registration')
        if any(type(v) is not str or len(v)!=64 for v in confirmation_source_receipt.values()):
            raise RuntimeError('Invalid public source receipt')
    else:
        confirmation_source_receipt=confirmation_source_receipt or {'adapter_file_sha256':'offline_fixture',
                                                        'executed_cell_sha256':'offline_fixture'}
    validate_final_cases(cases)
    if type(source_hashes) is not dict or len(source_hashes)!=4:
        raise ValueError('Expected four frozen science source hashes')
    if any(type(v) is not str or len(v)!=64 for v in source_hashes.values()):
        raise ValueError('Invalid source inventory')
    require_native_free_proxy(kbench,fixture_mode)
    cases=copy.deepcopy(cases)
    hashes=copy.deepcopy(source_hashes)
    dataset_sha=digest(cases)
    output_root=Path(output_root)

    @kbench.task(name='fechamento_br_confirmation_row_v1',store_task=False,store_run=False)
    @concrete_return(dict)
    def public_row(llm,case,record_path) -> dict:
        prompt=build_final_prompt(case)
        raw=llm.prompt(prompt,seed=0,temperature=(0 if getattr(llm,'support_temperature',None) is True else None))
        if type(raw) is not str:
            raise TypeError('Model response is not a string')
        grade=score_response(raw,case['expected'])
        record={'phase':CONFIRMATION_PROTOCOL_ID,'original_study':False,'evidence_kind':('offline_fixture' if fixture_mode else 'kaggle_model_run'),'case_id':case['id'],
                'model':llm.name,'prompt':prompt,'prompt_sha256':sha256_text(prompt),
                'raw_response':raw,'expected':case['expected'],'grade':grade,
                'dataset_sha256':dataset_sha}
        atomic_json(Path(record_path),record)
        return {'case_id':case['id'],'correct':bool(grade['overall_correct'])}

    @kbench.task(name='fechamento_br_confirmation_v1',version=1,
                 description='12 fictional money follow-up cases, four pairs and four controls; separate from the original study.')
    @concrete_return(float)
    def public_task(llm, repetition=1) -> float:
        require_native_free_proxy(kbench,fixture_mode)
        model_id=getattr(llm,'name',None)
        if type(model_id) is not str or not model_id.strip():
            raise ValueError('A concrete selected model identifier is required')
        if model_id not in CONFIRMATION_MODELS:
            raise ValueError('Model is outside the predeclared confirmation lineup')
        if type(repetition) is not int or repetition not in (1,2):
            raise ValueError('Only predeclared repetitions 1 and 2 are permitted')
        client=getattr(llm,'client',None)
        if client is None or not callable(getattr(client,'with_options',None)):
            raise RuntimeError('No configurable model client; cannot guarantee timeout/retries')
        model=copy.copy(llm)
        model.client=client.with_options(timeout=120,max_retries=0)
        model.stream_responses=False
        run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid4().hex[:12]
        folder=output_root/('repetition_'+str(repetition))/run_id
        folder.mkdir(parents=True,exist_ok=False)
        recdir=folder/'records'
        recdir.mkdir()
        manifest={'phase':CONFIRMATION_PROTOCOL_ID,'original_study':False,'evidence_kind':('offline_fixture' if fixture_mode else 'kaggle_model_run'),'model':model_id,
                  'run_id':run_id,'repetition':repetition,'dataset_sha256':dataset_sha,
                  'source_hashes':hashes,'confirmation_source_receipt':copy.deepcopy(confirmation_source_receipt),
                  'planned_cases':len(cases),
                  'model_selection':'predeclared three-model confirmation lineup; selected explicitly by experiment schedule',
                  'sampling':{'requested_seed':0,'temperature_override':(0 if getattr(model,'support_temperature',None) is True else None),
                              'provider_seed_support':'not_verified'},
                  'http_timeout_seconds':120,'http_retries':0,'sdk_cache':False,
                  'provider_cache':'not_controlled'}
        atomic_json(folder/'manifest.json',manifest)
        state={'state':'running','model':model_id,'run_id':run_id,
               'planned_cases':len(cases),'completed_cases':0,'dataset_sha256':dataset_sha}
        atomic_json(folder/'status.json',state)
        error = None
        try:
            def do_case(case):
                destination=recdir/(case['id']+'.json')
                run=public_row.run(llm=model,case=case,record_path=str(destination))
                if str(run.status).lower()!='success':
                    raise RuntimeError('Native child task not successful for '+case['id'])
                if run.result['case_id']!=case['id']:
                    raise RuntimeError('Native case result ID mismatch')
            try:
                results=dispatch_confirmation_fail_fast(cases,do_case)
            except Exception as exc:
                raise RuntimeError('Incomplete public model run: provider or child task failed') from exc
            if len(results)!=len(cases) or any(x!='returned' for x in results):
                raise RuntimeError('Incomplete public model run: provider or child task failed')
            records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(recdir.glob('*.json'))]
            if len(records)!=len(cases) or set(r['case_id'] for r in records)!={c['id'] for c in cases}:
                raise RuntimeError('Public records are incomplete/duplicated')
            for rec in records:
                case=next(c for c in cases if c['id']==rec['case_id'])
                if rec['model']!=model_id or rec['dataset_sha256']!=dataset_sha:
                    raise RuntimeError('Wrong public model/dataset attached')
                if rec['prompt_sha256']!=sha256_text(build_final_prompt(case)):
                    raise RuntimeError('Prompt mismatch')
                if rec['expected']!=case['expected'] or rec['grade']!=score_response(rec['raw_response'],case['expected']):
                    raise RuntimeError('Saved public grade mismatch')
            correct=sum(bool(r['grade']['overall_correct']) for r in records)
            result={'deployment_protocol':CONFIRMATION_PROTOCOL_ID,'original_study':False,
                    'model':model_id,'dataset_sha256':dataset_sha,
                    'primary_correct':correct,'total_cases':len(cases),
                    'score':correct/len(cases),'run_id':run_id}
            atomic_json(folder/'summary.json',result)
            state.update(state='completed',completed_cases=len(cases))
            print('CONFIRMATION_MODEL_COMPLETE',model_id,correct,'/',len(cases),flush=True)
            return float(result['score'])
        except BaseException as exc:
            error = exc
            state.update(state='incomplete_no_score',exception_type=type(exc).__name__)
            raise
        finally:
            try:
                state['completed_cases']=len(list(recdir.glob('*.json')))
            except BaseException as rec_error:
                if error is None:
                    raise
                if hasattr(error,'add_note'):
                    error.add_note('Public evidence reconciliation also failed: '+type(rec_error).__name__)
            state['finished_at_utc']=datetime.now(timezone.utc).isoformat()
            _preserve_error_write(folder/'status.json',state,error)
    return public_task
