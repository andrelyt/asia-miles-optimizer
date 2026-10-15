"""Evidence-aware pricing orchestration; V1.1 remains the only pricing kernel."""
from optimizer import evaluate
from .award_adapter import adapt_candidate


def price_candidate(candidate, request, rules, evidence=None, balances_by_account=None):
    """Evaluate ready shared-itinerary tickets; preserve partial prices as subtotals."""
    result = adapt_candidate(candidate, request, rules, evidence, balances_by_account)
    travelers = result.get('candidate', {}).get('traveler_ids', [])
    known = sum(t['miles_per_person'] for t in result['tickets'] if t['miles_per_person'] is not None)
    result.update(kernel_result=None, per_person_miles=None, group_miles=None,
                  miles_by_traveler={t: None for t in travelers}, account_allocation=[],
                  account_allocation_status='NOT_CHECKED', known_miles_subtotal_per_person=known,
                  known_group_miles_subtotal=known * len(travelers), v1_evaluated=False,
                  taxes_hkd_per_person=None)
    for ticket in result['tickets']:
        miles = ticket['miles_per_person']
        ticket['group_miles'] = miles * len(travelers) if miles is not None else None
    if result['status'] != 'READY_FOR_EVALUATION':
        return result
    evaluated = evaluate(result['scenario'], rules, result['settings'])
    result['status'] = 'EVALUATED'
    result['kernel_result'] = evaluated
    result['v1_evaluated'] = True
    result['taxes_hkd_per_person'] = result['scenario']['taxes_and_surcharges_hkd_per_person']
    result['account_allocation'] = evaluated['account_allocation']
    result['account_allocation_status'] = evaluated['account_allocation_status']
    if evaluated['errors']:
        # Funding infeasibility does not erase valid ticket mile requirements.
        funding_only = evaluated['account_allocation_status'] == 'INSUFFICIENT'
        result['status'] = 'NEEDS_DATA' if funding_only else 'UNSUPPORTED'
        result['diagnostics'].append('ACCOUNT_BALANCE_INSUFFICIENT' if funding_only else 'V1_VALIDATION_FAILED')
        if not funding_only:
            result['pricing_status'] = 'UNKNOWN'
            return result
    result['per_person_miles'] = evaluated['per_person_miles']
    result['group_miles'] = evaluated['group_miles']
    result['miles_by_traveler'] = {t: evaluated['per_person_miles'] for t in travelers}
    result['complete_price_comparison_eligible'] = (result['status'] == 'EVALUATED' and
        result['pricing_status'] == 'QUOTED' and evaluated['complete_price_comparison_eligible'])
    return result
