"""Generate explanatory Chinese SVG formula/decision cards for the 23 options lessons.

Each card is an independent, hypothetical teaching example. The original lesson
math and payoff diagrams remain authoritative; this generator avoids LaTeX and
uses only plain SVG/XML and standard-library code.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET

# (short title, one-sentence purpose, cards, variables, common mistakes).
# Card = (name, plain-language formula/rule, why, worked example, scope).
DATA = {
"L01": (
"期权到底怎么赚、怎么亏", "先把每股的到期结果算清，再乘每张合约的股数。",
[
("买入看涨 Call｜到期净盈亏", "净盈亏/股 = max(到期股价 − 行权价, 0) − 买入权利金", "涨过行权价才有内在价值；还要先挣回买入的权利金。", "K=100、权利金4、到期112 → (12−4)×100 = 盈利800美元", "仅是到期结果；持有期间价格还受IV等因素影响。"),
("买入看跌 Put｜到期净盈亏", "净盈亏/股 = max(行权价 − 到期股价, 0) − 买入权利金", "下跌越深，看跌合约的到期内在价值越高。", "K=100、权利金3、到期90 → (10−3)×100 = 盈利700美元", "买方最大亏损是已付权利金；标准股票不会跌破零。"),
("盈亏平衡｜先问要涨跌多少", "Call保本价 = K + 权利金；Put保本价 = K − 权利金", "到期内在价值刚好覆盖权利金时，经济净盈亏为零。", "Call：100+4=104；Put：100−3=97（均未计交易费）", "若加上手续费或真实买卖价差，保本价还会改变。")
], "K＝行权价；到期股价＝合约到期时股票价格；max(a,0)＝a与0取较大值；每张示例＝100股。",
["“股票涨了”不代表买Call赚钱：必须超出权利金成本。","到期盈亏函数不是今天可以成交的平仓价格。"]),
"L02": (
"合约乘数、行权和指派", "先认清持有的是“权利”还是“义务”，再算实际现金和股票。",
[
("支付或收取多少权利金", "合约权利金总额 = 每股期权报价 × 乘数 × 张数", "美股普通标准股票期权通常按每张100股计价。", "报价2.50美元/股，买2张 → 2.50×100×2 = 支付500美元", "调整合约的乘数/交割物可能不同，必须核对合约说明。"),
("Call买方主动行权", "行权买股支付 = 行权价 × 每张股数 × 张数", "行权后通常付钱买股票；不是按市场价任意结算。", "1张K100、交割100股 → 支付10,000美元，收到100股", "仅适用实物交割的股票Call；指数现金结算合约不同。"),
("Put卖方被指派", "接股需付现金 = 行权价 × 交割股数 × 被指派张数", "卖Put得到权利金，同时承担按K买入股票的义务。", "被指派1张K95普通Put → 付9,500美元，收到100股", "美式期权可能提前指派；保证金不等于实际交割款。")
], "乘数＝每张对应的合约单位；K＝行权价；卖方被指派＝须履行合同；买方行权＝选择使用权利。",
["平台显示的权利金入账，不等于已经实现无风险利润。","实物交割与现金结算不能用同一个接股公式。"]),
"L03": (
"一张期权为什么值这个价", "先拆内在价值，再看外在价值，最后讨论IV与成交价格。",
[
("Call当前内在价值", "看涨内在价值/股 = max(当前股价 − K, 0)", "只有立即行权有利的部分，才属于Call的内在价值。", "当前股价105、K100 → 内在价值5美元/股", "美式普通股票期权的内在价值定义；不含交易费用。"),
("Put当前内在价值", "看跌内在价值/股 = max(K − 当前股价, 0)", "股票越低于Put的行权价，内在价值通常越高。", "当前股价94、K100 → 内在价值6美元/股", "价外期权内在价值为零，但仍可能有外在价值。"),
("外在价值（常被叫时间价值）", "外在价值 = 期权报价 − 内在价值", "支付的溢价中，超过立刻行权价值的部分。", "Call报价7.20、内在价值5 → 外在价值2.20美元/股", "报价需明确Bid、Ask或Mid；IV不是能直接加减的现金。")
], "当前股价＝此刻的股票价格；K＝行权价；IV＝市场价格反推的隐含波动率；RV＝历史或未来实现波动率。",
["价外期权“内在价值为零”并不等于价格为零。","IV不是交易所额外发给你的收益，也不是保证实现的涨跌幅。"]),
"L04": (
"买卖Call/Put四种基本头寸", "每一种都先分清：哪边有权利、哪边承担义务。",
[
("买Call｜看涨，付钱换上涨", "盈亏/股 = max(到期价 − K, 0) − C", "下跌时最多损失所付权利金，上涨时理论收益不封顶。", "K100、C4、到期115 → (15−4)×100 = +1,100美元", "C是买入成本，不是期权当日市场最新报价。"),
("卖Call｜赚权利金，怕暴涨", "盈亏/股 = C − max(到期价 − K, 0)", "卖出的是义务；裸卖Call理论最大亏损无上限。", "K100、收C4、到期115 → (4−15)×100 = −1,100美元", "备兑Call要再加入持股的收益，不能只看空Call腿。"),
("买Put｜付钱换下跌保护", "盈亏/股 = max(K − 到期价, 0) − P", "到期下跌才有内在价值；最大损失为购买成本。", "K100、P3、到期90 → (10−3)×100 = +700美元", "若与股票组成保护性Put，必须把持股损益一起计算。"),
("卖Put｜收钱，承担接股义务", "盈亏/股 = P − max(K − 到期价, 0)", "最赚所收权利金，股票暴跌时亏损可能远大于收入。", "K100、收P3、到期90 → (3−10)×100 = −700美元", "现金担保和裸卖Put的经济到期函数一样、资金风险不同。")
], "K＝行权价；C＝Call权利金；P＝Put权利金；max＝取较大值；全部示例每张100股且忽略手续费。",
["卖方最大利润是权利金，但并不意味着收款当日就锁定盈利。","到期损益图无法显示早指派、追加保证金和强制平仓。"]),
"L05": (
"Delta和股票等效暴露", "Delta告诉你小幅股价变动时，期权价格大概跟着动多少。",
[
("Delta｜一阶价格近似", "期权价格变化 ≈ Delta × 股票价格变化", "股价只动一点时，可用Delta估算期权每股价格变化。", "Call Delta=0.60、股价涨3美元 → 期权约涨1.80美元/股", "这是一阶局部近似；Gamma、IV和时间仍会造成误差。"),
("组合的股票等效股数", "等效股数 ≈ Delta × 乘数 × 合约张数", "把方向暴露换算成多少股股票的近似反应。", "2张Call、每张100股、Delta=0.60 → 等效多头120股", "等效股数会随着行情变化，不是真实交割的持股数量。"),
("临时对冲｜方向暴露归零", "需交易股票数 ≈ −期权组合等效股数", "正Delta通常用卖出股票对冲，负Delta通常反向操作。", "期权组合等效多头120股 → 暂时卖出120股做Delta对冲", "Delta中性不代表Gamma、Vega、跳空风险也为零。")
], "Delta＝期权每股价格对股价的局部敏感度；乘数＝每张股数；负号＝反向持仓。",
["Delta接近0.6，不表示真实到期赚钱概率一定是60%。","做完一次Delta对冲，不等于未来任何时刻都保持中性。"]),
"L06": (
"Gamma、Theta和路径风险", "理解为什么方向没变，期权的涨跌节奏却变了。",
[
("Gamma｜Delta变化得多快", "新的Delta ≈ 旧Delta + Gamma × 股价变化", "Gamma刻画股价移动时，Delta会如何跟着变。", "Delta=0.50、Gamma=0.04、股价涨2 → 新Delta约0.58", "这是局部近似；移动过大时要重新估算。"),
("Theta｜时间带来的价格变化", "期权价格变化 ≈ 每日Theta × 经过天数", "在其他条件不变时，时间过去会影响期权价格。", "每日Theta=−0.08美元/股，过3天 → 约−0.24美元/股", "Theta不是每天固定扣费；近到期及IV变化会影响结果。"),
("Gamma｜为什么大波动不能只看Delta", "二阶价格影响 ≈ 0.5 × Gamma × 股价变化²", "方向敞口以外，价格曲率还会影响期权估值。", "Gamma=0.04、股价涨2 → 二阶项约+0.08美元/股", "局部泰勒近似；与Delta项、Theta项一并理解。")
], "Gamma＝Delta对股价的变化速度；Theta＝时间敏感度；例中价格单位均为每股期权美元。",
["近到期的期权“便宜”，不代表亏损概率和损耗小。","将Gamma或Theta当成固定收益，忽略IV与离散跳空会误判风险。"]),
"L07": (
"Vega、IV、RV别混淆", "波动率变化能让股票方向看对的交易仍然亏钱。",
[
("Vega｜IV变化时价格怎么动", "期权价格变化 ≈ Vega × IV变化的百分点数", "先确认交易平台的Vega按1个波动率百分点计价。", "Vega=0.12美元/百分点，IV升3个百分点 → +0.36美元/股", "不同软件的Vega单位可能不同，先统一口径再计算。"),
("买方和卖方对IV变化方向相反", "短期权Vega = −对应长期权Vega（同一合约）", "其他条件相同，IV上升一般有利多头、不利空头。", "卖1张Vega为0.12的期权，IV升3点 → 约亏36美元", "此处仅估算IV影响；股价、时间和交易费未计入。"),
("IV与RV差多少", "波动率差 = IV − RV（单位：百分点）", "历史实现波动率与目前期权隐含波动率的差距。", "IV=40%、RV=25% → 相差15个百分点", "历史RV不是未来RV；高IV不自动证明卖方占优。")
], "IV＝隐含波动率；RV＝实现波动率；Vega＝对IV的价格敏感度；百分点与百分比变化不可混用。",
["“IV高于历史RV”不是可以无风险卖期权的套利。","Vega乘以3之前必须确认你的Vega报价单位。"]),
"L08": (
"Rho、股息、期限与偏斜", "把不同因素拆开，避免把波动率、利率、股息混算。",
[
("Rho｜利率变化时的局部影响", "期权价格变化 ≈ Rho × 利率变化的百分点数", "Rho反映利率改变对理论期权价格的敏感度。", "每1个百分点Rho=+0.05美元/股，利率升1点 → +5美元/张", "先确认软件Rho计价单位，且其他条件保持不变。"),
("预期股息｜影响远期与期权", "零利率简化：除息后理论股价 ≈ 除息前股价 − 股息", "现金股息使股票价值部分流向股东，改变远期关系。", "100美元股票、派息2美元 → 除息参考价约98美元", "只是机械除息参考，实际市场股价可能涨跌。"),
("偏斜｜同期限不同K的IV差", "IV偏斜差 = 某Put的IV − 同期限ATM的IV", "不同执行价可能对应不同风险定价。", "虚构例：Put IV=30%、ATM IV=25% → 高5个百分点", "跨期限比较还要检查期限总方差和事件日。")
], "Rho＝对利率敏感度；ATM＝平值；K＝行权价；IV＝隐含波动率。",
["Rho高低不能直接转换为确定获利金额。","股息和除息参考价不是无风险预测，提前行权规则仍重要。"]),
"L09": (
"期权链报价与主观期望值", "先看真实能成交的Bid/Ask，再用情景验证是否值得做。",
[
("Mid｜只是报价中点", "中间价Mid = (Bid + Ask) ÷ 2", "Mid有助于比较盘口，但不是一定能成交的价格。", "Bid=9.40、Ask=10.00 → Mid=9.70美元/股", "实际买入可能需付Ask，卖出只能拿Bid。"),
("买卖价差｜交易的起跑成本", "立即买入再卖出价差 ≈ (Ask − Bid) × 乘数", "即使标的未动，买卖价差也可能形成损失。", "价差0.60美元/股、乘数100 → 一张约60美元", "未计手续费；市场变化时盘口也会变化。"),
("真实情景期望值", "预期净盈亏 = Σ(情景概率 × 该情景净盈亏)", "把每种可能结果按主观概率加权，之后再看风险。", "30%赢500、70%亏300 → 0.30×500−0.70×300 = −60美元", "概率为教学假设；市场隐含Q不是你真实预测的P。")
], "Bid＝最高买价；Ask＝最低卖价；Mid＝中点；Σ＝逐项相加；P＝真实主观概率；Q＝风险中性概率。",
["赚钱概率高，不保证期望值为正，更不保证账户能够撑到到期。","把Mid当成交价往往高估可执行策略收益。"]),
"L10": (
"长期Call、Put与持股", "比较同一股票观点下谁付钱、谁承担时间风险。",
[
("买长期Call的到期保本价", "Call到期保本股价 = 行权价 + 已付权利金", "上涨必须先覆盖期权购买成本。", "K100、买入Call权利金8 → 保本股价108美元", "时间越长也不保证足够上涨；费用需另计。"),
("买Call的最大损失", "最大亏损 = 每股权利金 × 每张股数 × 张数", "买方最坏情况可以让合约到期归零。", "1张、权利金8、乘数100 → 最大亏损800美元", "不代表持有期间能够随时按合适价格退出。"),
("正股与Call在同一终价比较", "持股盈亏 = (到期股价 − 买入股价) × 股数", "要用同一时间、标的和总风险预算公平比较。", "股价100→120：100股赚2,000美元；K100的Call付8赚1,200美元", "两种工具初始占资不同，不能只比利润百分比。")
], "LEAPS＝长期到期期权；K＝行权价；权利金为每股报价，图中标准合约为100股。",
["Call看对方向仍可能因幅度不足或兑现太晚而亏损。","低资金占用不等于同等风险的高回报。"]),
"L11": (
"卖Put、备兑Call和裸卖风险", "把“收到权利金”和“最大可能损失”拆开计算。",
[
("现金担保卖Put｜最坏经济亏损", "最大亏损 = (Put行权价 − 每股收到权利金) × 乘数", "假设股票跌到0，卖Put仍可能需要按K接股。", "卖K95 Put，收3美元/股 → (95−3)×100 = 9,200美元", "仅为合约经济损失；保证金、融资与强平另算。"),
("备兑Call｜最多能赚多少", "最大盈利 = (Call行权价 − 持股成本 + 权利金) × 股数", "上涨超过K时，持股超出行权价的收益被放弃。", "股票买100、卖K110 Call收2.5 → (110−100+2.5)×100=1,250美元", "假设100股恰好备兑1张Call；未计费用或股息。"),
("裸卖Call｜暴涨带来无上限风险", "到期盈亏 = (收款 − max(到期股价−K, 0)) × 乘数", "卖Call只收有限权利金，但理论上可能无限赔。", "K110、收2.5、到期150 → (2.5−40)×100 = −3,750美元", "美式提前指派可能令账户先产生空股。")
], "K＝行权价；乘数＝每张股票数；Cash-Secured＝准备接股现金；Covered＝有对应股票备兑。",
["3美元收入不是3美元安全利润，卖Put可面对9,500美元接股款。","备兑Call不是免费的上涨收益：上涨空间被卖掉了。"]),
"L12": (
"保护性Put与Collar", "看清保险费、下跌底线以及放弃的上涨空间。",
[
("Protective Put｜最坏下跌损失", "最大亏损 = (持股成本 − Put行权价 + Put权利金) × 股数", "买Put给持股设置到期卖出保底价格。", "股票买100、买K95 Put付3 → (100−95+3)×100 = 800美元", "对应相同股数与到期；费用、指派及中途风险另算。"),
("Collar｜每股净保险费", "净成本 = 买Put付出的权利金 − 卖Call收到的权利金", "用卖出部分上涨换取下跌保护的费用。", "Put付3、Call收2 → 保险净成本1美元/股", "零权利金不意味着无经济机会成本。"),
("Collar｜到期损益上下界", "最坏 = (Put K−持股成本−净成本)×股数；最好 = (Call K−持股成本−净成本)×股数", "Put决定最差卖出价，Call决定上行交割封顶价。", "持股100、Put K95、Call K110、净成本1 → 最差−600、最好+900美元", "假设匹配的100股、同到期，且不计额外费用。")
], "K＝行权价；持股成本＝股票买入价；Collar＝持股＋买Put＋卖Call。",
["买Put能限制到期股价下跌，但不能消除交易和现金流风险。","“零成本Collar”仍有上涨封顶的机会成本。"]),
"L13": (
"跨式、宽跨式交易波动", "两边都买，并不代表涨跌总有一边赚过权利金。",
[
("买入跨式Straddle｜双保本价", "上下保本价 = 共同K ± Call和Put权利金总和", "需要到期股价偏离K的幅度超过两张期权总成本。", "K100、Call付5、Put付4 → 保本价91和109美元", "适用于同执行价、同到期的到期经济函数。"),
("跨式到期盈利怎么计算", "净盈亏/股 = |到期股价 − K| − 总权利金", "股价远离行权价才覆盖两腿成本。", "到期120，K100，总成本9 → (20−9)×100 = 盈利1,100美元", "若到期正好K，最大亏损为900美元/张组合。"),
("宽跨式Strangle｜需要更大突破", "下保本价 = Put K − 总权利金；上保本价 = Call K + 总权利金", "不同K让初始成本可能较低，但门槛变宽。", "买P90付3、C110付3 → 总成本6，保本价84和116", "财报后IV崩落会影响到期前卖出价格。")
], "Straddle＝同K同时买Put和Call；Strangle＝不同K；|x|＝x的绝对值。",
["股价走得很大，也可能不够大，无法覆盖双腿权利金。","到期收益图不表示事件后IV下降时仍能盈利平仓。"]),
"L14": (
"四类垂直价差的三本账", "先认净支出还是净收入，再算翼宽与盈亏边界。",
[
("Bull Call｜看多借记价差", "最大盈利 = (高K−低K−净支出)×乘数；最大亏损=净支出×乘数", "买低K Call卖高K Call，盈利被高K封顶。", "K95/105、净付4 → 最大赚600、最多亏400、保本99美元", "在到期且两腿同股数的前提下成立。"),
("Bear Put｜看空借记价差", "最大盈利 = (高K−低K−净支出)×乘数；保本价=高K−净支出", "买高K Put卖低K Put，下跌收益有上限。", "买105/卖95 Put，净付4 → 最多赚600、保本101美元", "期中卖出价格还受IV/时间影响。"),
("Bull Put｜看多信用价差", "最大盈利 = 净收款×乘数；最大亏损=(翼宽−净收款)×乘数", "卖高K Put并买低K Put限制到期最大亏损。", "卖105/买95 Put，净收4 → 最多赚400、最多亏600、保本101美元", "美式两腿可能异步指派，期中现金风险另算。"),
("Bear Call｜看空信用价差", "最大盈利 = 净收款×乘数；保本价=低K+净收款", "卖低K Call买高K Call，限制裸Call上行尾部。", "卖95/买105 Call，净收4 → 最多赚400、最多亏600、保本99美元", "需要核对成交组合净价及实际合约乘数。")
], "K＝行权价；翼宽＝两个行权价的差；借记＝净付；信用＝净收；示例乘数100。",
["信用价差的到账权利金不是无风险利润。","组合到期最大损失不等于持仓途中一定不会被强平。"]),
"L15": (
"Calendar与Diagonal跨期组合", "不同到期日不能直接套“一条固定终价收益线”。",
[
("Calendar｜两期限同一K", "初始净支出 = 买远期期权费 − 卖近期期权费", "远期腿通常更贵；近月短腿先到期。", "买远期费6、卖近期收3 → 净付(6−3)×100 = 300美元", "不包含手续费；远期合约不会和近期同步到期。"),
("近期到期时｜重新算剩余价值", "组合暂估盈亏 = 远期可卖价 − 近期平仓/到期负债 − 初始净支出", "关键是近月到期时，远月期权还能卖多少。", "远期可卖4、近月归零、初始净付3 → (4−0−3)×100 = +100美元", "远期4是虚构的可成交Bid，不是自动保证的结果。"),
("Diagonal｜执行价与期限都不同", "结构检查 = 到期日不同 + 行权价不同 + 两腿买卖方向", "它的盈亏随股价、时间和IV一起变动。", "例：买远月K100 Call，同时卖近月K105 Call", "美式短Call可能提前指派；不能用普通垂直价差最大亏损套用。")
], "Calendar＝同K不同到期；Diagonal＝K与到期日均不同；远期Bid＝实际可卖报价。",
["两个期限的到期收益不能机械相减得到固定最大盈亏。","收到近期权利金后仍有远期估值与短腿指派风险。"]),
"L16": (
"铁鹰如何算有限到期风险", "盈利最多是净收权利金；亏损主要取决于单侧翼宽。",
[
("卖出铁鹰｜四腿结构", "买低K Put、卖较高K Put；卖较低K Call、买高K Call", "用两边买入的保护腿限制极端到期亏损。", "例：P90/P95和C105/C110，共收2.20美元/股", "示例为标准、两侧等宽的短铁鹰组合。"),
("最大盈利和最大亏损", "最大赚 = 净收×乘数；最大亏 = (单侧翼宽−净收)×乘数", "到期落在中间时留住净收；突破外侧保护K时达到最大亏损。", "净收2.20、翼宽5 → 最多赚220、最多亏280美元", "限同标的、同到期、保护腿完整且两侧翼宽相同。"),
("两个保本边界", "下保本 = 卖Put的K−净收；上保本 = 卖Call的K+净收", "介于两保本点之间的到期经济净盈亏非负。", "短Put K95、短Call K105、收2.20 → 92.80至107.20", "不是胜率预测，且实物交割和提前指派有额外风险。")
], "短Put＝卖出的Put；短Call＝卖出的Call；翼宽＝同侧保护K与卖方K的差。",
["最坏到期亏损有限，不代表不会临时产生巨大交割义务。","短铁鹰的高盈利频率不直接说明长期期望收益为正。"]),
"L17": (
"Roll不是抹去亏损", "展期就是一笔旧仓平仓，外加一笔新仓开仓。",
[
("旧仓必须先结账", "旧仓已实现盈亏 = 最初收款 − 回补付款", "回补价格比最初收到的更贵，旧交易仍然亏了。", "旧卖Put收3，后来花7买回 → (3−7)×100 = −400美元", "忽略手续费；亏损不会因新卖一张Put而消失。"),
("展期时总累计现金流", "到目前累计现金流 = 旧仓收款 − 旧仓回补款 + 新仓收款", "新收到的Credit属于新的风险合约，不能算旧仓已扭亏。", "旧收300、回补700、新收500 → 累计现金流+100美元", "新仓仍未平，+100不等于已经实现+100利润。"),
("最终整体结果看新仓的结局", "全部交易净盈亏 = 累计现金流 − 新仓最终履约/平仓成本", "直到新仓关闭，展期的真正经济结果才完整。", "若新仓后来需900美元平仓 → 累计100−900=−800美元", "有提前指派、滑点、时间和保证金等风险。")
], "Roll＝平旧仓＋开新仓；Credit＝净收款；Debit＝净付款；P/L＝已实现加未实现经济盈亏。",
["新仓收了比旧亏损更多的钱，也不能把所有收款叫盈利。","连续展期不是债务消失术：要重新评估股票价值和资金约束。"]),
"L18": (
"账户生存需要三本账", "经济最大损失、占用保证金、交割现金不是同一个数。",
[
("策略最大经济亏损", "例如借记价差：最大到期亏损 = 已付净权利金×乘数", "结构限制到期损失，但仍可能出现期中保证金和结算问题。", "一张借记价差净付4美元/股 → 到期最大亏损400美元", "仅限完整持有、匹配到期的借记价差示例。"),
("现金担保Put要预留多少现金", "接股现金需求 = Put行权价 × 交割股数", "有能力接股跟券商最低保证金不是一回事。", "卖一张K95普通Put，100股交割 → 需准备9,500美元", "实际保证金与交割方式因券商和合约而异。"),
("回撤｜账户从峰值跌了多少", "最大回撤比例 = (过去峰值净值 − 当前净值) ÷ 过去峰值净值", "只看某笔策略收益，容易忽略账户生存风险。", "账户高点10,000，降到7,000 → 回撤30%", "真实最大回撤要沿整条资金曲线找最严重的峰谷。")
], "保证金＝券商要求的抵押/风控金额；接股款＝实际股票交割现金；净值＝账户市值。",
["券商只占用2,500保证金，不代表最多只亏2,500。","到期理论有限亏损，也不保证途中不会强平。"]),
"L19": (
"股息、拆股与提前指派", "公司行动改变实际现金与股票义务，不只是改变IV。",
[
("提前行权｜注意剩余外在价值", "Call外在价值 ≈ 市场Call价格 − 立即行权内在价值", "除息前，短Call的提前指派风险常与股息和剩余外在价值有关。", "Call报价12.30、内在价值12 → 剩余外在价值0.30美元", "若股息1美元大于0.30，可能更值得研究提前行权；非充分条件。"),
("普通2拆1｜总经济权利守恒", "拆股前总行权款 = 拆股后调整合约总行权款", "股票股数翻倍，行权价等参数通常对应调整。", "旧1张K100×100股=10,000；示意新2张K50×100股=10,000", "仅为常见2拆1的示意，实际合约调整必须查OCC公告。"),
("Put被指派｜真的要掏现金", "应付接股现金 = K × 合约约定交割股数 × 被指派张数", "股票突然进入账户，是卖方履约带来的结果。", "卖1张K90普通Put被指派 → 支付9,000美元并取得100股", "非标准合约可能对应不同交割物，不能直接套100股。")
], "外在价值＝市场期权价减内在价值；OCC＝期权清算公司；K＝行权价。",
["股息高于Call外在价值只是风险提示，还要看融资、行权与经纪商条件。","拆股后不能只改行权价而忽略合约份数与交割物。"]),
"L20": (
"到底买哪一张期权", "期限、行权价和可执行买入价要合起来看。",
[
("买Call真正的到期保本门槛", "保本股价 = K + 买入Ask + 每股分摊交易费", "用可执行的买入成本，而不是理想的Mid估计保本。", "K100、Ask6、每张手续费1美元 → 保本价106.01美元", "同一合约100股；其他退出滑点仍未计入。"),
("买Call到期盈亏", "到期盈亏 = [max(到期价−K,0)−Ask]×乘数 − 费用", "比较合约要看同一终价、同一时间的净收益。", "K100、Ask6、到期110、不计费用 → 盈利400美元", "不是中途期权市场可卖价格。"),
("不同K可以得出不同结果", "到期每股净盈亏 = max(终价−K,0) − 买入权利金", "便宜的高K并不等于更划算，要核对盈亏门槛。", "终价110：K95付9赚6/股；K105付3赚2/股", "仍要比较资金占用、风险、真实Bid/Ask与到期时点。")
], "Ask＝卖方最低报价（买方成本参考）；K＝行权价；Mid＝买卖盘中点；乘数＝每张股数。",
["“股价要涨”不是有效的合约选型规则，还必须问何时涨多大。","以Mid测算长期策略常会高估实际可买到的表现。"]),
"L21": (
"VIX、VX期货与指数期权", "看对VIX现货方向，并不等于买的衍生品一定盈利。",
[
("VX期货盈亏", "期货盈亏 = (平仓期货价 − 开仓期货价) × 合约乘数 × 张数", "VX期货跟踪自身的期货价格，不是直接买卖现货VIX。", "买1张VX期货，21.2开仓、20.3平仓、乘数1000 → 亏900美元", "这是标准VX期货示例；保证金和每日结算另计。"),
("VIX指数Call现金结算", "净盈亏 = [max(结算值VRO−K,0)−买入权利金]×100", "VIX指数期权依其合约最终结算值现金交割。", "VRO=25、K20、买Call费3 → (5−3)×100 = +200美元", "VRO不是收盘时随便看到的即时报价；要核对具体合约。"),
("期限结构｜不能只盯现货", "期货基差 = VX期货价格 − VIX现货指数", "正基差不保证未来正收益，期货价会随预期变化。", "VIX现货18、近月VX期货21 → 基差+3指数点", "不同到期、现金/期货交割的规则不同，不能混买。")
], "VX＝VIX相关期货；VIX＝波动率指数；VRO＝特定指数期权最终结算值；K＝行权价。",
["VIX现货上升，不意味着某张VX期货或VIX期权就一定上涨。","VIX指数期权不是一般美国股票期权的实物交割。"]),
"L22": (
"高胜率与复利为什么会骗人", "胜率、赔率、成本、尾部与仓位规模必须一起算。",
[
("期望盈亏｜别只盯胜率", "单笔期望 = 胜率×平均盈利 − 亏损率×平均亏损", "小赚很多次，也可能被少数大亏抹掉。", "95%赚1、5%亏30 → 0.95×1−0.05×30 = −0.55单位", "必须统计同一口径的净收益、费用和尾部事件。"),
("复利｜先看乘法再看平均", "最终资金 = 起始资金 × 每期(1+当期收益率)连乘", "先涨10%再跌10%，账户并不会回到原点。", "10,000先涨10%到11,000、再跌10% → 9,900", "路径和仓位调整会显著改变复利结果。"),
("Kelly｜理论上限不是实盘指令", "理论Kelly比例 = [胜率×赔率−亏损率]÷赔率", "赔率指每亏1元平均赚多少，不是盈亏百分数之差。", "胜率55%、盈亏赔率1.5 → (0.55×1.5−0.45)÷1.5=25%", "依赖极精确的概率与独立同分布假设，估计误差很危险。")
], "胜率与亏损率合为100%；赔率＝平均盈利÷平均亏损；Kelly＝理想化资金下注比例。",
["95%胜率仍可能亏钱，尤其当少数尾部亏损足够大。","理论Kelly计算值不等于安全或适合个人的持仓比例。"]),
"L23": (
"同一股票，六种表达别乱比较", "用同一终价把收益算清，再比较最大亏损和资金占用。",
[
("正股｜承担全部下行", "持股盈亏 = (终价−买入股价)×股数", "股价每涨1美元、100股大致多赚100美元。", "股价100买100股，终价110 → 盈利1,000美元", "股票跌到零仍可亏10,000美元。"),
("Cash-Secured Put｜先问接股价格", "卖Put到期盈亏 = [收到权利金−max(K−终价,0)]×乘数", "收钱同时承诺按K买股。", "卖K95 Put收3、终价110 → 盈利300美元", "最大经济亏损9,200美元；收款不是确定收益。"),
("Long Call与Bull Call价差", "Call净赚 = max(终价−K,0)−权利金；价差另减去高K短腿到期支付", "价差降低成本，同时牺牲超过高K的潜在收益。", "终价110：K100 Call付8 → +200；K100/115价差净付5 → +500美元", "均为100股同到期示例；不表示相同风险或相同占资。"),
("保护性Put与不交易", "保护性Put = 股票盈亏 + Put到期价值 − 保险费；不交易盈亏=0", "保险限制下行，不交易则保留现金和未来选择权。", "持股买100、K95 Put付4、终价110 → (10−4)×100=+600美元", "六种表达应按相同终价、风险预算和资金占用另做比较。")
], "K＝行权价；终价＝同一观察日股票价；保护性Put＝持股加买Put；不交易＝本次不产生期权损益。",
["把100股正股与一张便宜Call按表面ROI直接比高低没有意义。","最优选择可能是不交易，而不是硬选一张看似划算的期权。"])
}

ROOT = Path(__file__).resolve().parents[1]
COURSES = ROOT / "课程"
WIDTH = 1240
MARGIN = 62
CARD_X = MARGIN
CARD_W = WIDTH - MARGIN * 2
INNER_X = CARD_X + 30
INNER_W = CARD_W - 60
FONT = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"


def glyph_width(char: str, font_size: int) -> float:
    """Conservative CJK-aware estimate, enough to keep all text inside cards."""
    if unicodedata.east_asian_width(char) in ("W", "F"):
        return font_size * 1.11
    if char in "MW@%":
        return font_size * 0.81
    if char in "ijlI. ,:'|":
        return font_size * 0.38
    return font_size * 0.67


def wrap(text: str, font_size: int, max_width: int) -> list[str]:
    """SVG doesn't wrap <text>; explicitly compute lines before sizing blocks."""
    output: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            output.append("")
            continue
        start = 0
        while start < len(paragraph):
            width = 0.0
            stop = start
            while stop < len(paragraph):
                advance = glyph_width(paragraph[stop], font_size)
                if stop > start and width + advance > max_width:
                    break
                width += advance
                stop += 1
            # Preserve word boundaries if sensible, but never truncate content.
            if stop < len(paragraph) and stop - start > 6:
                segment = paragraph[start:stop]
                space = segment.rfind(" ")
                if space > (stop - start) * 0.6:
                    stop = start + space + 1
            output.append(paragraph[start:stop].strip())
            start = stop
    return output


