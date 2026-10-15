#!/usr/bin/env python3
"""Asia Miles Hybrid Award Optimizer v1.1: supplied-candidate comparison only."""
from __future__ import annotations
import argparse, csv, itertools, json, math, sys
from pathlib import Path

CABIN_RANK={"Y":1,"W":2,"J":3,"F":4}

def number(value, label, positive=False, integer=False):
    if (isinstance(value,bool) or not isinstance(value,(int,float))
            or not math.isfinite(value) or value<0 or (positive and value==0)
            or (integer and int(value)!=value)):
        raise ValueError(label+" 必须是有限"+("正数" if positive else "非负数")+("整数" if integer else ""))
    return value

def tier_price(distance,cabin,bands,constraints):
    number(distance,"oneworld 距离",positive=True)
    if cabin not in CABIN_RANK: raise ValueError("舱位代码非法")
    if cabin=="W" and not constraints["premium_economy_offered"]:
        raise ValueError("oneworld multi-carrier 不提供 PE 舱位")
    if distance>constraints["max_flight_miles"]: raise ValueError("oneworld 总飞行距离超过规则上限")
    for b in bands:
        if distance<=b["max_distance_miles"]:
            if cabin not in b["miles"]: raise ValueError(f"没有可用的 {cabin} 档位")
            return number(b["miles"][cabin],"档位里数",integer=True),min(b["max_distance_miles"],constraints["max_flight_miles"])-distance
    raise ValueError("oneworld 距离没有可用计价档位")

def cx_standard_base(distance,cabin,route_type,chart):
    number(distance,"CX 距离",positive=True)
    if cabin not in CABIN_RANK: raise ValueError("舱位代码非法")
    route_types={b["route_type"] for b in chart if "route_type" in b}
    if route_type is not None and (isinstance(route_type,bool) or route_type not in route_types):
        raise ValueError("route_type 不属于规则表中的航线类型")
    for band in chart:
        if band["min_mi"]<=distance<=band["max_mi"]:
            if band.get("route_type")!=route_type and "route_type" in band: continue
            if cabin not in band["miles"]: raise ValueError(f"该距离/航线未有 {cabin} 舱兑换价")
            return number(band["miles"][cabin],"CX 档位里数",integer=True)
    raise ValueError("找不到当前 CX 标准表档位；部分距离需指定规则表中的 route_type")

