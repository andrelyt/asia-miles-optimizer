"""Bounded whole-portfolio account assignment, never award pricing or pooling."""
from .award_adapter import sourced


def eligibility_confirmed(record, account, passenger, start, end):
    return (sourced(record, {"SUPPLIED_CONFIRMED"}) and record.get("decision") == "ELIGIBLE" and
            record.get("account_id") == account and record.get("traveler_id") == passenger and
            start is not None and end is not None and
            record.get("valid_from", "~") <= start <= end <= record.get("valid_until", ""))


def allocate(jobs, balances, eligibility, counter, limit, confirmed_only=False):
    """DFS with residual-state memoization. Each job is wholly paid by one account.

    counter is shared across all portfolios and both eligibility searches. LIMIT
    is unresolved, never proof of insufficient balances. No yearly replenishment.
    """
    accounts = sorted(balances)
    ordered = sorted(jobs, key=lambda j: (-j['miles'], j['candidate_id'], j['ticket_id'], j['passenger']))
    initial = tuple(balances[a] for a in accounts)
    if counter['visited'] >= limit:
        counter['truncated'] = True
        return 'LIMIT', None
    stack = [(0, initial, ())]
    counter['visited'] += 1
    seen = set()
    while stack:
        index, remaining, choices = stack.pop()
        key = (index, remaining)
        if key in seen:
            continue
        seen.add(key)
        if index == len(ordered):
            rows = [dict(job, payer=accounts[a]) for job, a in zip(ordered, choices)]
            return 'FEASIBLE', rows
        job = ordered[index]
        for a in reversed(range(len(accounts))):
            account = accounts[a]
            if remaining[a] < job['miles']:
                continue
            eligibility_start = job['start_date']
            if eligibility_start and job.get('booking_date'):
                eligibility_start = min(eligibility_start, job['booking_date'])
            if confirmed_only and not any(eligibility_confirmed(e, account, job['passenger'],
                    eligibility_start, job['end_date']) for e in eligibility):
                continue
            if counter['visited'] >= limit:
                counter['truncated'] = True
                return 'LIMIT', None
            counter['visited'] += 1
            updated = list(remaining); updated[a] -= job['miles']
            stack.append((index + 1, tuple(updated), choices + (a,)))
    return 'INFEASIBLE', None
