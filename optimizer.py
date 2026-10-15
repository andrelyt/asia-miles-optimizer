#!/usr/bin/env python3
"""Asia Miles Hybrid Award Optimizer v1: auditable scenario comparator, not a booking service."""
from __future__ import annotations
import argparse, csv, itertools, json, sys
from pathlib import Path

CABIN_RANK={"Y":1,"W":2,"J":3,"F":4}
ONEWORLD_CARRIERS=set("AA AS BA CX AY IB JL MH QF QR RJ AT UL".split())

def tier_price(distance,cabin,bands):
    if distance is None or distance<=0: raise ValueError("oneworld 距离缺失或非正数")
    if cabin=="W": raise ValueError("oneworld multi-carrier 不提供 PE 舱位")
    for b in bands:
        if distance<=b["max_distance_miles"]:
            if cabin not in b["miles"]: raise ValueError(f"没有可用的 {cabin} 档位")
            return b["miles"][cabin],b["max_distance_miles"]-distance
    raise ValueError("oneworld 总飞行距离超过 50,000 英里")

def cx_standard_base(distance,cabin,route_type,chart):
    for band in chart:
        if band["min_mi"]<=distance<=band["max_mi"]:
            if band.get("route_type")!=route_type and "route_type" in band: continue
            if cabin not in band["miles"]: raise ValueError(f"该距离/航线未有 {cabin} 舱兑换价")
            return band["miles"][cabin]
    raise ValueError("找不到当前 CX 标准表档位；751–2750 英里需指定 route_type=1/2")

