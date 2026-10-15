# Asia Miles Hybrid Award Optimizer · V1.1 (2026-10-15)

**目的：**对人工提供的多人、多次旅行候选路线进行确定性计价、基础校验和成本比较。标准 Python，无第三方依赖。它不会查找实时航班、奖励座位或现金票价，不会自动生成路线、确认可出票或出票。

GitHub 仓库是可执行代码、规则版本与测试的 **Source of Truth**；AndreOS 保存项目入口与检查点，不复制执行代码。

## 已实现

- oneworld 多航司票按规则文件的距离档位计价；执行航司资格、航司数量、停留/转机/开口数量和总距离上限校验。当前规则为含 CX 至少 3 家、不含 CX 至少 2 家，最多 5 停留、2 转机、2 开口、50,000 英里。距离档位或总上限余量不超过 250 英里时提醒。
- 当前 oneworld 规则不提供 PE；混合 J/Y 的整票按最高舱位 J 计价。
- `standard` 奖励票使用输入的非负整数 `miles_per_person`，不自动查价；未标 `pricing_status="verified"` 的里数会给出参考价警告。
- `standard_mixed` 已接入 `evaluate()`：从 `trips[].legs` 按 `ticket_id` 关联航段，以输入顺序取得同一次 trip 内的一张单程两段 CX 联程；按每段距离比例分配整条单程总距离档位下的各舱里数，向下取整至百里，并参与独立账户分配。它仍是试算，最终以国泰整票报价为准。
- 混舱要求航段连续、起终点不同、每段距离为有限正数，且提供 0–24 小时的 `transfer_hours`。当总距离落在含 `route_type` 的档位时必须提供对应类型；提供的类型必须在规则表中存在。
- 每次 trip 检查非空 legs、从允许机场出发、回到允许机场、航段连续及经过 `must_visit` 中的机场；检查长短途最低舱位。
- 对每位旅客的每张奖励票枚举付款账户，检查各账户独立余额，不假设余额可合并。没有里数支付需求时不做分配，纯现金方案正常计价、校验。未提供余额时明确标记未检查。
- 拒绝空 trips/legs、负或非有限里数/现金/税费/距离、非法舱位及非法数量输入；整数里数和停留次数不接受小数、布尔值或数字字符串。非法方案标记 `INVALID`，估值输出为 `null`，放在展示列表末尾。
- 输出 JSON 与 CSV，保留成本完整性、缺失项、假设项、账户分配状态及风险警告。

## 使用

```bash
python3 -B -m unittest discover -p 'test_*.py' -v
python3 -B optimizer.py
```

默认载入仓库内文件名排序最新的 `rules_*.json`（版本命名须使用补零的 `rules_YYYY_MM.json`）与 `sample_input.json`；默认生成 `sample_comparison.csv` 和 `sample_output.json`。可显式锁定规则版本：

```bash
python3 -B optimizer.py --rules rules_2026_10.json --input my_trip.json --output my_result.json --csv my_result.csv
```

存在 validation error 时仍写出诊断结果，退出码为 1；否则为 0。结果文件与缓存不应提交。

### 输入约定

- 参考样例编辑 `settings.passengers`、独立 `balances_by_account`、可接受 `home_airports`、最低长短途舱位和 `scenarios`。每人假定乘坐同一方案；不支持旅客各自不同路线。账户分配仅检查数学余额，不验证兑换受益人资格。
- 每个飞行 leg 明确填写 `from`、`to`、`payment`、`cabin`；`mode` 省略时视为 `flight`。奖励飞行 leg 的 `ticket_id` 对应 `award_tickets[].id`，id 必须非空且唯一。地面接驳使用 `mode="ground"`、`payment="cash"`。
- `standard_mixed` 票填写 `scheme`、`transfer_hours`、必要时填写 `route_type`；各 leg 填写 `airline="CX"`、`cabin`、`distance_mi`。不要在 ticket 内另复制一套 legs。样例 M 展示往返分别作为两张单程混舱票。
- 每个现金 leg 的 `cash_item_id` 对应 `cash_items[].id`，每项金额为 `hkd_per_person`。往返票或多段接驳可共用一个合并现金项，该项只加总一次；输入方负责确认覆盖完整、没有重复计费。
- 未知现金金额使用 `null`；真实已取得报价标 `quote_type="quoted"`，演示值标 `"assumption"`。未标 quoted 的已知金额均按假设处理。
- 税费单独填写 `taxes_and_surcharges_hkd_per_person` 和 `taxes_quote_type`。若现金项已经含全部税费，可填税费 0，并在现金项说明中注明含税，避免重复计费；0 也需要说明报价状态。
- 所有现金使用 HKD、每人金额；`mile_value_hkd` 是比较假设，默认 0.10，不代表官方现金兑换价值。

