"""Date-free decision presentation. Never removes candidates or asserts bookability."""
from .route_graph import stable_id

VIEWS = ('Miles Saver', 'Balanced', 'Comfort First', 'Leave Efficient')
HOLIDAY_LABEL = {'labor_day': 'MAY', 'national_day': 'OCT'}


def canonical_key(portfolio, candidates):
    trips = []
    for cid in portfolio['candidate_ids']:
        c = candidates[cid]
        window = c.get('holiday_window') or {}
        holiday = window.get('holiday_type')
        outbound = [l['cabin'] for l in c['legs'] if l['direction'] == 'outbound']
        inbound = [l['cabin'] for l in c['legs'] if l['direction'] == 'return']
        if not holiday or len(outbound) != 1 or len(inbound) != 1:
            raise ValueError('decision families currently require dated direct roundtrips')
        trips.append(':'.join((HOLIDAY_LABEL.get(holiday, holiday), c['destination'], outbound[0]+'-'+inbound[0])))
    return str(len(trips)) + '_TRIPS|' + '|'.join(sorted(trips))


def overlap(a, b):
    left, right = set(a), set(b)
    union = left | right
    return {'intersection': len(left & right), 'left_count': len(left), 'right_count': len(right),
            'overlap': len(left & right)/max(len(left), len(right)) if union else 1.0,
            'jaccard': len(left & right)/len(union) if union else 1.0}


def representative_key(row, request):
    leave = [sum(v.values()) for v in row['leave_days_by_traveler_by_year'].values()]
    miles = (row.get('estimate') or {}).get('total_miles')
    # No preferred-duration target was supplied. Do not invent one; all valid
    # request-range durations have equal fit. Duration remains a Pareto dimension.
    uncertainty = sum(v in ('UNKNOWN', 'UNVERIFIED', 'ESTIMATED', 'NOT_CHECKED', 'RULE_ESTIMATED')
                      for values in row['evidence'].values() for v in values)
    return (max(leave, default=0), sum(leave), miles is None, miles or 0,
            uncertainty, tuple(sorted(row['candidate_ids'])), row['portfolio_id'])


def _family_vector(family):
    p = family['best_representative']; miles = (p.get('estimate') or {}).get('total_miles')
    if miles is None or p['travel_calendar_days'] is None:
        return None
    return (miles, -p['trip_count'], p['group_leave_days'],
            -(p['longhaul_cabin_mean_rank'] or 0), -p['estimate']['cabin_mean_rank'],
            -p['travel_calendar_days']) + tuple(
                n for tid in sorted(p['leave_days_by_traveler_by_year'])
                for _, n in sorted(p['leave_days_by_traveler_by_year'][tid].items()))


def family_dominates(a, b):
    pa, pb = a['best_representative'], b['best_representative']
    # Optional destinations are meaningful alternatives, not interchangeable
    # utility. Compare cabins/windows only within the same destination/holiday mix.
    if (a['destination_holiday_mix'] != b['destination_holiday_mix'] or
            pa['evidence'] != pb['evidence'] or pa['status'] != pb['status'] or
            (pa.get('estimate') or {}).get('reference_digests') != (pb.get('estimate') or {}).get('reference_digests') or
            {t: sorted(y) for t,y in pa['leave_days_by_traveler_by_year'].items()} !=
            {t: sorted(y) for t,y in pb['leave_days_by_traveler_by_year'].items()}):
        return False
    av, bv = _family_vector(a), _family_vector(b)
    return (av is not None and bv is not None and len(av) == len(bv) and
            all(x <= y for x,y in zip(av,bv)) and any(x < y for x,y in zip(av,bv)))


def _order(family, view):
    p = family['best_representative']; miles = (p.get('estimate') or {}).get('total_miles')
    if view == 'Miles Saver':
        return (miles is None, miles or 0, family['canonical_key'])
    if view == 'Balanced':
        return (-p['trip_count'], miles is None, miles or 0, family['canonical_key'])
    if view == 'Comfort First':
        return (p['longhaul_cabin_mean_rank'] is None, -(p['longhaul_cabin_mean_rank'] or 0),
                -p['trip_count'], family['canonical_key'])
    return (not p['zero_leave'], p['leave_efficiency'] is None, -(p['leave_efficiency'] or 0),
            -(p['travel_calendar_days'] or 0), family['canonical_key'])


def verification_priority(family, core=False):
    if family['best_representative']['status'] != 'ESTIMATED_BUDGET_FEASIBLE':
        return 'LOW'
    p=family['best_representative']; funding=p.get('approximate_funding') or {}
    spend=funding.get('spend_by_traveler') or {}; remaining=funding.get('remaining_by_traveler') or {}
    near=any(remaining.get(t, float('inf')) <= 0.05*(spend[t]+remaining.get(t,0)) for t in spend)
    return 'HIGH' if near or (core and family['longhaul_premium']) else 'MEDIUM'


