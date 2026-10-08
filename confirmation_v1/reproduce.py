"""Portable, standard-library-only reproduction. Makes zero model/network calls.

Works in the public repository and the original private development layout.
The historical builder and measured source files are never rewritten.
"""
from pathlib import Path
import argparse,importlib.util,json,os,shutil,subprocess,sys,tempfile

HERE=Path(__file__).resolve().parent
SOURCE_FILES=('cases.json','PROTOCOL.md','build_confirmation.py','confirmation_runner.py',
              'confirmation_analysis.py','verify_confirmation.py',
              'Fechamento_BR_Confirmation_v1_SAFE.ipynb')
TEST_FILES=('test_confirmation.py','test_confirmation_verifier.py','test_review_regressions.py')

def command(args,cwd):
    env=dict(os.environ);env['PYTHONIOENCODING']='utf-8'
    run=subprocess.run([sys.executable,*map(str,args)],cwd=cwd,env=env,
        capture_output=True,text=True,encoding='utf-8',timeout=120)
    text=run.stdout+run.stderr
    if run.returncode:
        raise RuntimeError('Offline verification failed:\n'+text[-7000:])
    return text

def reproduce(run_tests=False):
    frozen=HERE.parent/'research'
    if not frozen.is_dir():frozen=HERE.parent/'submission/FechamentoBR_PublicEvidenceSite/research'
    if not (frozen/'FILE_HASHES.json').is_file():raise ValueError('Run inside the complete Fechamento BR repository')
    with tempfile.TemporaryDirectory(prefix='fechamento-offline-reproduction-') as temp:
        root=Path(temp);work=root/'confirmation_v1';work.mkdir()
        target=root/'submission/FechamentoBR_PublicEvidenceSite/research'
        shutil.copytree(frozen,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in SOURCE_FILES:
            shutil.copyfile(HERE/name,work/name)
        spec=importlib.util.spec_from_file_location('frozen_confirmation_builder',work/'build_confirmation.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        rebuilt=builder.build(root)
        saved=json.loads((work/'Fechamento_BR_Confirmation_v1_SAFE.ipynb').read_text(encoding='utf-8'))
        if rebuilt!=saved:raise ValueError('Rebuilt notebook differs from the frozen SAFE artifact')
        print('PASS: frozen SAFE notebook rebuilt identically, including its source bundle.')
        print(command([target/'verify_results.py'],root).strip())
        if run_tests:
            for name in TEST_FILES:shutil.copyfile(HERE/name,work/name)
            output=command(['-m','unittest','discover','-s',work,'-p','test*.py','-v'],root)
            print('OFFLINE FIXTURE TESTS -- synthetic answers are not measurements.')
            print('\n'.join(output.strip().splitlines()[-4:]))
        evidence=HERE/'results/fechamento_confirmation_v1'
        if evidence.is_dir():
            shutil.copyfile(HERE/'FREEZE_RECEIPT.json',work/'FREEZE_RECEIPT.json')
            destination=work/'results/fechamento_confirmation_v1';shutil.copytree(evidence,destination)
            print(command([work/'verify_confirmation.py',destination],root).strip())
        else:
            print('No supplementary measurement bundle present. No supplementary performance claim verified.')
    print('Model calls: 0. Network calls: 0. Historical sources unchanged.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test',action='store_true',help='Also run the isolated offline regression tests')
    options=parser.parse_args()
    reproduce(run_tests=options.test)