def mixed_cabin_price(legs,ticket,chart):
    if len(legs)!=2 or any(l.get("airline")!="CX" for l in legs):
        raise ValueError("V1 mixed cabin 仅支持单程2段且全部由 CX 承运")
    if legs[0]["to"]!=legs[1]["from"]: raise ValueError("mixed cabin 航段不连续")
    transfer_hours=ticket.get("transfer_hours")
    if transfer_hours is None or not 0<=transfer_hours<=24:
        raise ValueError("mixed cabin 中转时间必须提供且不超过24小时")
    distances=[l.get("distance_mi") for l in legs]
    if any(d is None or d<=0 for d in distances): raise ValueError("mixed cabin 每段必须提供经过复核的大圆距离")
    total=sum(distances); route_type=ticket.get("route_type")
    value=sum(cx_standard_base(total,l["cabin"],route_type,chart)*l["distance_mi"]/total for l in legs)
    return int(value//100*100)

def cash_check(option):
    known=0; missing=[]; assumed=[]
    for c in option.get("cash_items",[]):
        amount=c.get("hkd_per_person")
        if amount is None: missing.append(c["description"])
        elif amount<0: missing.append(f"负现金报价: {c['description']}")
        else: known+=amount
        if c.get("quote_type")=="assumption": assumed.append(c["description"])
    tax=option.get("taxes_and_surcharges_hkd_per_person")
    if tax is None: missing.append("税费/燃油附加费")
    else: known+=tax
    return known,missing,assumed

def validate_trip_paths(option,home_airports):
    issues=[]
    for trip in option.get("trips",[]):
        legs=trip.get("legs",[])
        if not legs: issues.append(trip.get("id","?")+" 无行程"); continue
        if legs[0]["from"] not in home_airports: issues.append(trip["id"]+" 未从允许的出发机场启程")
        if legs[-1]["to"] not in home_airports: issues.append(trip["id"]+" 未返回允许的到达机场")
        for a,b in zip(legs,legs[1:]):
            if a["to"]!=b["from"]: issues.append(trip["id"]+f" 断点 {a['to']} != {b['from']}")
        for v in trip.get("must_visit",[]):
            if v not in {x["to"] for x in legs}: issues.append(trip["id"]+" 未经过必访城市 "+v)
    return issues

def evaluate(option,rule_data,settings):
    errors=validate_trip_paths(option,settings.get("home_airports",["HKG"])); warnings=[]; per_person_miles=0; ticket_info=[]
    legs=[l for t in option.get("trips",[]) for l in t.get("legs",[])]
    award_legs=[l for l in legs if l.get("payment")=="award"]
    ticket_ids={t["id"] for t in option.get("award_tickets",[])}
    for l in award_legs:
        if l.get("ticket_id") not in ticket_ids: errors.append("奖励航段缺少 ticket 定义: "+str(l))
    for t in option.get("award_tickets",[]):
        tl=[l for l in award_legs if l.get("ticket_id")==t["id"]]
        if not tl: errors.append(t["id"]+" 没有关联飞行航段"); continue
        airlines={x.get("airline") for x in tl}; cabins={x.get("cabin") for x in tl}
        if any(c not in CABIN_RANK for c in cabins): errors.append(t["id"]+" 舱位代码非法"); continue
        top=max(cabins,key=lambda c:CABIN_RANK[c]); headroom=None
        if t["scheme"]=="oneworld_multi":
            if not airlines.issubset(ONEWORLD_CARRIERS): errors.append(t["id"]+" 有非 oneworld 航司或缺失航司")
            if ("CX" in airlines and len(airlines)<3) or ("CX" not in airlines and len(airlines)<2): errors.append(t["id"]+" 不满足多航空公司数量要求")
            if t.get("stopovers",0)>5 or t.get("transfers",0)>2 or t.get("open_jaws",0)>2: errors.append(t["id"]+" 超过停留/转机/开口上限")
            if "W" in cabins: errors.append(t["id"]+" oneworld multi-carrier 禁止 PE")
            if not t.get("route_constraints_confirmed"): warnings.append(t["id"]+" 复杂航线停留/开口/城市重复未获国泰确认")
            try:
                miles,headroom=tier_price(t.get("total_flight_distance_mi"),top,rule_data["oneworld_bands"])
                if headroom<=250: warnings.append(t["id"]+f" 距离跳档余量仅 {headroom:.0f} 英里，需要复核官方距离")
            except ValueError as exc: errors.append(t["id"]+" "+str(exc)); miles=0
        elif t["scheme"]=="standard":
            if t.get("miles_per_person") is None: errors.append(t["id"]+" 普通奖励票需要官方/人工里数报价"); miles=0
            else: miles=t["miles_per_person"]
            if t.get("pricing_status")!="verified": warnings.append(t["id"]+" 普通/伙伴奖励里数为参考值，需实际搜索确认")
        else: errors.append(t["id"]+" 未知兑换类型"); miles=0
        per_person_miles+=miles
        ticket_info.append({"ticket_id":t["id"],"scheme":t["scheme"],"miles_per_person":miles,"highest_cabin":top,"airlines":sorted(airlines),"distance_headroom_mi":headroom})
    pcount=len(settings["passengers"]); cost_cash,missing,assumed=cash_check(option)
    long_cabins=[]; short_cabins=[]
    for l in legs:
        if l.get("mode","flight")=="ground": continue
        (long_cabins if l.get("long_haul",False) else short_cabins).append(l.get("cabin","Y"))
    if any(CABIN_RANK.get(c,0)<CABIN_RANK.get(settings.get("min_longhaul_cabin","Y"),1) for c in long_cabins): errors.append("部分长途航班低于所选最低舱位")
    if any(CABIN_RANK.get(c,0)<CABIN_RANK.get(settings.get("min_shorthaul_cabin","Y"),1) for c in short_cabins): errors.append("部分短途航班低于所选最低舱位")
    award_seats=option.get("award_seats_two_people_confirmed",False)
    if not award_seats: warnings.append("尚未确认全部奖励航段有两个同航班、同舱位座位")
    if any(l.get("mode")=="flight" and l.get("payment")=="cash" for l in legs): warnings.append("有独立现金机票，联程保护和行李直挂不可默认成立")
    if missing: warnings.append("现金成本尚未完整报价: "+", ".join(missing))
    if assumed: warnings.append("现金数字只是演示假设: "+", ".join(assumed))
    group_miles=per_person_miles*pcount; balances=settings.get("balances_by_account",{}); allocations=[(p,t["ticket_id"],t["miles_per_person"]) for p in settings["passengers"] for t in ticket_info]; feasible=[]
    names=list(balances)
    if balances:
        for choices in itertools.product(names,repeat=len(allocations)):
            used=dict.fromkeys(names,0)
            for a,(_,__,val) in zip(choices,allocations): used[a]+=val
            if all(used[a]<=balances[a] for a in names):
                feasible=[{"payer":a,"passenger":p,"ticket_id":tid,"miles":cost} for a,(p,tid,cost) in zip(choices,allocations)]; break
        if not feasible: errors.append("现有两账户余额无法按独立奖励票分配支付（未假设跨账户合并）")
    estimated=group_miles*settings.get("mile_value_hkd",0.10)+cost_cash*pcount
    status="quoted_amounts_subject_to_ticketing" if not missing and not assumed and award_seats else "ILLUSTRATIVE_LOWER_BOUND_NOT_FINAL_PRICE"
    return {"id":option["id"],"name":option["name"],"per_person_miles":per_person_miles,"group_miles":group_miles,"cash_hkd_per_person_known":cost_cash,"group_cash_hkd_known":cost_cash*pcount,"valued_miles_plus_known_cash_hkd":round(estimated,2),"extra_travel_hours_per_person":option.get("extra_travel_hours_per_person"),"errors":errors,"warnings":warnings,"ticket_details":ticket_info,"account_allocation":feasible,"cost_status":status,"category":option.get("category","unspecified")}

def main():
    ap=argparse.ArgumentParser(description="Comparison only; no availability/fare searches")
    base=Path(__file__).parent
    ap.add_argument("--input",default=str(base/"sample_input.json")); ap.add_argument("--rules",default=str(base/"rules_2026_10.json")); ap.add_argument("--output",default=str(base/"sample_output.json")); ap.add_argument("--csv",default=str(base/"sample_comparison.csv"))
    args=ap.parse_args(); cfg=json.loads(Path(args.input).read_text(encoding="utf-8")); rules=json.loads(Path(args.rules).read_text(encoding="utf-8"))
    rows=[evaluate(x,rules,cfg["settings"]) for x in cfg["scenarios"]]; rows.sort(key=lambda r:(len(r["errors"])>0,r["valued_miles_plus_known_cash_hkd"]))
    Path(args.output).write_text(json.dumps({"metadata":{"purpose":"scenario comparison and rule validation only","warning":"NO LIVE award availability, NO real-time fares; missing fees excluded"},"results":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["name","category","per_person_miles","group_miles","cash_hkd_per_person_known","group_cash_hkd_known","valued_miles_plus_known_cash_hkd","cost_status","extra_travel_hours_per_person","errors","warnings"]
    with Path(args.csv).open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:" / ".join(r[k]) if isinstance(r.get(k),list) else r.get(k) for k in fields})
    print("写出:",args.output,"及",args.csv); return 0

if __name__=="__main__": sys.exit(main())
