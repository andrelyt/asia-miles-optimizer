"""Explicit self-funded scenario; no verified balances or beneficiary inference."""
import copy
from optimizer import number
from ._validation import ValidationError
from .route_graph import stable_id


def validate_scenario(scenario, travelers):
    if scenario is None:
        return None
    if (not isinstance(scenario, dict) or set(scenario) != {'evidence_level', 'balances_by_traveler'} or
            scenario['evidence_level'] != 'USER_REPORTED_APPROXIMATE' or
            not isinstance(scenario['balances_by_traveler'], dict) or
            set(scenario['balances_by_traveler']) != set(travelers)):
        raise ValidationError('explicit approximate balances must cover exactly the travelers')
    for value in scenario['balances_by_traveler'].values():
        if value is not None:
            number(value, 'approximate balance', integer=True)
    return copy.deepcopy(scenario)


def simulate(spend, scenario):
    """Each traveler pays their own cumulative itinerary; no cross-funding.

    Null means unknown. Never echo input balances in output metadata.
    """
    balances = scenario['balances_by_traveler']
    unknown = spend is None or any(v is None for v in balances.values())
    exceeded = [] if spend is None else sorted(t for t in spend if balances[t] is not None and spend[t] > balances[t])
    status = 'INFEASIBLE' if exceeded else 'UNKNOWN' if unknown else 'ESTIMATED_BUDGET_FEASIBLE'
    return {'status': status, 'evidence_level': 'USER_REPORTED_APPROXIMATE',
            'policy': 'OWN_ACCOUNT_PER_TRAVELER_NO_POOLING',
            'scenario_digest': stable_id('funding_scenario_', scenario),
            'spend_by_traveler': copy.deepcopy(spend),
            'remaining_by_traveler': {t: balances[t] - spend[t] for t in balances} if not unknown else None,
            'exceeded_travelers': exceeded,
            'funding_eligibility_status': 'NOT_CHECKED', 'airline_balance_verification': 'NOT_CHECKED'}