def mixed_cabin_price(legs,ticket,chart,constraints):
    if len(legs)!=constraints["leg_count"] or any(l.get("airline") not in constraints["allowed_carriers"] for l in legs):
        raise ValueError("mixed cabin 航段数或承运航司不符合规则")
    if any(not l.get("from") or not l.get("to") for l in legs): raise ValueError("mixed cabin 缺少起降机场")
    if any(a["to"]!=b["from"] for a,b in zip(legs,legs[1:])): raise ValueError("mixed cabin 航段不连续")
    if legs[0]["from"]==legs[-1]["to"]: raise ValueError("mixed cabin 必须是单程，不能将往返作为一张单程报价")
    transfer_hours=ticket.get("transfer_hours")
    number(transfer_hours,"mixed cabin transfer_hours")
    if transfer_hours>constraints["max_transfer_hours"]:
        raise ValueError("mixed cabin 中转时间超过规则上限")
    distances=[l.get("distance_mi") for l in legs]
    for d in distances: number(d,"mixed cabin 每段大圆距离",positive=True)
    total=sum(distances); route_type=ticket.get("route_type")
    value=sum(cx_standard_base(total,l.get("cabin"),route_type,chart)*l["distance_mi"]/total for l in legs)
    increment=number(constraints["round_down_increment"],"混舱取整单位",positive=True,integer=True)
    return int(value//increment*increment)

def cash_check(option,legs):
    known=0; missing=[]; assumed=[]; errors=[]; item_ids=set()
    for c in option.get("cash_items") or []:
        label=c.get("description",c.get("id","现金项"))
        if c.get("id"):
            if c["id"] in item_ids: errors.append("现金项 id 重复: "+c["id"])
            item_ids.add(c["id"])
        amount=c.get("hkd_per_person")
        if amount is None: missing.append(label)
        else:
            try: known+=number(amount,label)
            except ValueError as exc: errors.append(str(exc))
            if c.get("quote_type")!="quoted": assumed.append(label)
    for l in legs:
        if l.get("payment")=="cash" and l.get("cash_item_id") not in item_ids:
            missing.append("未关联现金报价: "+str(l.get("from"))+"-"+str(l.get("to")))
    tax=option.get("taxes_and_surcharges_hkd_per_person")
    if tax is None: missing.append("税费/燃油附加费")
    else:
        try: known+=number(tax,"税费/燃油附加费")
        except ValueError as exc: errors.append(str(exc))
        if option.get("taxes_quote_type")!="quoted": assumed.append("税费/燃油附加费")
    return known,list(dict.fromkeys(missing)),list(dict.fromkeys(assumed)),errors

def validate_trip_paths(option,home_airports):
    issues=[]
    if not option.get("trips"): return ["scenario 缺少非空 trips 行程"]
    for trip in option.get("trips",[]):
        tid=trip.get("id","?")
        legs=trip.get("legs",[])
        if not legs: issues.append(tid+" 无行程 legs"); continue
        if any(not l.get("from") or not l.get("to") for l in legs): issues.append(tid+" 缺少起降机场")
        if legs[0].get("from") not in home_airports: issues.append(tid+" 未从允许的出发机场启程")
        if legs[-1].get("to") not in home_airports: issues.append(tid+" 未返回允许的到达机场")
        for a,b in zip(legs,legs[1:]):
            if a.get("to")!=b.get("from"): issues.append(tid+f" 断点 {a.get('to')} != {b.get('from')}")
        for v in trip.get("must_visit",[]):
            if v not in {x.get("to") for x in legs}: issues.append(tid+" 未经过必访机场 "+v)
    return issues

def evaluate(option,rule_data,settings):
    errors=validate_trip_paths(option,settings.get("home_airports",["HKG"])); warnings=[]; per_person_miles=0; ticket_info=[]
    legs=[l for t in option.get("trips") or [] for l in t.get("legs") or []]
    for l in legs:
        if l.get("mode","flight") not in ("flight","ground"): errors.append("非法交通 mode")
        if l.get("payment") not in ("award","cash"): errors.append("非法 payment 类型")
        if l.get("mode","flight")=="ground" and l.get("payment")=="award": errors.append("地面接驳不能作为奖励飞行航段")
        if l.get("mode","flight")=="flight" and l.get("cabin") not in CABIN_RANK: errors.append("舱位代码非法")
        if "distance_mi" in l:
            try: number(l["distance_mi"],"航段距离",positive=True)
            except ValueError as exc: errors.append(str(exc))
    award_legs=[l for l in legs if l.get("payment")=="award" and l.get("mode","flight")=="flight"]
    tickets=option.get("award_tickets") or []; ticket_ids=[t.get("id") for t in tickets]
    if any(not tid for tid in ticket_ids) or len(set(ticket_ids))!=len(ticket_ids): errors.append("奖励票 id 缺失或重复")
    for l in award_legs:
        if not l.get("ticket_id") or l.get("ticket_id") not in ticket_ids: errors.append("奖励航段缺少 ticket 定义")
    for t in tickets:
        tid=t.get("id","?"); tl=[l for l in award_legs if l.get("ticket_id")==tid]
        if not tl: errors.append(str(tid)+" 没有关联飞行航段"); continue
        airlines={x.get("airline") for x in tl}; cabins={x.get("cabin") for x in tl}
        if any(c not in CABIN_RANK for c in cabins): errors.append(str(tid)+" 舱位代码非法"); continue
        top=max(cabins,key=lambda c:CABIN_RANK[c]); headroom=None; scheme=t.get("scheme")
        try:
            if scheme=="oneworld_multi":
                c=rule_data["oneworld_constraints"]
                if not airlines.issubset(set(c["allowed_carriers"])): raise ValueError("有非 oneworld 航司或缺失航司")
                count_key="carrier_count_if_CX_included" if "CX" in airlines else "carrier_count_if_no_CX"
                if len(airlines)<c[count_key]: raise ValueError("不满足多航空公司数量要求")
                for field,limit in (("stopovers","max_stopovers"),("transfers","max_transfers"),("open_jaws","max_open_jaws")):
                    count=number(t.get(field,0),field,integer=True)
                    if count>c[limit]: raise ValueError(field+" 超过规则上限")
                if "W" in cabins and not c["premium_economy_offered"]: raise ValueError("oneworld multi-carrier 禁止 PE")
                if not c["whole_ticket_highest_cabin_pricing"] and len(cabins)>1:
                    raise ValueError("规则不采用最高舱位计价；V1.1 尚不支持替代混舱算法")
                miles,headroom=tier_price(t.get("total_flight_distance_mi"),top,rule_data["oneworld_bands"],c)
                if headroom<=c["distance_warning_headroom_mi"]: warnings.append(str(tid)+f" 距离跳档余量仅 {headroom:.0f} 英里，需要复核官方距离")
                if not t.get("route_constraints_confirmed"): warnings.append(str(tid)+" 复杂航线停留/开口/城市重复未获国泰确认")
            elif scheme=="standard":
                miles=number(t.get("miles_per_person"),"普通奖励票 miles_per_person",integer=True)
                if t.get("pricing_status")!="verified": warnings.append(str(tid)+" 普通/伙伴奖励里数为参考值，需实际搜索确认")
            elif scheme=="standard_mixed":
                # Legs are linked from trips by ticket_id, in supplied travel order.
                if sum(any(l.get("ticket_id")==tid and l.get("payment")=="award" for l in trip.get("legs") or []) for trip in option.get("trips") or [])!=1:
                    raise ValueError("mixed cabin 单程航段必须位于同一次 trip")
                miles=mixed_cabin_price(tl,t,rule_data["cx_standard_chart"],rule_data["standard_mixed_constraints"])
                warnings.append(str(tid)+" mixed cabin 为距离比例试算，最终以国泰整票报价为准")
            else: raise ValueError("未知兑换类型: "+str(scheme))
        except (ValueError,TypeError,KeyError) as exc:
            errors.append(str(tid)+" "+str(exc)); continue
        per_person_miles+=miles
        ticket_info.append({"ticket_id":tid,"scheme":scheme,"miles_per_person":miles,"highest_cabin":top,"airlines":sorted(a for a in airlines if a),"distance_headroom_mi":headroom})
    passengers=settings.get("passengers") or []; pcount=len(passengers)
    if not passengers or len(set(passengers))!=pcount: errors.append("passengers 必须非空且不重复")
    cost_cash,missing,assumed,cash_errors=cash_check(option,legs); errors.extend(cash_errors)
    for key in ("min_longhaul_cabin","min_shorthaul_cabin"):
        if settings.get(key,"Y") not in CABIN_RANK: errors.append(key+" 舱位代码非法")
    for l in legs:
        if l.get("mode","flight")=="ground": continue
        key="min_longhaul_cabin" if l.get("long_haul",False) else "min_shorthaul_cabin"
        if CABIN_RANK.get(l.get("cabin"),0)<CABIN_RANK.get(settings.get(key,"Y"),1): errors.append("航班低于所选最低舱位: "+key)
    if award_legs and not option.get("award_seats_two_people_confirmed",False): warnings.append("尚未确认全部奖励航段有两个同航班、同舱位座位")
    if any(l.get("mode","flight")=="flight" and l.get("payment")=="cash" for l in legs): warnings.append("有独立现金机票，联程保护和行李直挂不可默认成立")
    if missing: warnings.append("现金成本尚未完整报价: "+", ".join(missing))
    if assumed: warnings.append("现金数字为假设或未标 quoted: "+", ".join(assumed))
    group_miles=per_person_miles*pcount; balances=settings.get("balances_by_account") or {}; feasible=[]
    allocations=[(p,t["ticket_id"],t["miles_per_person"]) for p in passengers for t in ticket_info if t["miles_per_person"]>0]
    try:
        for balance in balances.values(): number(balance,"账户余额",integer=True)
        mile_value=number(settings.get("mile_value_hkd",0.10),"mile_value_hkd")
    except ValueError as exc:
        errors.append(str(exc)); mile_value=0
    allocation_status="NOT_CHECKED" if errors else "NOT_REQUIRED" if not allocations else "NOT_CHECKED"
    if allocations and not balances: warnings.append("未提供独立账户余额，未检查支付可行性")
    if allocations and balances and not errors:
        names=list(balances); allocation_status="INSUFFICIENT"
        for choices in itertools.product(names,repeat=len(allocations)):
            used=dict.fromkeys(names,0)
            for a,(_,__,val) in zip(choices,allocations): used[a]+=val
            if all(used[a]<=balances[a] for a in names):
                feasible=[{"payer":a,"passenger":p,"ticket_id":tid,"miles":cost} for a,(p,tid,cost) in zip(choices,allocations)]
                allocation_status="FEASIBLE"; break
        if allocation_status=="INSUFFICIENT": errors.append("账户余额无法按独立奖励票分配支付（未假设跨账户合并）")
    estimated=round(group_miles*mile_value+cost_cash*pcount,2) if not errors else None
    status=("INVALID" if errors else "PARTIAL_ASSUMPTION" if missing and assumed else
            "PARTIAL_LOWER_BOUND" if missing else "ASSUMPTION" if assumed else "COMPLETE_QUOTED")
    comparable=not errors and not missing and not assumed
    return {"id":option.get("id","?"),"name":option.get("name","?"),"per_person_miles":per_person_miles,"group_miles":group_miles,"cash_hkd_per_person_known":cost_cash,"group_cash_hkd_known":cost_cash*pcount,"valued_miles_plus_known_cash_hkd":estimated,"extra_travel_hours_per_person":option.get("extra_travel_hours_per_person"),"errors":errors,"warnings":warnings,"ticket_details":ticket_info,"account_allocation":feasible,"account_allocation_status":allocation_status,"cost_status":status,"missing_cost_components":missing,"assumed_cost_components":assumed,"complete_price_comparison_eligible":comparable,"category":option.get("category","unspecified")}


def sort_results(rows):
    """Only rank complete declared costs within a cabin/category group.

    Partial/assumption rows retain input order; invalid rows go last.
    This is display order, never a ticketability or global optimality claim.
    """
    return sorted(rows,key=lambda r:(bool(r["errors"]),r["category"],
                  not r["complete_price_comparison_eligible"],
                  r["valued_miles_plus_known_cash_hkd"] if r["complete_price_comparison_eligible"] else 0))


def latest_rules(base):
    paths=sorted(base.glob("rules_*.json"))
    if not paths: raise ValueError("没有 rules_*.json")
    return paths[-1]

def main():
    ap=argparse.ArgumentParser(description="Comparison only; no availability/fare searches")
    base=Path(__file__).parent
    ap.add_argument("--input",default=str(base/"sample_input.json")); ap.add_argument("--rules",default=str(latest_rules(base))); ap.add_argument("--output",default=str(base/"sample_output.json")); ap.add_argument("--csv",default=str(base/"sample_comparison.csv"))
    args=ap.parse_args(); cfg=json.loads(Path(args.input).read_text(encoding="utf-8")); rules=json.loads(Path(args.rules).read_text(encoding="utf-8"))
    rows=sort_results([evaluate(x,rules,cfg["settings"]) for x in cfg["scenarios"]])
    Path(args.output).write_text(json.dumps({"metadata":{"purpose":"scenario comparison and rule validation only","version":"1.1", "rules_file":Path(args.rules).name, "rules_as_of":rules.get("as_of"), "sorting":"category; complete declared costs ascending; partial/assumption input order; invalid last", "warning":"NO LIVE award availability or fares; COMPLETE_QUOTED describes supplied cash only, not ticketability; partial/assumed costs cannot be ranked as full prices"},"results":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["name","category","per_person_miles","group_miles","cash_hkd_per_person_known","group_cash_hkd_known","valued_miles_plus_known_cash_hkd","cost_status","complete_price_comparison_eligible","missing_cost_components","assumed_cost_components","account_allocation_status","extra_travel_hours_per_person","errors","warnings"]
    with Path(args.csv).open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:" / ".join(r[k]) if isinstance(r.get(k),list) else r.get(k) for k in fields})
    print("写出:",args.output,"及",args.csv); return int(any(r["errors"] for r in rows))

if __name__=="__main__": sys.exit(main())
