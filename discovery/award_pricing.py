"""Evidence-aware pricing orchestration; V1.1 remains the only pricing kernel."""
from optimizer import evaluate
from .award_adapter import adapt_candidate


def _official_price_candidate(candidate, request, rules, evidence=None, balances_by_account=None):
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


def price_candidate(candidate, request, rules, evidence=None, balances_by_account=None,
                    reference_chart=None):
    """Strict quote path first; optional separate reference planning estimate.

    No reference profile means the original PR3 result, unchanged. Neither a
    reference profile nor its estimates constitutes an applicability review.
    """
    result = _official_price_candidate(candidate, request, rules, evidence, balances_by_account)
    if reference_chart is None:
        return result
    result.update(estimate=None, quote=None, official_pricing_status=result['status'])
    if result['status'] == 'EVALUATED' and result['pricing_status'] == 'QUOTED':
        result['quote'] = {'per_person_miles': result['per_person_miles'],
                           'group_miles': result['group_miles'], 'evidence': result['input_evidence']}
        return result
    if result['status'] not in ('RULE_VERSION_REVIEW_REQUIRED', 'NEEDS_AIRLINE_QUOTE'):
        return result
    from .reference_estimate import reference_estimate
    estimate, reason = reference_estimate(candidate, request, rules, reference_chart)
    if estimate is None:
        result['diagnostics'].append(reason)
        return result
    from .route_graph import stable_id
    result.update(status='RULE_ESTIMATED', pricing_status='RULE_ESTIMATED', estimate=estimate,
                  complete_price_comparison_eligible=False)
    result['evaluation_id'] = stable_id('evaluation_', {'official_evaluation_id': result['evaluation_id'],
                                                      'estimate': estimate})
    result['diagnostics'].append('REFERENCE_ESTIMATE_NOT_AIRLINE_QUOTE')
    return result
