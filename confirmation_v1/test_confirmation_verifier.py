"""Synthetic native-trace fixtures; never evidence of model performance."""
import copy,importlib,json,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'submission/FechamentoBR_PublicEvidenceSite/research'))
sys.path.insert(0,str(H))
from final_contract import build_final_prompt,digest,sha256_text
from fechamento_core import score_response
C=json.loads((H/'cases.json').read_text(encoding='utf-8'))['cases'];M='google/gemini-3.8-flash'

def fixture():
    records={};children=[]
    for c in C:
        raw=json.dumps(c['expected'],ensure_ascii=False);prompt=build_final_prompt(c)
        rec={'case_id':c['id'],'model':M,'dataset_sha256':digest(C),'expected':c['expected'],'prompt':prompt,'prompt_sha256':sha256_text(prompt),'raw_response':raw,'grade':score_response(raw,c['expected']),'phase':'confirmation-v1-20261008','original_study':False,'evidence_kind':'kaggle_model_run'}
        records[c['id']]=rec
        children.append({'state':'BENCHMARK_TASK_RUN_STATE_COMPLETED','modelVersion':{'slug':M},'results':[{'dictResult':{'case_id':c['id'],'correct':True}}], 'conversations':[{'id':'synthetic-chat-'+c['id'],'requests':[{'id':'synthetic-req-'+c['id'],'contents':[{'role':'CONTENT_ROLE_USER','parts':[{'text':prompt}]},{'role':'CONTENT_ROLE_ASSISTANT','parts':[{'text':raw}]}],'metrics':{'inputTokensCostNanodollars':1,'outputTokensCostNanodollars':2}}]}]})
    native={'state':'BENCHMARK_TASK_RUN_STATE_COMPLETED','modelVersion':{'slug':M},'results':[{'numericResult':{'value':1.0}}],'subruns':children,'pyRunId':'synthetic-parent','startTime':'2026-10-08T00:00:00Z'}
    return records,native

class NativeVerificationTests(unittest.TestCase):
    def fn(self):
        self.assertTrue((H/'verify_confirmation.py').is_file(),'supplementary verifier implementation missing')
        return importlib.import_module('verify_confirmation').match_native_trace
    def test_matching_prompts_outputs_models_and_container(self):
        records,native=fixture();r=self.fn()(native,records,C,M)
        self.assertEqual(r['native_children'],12);self.assertEqual(r['native_conversations'],12)
        self.assertEqual(r['native_quota_nanodollars'],36)
    def test_wrong_native_model_rejected(self):
        records,native=fixture();native['modelVersion']['slug']='google/gemini-3.7-flash'
        with self.assertRaises(ValueError):self.fn()(native,records,C,M)
    def test_changed_native_response_rejected(self):
        records,native=fixture();native['subruns'][0]['conversations'][0]['requests'][0]['contents'][1]['parts'][0]['text']='{}'
        with self.assertRaises(ValueError):self.fn()(native,records,C,M)
    def test_duplicate_chat_rejected(self):
        records,native=fixture();native['subruns'][1]['conversations'][0]['id']=native['subruns'][0]['conversations'][0]['id']
        with self.assertRaises(ValueError):self.fn()(native,records,C,M)
    def test_wrong_primary_score_rejected(self):
        records,native=fixture();native['results'][0]['numericResult']['value']=0.5
        with self.assertRaises(ValueError):self.fn()(native,records,C,M)
    def test_incomplete_native_run_rejected(self):
        records,native=fixture();native['subruns'].pop()
        with self.assertRaises(ValueError):self.fn()(native,records,C,M)
if __name__=='__main__':unittest.main()
