"""Offline reproductions of review findings. No SDK, network or real model calls."""
import copy,hashlib,json,linecache,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H));sys.path.insert(0,str(H.parent/'submission/FechamentoBR_PublicEvidenceSite/research'))
import build_confirmation
import verify_confirmation as verifier
from test_confirmation import CASES,HASHES,MODELS,FakeRun,Model
from test_confirmation_verifier import fixture
from final_contract import build_final_prompt,digest


def load_notebook(mutate_id=None,old=None,new=None):
    nb=build_confirmation.build(H.parent);ns={'__name__':'offline_review_fixture'}
    for i,c in enumerate(nb['cells']):
        if c['cell_type']!='code':continue
        source=''.join(c['source'])
        if c['id']==mutate_id:
            if old not in source:raise AssertionError('Mutation target missing')
            source=source.replace(old,new,1)
        filename='<offline-review-cell-'+str(i)+'>'
        linecache.cache[filename]=(len(source),None,source.splitlines(keepends=True),filename)
        exec(compile(source,filename,'exec'),ns)
    ns['REVIEW_APPROVED']=True;ns['APPROVED_BUNDLE']=ns['BUNDLE_SHA256']
    return nb,ns


def complete_fixture(base):
    nb=build_confirmation.build(H.parent);recipe=dict(nb['metadata']['fechamento_confirmation']);recipe.pop('bundle_sha256')
    schedule=[];native_dir=base/'native';native_dir.mkdir(parents=True)
    for rep in (1,2):
        for j,model in enumerate(MODELS):
            slot=(rep-1)*3+j+1;runid='fixture_'+str(slot);rel='repetition_'+str(rep)+'/'+runid
            folder=base/rel;(folder/'records').mkdir(parents=True)
            records,native=fixture();native['modelVersion']['slug']=model;native['pyRunId']='native-fixture-'+str(slot);native['startTime']=f'2026-10-08T00:{slot:02d}:00Z'
            for child in native['subruns']:
                child['modelVersion']['slug']=model
                child['conversations'][0]['id']+='-'+str(slot)
                child['conversations'][0]['requests'][0]['id']+='-'+str(slot)
            for cid,rec in records.items():
                rec['model']=model
                (folder/'records'/(cid+'.json')).write_text(json.dumps(rec),encoding='utf-8')
            manifest={'phase':verifier.PHASE,'original_study':False,'evidence_kind':'kaggle_model_run','model':model,'dataset_sha256':digest(CASES),'planned_cases':12,'repetition':rep,'source_hashes':HASHES,'confirmation_source_receipt':{'adapter_file_sha256':recipe['confirmation_adapter_file_sha256'],'executed_cell_sha256':recipe['cell_hashes']['confirmation_runner.py']},'run_id':runid,'http_timeout_seconds':120,'http_retries':0,'sdk_cache':False}
            summary={'deployment_protocol':verifier.PHASE,'original_study':False,'model':model,'dataset_sha256':digest(CASES),'run_id':runid,'primary_correct':12,'total_cases':12,'score':1.0}
            for name,obj in [('manifest.json',manifest),('summary.json',summary),('status.json',{'state':'completed','completed_cases':12})]:
                (folder/name).write_text(json.dumps(obj),encoding='utf-8')
            (native_dir/(str(slot)+'.run.json')).write_text(json.dumps(native),encoding='utf-8')
            schedule.append({'repetition':rep,'model':model,'run_id':runid,'relative_folder':rel,'state':'completed','strict_correct':12})
    exp={'experiment_id':verifier.PHASE,'original_study':False,'state':'completed','completed_requests':72,'planned_requests':72,'cases':CASES,'recipe':recipe,'bundle_sha256':nb['metadata']['fechamento_confirmation']['bundle_sha256'],'protocol_text':(H/'PROTOCOL.md').read_text(encoding='utf-8'),'schedule':schedule}
    (base/'experiment.json').write_text(json.dumps(exp),encoding='utf-8')
    return recipe