def rect(x, y, w, h, fill, stroke="none", radius=18, sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def text(x, y, value, size=22, fill="#263548", weight=400, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" {extra}>{escape(value)}</text>')


def multiline(out, x, baseline, lines, size, fill, weight=400, step=None):
    step = step or int(size * 1.42)
    for i, line in enumerate(lines):
        out.append(text(x, baseline + i * step, line, size, fill, weight))
    return baseline + len(lines) * step


def create_svg(code: str, data: tuple) -> tuple[str, int]:
    short_title, purpose, cards, variables, mistakes = data
    assert 3 <= len(cards) <= 6, (code, "card count")
    assert 2 <= len(mistakes) <= 4, (code, "mistakes count")
    out = []
    y = 58
    out.append(rect(0, 0, WIDTH, 20000, "#f6f8fc", radius=0))
    out.append(rect(62, 41, 191, 42, "#dbeafe", radius=19))
    out.append(text(85, 70, f"{code} / 公式速读", 20, "#1d4ed8", 700))
    y = 126
    title_lines = wrap(short_title, 38, WIDTH - 2 * MARGIN)
    y = multiline(out, MARGIN + 3, y, title_lines, 38, "#102a43", 700, 50)
    purpose_lines = wrap(purpose, 24, WIDTH - 2 * MARGIN)
    y = multiline(out, MARGIN + 3, y + 3, purpose_lines, 24, "#48576a", step=35) + 15
    out.append(rect(MARGIN, y, CARD_W, 3, "#2563eb", radius=1))
    y += 31
    for i, card in enumerate(cards, 1):
        name, formula, why, example, limit = card
        label_lines = wrap(f"{i:02d}  {name}", 26, INNER_W)
        formula_lines = wrap(formula, 28, INNER_W - 50)
        why_lines = wrap("人话解释： " + why, 22, INNER_W - 12)
        example_lines = wrap("数字代入： " + example, 22, INNER_W - 44)
        limit_lines = wrap("使用边界： " + limit, 20, INNER_W - 12)
        title_h = max(1, len(label_lines)) * 39
        formula_h = max(1, len(formula_lines)) * 39 + 31
        why_h = len(why_lines) * 32
        example_h = len(example_lines) * 33 + 27
        limit_h = len(limit_lines) * 30
        card_h = 38 + title_h + 13 + formula_h + 25 + why_h + 21 + example_h + 20 + limit_h + 30
        out.append(rect(CARD_X, y, CARD_W, card_h, "white", "#d9e1ed", radius=22, sw=2))
        out.append(rect(CARD_X, y + 16, 5, card_h - 32, "#3b82f6", radius=2))
        cy = y + 45
        cy = multiline(out, INNER_X, cy, label_lines, 26, "#162d48", 700, 39) + 7
        out.append(rect(INNER_X - 9, cy - 7, INNER_W + 8, formula_h, "#eff6ff", radius=13))
        cy = multiline(out, INNER_X + 15, cy + 33, formula_lines, 28, "#1445a0", 700, 39) + 11
        cy = multiline(out, INNER_X + 1, cy + 19, why_lines, 22, "#31445b", 400, 32) + 17
        out.append(rect(INNER_X - 9, cy - 7, INNER_W + 8, example_h, "#eaf8f0", radius=13))
        cy = multiline(out, INNER_X + 15, cy + 29, example_lines, 22, "#146c44", 600, 33) + 8
        cy = multiline(out, INNER_X + 1, cy + 21, limit_lines, 20, "#58677a", 400, 30)
        # Measured content must fit the card with a nonzero bottom margin.
        assert cy <= y + card_h + 8, (code, i, "layout overflow", cy, y + card_h)
        y += card_h + 20
    # Separate legend and mistakes so readers don't have to infer mathematical letters.
    y += 3
    legend_lines = wrap(variables, 23, INNER_W - 12)
    legend_h = 83 + len(legend_lines) * 35
    out.append(rect(CARD_X, y, CARD_W, legend_h, "#e9f0fb", radius=19))
    out.append(text(INNER_X, y + 46, "符号和单位｜不要猜缩写", 26, "#173968", 700))
    multiline(out, INNER_X, y + 88, legend_lines, 23, "#344b68", step=35)
    y += legend_h + 24
    warning_rows = []
    for mistake in mistakes:
        warning_rows.append(wrap("• " + mistake, 22, INNER_W - 12))
    warning_h = 84 + sum(len(x) * 34 + 7 for x in warning_rows)
    out.append(rect(CARD_X, y, CARD_W, warning_h, "#fff7e8", radius=19))
    out.append(text(INNER_X, y + 46, "两条最容易踩的坑", 26, "#905320", 700))
    wy = y + 89
    for lines in warning_rows:
        wy = multiline(out, INNER_X, wy, lines, 22, "#704b25", step=34) + 7
    y += warning_h + 33
    out.append(text(MARGIN + 3, y, "独立教学示例｜忽略费用等简化假设已标明｜以讲义合约条件和官方规则为准", 18, "#677489"))
    height = y + 42
    # Replace generous working background height with the exact computed image size.
    out[0] = rect(0, 0, WIDTH, height, "#f6f8fc", radius=0)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
           f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{code}期权公式速读图">\n'
           + "\n".join(out) + "\n</svg>\n")
    ET.fromstring(svg)  # render-safe XML before writing
    return svg, height


def insert_in_lecture(lecture: Path, code: str):
    original = lecture.read_text(encoding="utf-8")
    link = f"![{code}核心公式与计算速读图](公式速读图.svg)"
    if link in original:
        return False
    # Insert between 5-minute preface and first main chapter (not before quick summary).
    headings = list(re.finditer(r"(?m)^## [^\r\n]+", original))
    if len(headings) < 2:
        raise ValueError(f"{code}: cannot find first main chapter")
    heading = "## 本课公式速读图｜先看人话，再看推导\n\n"
    caution = ("> 下图给出本课核心公式与计算判断的**独立教学示例**。"
               "请先看名称、代入和使用边界，再读正文完整推导；原有收益图仍保留。\n\n")
    extra = heading + link + "\n\n" + caution + "---\n\n"
    pos = headings[1].start()
    lecture.write_text(original[:pos] + extra + original[pos:], encoding="utf-8", newline="\n")
    return True


def update_course_index(index: Path, code: str):
    original = index.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if re.match(r"^- \*\*" + re.escape(code) + r" ", line):
            assert "公式速读图.svg" not in line, (code, "already indexed")
            folder = re.search(r"\]\((L\d\d-[^)]*)/讲义\.md\)", line)
            assert folder, (code, "index path missing")
            suffix = f" · [公式速读图]({folder.group(1)}/公式速读图.svg)"
            lines[i] = line.rstrip("\n") + suffix + "\n"
            found = True
            break
    assert found, (code, "not in index")
    index.write_text("".join(lines), encoding="utf-8", newline="\n")


def main():
    lessons = sorted(p for p in COURSES.iterdir() if p.is_dir() and re.match(r"^L\d\d-", p.name))
    assert len(lessons) == len(DATA) == 23, ("lesson count", len(lessons), len(DATA))
    index = COURSES / "目录.md"
    existing = [(d / "公式速读图.svg").exists() for d in lessons]
    assert len(set(existing)) == 1, "partial generation detected; inspect missing files"
    if existing[0]:
        assert all("公式速读图.svg" in (d / "讲义.md").read_text("utf-8") for d in lessons)
        assert "公式速读图.svg" in index.read_text("utf-8")
    for lesson in lessons:
        code = lesson.name[:3]
        svg, height = create_svg(code, DATA[code])
        (lesson / "公式速读图.svg").write_text(svg, encoding="utf-8", newline="\n")
        if not existing[0]:
            assert insert_in_lecture(lesson / "讲义.md", code)
            update_course_index(index, code)
        print(f"RENDERED {code}: {len(DATA[code][2])} cards; SVG {WIDTH}x{height}")
    print(f"DONE: {len(lessons)} SVG images; {sum(len(d[2]) for d in DATA.values())} cards; embedded in all lessons")


if __name__ == "__main__":
    main()