样例 A/B/G/I 保留原有商务/PE/经济组合；新增 M 混舱、C 纯现金。所有样例账户余额、距离与金额均为演示输入，不是用户真实余额、观测价格或可出票证明。`travel_windows` 仅为上下文，程序不检查日期。

## 成本状态与排序语义

`valued_miles_plus_known_cash_hkd` = 全组里数 × 所选里数估值 + 全组已输入现金。它不会补齐未知费用，也不把假设变成报价。

| cost_status | 含义 | complete_price_comparison_eligible |
|---|---|---|
| `COMPLETE_QUOTED` | 已声明现金项目完整且均标 quoted，无校验错误 | true |
| `PARTIAL_LOWER_BOUND` | 有缺失费用，没有已知假设金额 | false |
| `ASSUMPTION` | 无缺失项，但包含假设或未标 quoted 金额 | false |
| `PARTIAL_ASSUMPTION` | 同时有缺失项与假设金额；不保证是真实总价下界 | false |
| `INVALID` | 输入/约束/支付余额校验失败，估值为 null | false |

机器还应读取 `missing_cost_components`、`assumed_cost_components`、`errors`、`warnings`、`account_allocation_status`。账户状态为 `NOT_REQUIRED`、`NOT_CHECKED`、`FEASIBLE` 或 `INSUFFICIENT`；有其他输入错误时不尝试分配。

**true 仅允许比较当前输入模型下的完整声明成本，不代表官方最终全包价。** 里数可能仍为静态表或混舱估算；quoted、座位和路线确认标记均由输入方提供，程序没有独立核验。缺失现金 leg 报价关联时一定标 PARTIAL。

展示顺序先区分有效/非法，再按输入 `category` 分组；同组完整声明成本才按数值升序。不完整/假设方案保留同组输入顺序，不按较低估值评优。不同舱位、不同里数估值基准或不同缺失程度不得直接宣布全局胜者；category 由输入方负责准确标注。一个完整报价排在不完整方案前，仅表示可比较性分组，不能证明它更便宜。

## 规则 Source of Truth

`rules_*.json` 管理价格表、oneworld 航司集合/数量、数量上限、总距离、PE 开关、最高舱位计价开关和边界提醒阈值；也管理混舱航段数、允许航司、中转时长和取整单位。Python 解释和执行这些值，不再维护另一套政策数字。

`whole_ticket_highest_cabin_pricing=false` 时，统一舱位仍可计价；不同舱位票会明确报“不支持替代混舱算法”，不会悄悄继续按最高舱位。启用 PE 也必须同时提供 W 价格；提高距离上限也须提供相应档位。JSON 可以改变参数和开关，不能凭空提供新的计价算法。

Python 保留舱位代码/等级、票种分派、单程/连续性验证、账户枚举、默认估值等程序语义或比较默认值。旧版直接调用计价函数的代码需显式传入对应 constraints；缺少规则字段不会回退到旧政策常量。

## 尚未实现 / 风险边界

- 实时奖励座位、真实现金价格/税费查询、API/登录账户集成、自动出票。
- 自动候选生成、全球路线图搜索和全局最优/Pareto 优化。
- 真实日期、航线运营、最短换乘时间、独立票转机保护、出票有效期和城市重复规则的完整核验。
- 停留/转机/开口数量与总飞行距离由输入方提供，程序只检查数值和上限，不根据航段/日期重新推导；复杂多航司整票需国泰复核。
- 独立账户枚举在票/旅客数量很多时呈指数增长；当前用于小规模人工候选。

规则来源含官方条款及第三方重建表，URL 保留在规则文件；本次重构没有重新认定这些表为官方报价，最终以国泰实际搜索和客服整票报价为准。