class ReviewRegressions(unittest.TestCase):
    def test_unmodified_executed_cells_are_accepted(self):
        nb,ns=load_notebook();ns['verify_confirmation_freeze']()
    def test_extra_repetition_in_executed_cell_rejected_before_calls(self):
        nb,ns=load_notebook('confirmation-execution','for r in (1,2)','for r in (1,2,3)')
        with self.assertRaisesRegex(RuntimeError,'source|cell|operational|bundle'):
            ns['verify_confirmation_freeze']()
    def test_changed_guard_cell_is_rejected(self):
        nb,ns=load_notebook('confirmation-guard','Native SDK version differs from reviewed 0.6.1','Changed guard diagnostic')
        with self.assertRaisesRegex(RuntimeError,'source|cell|operational|bundle'):
            ns['verify_confirmation_freeze']()
    def test_whole_valid_six_attempt_fixture_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);recipe=complete_fixture(base)
            result=verifier.verify_directory(base,CASES,recipe)
            self.assertEqual(result['responses'],72);self.assertEqual(result['native_individual_conversations'],72)
    def test_extra_parent_request_rejected_in_complete_experiment(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);recipe=complete_fixture(base);path=base/'native/1.run.json';native=json.loads(path.read_text())
            extra=copy.deepcopy(native['subruns'][0]['conversations'][0]);extra['id']='extra-parent-chat';extra['requests'][0]['id']='extra-parent-request'
            native['conversations']=[extra];path.write_text(json.dumps(native),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'extra|unaccounted|conversation|request'):
                verifier.verify_directory(base,CASES,recipe)
    def test_nested_extra_request_rejected(self):
        records,native=fixture();extra=copy.deepcopy(native['subruns'][0]);extra['conversations'][0]['id']='nested-extra';extra['conversations'][0]['requests'][0]['id']='nested-extra-request'
        native['subruns'][0]['subruns']=[extra]
        with self.assertRaisesRegex(ValueError,'extra|unaccounted|conversation|request'):
            verifier.match_native_trace(native,records,CASES,MODELS[0])
    def test_duplicate_parent_reference_is_deduplicated(self):
        records,native=fixture();native['conversations']=[copy.deepcopy(native['subruns'][0]['conversations'][0])]
        proof=verifier.match_native_trace(native,records,CASES,MODELS[0]);self.assertEqual(proof['native_conversations'],12)
    def test_one_registered_parent_preserves_six_native_run_ids(self):
        import confirmation_runner
        registered=[];native_keys=[]
        class Task:
            def __init__(self,fn,name,store):self.fn=fn;self.name=name;self.store=store;self.counter=0
            def run(self,**kwargs):
                self.counter+=1;result=FakeRun(self.fn(**kwargs))
                if self.store:native_keys.append((kwargs['llm'].name,self.counter))
                return result
        class SDK:
            def __init__(self):
                from types import SimpleNamespace
                self.client=SimpleNamespace(use_cache=False);self.llms={m:Model(m) for m in MODELS}
            def task(self,**kw):
                registered.append(kw['name'])
                return lambda fn:Task(fn,kw['name'],kw.get('store_run',True))
        nb,ns=load_notebook();sdk=SDK()
        def register(*args,**kwargs):
            kwargs['fixture_mode']=True
            return confirmation_runner.register_confirmation_task(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            realpath=Path
            def redirected(p):
                if str(p).startswith('/kaggle/working/'):return realpath(tmp)/str(p).split('/kaggle/working/',1)[1]
                return realpath(p)
            ns['Path']=redirected;ns['verify_native_environment']=lambda:sdk
            ns['require_native_free_proxy']=lambda *args:None
            ns['register_confirmation_task']=register;ns['NATIVE_QUOTA_VERIFIED']=True
            ns['run_confirmation_experiment']()
            self.assertEqual(len(native_keys),6)
            self.assertEqual(len(set(native_keys)),6,'Per-task run counters collide after re-registering each attempt')
            self.assertEqual(registered.count('fechamento_br_confirmation_v1'),1,'Register the parent once for the whole experiment')

if __name__=='__main__':unittest.main()
