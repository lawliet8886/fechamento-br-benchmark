"""Bounded work, atomic evidence and interruption-aware coverage for final-v1.

No model/SDK is imported here. Caller supplies the authorized provider dispatcher.
Workers must implement the protocol's finite HTTP timeout; Python cannot forcibly
terminate an arbitrary running thread. On interruption we wait for active workers.
"""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextvars import copy_context
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from uuid import uuid4
from final_contract import validate_manifest, make_record, record_base, summarize_final


class IncompleteRun(RuntimeError):
    """A partial/failed attempt has coverage evidence but no total score."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _preserve_error_write(path, data, original):
    try:
        atomic_json(path, data)
    except BaseException as write_error:
        if original is None:
            raise
        # Preserve the provider/interruption exception, not a secondary disk error.
        note = f'Evidence write also failed: {type(write_error).__name__}'
        if hasattr(original, 'add_note'):
            original.add_note(note)


def run_one_case(case, manifest, folder, prompt_provider):
    folder = Path(folder)
    dst = folder/'records'/(case['id']+'.json')
    if dst.exists():
        raise FileExistsError('A case in this attempt already has evidence')
    base = record_base(case, manifest)
    record = dict(base, started_at=utc_now(), run_status='started')
    started = time.monotonic()
    error = None
    try:
        raw = prompt_provider(case['id'], base['prompt'])
        record.update(make_record(case, manifest, raw))
        return record
    except BaseException as exc:
        error = exc
        record.update(run_status='infrastructure_error' if isinstance(exc, Exception) else 'interrupted',
                      exception_type=type(exc).__name__)
        raise
    finally:
        record.update(finished_at=utc_now(), elapsed_seconds=time.monotonic()-started)
        _preserve_error_write(dst, record, error)


def dispatch_threads(items, worker, *, workers=2):
    """At most two active jobs; collect failures without retry; drain on exit.

    Ordinary failures are persisted by run_one_case and do not stop other items.
    BaseException interruptions stop further scheduling and cancel queued work.
    """
    if type(workers) is not int or workers not in (1, 2):
        raise ValueError('Only one or two workers are permitted')
    items = iter(items)
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='fechamento-final')
    pending = set()
    outcomes = []
    try:
        for _ in range(workers):
            item = next(items, None)
            if item is not None:
                pending.add(pool.submit(copy_context().run, worker, item))
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            # Process completed jobs before scheduling their replacements.
            for future in done:
                try:
                    future.result()
                    outcomes.append('returned')
                except Exception as exc:
                    outcomes.append(type(exc).__name__)
            for _ in done:
                item = next(items, None)
                if item is not None:
                    pending.add(pool.submit(copy_context().run, worker, item))
        return outcomes
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)


def read_records(folder):
    records = []
    for p in sorted((Path(folder)/'records').glob('*.json')):
        r = json.loads(p.read_text(encoding='utf-8'))
        if r.get('case_id') != p.stem:
            raise ValueError('Record filename differs from case ID')
        records.append(r)
    return records


def run_attempt(cases, manifest, output_root, dispatcher):
    validate_manifest(manifest, cases)
    # Deep copy prevents caller mutation from changing a running attempt.
    cases = json.loads(json.dumps(cases, ensure_ascii=False))
    manifest = json.loads(json.dumps(manifest, ensure_ascii=False))
    folder = Path(output_root)/manifest['run_id']
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'records').mkdir()
    atomic_json(folder/'manifest.json', manifest)
    state = {key: manifest[key] for key in ('run_id','model','evidence_kind','dataset_sha256','instrument_sha256','protocol_sha256','manifest_sha256')}
    state.update(state='running', started_at=utc_now(), planned_cases=len(cases), completed_cases=0,
                 failed_cases=0, missing_cases=len(cases), dispatch_finished=False)
    atomic_json(folder/'status.json', state)
    error = None
    try:
        dispatcher(cases, manifest, folder)
        state['dispatch_finished'] = True
        records = read_records(folder)
        try:
            summary = summarize_final(records, cases, manifest)
        except ValueError as exc:
            raise IncompleteRun('Incomplete or invalid evidence; no total score') from exc
        atomic_json(folder/'summary.json', summary)
        state['state'] = 'completed'
        return summary
    except BaseException as exc:
        error = exc
        state.update(state='incomplete_no_score' if isinstance(exc, Exception) else 'interrupted_no_score',
                     exception_type=type(exc).__name__)
        raise
    finally:
        try:
            records = read_records(folder)
            state['completed_cases'] = sum(r.get('run_status') == 'completed' for r in records)
            state['failed_cases'] = sum(r.get('run_status') != 'completed' for r in records)
            state['missing_cases'] = len(cases)-len(records)
        except BaseException as reconciliation_error:
            state['reconciliation_error'] = type(reconciliation_error).__name__
            if error is None:
                state['state'] = 'invalid_evidence_no_score'
                _preserve_error_write(folder/'status.json', state, reconciliation_error)
                raise
        state['finished_at'] = utc_now()
        _preserve_error_write(folder/'status.json', state, error)
