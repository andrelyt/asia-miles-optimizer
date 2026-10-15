"""Opt-in reference evidence; all numerical lookup remains in V1.1.

Public corroboration is an auditable supplied attestation, never an airline quote.
Scope deliberately limited to supplied direct CX directions. No invented route type.
"""
import copy
from urllib.parse import urlparse

from optimizer import CABIN_RANK, cx_standard_base, number
from .award_adapter import _validate_candidate, rules_digest
from ._validation import parse_date
from .route_graph import stable_id

BASIS = 'SECONDARY_CORROBORATED_REFERENCE_CHART'


def reference_estimate(candidate, request, rules, profile):
    try:
        if _validate_candidate(candidate, request, rules):
            return None, 'REFERENCE_CANDIDATE_UNSUPPORTED'
        if (not isinstance(profile, dict) or profile.get('basis') != BASIS or
                profile.get('evidence_level') != 'SECONDARY_CORROBORATED_REFERENCE' or
                profile.get('rules_digest') != rules_digest(rules) or
                profile.get('rules_version') != rules['version'] or
                not isinstance(profile.get('chart_version'), str) or not profile['chart_version']):
            return None, 'REFERENCE_PROFILE_OR_RULE_BINDING_INVALID'
        checked = parse_date(profile['checked_at'])
        if checked < parse_date(rules['as_of']):
            return None, 'REFERENCE_CHECK_DATE_INVALID'
        sources = profile['sources']
        if not isinstance(sources, list):
            return None, 'REFERENCE_CORROBORATION_REQUIRED'
        hosts = set()
        for source in sources:
            url = urlparse(source['url'])
            if (url.scheme != 'https' or not url.hostname or
                    source['chart_digest'] != stable_id('chart_', rules['cx_standard_chart']) or
                    source['evidence_level'] != 'SECONDARY_CORROBORATION' or
                    source.get('independent_publication') is not True or
                    parse_date(source['checked_at']) > checked):
                return None, 'REFERENCE_CORROBORATION_REQUIRED'
            # Collapse subdomains; two URLs from one publisher are not independent.
            hosts.add('.'.join(url.hostname.lower().split('.')[-2:]))
        if len(hosts) < 2:
            return None, 'REFERENCE_CORROBORATION_REQUIRED'
        if (candidate['ticketing_mode'] != 'SINGLE_AWARD' or len(candidate['legs']) != 2 or
                len(candidate['tickets']) != 2 or any(
                    l['operating_carrier'] != rules['standard_award_constraints']['primary_carrier']
                    for l in candidate['legs'])):
            return None, 'REFERENCE_DIRECT_CX_ONLY'
        tickets = []
        for ticket in candidate['tickets']:
            if ticket['proposed_scheme'] != 'standard' or len(ticket['leg_indices']) != 1:
                return None, 'REFERENCE_DIRECT_CX_ONLY'
            leg = candidate['legs'][ticket['leg_indices'][0]]
            minimum = request['cabin_preferences']['longhaul_minimum' if leg['long_haul'] else 'shorthaul_minimum']
            if CABIN_RANK[leg['cabin']] < CABIN_RANK[minimum]:
                return None, 'REFERENCE_CABIN_BELOW_MINIMUM'
            route = profile['route_bands'].get(leg['origin'] + '-' + leg['destination'])
            if not isinstance(route, dict) or route.get('distance_status') != 'DISTANCE_PROVISIONAL':
                return None, 'REFERENCE_ROUTE_BAND_REQUIRED'
            band = next((b for b in rules['cx_standard_chart'] if b['label'] == route.get('band')), None)
            if (band is None or not band['min_mi'] <= leg['distance_miles'] <= band['max_mi'] or
                    band.get('route_type') != route.get('route_type') or
                    ('route_type' in band and not route.get('route_type_source_url'))):
                return None, 'REFERENCE_ROUTE_BAND_INVALID'
            miles = cx_standard_base(leg['distance_miles'], leg['cabin'], route.get('route_type'),
                                     rules['cx_standard_chart'])
            number(miles, 'reference miles', positive=True, integer=True)
            tickets.append({'ticket_id': ticket['ticket_id'], 'direction': ticket['direction'],
                            'cabin': leg['cabin'], 'band': band['label'],
                            'miles_per_person': miles, 'group_miles': miles * len(candidate['traveler_ids'])})
        total = sum(t['miles_per_person'] for t in tickets)
        return {'miles_per_person': total, 'group_miles': total * len(candidate['traveler_ids']),
                'miles_by_traveler': {t: total for t in candidate['traveler_ids']}, 'tickets': tickets,
                'basis': BASIS, 'evidence_level': profile['evidence_level'],
                'reference_digest': stable_id('reference_', profile), 'chart_version': profile['chart_version'],
                'rules_version': rules['version'], 'rules_digest': rules_digest(rules),
                'checked_at': profile['checked_at'], 'sources': copy.deepcopy(sources),
                'distance_status': 'DISTANCE_PROVISIONAL',
                'rule_applicability': 'CURRENT_REFERENCE_NOT_VERIFIED_FOR_TRAVEL_DATES',
                'award_seat_status': 'NOT_CHECKED', 'ticketability_status': 'NOT_CHECKED',
                'complete_price_comparison_eligible': False}, None
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration):
        return None, 'REFERENCE_INPUT_INVALID'
