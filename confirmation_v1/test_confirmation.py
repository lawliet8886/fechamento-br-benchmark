"""Offline tests only. Synthetic fixture outputs are not model measurements."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FROZEN=ROOT/'submission/FechamentoBR_PublicEvidenceSite/research'
sys.path.insert(0,str(FROZEN));sys.path.insert(0,str(HERE))
from final_contract import build_final_prompt, digest, validate_final_cases
CASES=json.loads((HERE/'cases.json').read_text(encoding='utf-8'))['cases']
NAMES=('fechamento_core.py','final_contract.py','final_runner.py','kaggle_final_adapter.py')
HASHES={n:hashlib.sha256((FROZEN/n).read_bytes()).hexdigest() for n in NAMES}
MODELS=['google/gemini-3.8-flash','anthropic/claude-sonnet-4-6@default','google/gemma-4-26b-a4b']

class FakeRun:
    def __init__(self,value):self.status='success';self.result=value
class FakeTask:
    def __init__(self,fn,name):self.fn=fn;self.name=name
    def run(self,**kwargs):return FakeRun(self.fn(**kwargs))
class FakeSDK:
    def __init__(self,cache=False):self.client=SimpleNamespace(use_cache=cache);self.names=[]
    def task(self,**kwargs):
        self.names.append(kwargs['name'])
        return lambda fn:FakeTask(fn,kwargs['name'])
class Model:
    def __init__(self,name=MODELS[0],fail=False):
        self.name=name;self.fail=fail;self.client=self;self.prompts=[]
        self.support_temperature=False;self.stream_responses=True
        self.answers={build_final_prompt(c):c['expected'] for c in CASES}
    def with_options(self,**opts):self.opts=opts;return self
    def prompt(self,prompt,**opts):
        self.prompts.append((prompt,opts))
        if self.fail:raise TimeoutError('OFFLINE_SIMULATED_QUOTA_FAILURE')
        return json.dumps(self.answers[prompt],ensure_ascii=False)

class ConfirmationTests(unittest.TestCase):
    def load(self,name):
        self.assertTrue((HERE/(name+'.py')).is_file(),name+' implementation is missing')
        return importlib.import_module(name)
    def register(self,model=None,cache=False):
        module=self.load('confirmation_runner');sdk=FakeSDK(cache)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        task=module.register_confirmation_task(sdk,CASES,HASHES,tmp.name,fixture_mode=True)
        return task,sdk,Path(tmp.name),model or Model()
    def test_new_corpus_is_valid_and_excludes_old_raw_money_pair(self):
        validate_final_cases(CASES)
        self.assertEqual(len(CASES),12)
        self.assertEqual(sum(c['role']=='contrast' for c in CASES),8)
        self.assertTrue(all(c['input']['raw']!='4.700' for c in CASES))
        for c in CASES:
            prompt=build_final_prompt(c)
            self.assertNotIn('"expected"',prompt);self.assertNotIn(c['id'],prompt)
            self.assertNotIn(c['rationale'],prompt)
    def test_registration_has_no_calls(self):
        task,sdk,path,model=self.register()
        self.assertEqual(model.prompts,[]);self.assertEqual(list(path.iterdir()),[])
        self.assertEqual(sdk.names,['fechamento_br_confirmation_row_v1','fechamento_br_confirmation_v1'])
    def test_complete_fixture_has_separate_phase_and_provenance(self):
        task,sdk,path,model=self.register();result=task.run(llm=model)
        self.assertEqual(result.result,1.0);self.assertEqual(len(model.prompts),12)
        manifest=json.loads(next(path.glob('repetition_1/*/manifest.json')).read_text(encoding='utf-8'))
        self.assertEqual(manifest['phase'],'confirmation-v1-20261008')
        self.assertEqual(manifest['evidence_kind'],'offline_fixture')
        self.assertEqual(manifest['planned_cases'],12);self.assertFalse(manifest['original_study'])
        self.assertEqual(manifest['source_hashes'],HASHES)
        self.assertIn('predeclared',manifest['model_selection'])
        for prompt,opts in model.prompts:self.assertEqual(opts,{'seed':0,'temperature':None})
        self.assertEqual(model.opts,{'timeout':120,'max_retries':0})
    def test_unplanned_model_is_rejected_before_calls(self):
        task,sdk,path,model=self.register(Model('google/gemini-3.7-flash'))
        with self.assertRaisesRegex(ValueError,'predeclared'):task.run(llm=model)
        self.assertEqual(model.prompts,[]);self.assertEqual(list(path.iterdir()),[])
    def test_first_failure_stops_scheduling_and_has_no_total(self):
        task,sdk,path,model=self.register(Model(fail=True))
        with self.assertRaises(RuntimeError):task.run(llm=model)
        self.assertLessEqual(len(model.prompts),2)
        self.assertFalse(list(path.glob('repetition_1/*/summary.json')))
        status=json.loads(next(path.glob('repetition_1/*/status.json')).read_text(encoding='utf-8'))
        self.assertEqual(status['state'],'incomplete_no_score')
    def test_enabled_or_unknown_sdk_cache_is_rejected(self):
        for flag in (True,None):
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(RuntimeError,'cache'):self.register(cache=flag)
    def test_diagnostic_distinguishes_decision_from_representation(self):
        fn=self.load('confirmation_analysis').diagnose
        c=next(c for c in CASES if c['id']=='C01A')
        for raw,label in [('{"status":"ok","value":"7300.00"}','strict_pass'),('{"status":"ambiguous","value":null}','unnecessary_abstention'),('{"status":"missing","value":null}','wrong_decision'),('{"status":"ok","value":"7300"}','canonical_format_only'),('{"status":"ok","value":"7.30"}','wrong_value'),('{"status":"ok","value":7300}','json_container_violation'),('```json\n{"status":"ok","value":"7300.00"}\n```','json_container_violation')]:
            with self.subTest(raw=raw):self.assertEqual(fn(c,raw),label)
    def test_nonfinite_and_invalid_decimal_are_not_equivalent(self):
        fn=self.load('confirmation_analysis').diagnose;c=CASES[0]
        for text in ('NaN','Infinity','7_300','7,300','0x1c84'):
            with self.subTest(text=text):self.assertEqual(fn(c,json.dumps({'status':'ok','value':text})),'wrong_value')
    def test_builder_defaults_disabled_and_uses_separate_paths(self):
        nb=self.load('build_confirmation').build(ROOT)
        code='\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
        self.assertIn('RUN_CONFIRMATION = False',code);self.assertIn('REVIEW_APPROVED = False',code)
        self.assertIn('/kaggle/working/fechamento_confirmation_v1',code)
        self.assertNotIn("output_root=Path('/kaggle/working/fechamento_final_v1')",code)
        for c in nb['cells']:
            if c['cell_type']=='code':ast.parse(''.join(c['source']));self.assertFalse(c['outputs'])
        self.assertEqual(nb['metadata']['fechamento_confirmation']['planned_requests'],72)
        self.assertEqual(nb['metadata']['fechamento_confirmation']['source_hashes'],HASHES)
    def test_builder_guard_catches_case_drift(self):
        module=self.load('build_confirmation');nb=module.build(ROOT)
        guard=next(c for c in nb['cells'] if c['id']=='confirmation-guard')
        self.assertIn('CASE_TEXT',''.join(guard['source']))
        self.assertIn('EXECUTED_SOURCE_CELLS',''.join(guard['source']))
        self.assertIn('PROTOCOL_TEXT',''.join(guard['source']))
    def test_frozen_files_match_published_inventory(self):
        inventory=json.loads((FROZEN/'FILE_HASHES.json').read_text(encoding='utf-8'))
        for rel,expected in inventory.items():
            with self.subTest(rel=rel):self.assertEqual(hashlib.sha256((FROZEN/rel).read_bytes()).hexdigest(),expected)

if __name__=='__main__':unittest.main()
