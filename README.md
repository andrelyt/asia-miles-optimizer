# Asia Miles Hybrid Award Optimizer · V1.0 (2026-10-15)

**目的：**对两人、多次旅行的候选路线统一评估，涵盖 oneworld 多航司、国泰普通奖励、长途商务+短途经济、PE、全经济及现金/高铁接驳。它是可重复计算的**规则/方案比较原型**，不是实时航班查询器或出票代理。

## 已实现

- 自动根据距离档位给 oneworld 多航司票定价（Y/J/F），校验参与航司数、最多 5 停留、2 转机、2 开口、50,000 里上限；在距离跳档余量 <=250 英里时提醒。
- oneworld 不支持 PE；混入短途 Y 的多航司 J 票仍按 J 收费。
- 支持标准奖励票逐张独立报价。
- 支持国泰标准单程两段联程 `standard_mixed` 试算：按两段大圆距离比例，将整条单程距离档位下的对应舱等里数分配，再向下取整至百里；最终以国泰报价为准。
- 对每一次旅行检查从家门口枢纽出发、航段连续、经过必访目的地、返回可接受枢纽。
- 两人分别计价；真实账户不能直接合并。按每张旅客奖励票枚举由 Andre 或 Dony 哪个账户支付，检查各自余额是否够。
- 把机场往返地面交通、现金经济舱、普通奖励票、oneworld 多航司奖励票纳入统一已知成本比较。

## 使用

```bash
python3 optimizer.py
python3 -m unittest discover -p 'test_*.py' -v
```

默认载入 `rules_2026_10.json` 与 `sample_input.json`，默认生成 `sample_comparison.csv` 与 `sample_output.json`。生成文件不作为源码提交，可随时重新计算。

需要新的具体旅行时，复制 `sample_input.json`，编辑 `settings.passengers` / `balances_by_account` / `scenarios`，再执行：

```bash
python3 optimizer.py --input my_trip.json --output my_result.json --csv my_result.csv
```

## 重要警告

1. **没有自动找真实航班和奖励座位功能。** 要核验旅行日期、航线是否运营、有无两人同舱位奖励票，以及能否按一张多航司票出票。
2. 示例中的现金金额是**假设输入，为验证比较计算而非真实票价**。不得在对外推荐中当作实际报价。
3. 示例税费为 `null`，因此输出里的「里数估值+已输入现金」是**不完整成本**，不是全包价。
4. oneworld 多航司不能采用 PE。
5. 复杂行程里，停留/开口/城市重复/出票有效期尚未程序化逐时刻验证；最终需官方复核。
6. 距离接近档位边界需要重新核对。
7. 不访问、不抓取国泰账户，不处理个人登录凭据，不提供出票能力。

## 未来扩展

- 自动候选生成与航线图搜索。
- 航段级真实日期、最短换乘时间与独立机票转机风险。
- 奖励座位、现金价格、税费的实时查询接口。
- Pareto 前沿：里数、现金、时间、舱位覆盖与风险联合优化。
- AndreOS Knowledge/Skill 路由，让 Codex、ChatGPT 等 AI 读取同一规则源。

## 参考资料

- Cathay 2026 membership programme terms
- FlyAsia oneworld split planner / Cathay chart / mixed-cabin explainer
- PointsPlug 2026 award chart summary

具体来源 URL 保存在 `rules_2026_10.json`。第三方价格表可能存在版本差异，**最终以国泰实际搜索和客服报价为准**。

## Codex / AndreOS

Codex 开始任务时应先阅读 `SKILL.md`，再读取 `rules_2026_10.json`。GitHub 仓库是代码与规则版本的 SoT；AndreOS 只需保存仓库入口、版本和调用说明，不复制执行代码。
