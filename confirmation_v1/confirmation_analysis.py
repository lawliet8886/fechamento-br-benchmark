"""Predeclared secondary diagnoses. Never repair or replace strict scores."""
from decimal import Decimal, InvalidOperation
import re
from fechamento_core import score_response

NUMBER=re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')

def diagnose(case: dict, raw: str) -> str:
    expected=case['expected']
    grade=score_response(raw,expected)
    if grade['overall_correct']:
        return 'strict_pass'
    if not grade['format_ok']:
        return 'json_container_violation'
    parsed=grade['parsed']
    if parsed['status']!=expected['status']:
        if expected['status']=='ok' and parsed['status']=='ambiguous':
            return 'unnecessary_abstention'
        return 'wrong_decision'
    if expected['status']=='ok' and case['input']['kind']=='money':
        value=parsed['value']
        if isinstance(value,str) and NUMBER.fullmatch(value):
            try:
                actual=Decimal(value);gold=Decimal(expected['value'])
                if actual.is_finite() and gold.is_finite() and actual==gold:
                    return 'canonical_format_only'
            except InvalidOperation:
                pass
    return 'wrong_value'