def summarize_families(result, request):
    candidates={t['candidate_id']:t['candidate'] for t in result['trips']}
    groups={}
    for p in result['conditional'] + result['budget_feasible']:
        key=canonical_key(p,candidates);groups.setdefault(key,[]).append(p)
    families=[]
    for key,variants in sorted(groups.items()):
        best=min(variants,key=lambda p:representative_key(p,request))
        trips=[]
        for cid in best['candidate_ids']:
            c=candidates[cid];w=c['holiday_window'];trips.append({
                'holiday':w['holiday_type'],'origin':c['origin'],'destination':c['destination'],
                'outbound_cabin':c['legs'][0]['cabin'],'inbound_cabin':c['legs'][-1]['cabin'],
                'start_date':w['start_date'],'end_date':w['end_date'],
                'calendar_days':w['calendar_trip_days'], 'leave_days_by_traveler':w['leave_days_by_traveler'],
                'candidate_id':cid,'longhaul':any(l['long_haul'] for l in c['legs'])})
        trips.sort(key=lambda t:(t['holiday'],t['destination'],t['outbound_cabin'],t['inbound_cabin']))
        family={'family_id':stable_id('family_',key),'canonical_key':key,'trip_count':len(trips),
                'trips':trips,'variant_count':len(variants),
                'variant_portfolio_ids':sorted(p['portfolio_id'] for p in variants),
                'best_representative':best,
                'destination_holiday_mix':sorted((t['holiday'],t['destination']) for t in trips),
                'longhaul_premium':any(t['longhaul'] and ('J' in (t['outbound_cabin'],t['inbound_cabin']) or 'W' in (t['outbound_cabin'],t['inbound_cabin'])) for t in trips),
                'longhaul_j':any(t['longhaul'] and 'J' in (t['outbound_cabin'],t['inbound_cabin']) for t in trips),
                'asymmetric':any(t['outbound_cabin']!=t['inbound_cabin'] for t in trips)}
        families.append(family)
    for f in families:
        f['family_pareto']=not any(family_dominates(other,f) for other in families if other is not f)
        f['verification_priority']=verification_priority(f)
    eligible=[f for f in families if f['best_representative']['status']=='ESTIMATED_BUDGET_FEASIBLE' and f['family_pareto']]
    views={v:[f['family_id'] for f in sorted(eligible,key=lambda f:_order(f,v))[:5]] for v in VIEWS}
    shortlist=[];roles={};byid={f['family_id']:f for f in families}
    def add(f,role):
        if f is None:return
        fid=f['family_id'];roles.setdefault(fid,[]).append(role)
        if fid not in shortlist and len(shortlist)<8:shortlist.append(fid)
    def choose(pool,view):
        return min(pool,key=lambda f:_order(f,view)) if pool else None
    for v in VIEWS:
        add(byid[views[v][0]] if views[v] else None,'BEST_'+v.upper().replace(' ','_'))
    add(choose([byid[fid] for fid in shortlist if byid[fid]['trip_count']==1] or
               [f for f in eligible if f['trip_count']==1],'Comfort First'),'STRONG_ONE_TRIP')
    add(choose([f for f in eligible if f['trip_count']==2],'Balanced'),'STRONG_TWO_TRIP')
    add(choose([f for f in eligible if f['asymmetric'] and f['longhaul_premium']],'Miles Saver'),'MIXED_CABIN_EFFICIENT')
    add(choose([f for f in eligible if f['longhaul_j']],'Comfort First'),'LONGHAUL_J')
    # Cover missing destinations before optional cabin variants. Roles overlap;
    # eight is a ceiling, never a target.
    covered_dest={t['destination'] for fid in shortlist for t in byid[fid]['trips']}
    for f in sorted(eligible,key=lambda f:_order(f,'Balanced')):
        dest={t['destination'] for t in f['trips']}
        if len(shortlist)>=8:break
        if dest-covered_dest:
            add(f,'DESTINATION_DIVERSITY');covered_dest|=dest
    reverse_mixed=[f for f in eligible if any(t['longhaul'] and t['outbound_cabin']=='W' and t['inbound_cabin']=='J' for t in f['trips'])]
    if len(shortlist)<8:
        add(choose(reverse_mixed,'Miles Saver'),'MIXED_CABIN_ALTERNATIVE_DIRECTION')
    shortlist_rows=[]
    for fid in shortlist:
        f=byid[fid];shortlist_rows.append({'family_id':fid,'canonical_key':f['canonical_key'],
            'roles':sorted(set(roles[fid])),'verification_priority':verification_priority(f,True)})
    # This is the exact unique direction/date/cabin lead set for later checking,
    # not evidence of a flight or an inventory request performed now.
    leads=set()
    for fid in shortlist:
        for t in byid[fid]['trips']:
            leads.add((t['origin'],t['destination'],t['start_date'],t['outbound_cabin']))
            leads.add((t['destination'],t['origin'],t['end_date'],t['inbound_cabin']))
    return {'families':families,'views':views,'verification_shortlist':shortlist_rows,
            'verification_leads':[dict(zip(('origin','destination','planning_date','cabin'),x)) for x in sorted(leads)],
            'family_pareto_count':sum(f['family_pareto'] for f in families),
            'representative_order':'max individual leave, group leave, estimated miles, uncertainty dimensions, candidate IDs; no preferred duration target supplied',
            'pareto_scope':'BEST_REPRESENTATIVES_WITHIN_DESTINATION_HOLIDAY_MIX_PLANNING_ONLY',
            'aggregation_scope':'RETURNED_PLANNING_FRONT; CANDIDATES_AND_PORTFOLIOS_NOT_REMOVED',
            'notice':'NOT BOOKABLE; CALENDAR ESTIMATED; SEATS/SCHEDULES/TAXES/TICKETABILITY NOT CHECKED'}
