"""Register final-v1 tasks with the native Kaggle SDK; offline by default at import.

Real execution uses only Kaggle's authenticated model proxy, never personal API
keys. Tests use an explicit offline_fixture label and a simulated SDK.
"""
import copy
from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4
from final_contract import default_protocol, make_manifest, validate_final_cases
from final_runner import dispatch_threads, run_attempt, run_one_case


def _concrete_return(tp):
    def annotate(fn):
        fn.__annotations__['return'] = tp
        return fn
    return annotate


def require_uncached_sdk(kbench):
    """Fail closed unless the native SDK explicitly reports cache disabled.

    KaggleClient.use_cache is a public flag in the SDK's official source. This
    checks that flag without altering global configuration. Provider-side prompt
    caching is outside this client control and is not claimed to be disabled.
    """
    if getattr(getattr(kbench, 'client', None), 'use_cache', None) is not False:
        raise RuntimeError('SDK cache must be explicitly false; unknown/enabled cache is not allowed')


def register_final_task(kbench, cases, source_hashes,
                        output_root='/kaggle/working/fechamento_final_v1', *,
                        evidence_kind='kaggle_model_run'):
    validate_final_cases(cases)
    require_uncached_sdk(kbench)
    if evidence_kind not in {'kaggle_model_run', 'offline_fixture'}:
        raise ValueError('Unsupported evidence origin')
    # Freeze the definitions read by the registration; the manifest will bind them.
    cases = copy.deepcopy(cases)
    source_hashes = copy.deepcopy(source_hashes)

    @kbench.task(name='fechamento_br_final_row_v1', store_task=False, store_run=False)
    @_concrete_return(dict)
    def final_row(llm, case, manifest, folder) -> dict:
        if llm.name != manifest['model']:
            raise RuntimeError('Actual model name does not match attempt manifest')
        settings = manifest['model_settings']
        def prompt_provider(case_id, prompt):
            return llm.prompt(prompt, seed=0, temperature=settings['temperature_passed'])
        # Task.run creates the SDK's isolated orphan conversation for this row.
        return run_one_case(case, manifest, folder, prompt_provider)

    @kbench.task(name='fechamento_br_final_v1', version=1,
                 description='Context-sensitive normalization: fixed contrast pairs and controls with deterministic grading.')
    @_concrete_return(float)
    def final_task(llm) -> float:
        protocol = default_protocol()
        require_uncached_sdk(kbench)
        if evidence_kind == 'kaggle_model_run':
            if not Path('/kaggle/working').is_dir() or os.environ.get('KAGGLE_USE_MODEL_PROXY', '').lower() != 'true':
                raise RuntimeError('Native free Kaggle proxy required; no personal API fallback')
            if getattr(llm, 'name', None) not in protocol['model_order']:
                raise RuntimeError('Model is outside the predeclared final selection')
        client = getattr(llm, 'client', None)
        if client is None or not callable(getattr(client, 'with_options', None)):
            raise RuntimeError('Cannot enforce the declared HTTP timeout/retry policy')
        model = copy.copy(llm)
        model.client = client.with_options(timeout=protocol['http_timeout_seconds'], max_retries=0)
        model.stream_responses = False
        support = getattr(model, 'support_temperature', None)
        # None is explicitly reported as unknown; no claim of deterministic sampling.
        settings = {'support_temperature': support,
                    'temperature_passed': 0 if support is True else None,
                    'seed_requested': 0, 'effective_seed': 'not_verified_by_provider',
                    'stream': False, 'http_timeout_seconds':120, 'client_retries':0,
                    'sdk_cache_enabled_observed': False,
                    'provider_prompt_cache': 'not_controlled_by_this_instrument'}
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid4().hex[:12]
        manifest = make_manifest(cases, model=model.name, run_id=run_id,
                                 evidence_kind=evidence_kind, source_hashes=source_hashes,
                                 protocol=protocol, model_settings=settings)
        def dispatch(items, m, folder):
            def worker(case):
                # Native child task preserves the actual chat trace in the SDK.
                require_uncached_sdk(kbench)
                return final_row.run(llm=model, case=case, manifest=m, folder=str(folder))
            return dispatch_threads(items, worker, workers=protocol['n_jobs'])
        summary = run_attempt(cases, manifest, output_root, dispatch)
        print('FINAL_ATTEMPT_COMPLETED', model.name, run_id,
              summary['primary_correct'], '/', summary['planned_cases'], flush=True)
        return float(summary['score'])

    return final_task
