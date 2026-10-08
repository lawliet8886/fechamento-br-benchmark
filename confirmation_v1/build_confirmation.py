"""Build an offline-by-default supplementary Kaggle notebook; no model calls."""
import ast
import hashlib
import json
from pathlib import Path

SOURCE_NAMES=('fechamento_core.py','final_contract.py','final_runner.py','kaggle_final_adapter.py')

def sha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def build(root):
    root=Path(root);here=root/'confirmation_v1'
    frozen=root/'submission/FechamentoBR_PublicEvidenceSite/research'
    sources={n:(frozen/n).read_text(encoding='utf-8') for n in SOURCE_NAMES}
    source_hashes={n:hashlib.sha256((frozen/n).read_bytes()).hexdigest() for n in SOURCE_NAMES}
    original_inventory=json.loads((frozen/'FILE_HASHES.json').read_text(encoding='utf-8'))
    if any(source_hashes[n]!=original_inventory[n] for n in SOURCE_NAMES):
        raise RuntimeError('Frozen original source mismatch')
    sources['confirmation_runner.py']=(here/'confirmation_runner.py').read_text(encoding='utf-8')
    cells={}
    for name,source in sources.items():
        definition=''.join(line for line in source.splitlines(keepends=True)
            if not line.startswith(('from fechamento_core import ','from final_contract import ','from final_runner import ')))
        capture=("\nimport linecache as _confirmation_lc, sys as _confirmation_sys\n"
                 f"EXECUTED_SOURCE_CELLS[{name!r}] = ''.join(_confirmation_lc.getlines(_confirmation_sys._getframe().f_code.co_filename))\n")
        cells[name]=definition+capture
    case_text=(here/'cases.json').read_text(encoding='utf-8')
    protocol_text=(here/'PROTOCOL.md').read_text(encoding='utf-8')
    recipe={'source_hashes':source_hashes,'cell_hashes':{n:sha(t) for n,t in cells.items()},
            'confirmation_adapter_file_sha256':hashlib.sha256((here/'confirmation_runner.py').read_bytes()).hexdigest(),
            'cases_text_sha256':sha(case_text),'protocol_text_sha256':sha(protocol_text),
            'analysis_file_sha256':hashlib.sha256((here/'confirmation_analysis.py').read_bytes()).hexdigest(),
            'verifier_file_sha256':hashlib.sha256((here/'verify_confirmation.py').read_bytes()).hexdigest(),
            'builder_file_sha256':hashlib.sha256((here/'build_confirmation.py').read_bytes()).hexdigest(),
            'planned_requests':72,'repetitions':2}
    bundle=sha(json.dumps(recipe,sort_keys=True,separators=(',',':')))
    nb_cells=[]
    def add(cid,text,kind='code'):
        c={'cell_type':kind,'id':cid,'metadata':{},'source':text.splitlines(keepends=True)}
        if kind=='code':ast.parse(text);c.update(execution_count=None,outputs=[])
        nb_cells.append(c)
    add('confirmation-intro','''# Fechamento BR — separate targeted confirmation, 08 October 2026

Twelve newly authored fictional money cases, three predeclared models, two repetitions.
This notebook is not the original 28-case/84-response study and must not update its public task.
Four contrast pairs and four controls. All requests use the frozen original prompt and strict grader.
The supplementary execution adapter is derived from the reviewed fail-fast public-v2 adapter;
its separate source receipt is retained. This is NOT byte-for-byte reuse of the original dispatcher.

No model requests by default. A matching review/freeze receipt and verified native free quota are required.
No personal API, paid fallback, package installation, Build Task or Update Task actions.
''','markdown')
    add('confirmation-config',f'''RUN_CONFIRMATION = False
REVIEW_APPROVED = False
NATIVE_QUOTA_VERIFIED = False
VERIFY_NATIVE_ONLY = False
APPROVED_BUNDLE = ""
BUNDLE_SHA256 = {bundle!r}
RECIPE = {recipe!r}
SOURCE_HASHES = {source_hashes!r}
EXECUTED_SOURCE_CELLS = {{}}
''')
    for name,text in cells.items():add('source-'+name.replace('.','-'),text)
    add('confirmation-data',f'''CASE_TEXT = {case_text!r}
PROTOCOL_TEXT = {protocol_text!r}
CONFIRMATION_DOCUMENT = json.loads(CASE_TEXT)
CONFIRMATION_CASES = CONFIRMATION_DOCUMENT['cases']
validate_final_cases(CONFIRMATION_CASES)
if len(CONFIRMATION_CASES)!=12 or sum(c['role']=='contrast' for c in CONFIRMATION_CASES)!=8:
    raise RuntimeError('Unexpected confirmation design')
print('CONFIRMATION_OFFLINE_READY: 12 cases; zero model calls')
''')
    add('confirmation-guard','''def verify_confirmation_freeze():
    if not REVIEW_APPROVED or not APPROVED_BUNDLE:
        raise RuntimeError('Premeasurement review and matching freeze receipt required')
    if set(EXECUTED_SOURCE_CELLS)!=set(RECIPE['cell_hashes']) or not all(EXECUTED_SOURCE_CELLS.values()):
        raise RuntimeError('Cannot verify actual executed IPython source cells')
    actual_cells={n:sha256_text(text) for n,text in EXECUTED_SOURCE_CELLS.items()}
    if actual_cells!=RECIPE['cell_hashes']:
        raise RuntimeError('Executed source cells differ from reviewed bundle')
    if SOURCE_HASHES!=RECIPE['source_hashes']:
        raise RuntimeError('Original source inventory changed')
    if sha256_text(CASE_TEXT)!=RECIPE['cases_text_sha256'] or sha256_text(PROTOCOL_TEXT)!=RECIPE['protocol_text_sha256']:
        raise RuntimeError('Corpus or protocol text changed after review')
    if json.loads(CASE_TEXT)!=CONFIRMATION_DOCUMENT or CONFIRMATION_DOCUMENT['cases']!=CONFIRMATION_CASES:
        raise RuntimeError('Runtime corpus changed after review')
    actual=hashlib.sha256(json.dumps(RECIPE,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    if actual!=BUNDLE_SHA256 or actual!=APPROVED_BUNDLE:
        raise RuntimeError('Bundle does not match recorded approval')
    validate_final_cases(CONFIRMATION_CASES)

def verify_native_environment():
    if not Path('/kaggle/working').is_dir() or os.environ.get('KAGGLE_USE_MODEL_PROXY','').lower()!='true':
        raise RuntimeError('Only native Kaggle included model proxy is permitted')
    import kaggle_benchmarks as kbench
    from importlib.metadata import version
    if version('kaggle-benchmarks')!='0.6.1':
        raise RuntimeError('Native SDK version differs from reviewed 0.6.1')
    require_native_free_proxy(kbench,False)
    if any(m not in kbench.llms for m in CONFIRMATION_MODELS):
        raise RuntimeError('A predeclared model is unavailable; no substitution')
    print('NATIVE_PREFLIGHT_PASS',version('kaggle-benchmarks'),'cache=',kbench.client.use_cache)
    print('PLANNED_MODELS',list(CONFIRMATION_MODELS))
    return kbench

''')
    add('confirmation-execution','''def run_confirmation_experiment():
    verify_confirmation_freeze()
    if not NATIVE_QUOTA_VERIFIED:
        raise RuntimeError('Included quota must be inspected before any model requests')
    kbench=verify_native_environment()
    base=Path('/kaggle/working/fechamento_confirmation_v1')
    if base.exists() and any(base.iterdir()):
        raise RuntimeError('Existing supplementary evidence: refuse rerun or overwrite')
    base.mkdir(parents=True,exist_ok=True)
    schedule=[{'repetition':r,'model':m,'state':'not_started'} for r in (1,2) for m in CONFIRMATION_MODELS]
    if len(schedule)!=6 or len(schedule)*len(CONFIRMATION_CASES)!=72 or [(x['repetition'],x['model']) for x in schedule]!=[(r,m) for r in (1,2) for m in CONFIRMATION_MODELS]:
        raise RuntimeError('Supplement schedule differs from the six predeclared attempts')
    experiment={'experiment_id':'confirmation-v1-20261008','original_study':False,
        'state':'running','bundle_sha256':BUNDLE_SHA256,'recipe':RECIPE,
        'cases':CONFIRMATION_CASES,'protocol_text':PROTOCOL_TEXT,
        'planned_requests':72,'completed_requests':0,'schedule':schedule,
        'started_at_utc':datetime.now(timezone.utc).isoformat()}
    atomic_json(base/'experiment.json',experiment)
    source_receipt={'adapter_file_sha256':RECIPE['confirmation_adapter_file_sha256'],
                    'executed_cell_sha256':RECIPE['cell_hashes']['confirmation_runner.py']}
    try:
        task=register_confirmation_task(kbench,CONFIRMATION_CASES,SOURCE_HASHES,base,
                 confirmation_source_receipt=source_receipt)
        for item in schedule:
            verify_confirmation_freeze()
            require_native_free_proxy(kbench,False)
            slot=base/('repetition_'+str(item['repetition']))
            before=set(slot.glob('*/manifest.json')) if slot.exists() else set()
            item['state']='running';atomic_json(base/'experiment.json',experiment)
            print('BEGIN_CONFIRMATION_ATTEMPT',item['repetition'],item['model'],flush=True)
            native_run=task.run(llm=kbench.llms[item['model']],repetition=item['repetition'])
            if str(native_run.status).lower()!='success':
                raise RuntimeError('Native confirmation parent task was not successful')
            created=set(slot.glob('*/manifest.json'))-before
            if len(created)!=1:
                raise RuntimeError('Cannot bind exactly one attempt to the predeclared schedule')
            manifest_path=next(iter(created));folder=manifest_path.parent
            manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
            if manifest['model']!=item['model'] or summary['total_cases']!=12 or manifest['dataset_sha256']!=digest(CONFIRMATION_CASES):
                raise RuntimeError('Model, coverage or dataset mismatch')
            item.update(state='completed',run_id=manifest['run_id'],relative_folder=folder.relative_to(base).as_posix(),
                        strict_correct=summary['primary_correct'],native_status=str(native_run.status))
            experiment['completed_requests']+=12
            atomic_json(base/'experiment.json',experiment)
        experiment['state']='completed'
        print('CONFIRMATION_COMPLETED: 72 unchanged new responses, original study separate',flush=True)
    except BaseException as exc:
        experiment['state']='incomplete_no_aggregate'
        experiment['exception_type']=type(exc).__name__
        for item in schedule:
            if item['state']=='running':item['state']='failed_or_incomplete'
        print('CONFIRMATION_STOPPED',type(exc).__name__,'no further models requested',flush=True)
        raise
    finally:
        experiment['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        atomic_json(base/'experiment.json',experiment)


def export_confirmation_evidence():
    import shutil,zipfile,base64
    wd=Path('/kaggle/working');base=wd/'fechamento_confirmation_v1'
    if not base.is_dir():
        print('NO_CONFIRMATION_EVIDENCE_CREATED');return
    archive_dir=base/'native';archive_dir.mkdir(exist_ok=True)
    for path in wd.glob('fechamento_br_confirmation_v1*.json'):
        if path.name.endswith(('.run.json','.task.json','.result.json','.atif.json')):
            dst=archive_dir/path.name
            if dst.exists() and dst.read_bytes()!=path.read_bytes():
                raise RuntimeError('Native trace collision; do not overwrite evidence')
            if not dst.exists():shutil.copyfile(path,dst)
    zpath=wd/'Fechamento_BR_Confirmation_v1_Evidence.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(base.rglob('*.json')):
            archive.write(path,path.relative_to(wd).as_posix())
    data=zpath.read_bytes()
    print('CONFIRMATION_ARCHIVE_SHA256',hashlib.sha256(data).hexdigest())
    print('CONFIRMATION_ARCHIVE_B64_BEGIN')
    print(base64.b64encode(data).decode('ascii'))
    print('CONFIRMATION_ARCHIVE_B64_END')

if VERIFY_NATIVE_ONLY:
    if RUN_CONFIRMATION:
        raise RuntimeError('Native-only preflight and model execution must be separate')
    verify_confirmation_freeze()
    _preflight_sdk=verify_native_environment()
    _preflight_receipt={'adapter_file_sha256':RECIPE['confirmation_adapter_file_sha256'],
                       'executed_cell_sha256':RECIPE['cell_hashes']['confirmation_runner.py']}
    _preflight_task=register_confirmation_task(_preflight_sdk,CONFIRMATION_CASES,SOURCE_HASHES,
             '/kaggle/working/fechamento_confirmation_preflight',confirmation_source_receipt=_preflight_receipt)
    print('NATIVE_DECORATORS_REGISTERED_NO_RUN',_preflight_task.name)
    print('NO_MODEL_PREFLIGHT_COMPLETE: zero model calls')

if not RUN_CONFIRMATION:
    print('CONFIRMATION_MODEL_CALLS_DISABLED')
else:
    try:
        run_confirmation_experiment()
    finally:
        export_confirmation_evidence()
''')
    add('confirmation-limits','''## Interpretation
This follow-up was designed after seeing the original results, and is not a blinded holdout.
Both repeated runs were planned beforehand; requested seed support is unverified.
SDK run caching is checked, but provider-side caching is not controlled.
Report targets and controls separately, including disconfirming outcomes.
Do not replace the original 84-response dataset or treat correlated observations as a population sample.
Review by Codex is a separate AI review, not a human audit or proof of general reliability.
''','markdown')
    for c in nb_cells:
        if c['id'] not in ('confirmation-guard','confirmation-execution'):
            continue
        name=c['id']
        capture=("import linecache as _confirmation_lc, sys as _confirmation_sys\n"
                 f"EXECUTED_SOURCE_CELLS[{name!r}] = ''.join(_confirmation_lc.getlines(_confirmation_sys._getframe().f_code.co_filename))\n")
        text=capture+''.join(c['source'])
        ast.parse(text)
        c['source']=text.splitlines(keepends=True)
        recipe['cell_hashes'][name]=sha(text)
    bundle=sha(json.dumps(recipe,sort_keys=True,separators=(',',':')))
    config=next(c for c in nb_cells if c['id']=='confirmation-config')
    config_text=(f"RUN_CONFIRMATION = False\nREVIEW_APPROVED = False\nNATIVE_QUOTA_VERIFIED = False\nVERIFY_NATIVE_ONLY = False\nAPPROVED_BUNDLE = \"\"\n"
                 f"BUNDLE_SHA256 = {bundle!r}\nRECIPE = {recipe!r}\nSOURCE_HASHES = {source_hashes!r}\nEXECUTED_SOURCE_CELLS = {{}}\n")
    ast.parse(config_text)
    config['source']=config_text.splitlines(keepends=True)
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'fechamento_confirmation':{**recipe,'bundle_sha256':bundle,'planned_requests':72}},'cells':nb_cells}

if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent
    nb=build(root);out=root/'confirmation_v1/Fechamento_BR_Confirmation_v1_SAFE.ipynb'
    out.write_text(json.dumps(nb,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'notebook':str(out),'cells':len(nb['cells']),'bundle':nb['metadata']['fechamento_confirmation']['bundle_sha256'],'model_calls':0}))
