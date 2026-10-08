"""Offline regrade: standard library only, no Kaggle import or model calls."""
import hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from final_contract import summarize_final,compare_complete_summaries
manifest=json.loads((R/'FILE_HASHES.json').read_text(encoding='utf-8'))
for name,expected in manifest.items():
 p=R/name
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected, 'Integrity mismatch: '+name
cases=json.loads((R/'data/final_cases_v1.json').read_text(encoding='utf-8'))['cases']
runs=json.loads((R/'results/RUN_INDEX.json').read_text(encoding='utf-8'))
assert len(runs)==3 and len(cases)==28
summaries=[];count=0
for run in runs:
 folder=R/'results'/run['run_id']
 m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
 records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((folder/'records').glob('*.json'))]
 s=summarize_final(records,cases,m)
 assert s==json.loads((folder/'summary.json').read_text(encoding='utf-8'))
 summaries.append(s);count+=len(records)
 print(run['model'],str(s['primary_correct'])+'/28',str(s['pair_pass_count'])+'/12 pairs')
compare_complete_summaries(summaries)
assert count==84
print('PASS: 84 recorded responses regraded; file hashes match. Model calls: 0.')
