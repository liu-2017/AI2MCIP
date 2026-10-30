#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pangu2wrf **v7** 单文件版：盘古气象场 -> MCIP 可读的伪 wrfout。

===============================================================================
v7 相对 v6 的修改：针对「10/25 污染峰值日 与 10/26 大风清除日 的正午净短波
几乎相同（540~579 vs 536~574 W/m2，差 1~2%），模式在辐射上完全看不见这次
污染过程」所做的气溶胶-辐射与边界层修复。

诊断证据（MIDDLE_DATA/ERA5_2025-10-17_V6/mcip，BTH 6 城正午 UTC04）：

  城市      GSW 10-25   GSW 10-26   云量10-25  云量10-26
  保定        566         562        0.10       0.00
  北京        540         536        0.00       0.00
  石家庄      579         574        0.34       0.00
  唐山        570         566        0.03       0.00
  天津        577         572        0.13       0.00
  雄安        566         562        0.09       0.00

10/25 观测 PM2.5 = 79（窗内峰值，且仍在 +15/d 累积），10/26 = 42（大风清除）。
两者正午 GSW 几乎相等 —— 短波对霾完全没有响应。机制链：

  霾日无气溶胶-辐射反馈 + 云量偏少 1/3
    -> GSW 给碧空值
    -> HFX 偏高（正午 163~204 W/m2）
    -> encroachment h_conv=sqrt(2H/gamma) 主导 PBLH（v6 自标定 corr(dPBL,dHFX)=+0.842）
    -> PBLH 加深 -> 通风指数(风xPBLH) 翻倍（238 -> 603）
    -> CMAQ 的 PM2.5 累积被截断，而观测仍在 +15/d

v6 已修 F1~F5（短波云衰减病态放大 / 晴空透射率 / Jarvis 蒸发效率 /
假毛毛雨 / 夜间 PBLH 钉死），**本版不再改动 F1~F5**，只补三项：

-------------------------------------------------------------------------------
【F7-1】气溶胶-辐射：低层湿度驱动的霾湿增长衰减（本次主修复）

  现状：shortwave_down 只有云衰减 ``atten=(1-cld)+cld*exp(-tau_eff)``，
        完全没有气溶胶项。而 pangu2wrf 的输入只有气象场（msl/u10/v10/t2m
        与高空 z/q/t/u/v），**没有气溶胶/PM 场**，无法做一阶气溶胶辐射。
  做法：用**边界层相对湿度**作霾湿增长代理（RH 越高 -> 吸湿增长 -> 消光越强；
        同时高 RH 与静稳/污染累积高度相关，故可作霾负荷的粗代理）。
        tau_aer = aer_tau_max * clip((rh_bl-aer_rh_thresh)
                                     /(aer_rh_max-aer_rh_thresh),0,1)^aer_power
        该气溶胶层在边界层内混合均匀，对**整片天空**衰减（不像云只衰减其
        覆盖份额），故与云衰减相乘而非相加：
            SWDOWN = clear * atten_cloud * exp(-tau_aer*slant)
  效果：高湿污染日正午 GSW 明显下调，晴好日（RH<aer_rh_thresh）完全不受影响，
        故不破坏 v6 已对齐的晴空短波标定。
  标定：默认值针对 10/25~26 的对比量级取。请用 --param 重标：
        --param aer_tau_max=0.30   减弱
        --param aer_tau_max=0.60   增强
        --param aer_rh_thresh=0.55 提早起作用

-------------------------------------------------------------------------------
【F7-2】云量偏少：qc_rh_crit_base 0.85 -> 0.82

  v6 头部明确列出未修项「CLDTOT 0.675（云量仍偏少 1/3），会抬高 SWDOWN、
  削减 GLW，并影响 CMAQ 光解」，并建议用 --param qc_rh_crit_base=0.82
  评估。本版直接采用该建议作为默认值，使云量起报更早。
  注意：此项与 F1/F2 的短波标定耦合，若 SWDOWN 偏低可用
        --param sw_clear_transmissivity=0.86 补偿。

-------------------------------------------------------------------------------
【F7-3】边界层：pbl_wind_floor 2.0 -> 1.0

  v6 的 pbl_wind_floor=2.0 在静风点位把 Rib 支系统性抬高（Rib ∝ 1/speed^2）。
  用 MCIP 廓线实测（10/22 正午）：

    城市   风速    Rib(下限2.0)  Rib(无下限)   抬升倍数
    唐山   0.35       171           38          4.48
    承德   0.23       105           30          3.49
    天津   0.81       101           63          1.60

  下限降到 1.0 后，静风点位的 Rib 支回落到物理量级（正午由对流支主导，
  不受影响；夜间 Rib 支由 ~171 m 回到 ~50 m 量级，更贴近辐射逆温实况）。
  v1 的「PBLH 贴 pbl_min」问题已由 v2 的地表参考 + 对流支封顶共同解决，
  不再依赖高风速下限兜底。若仍见夜间过浅，用 --param pbl_wind_floor=1.5。

-------------------------------------------------------------------------------
【已知未修 · 方法论】标定基准不应是 WRF

  v6 的 PBLH/HFX 标定目标是真实 WRF 降尺度（PBLH V/WRF = 1.129/1.027/1.013），
  但 WRF 自身在 10/23~25 同样截断 PM 累积（观测 +15/d 仍在累积，两模式却
  停涨回落）—— 即 WRF 的边界层在该时段亦偏深。以 WRF 为基准等于把 WRF 的
  误差一并继承，调出来是「与 WRF 一致」而非「与真实边界层一致」。
  本版未改动 gamma 等已标定系数，但建议后续改用**探空/风廓线 PBLH 观测**
  （BTH 有站网）重标 pbl_inv_strength 与 HFX 相关系数。
  短期可用 --param pbl_inv_strength=1.1e-2 试更浅的混合层（v6 已备此开关）。

===============================================================================
v6 相对 v5 的修改：针对「V5(Pangu) 与 ERA5_WRF 动力降尺度 在 10/24-10/26
边界层差异最大」的诊断结论所做的定点物理修复。
===============================================================================

标定结果（域平均比值 V/WRF，1.000 为最佳；三天 10/24、10/25、10/26）：

  变量      V5                        v6
  SWDOWN  0.815 / 0.771 / 0.778  -> 0.896 / 0.855 / 0.855
  HFX     0.595 / 0.423 / 0.313  -> 1.155 / 0.960 / 0.816
  LH      1.443 / 1.396 / 1.273  -> 1.157 / 1.026 / 0.912
  PBLH    1.026 / 0.909 / 0.881  -> 1.129 / 1.027 / 1.013
  RAINNC  3.97  / 4.36  / 4.38   -> 1.26  / 1.23  / 0.91    (日累计)
  TSK     0.999 / 0.997 / 0.995  -> 0.999 / 0.997 / 0.996

用户原报告的现象「10/25-10/26 WRF 午后 PBLH 突破 1000 m 而 V5 卡在 950 m」：

  10/25 h07 UTC   V5  952 m   v6  989 m   WRF 1068 m
  10/26 h07 UTC   V5 1015 m   v6 1095 m   WRF 1138 m
  10/25 h09 UTC   V5  452 m   v6  731 m   WRF  731 m

夜间(h12-h22) PBLH 时间演变的标准差——v5 被"钉死"，v6 恢复演变：

  10/24  V5 7.04 m   v6 10.85 m   WRF 27.10 m
  10/25  V5 3.05 m   v6 11.23 m   WRF 30.25 m
  10/26  V5 7.93 m   v6 12.00 m   WRF 22.20 m

-------------------------------------------------------------------------------
泛化检验（避免只拟合 24-26 三天）
-------------------------------------------------------------------------------

只用 3 天选参数存在过拟合风险，因此另外取**未参与标定**的 10/19-10/21
三天做样本外检验。用 |ln(V/WRF)| 作为误差，两窗口平均得到"联合误差"：

                 PBLH     HFX      LH    SWDOWN    合计
    V5          0.078   1.042   0.186    0.296   1.601
    v6          0.044   0.267   0.186    0.201   0.698

即相对 v5 总误差下降 56%；HFX 改善 74%、PBLH 改善 44%、SWDOWN 改善 32%。

关于 LH：联合误差与 v5 持平（都是 0.186），因为 v5 的 LH 只是**在样本外
恰好准**（比值 0.94），它在标定日偏高 1.44 倍。v6 把全局无偏性做出来了，
代价是单日可能出现 ±20~35% 偏差。考虑到 HFX 的改善幅度大得多（1.042→0.267），
且 HFX 才是 PBLH 的驱动项（corr=+0.842），此权衡是值得的。

关于 pbl_inv_strength（γ）的两个候选，存在明确取舍：

  γ=6.5e-3（默认）  联合误差 0.698；10/25 日均 +2.7%、午后峰值 -9.2%
  γ=1.1e-2          联合误差 0.679；10/25 日均 -2.7%、午后峰值 -17.7%

  两者相差仅 3%。但用户报告的原现象是「午后 PBLH 突破 1000 m 而 V5 卡在
  950 m」——按午后峰值衡量，γ=1.1e-2 反而比 V5 更差（10/25 为 896 m vs
  V5 952 m、WRF 1089 m）。取 γ=6.5e-3 是唯一在**日均和峰值两项都优于 V5**
  的选择。若你更看重日均統計/夜间层结，可用
  --param pbl_inv_strength=1.1e-2 切换。

诊断方法：把同一时段的 V5 伪 wrfout 与 MIDDLE_DATA/ERA5_WRF_2025-10-17 的
真实 WRF wrfout 逐日、逐小时做域平均对照，得到 V5/WRF 比值（2025-10-24）：

    QCLOUD 0.437   TAU 0.738   CLDTOT 0.675   SWDOWN 0.815
    HFX    0.595   LH  1.443   TSK 0.999      UST 0.894   PBLH 1.026
    RAINNC 日累计 1.822 mm vs WRF 0.531 mm（3.4 倍）

由此定位四处**结构性**（而非标量偏差）缺陷，v6 逐一修复：

-------------------------------------------------------------------------------
【F1】短波云衰减：去掉 τ_col/cld 的病态放大（云-辐射自洽）

  现象：V5 的云量、云水、光学厚度全面**少于** WRF（CLDTOT 0.675、QCLOUD
        0.437、TAU 0.738），SWDOWN 却**低于** WRF（0.815）——两者方向相反。
  根因：v3 引入的 tau_in = tau_col/cld 把「网格平均」光学厚度放大成「云内」
        光学厚度，放大倍数为 1/cld。cld=0.1 时放大 10 倍、cld=0.03 时放大
        33 倍；而 CMAQ 的 ext=3LWC/(2·rho_w·re) 用的本就是**网格平均** LWC，
        tau_col 无需、也不应再被云量除。该除法使每个有云格点都被过度压暗。
  修复：tau_eff = tau_col/max(cosz, slant_floor)，保留 (1-cld)+cld·exp(-tau_eff)
        的云量加权形式——破碎云中无云的那部分天空依然按晴空透过。

-------------------------------------------------------------------------------
【F2】晴空透射率上调并改为斜程-光子程可标定形式

  v5 的 sw_clear_transmissivity=0.78 偏保守。敏感性试验（10/24，24 时次）：
    T=0.78 -> SWDOWN 域均 134.0（WRF 164.3，比值 0.815）
    T=0.82 -> SWDOWN 域均 140.9（比值 0.857）
  即透射率每 +0.01 只能抬升 SWDOWN 约 1.3%，单靠它无法补齐 22.7% 的缺口，
  必须与 F1 配合。v6 取 0.84，与 F1 合起来把 SWDOWN 拉到与 WRF 可比。

-------------------------------------------------------------------------------
【F3】蒸发效率：Jarvis 型冠层阻抗取代「裸土湿度线性折减」（Bowen 比失衡）

  现象：LH 是 WRF 的 1.443 倍、HFX 只有 0.595 倍；10/25-10/26 HFX 仅为
        WRF 的 1/3。这是 ΔPBL 的最强相关项（corr(dPBL, dHFX)=+0.842）。
  根因：Surface 蒸发效率取 beta = clip(SMOIS[0]/soil_moisture_ref, 0.1, 1)。
        模板表层土壤湿度时间平均为 0.3187、参考值 0.50 -> beta 恒为 0.637，
        既不随光照/水汽亏缺/植被物候变化，也没有冠层气孔阻抗。10 月底华北
        植被凋零、LAI 低，实际蒸腾应显著低于「湿土上限」。
        又因 close_surface_energy 按比例同时缩放 H 与 LH（保持 Bowen 比），
        偏大的 LH 会把 HFX 一并压下去——所以 HFX 偏低是 LH 偏高的连带后果。
  验证：--param soil_moisture_ref=1.0（beta 0.637->0.319）后 10/24 域均
        HFX 16.12->32.53（WRF 27.1）、LH 56.03->35.84（WRF 38.83）、
        PBLH 455.3->509.1，证实 beta 是唯一主因。
  修复：beta = r_a/(r_a+r_s)，其中 r_a=1/(C_H·U) 为空气动力学阻抗，
        r_s 为 Jarvis (1976) 型冠层阻抗 = rs_min/LAI_eff · f(PAR)·f(VPD)·f(theta)
        ——夜间/弱光/干旱/空气干燥时气孔关闭(r_s 增大)、beta 减小，能量更多
        以感热形式释放；湿润密植被正午则趋近潜在蒸发。比"裁剪 Charles 常数"
        多出真实的日夜变化，且与 WRF/Noah 的阻抗网络同构。

-------------------------------------------------------------------------------
【F4】降水：抑制全天候虚假毛毛雨

  现象：RAINNC 日累计 1.822 mm（WRF 0.531 mm），且逐小时增量几乎恒定在
        0.04~0.09 mm/h——呈现「全域均匀毛毛雨」形态，而非真实降水过程。
  根因：precipitation_rate 对任何 MFC>0 的格点都按常数 precip_efficiency
        直接出水，缺少湿度/云水判据；水汽通量辐合的数值噪声于是全域产水。
        这既高估 CMAQ 的湿清除，又白白消耗柱水汽。
  修复：① 用柱相对湿度（水汽加权）做 gate，低于 precip_rh_gate 不产水；
        ② 低于 precip_drizzle_cut 的毛毛雨直接置零。两项都做成 Params 系数，
        便于用 --param 重新标定到不同季节/区域。

-------------------------------------------------------------------------------
【F5】夜间边界层：给地表逆温强度加上时间演变

  现象：V5 夜间 PBLH 被"钉死"在常数（10/24 224~240 m、10/25 234~242 m，
        逐小时几乎不变），而 WRF 夜间随辐射冷却与风速由 450 m 缓慢演变到
        250~330 m。夜间缺少演变 → CMAQ 夜间累积层厚度失真。
  根因：pbl_night_dtheta 是**常数**（1.0 K），不随日落后的冷却过程加深；
        Rib 参考位温亏损因此恒定，在廓线变化缓慢的夜间给出同一个 h。
  修复：把该亏损改为向 pbl_night_dtheta_max 松弛的一阶过程（夜间松弛时间
        pbl_night_relax_hours，白天用更短的 pbl_night_recover_hours 回到 0），
        并按 10 m 风速做机械混合削弱。日落时 0 -> 夜间加深 -> 日出迅速消失。

-------------------------------------------------------------------------------
未修改但对结果有残余影响的已知项（供后续标定）：

  * CLDTOT 0.675（云量仍偏少 1/3）：会抬高 SWDOWN、削减 GLW，并影响 CMAQ
    光解。本次刻意不动——它和 F1/F2 的标定耦合，单独调会同时破坏已对齐的
    短波。建议用 --param qc_rh_crit_base=0.82 单独评估云量敏感性。
  * 土壤只有 2 层且无 Noah 陆面模式：缺少土壤水热记忆。F3 已用冠层阻抗补偿
    了最关键的陆气分配，但多日干旱/降水后的土壤湿度演变仍缺失。
  * UST 0.894、GLW 1.003、T2 1.001：已在可接受范围。

标定用法::

    python3 pangu2wrf_v6.py --out /tmp/v6.nc --start-hour 168 --count 72 \\
        --pangu-dir MIDDLE_DATA/ERA5_2025-10-17_V5/pangu \\
        --start-time 2025-10-17_00:00:00

===============================================================================
v3.2 修复：Q2 高值起不来
-------------------------------------------------------------------------------
v3.1 修复：Q2 高值起不来
  v3 的 two_meter_mixing_ratio 用 Q2 = RH(最低层) × q_sat(T2, PSFC)，
  三个压低高值的来源叠加：
    1) 最低层 RH ≠ 2 m RH。清晨辐射逆温时，2 m 处在逆温层内接近饱和
       (RH 0.95~1.0)，而最低质量层在逆温顶以上更干 (RH 0.7~0.85)，
       用最低层 RH 代 2 m RH 使清晨峰值低 15~25%。
    2) q_sat(T2) 是硬天花板。若 T2 清晨偏低 1~2 K，q_s(T2) 低 6~13%，
       Q2 被这个天花板压住。
    3) RH × q_s 近似本身偏低 1~3%（精确式 qv = εe/(p−e) 的修正因子
       (p−e_s)/(p−RH·e_s) > 1 被省掉）。
  v3.1 改为「近地层水汽压守恒」（比 RH 守恒更物理）+ 精确混合比公式：
      e_low = RH(最低层) · e_s(T_low)
      e_2m  = min(e_low, 0.99·e_s(T2))        # 2 m 饱和留 1% 余量
      Q2    = ε·e_2m / (p_sfc − e_2m)          # 精确式
  Q2 不再受 q_s(T2) 硬天花板限制；T2 < T_low（清晨逆温）时 RH_2m 自然
  升高，更接近实际 2 m 湿度。预期清晨峰值 +15~25%，白天 +1~5%。
  新增 saturation_vapor_pressure_ice / saturation_vapor_pressure_auto
  （冷层 RH/云量诊断备用；Q2 默认 use_ice=False）。

-------------------------------------------------------------------------------
v3.2 修复（本次）：Q2 高湿时（清晨逆温）仍偏低
  v3.1 的「近地层水汽压守恒」在不稳定层结（白天）成立，但在稳定边界层里
  把清晨的水汽压系统性低估 10~25%：
    - 辐射逆温时，近地面因辐射冷却导致水汽凝结/露水/辐射雾在 2 m 处堆积，
      2 m 处 RH 明显高于最低模式层（几十米高）的 RH；
    - v3.1 的 e 守恒 + `min(e_low, 0.99·es_2m)` 只能靠「T_low > T2 使 RH_2m
      被放大 es(T_low)/es(T2)」间接抬高，放大倍数不够（RH_low 已被 AI 模型
      平滑到 0.6~0.8，乘 1.19 后仍到不了实际清晨的 0.95~1.0），且无上限保护。
  v3.2 在 v3.1 的 e 守恒基础上，叠加一个「逆温强度 → 向饱和靠拢」的
  参数化补足这一段近地堆积：
      inv   = clip((T_low − T2) / q2_inv_scale, 0, 1)      # 逆温强度权重
      rh_2m = e_2m / e_s(T2)
      rh_2m ← rh_2m + q2_inv_weight · inv · (q2_inv_rh_target − rh_2m)
      e_2m  = min(rh_2m, 0.99) · e_s(T2)
  白天（T_low ≤ T2）inv = 0，完全退回 v3.1 行为，低湿时段不变；
  夜间逆温 3 K 时把 2 m RH 向 0.95 靠拢 60%（默认）。
  新增 Params 系数：q2_inv_rh_target / q2_inv_weight / q2_inv_scale。
  下游 Q2 增大后：GLW +2~5 W/m²（Brutsaert e 上升）、LH 略减（近地更湿）、
  TSK 白天 +0.0~0.3 K（潜热项减小），方向均合理。

-------------------------------------------------------------------------------
v2 相对 v1（pangu2wrf.py）的修改（均为针对 PGCMAQ 诊断结论的定点修复）：

1. 云水方案重写（cloud_water / cloud_fraction）
   v1：qc = qs*(rh-rhc)/(1-rhc)，把整格饱和水汽都当云水，域均 3.0e-4 kg/kg，
       CMAQ 云光学厚度 ~265（基准 7.2），光解被压死 -> O3 偏低 13%。
   v2：qc = cf^qc_cf_power × qc_incloud_ref，域均 ~3.3e-6、LWP ~0.019 kg/m²，
       云光学厚度回到 o(1~10)，与基准一致。云量阈值改用随高度变化的 rhc。
2. 云-辐射自洽（shortwave_down / cloud_optical_depth）
   v1：SWDOWN 用 RH 云量做 1-0.75·cf³ 衰减（RGRND 反而比基准高 38 W/m²），
       与 CMAQ 实际用的云水完全脱钩。
   v2：用同一条云光学厚度按 Beer 定律衰减（τ 与 CMAQ 的 ext=3LWC/(2ρw·re) 一致）。
3. 边界层高度（pbl_height）
   v1：以第一模式层为 Rib 参考且风速无下限，弱风 + 高地形时 PBLH 贴到 50 m 下限
       （太原一带全天 50~106 m，基准 300~1430 m），SO2 烟羽被闷在贴地层，
       源区 PM2.5/SO4 成倍偏高。
   v2：Rib 参考 + 风速下限 + 对流边界层 encroachment 解 h=sqrt(2H/γ)
       （H 为当日累积地表加热），夜间补等效地表逆温；白天混合层 ~900~1100 m。
4. 冰相水凝物（ice_water / VAR_SPECS）
   补写 QICE/QSNOW/QGRAUP，使 MCIP nqspecies=5（避免 QI/QS 单独出现触发 stop），
   CMAQ 可用冰云光学与温度加权。
5. 写入 CLDFRA（Switches.provide_cldfra=True）
   MCIP 据此输出 CFRAC_3D，CMAQ 光解直接采用该云量，不再由 QC 反推，
   消除"云量用 RH、云水用另一套"的不一致。
6. 降水拆分（precipitation_rate）：按强度拆成对流性 RAINC / 大尺度 RAINNC，
   并把降水效率由 0.80 降到 0.35（v1 域均降水是基准的 4.8 倍）。

新增命令行开关：--param NAME=VALUE（可重复），用于在不改代码的情况下标定
Params 中的经验系数。

-------------------------------------------------------------------------------
以下为 v1 原说明：由 pangu2wrf 包下的 11 个模块机械合并而成（config / grid / horiz_interp /
vert_interp / cloud_precip / radiation / land / pbl / write_wrfout /
run_pangu2wrf / validate）：去掉包内 import、把模块 docstring 变成注释、
去掉 `config.` 这类模块前缀（同名局部变量遮蔽的一处改成 _land_albedo 别名），
因此不再依赖 pangu2wrf 包，可单独拷走运行，其余代码与原包逐字一致。
已验证：自检输出、校验报告与原包逐字相同，转换出的 wrfout 60 个变量逐点相同。

常用用法（与原来的 RUN.SH 等价，环境变量名照旧）::

    export START_DAY=2026-09-18 DomainName=GFS_${START_DAY}
    python3 pangu2wrf.py                            # 1 小时起报的后 24 时次
    python3 pangu2wrf.py --days 4 --start-hour 0    # 0~96h（4 天）
    python3 pangu2wrf.py --pangu-dir ... --out ... --start-hour 1 --count 24
    python3 pangu2wrf.py --selftest                 # 自检，不产出文件
    python3 pangu2wrf.py --stage validate           # 链路校验（原 validate.py）

并行版：需要长时段（数百时次以上）时用同目录的 pangu2wrf_par.py，
参数与本脚本一致，另有 --workers / --merge / --check。它输出分块文件
（MCIP 的 InMetFiles 可直接列多个），加 --merge 则用 ncrcat 合成单文件。
实测 96 个时次：本脚本 12.6 s、并行 8 进程 6.6 s（同一台机器）。

参数优先级：命令行 > 环境变量 > 内置默认值。可用环境变量：
    DomainName / START_DAY     域目录名（GFS_YYYY-MM-DD）与起报日期
    PANGU_GFS_ROOT             数据根目录，默认 /home/ubuntu01/sdb/Pangu_AQF/MIDDLE_DATA
    PANGU_DIR / PANGU_OUT      直接指定输入目录与输出文件
    START_HOUR / RUN_COUNT     起始小时序号与时次数
    RUN_DAYS                   等价于 --days
    PANGU_TEMPLATE             模板 wrfout 路径
    PANGU_START_TIME           小时序号 0 对应的 UTC 时刻

每个时次的处理链：
    读 npy -> 水平插值 -> 风旋转 -> 静力下延求 PSFC -> 重建 eta（P/PB/PH/PHB）
    -> 连续方程诊断 W -> 云水/降水/辐射/陆面/湍流诊断 -> 写盘
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 本脚本的数组都在 (34, 99, 99) 量级，属于"小数组"。多线程 BLAS 在这种规模下
# 线程同步开销远超计算本身——实测 96 个时次：32 线程 183 s，单线程 13.6 s。
# 因此默认把 BLAS 线程压到 1（想覆盖就自行 export OPENBLAS_NUM_THREADS=N）。
for _blas_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                  "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_blas_var, "1")

import netCDF4 as nc
import numpy as np


# ==========================================================================
# 模块：config.py
# ==========================================================================
# pangu2wrf 全局配置。
#
# 集中放置路径、目标时段、物理常数、诊断参数化开关与经验查表系数，
# 其余模块只读不改，便于复现与调参。
#
# 所有经验系数都标注了来源/量级依据，便于后续替换为更精细的方案。




# ---------------------------------------------------------------------------
# 物理常数（与 WRF 取值保持一致，见 wrfnconsts / module_model_constants）
# ---------------------------------------------------------------------------
G = 9.80665              # 重力加速度 [m s-2]
RD = 287.0               # 干空气气体常数 [J kg-1 K-1]
RV = 461.6               # 水汽气体常数 [J kg-1 K-1]
CP = 1004.5              # 干空气定压比热 [J kg-1 K-1]
LV = 2.5e6               # 汽化潜热 [J kg-1]
KARMAN = 0.4             # von Karman 常数
SOLAR_CONST = 1361.0     # 太阳常数 [W m-2]
STEFAN_BOLTZMANN = 5.670374419e-8
P0 = 100000.0            # 参考气压 [Pa]
RDOVCP = 2.0 / 7.0       # Rd/cp
EPSILON = 0.622          # Rv/Rd 的倒数（q = eps*e/(p-0.378e) 中的 eps）

# ---------------------------------------------------------------------------
# 盘古气压层（与 Pangu/GFS/01_make_gfs_input.py:12 保持一致）
# ---------------------------------------------------------------------------
PLEV_HPA = np.array(
    [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50], dtype=np.float64
)
PLEV_PA = PLEV_HPA * 100.0
NLEV = PLEV_HPA.size

# ---------------------------------------------------------------------------
# 盘古源网格（0.25 度全球规则经纬度，见 forecast_decode_functions.py）
# ---------------------------------------------------------------------------
SRC_NLAT, SRC_NLON = 721, 1440
SRC_DLAT, SRC_DLON = 0.25, 0.25
SRC_LAT0, SRC_LON0 = 90.0, 0.125
# upper / surface 通道顺序
UPPER_CHANNELS = ("z", "q", "t", "u", "v")
SURFACE_CHANNELS = ("msl", "u10", "v10", "t2m")

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
TEMPLATE_NC = os.path.join(_PROJECT_ROOT, "wrfout_d01.nc")
# 默认盘古输出目录（02_inference_01.py 的默认 outdir）
PANGU_1H_DIR = os.path.join(_PROJECT_ROOT, "Pangu", "GFS", "PANGU_2025-06-03", "pangu_1h")
# 默认输出目录
OUT_DIR = os.path.join(_PROJECT_ROOT, "pangu_wrfout")
# MCIP 运行脚本位置（run_mcip_pangu.csh 会引用）
MCIP_SCRIPT = os.path.join(_PROJECT_ROOT, "mcip", "scripts", "run_mcip_pangu.csh")

# ---------------------------------------------------------------------------
# 诊断参数化开关
# ---------------------------------------------------------------------------


@dataclass
class Switches:
    """可逐个开关的诊断项；关闭后对应变量不写入输出文件。"""

    wind_rotation: bool = True      # earth-relative -> grid-relative 风旋转
    diagnose_w: bool = True         # 由连续方程诊断 omega 并转 w
    provide_rmol: bool = True       # 写入 RMOL(=1/L)，触发 MCIP 的 ifmol
    provide_soil: bool = True       # 写入 SMOIS/TSLB/ISLTYP，触发 ifsoil
    provide_znt: bool = True        # 写入 ZNT
    provide_lai: bool = True        # 写入 LAI
    provide_vegfra: bool = True     # 写入 VEGFRA
    provide_canwat: bool = True     # 写入 CANWAT（恒 0）
    provide_q2: bool = True         # 写入 Q2（由地表 RH 反推）
    provide_t2_u10_v10: bool = True  # 写入 T2/U10/V10
    provide_cldfra: bool = True     # 写入 CLDFRA（v2 默认开：MCIP 输出 CFRAC_3D 供 CMAQ 光解）
    tsk_energy_balance: bool = True  # TSK 由线性化地表能量平衡求（否则 TSK=T2M）


@dataclass
class Params:
    """诊断参数化的经验系数。"""

    # --- 云水方案 v2：次网格云量 × 云内凝结量 ---
    # v1 的 qc = qs*(rh-rhc)/(1-rhc) 会把整格饱和水汽都当云水（域均 3e-4 kg/kg，
    # 而 WRF 实况域均约 3e-6、云内约 1.5e-4），使 CMAQ 云光学厚度放大 ~37 倍、
    # 光解被压制（O3 偏低 13%）。v2 改为「云量 cf（RH 阈值）× 云内凝结量参考值」，
    # 量级与 WRF 可比，且与 SWDOWN 的云衰减自洽。
    qc_rh_crit_base: float = 0.82   # 低层临界相对湿度（云量起报阈值）v7[F7-2]: 0.85->0.82
    qc_rh_crit_top: float = 0.92    # 高空临界相对湿度（p < 300 hPa）
    qc_p_top_cut: float = 15000.0   # 该气压以上不再诊断云水 [Pa]
    cf_power: float = 1.0           # 云量对 (rh-rhc) 的非线性（1 = 线性）
    qc_cf_power: float = 2.0        # 云水对云量的非线性（水凝物 ∝ cf^2）
    qc_incloud_ref: float = 1.3e-4  # 云内凝结量参考值 [kg/kg]（≈0.13 g/m3）
    qc_max: float = 6.0e-4          # 云水上限 [kg/kg]
    qc_min: float = 1.0e-8          # 低于该值置零
    # 雨水自动转化：v2 的阈值 1e-4 与 qc_max 相同，导致 QR 恒为 0
    # （基准 QR 域均 2.37e-6），v3 下调阈值使云区产生雨水。
    rain_autoconv_coef: float = 0.6
    rain_autoconv_thresh: float = 1.5e-5
    rain_max: float = 3.0e-4

    # --- 冰相（v3：冷云用更低的 RH 阈值，使中层冰云真正出现）---
    ice_t_warm: float = 263.15      # 暖于该温度全为液水 [K]
    ice_t_cold: float = 253.15      # 冷于该温度全为冰 [K]
    ice_snow_frac: float = 0.35     # 冰水相中划为雪的份额
    graupel_frac: float = 0.0       # 划定霰的份额（默认 0）
    ice_rh_reduction: float = 0.15  # 冷云临界 RH 的最大下调量（冰面饱和更易达到）
    ice_rh_dt: float = 20.0         # 从 0℃ 到该温差内线性施加下调 [K]

    # --- 降水（水汽通量辐合）---
    # v6：加湿度 gate 与毛毛雨截断，抑制 v5 的"全天候均匀毛毛雨"
    # （10/24 日累计 1.822 mm，基准 0.531 mm，逐小时恒在 0.04~0.09 mm/h）。
    precip_efficiency: float = 0.35  # 降水效率（v1=0.8 时域均降水为基准 4.8 倍）
    precip_cap: float = 30.0         # 单小时降水上限 [mm/h]
    precip_conv_thresh: float = 2.0  # 超过该强度 [mm/h] 判为对流性降水
    precip_rh_gate: tuple = (0.65, 0.88)  # 柱相对湿度 gate [下界, 上界]，低于下界不产水
    precip_drizzle_cut: float = 0.15      # 毛毛雨截断 [mm/h]，低于此值置零

    # --- 辐射（v6：修正云衰减的病态放大）---
    # v6 把晴空透射率由 0.78 上调到 0.84，与去掉 tau_col/cld 放大配合，
    # 使 SWDOWN 域均与 WRF 可比（v5 为 0.815 倍：云少于 WRF 却更暗）。
    sw_clear_transmissivity: float = 0.84  # 晴空大气透射率
    sw_cloud_albedo: float = 0.85          # 云短波反射+吸收（无云光学厚度时的上限衰减）
    sw_use_tau: bool = True                # 用云光学厚度做 Beer 衰减
    lw_emiss_floor: float = 0.55           # 有效发射率下限
    reff_liquid: float = 10.0e-6           # 液滴有效半径 [m]（与 CMAQ 一致）
    reff_ice: float = 25.0e-6              # 冰晶有效半径 [m]
    sw_slant_floor: float = 0.15           # 斜程放大的 cosz 下限（防 cosz->0 时爆炸）
    sw_tau_eff_max: float = 60.0           # 有效光学厚度上限（数值保护）

    # --- v7【F7-1】气溶胶-辐射：低层湿度驱动的霾湿增长衰减 ---
    # 本方案输入只有气象场、无气溶胶/PM 场，故用边界层相对湿度作霾湿增长代理。
    # tau_aer = aer_tau_max * clip((rh_bl-aer_rh_thresh)/(aer_rh_max-aer_rh_thresh),
    #                             0,1)^aer_power
    # 该层在边界层内混合均匀，对整片天空衰减（云只衰减其覆盖份额），故相乘。
    # 晴好日（rh_bl < aer_rh_thresh）完全不受影响，不破坏 v6 的晴空短波标定。
    aer_use: bool = True                   # 总开关（False 则退回 v6 行为）
    aer_rh_thresh: float = 0.60            # 霾湿增长起报的边界层 RH 下限 [-]
    aer_rh_max: float = 0.90               # 达到该 RH 时取满 tau [-]
    aer_tau_max: float = 0.45              # 满 RH 时的气溶胶光学厚度 [-]
    aer_power: float = 1.0                 # RH 超阈后的非线性（1=线性）[-]
    aer_bl_top: float = 85000.0            # 边界层顶气压 [Pa]，取其下 RH 加权均值
    aer_tau_max_cap: float = 3.0           # 数值保护上限

    # --- 陆面 ---
    snowc_t_thresh: float = 271.15    # 判定积雪/海冰的地表温度阈值 [K]
    albedo_snow: float = 0.60         # 积雪反照率
    soil_moisture_ref: float = 0.50   # 参考土壤湿度（用于蒸发效率）[m3 m-3]
    canopy_wetness: float = 0.0       # CANWAT 常数 [kg m-2]
    emissivity: float = 0.98          # 地表长波发射率（陆面能量平衡用）
    tsk_delta_clip: tuple = (-10.0, 18.0)  # TSK-T2 的裁剪区间 [K]

    # --- v6【F3】蒸发效率：Jarvis (1976) 型冠层阻抗 ---
    # 取代 v5 的 beta = clip(SMOIS[0]/soil_moisture_ref, 0.1, 1)（恒为 0.637）。
    # rs_min 单位内涵为"单位叶面积的最小气孔阻抗"，除以有效 LAI 得到冠层阻抗。
    rs_min: float = 70.0            # 单位叶面积最小气孔阻抗 [s m-1]
    rs_lai_floor: float = 0.2       # 有效叶面积下限（裸土/稀疏植被保护）[m2 m-2]
    rs_par_coef: float = 0.004      # 光响应系数 [1/(W m-2)]
    rs_par_light: float = 400.0     # 气孔基本开放所需短波 [W m-2]
    rs_vpd_coef: float = 0.30       # VPD 胁迫系数 [1/kPa]
    rs_theta_wilt: float = 0.10     # 凋萎点土壤体积含水量 [m3 m-3]
    rs_theta_crit: float = 0.35     # 不受水分胁迫的临界含水量 [m3 m-3]
    rs_wet_floor: float = 0.10      # 有效湿度的下限，防止 rs 爆炸 [-]
    rs_floor: float = 20.0          # 冠层阻抗下限 [s m-1]
    rs_ceiling: float = 2000.0      # 冠层阻抗上限 [s m-1]（夜间/极干）
    beta_min: float = 0.05          # 蒸发效率下限 [-]
    beta_max: float = 1.00          # 蒸发效率上限 [-]

    # --- 湍流与 PBL v2 ---
    # v1 用「第一模式层」作 Rib 参考、且风速不设下限，弱风+高地形时 PBLH 会退化到
    # pbl_min（实测太原一带全天贴 50 m，而基准 300~1430 m），烟羽被闷在贴地层，
    # 导致 SO2/SO4/PM2.5 成倍偏高。v2 改为：地表参考 + 对流边界层热泡封顶。
    pbl_rib_crit: float = 0.25       # 总体 Richardson 数临界值
    pbl_min: float = 30.0            # PBLH 下限 [m]
    pbl_max: float = 3500.0          # PBLH 上限 [m]
    pbl_wind_floor: float = 1.0      # Rib 所用最小风速 [m s-1] v7[F7-3]: 2.0->1.0
    # v7 实测（MCIP 廓线 10/22 正午）：floor=2.0 在静风点位把 Rib 支抬 3.49~4.48 倍
    # （唐山 0.35 m/s -> 171 m vs 无下限 38 m；承德 0.23 -> 105 vs 30）。
    # v1 的「PBLH 贴 pbl_min」已由 v2 的地表参考 + 对流支封顶共同解决，不再依赖
    # 高风速下限兜底。若夜间过浅用 --param pbl_wind_floor=1.5。
    # 判为对流边界层的地表感热阈值 [W m-2]。取 2 W/m² 而非 20：
    # 四川盆地这类多云弱加热区 HFX 常在 5~20，阈值过高会退回 Rib 分支、
    # 在弱风下重新塌陷（实测 (21,7) 等格点 PBLH 仅 120 m，基准 310 m）。
    pbl_hfx_thresh: float = 2.0
    # 【敏感性实验 A2 用】是否启用对流边界层（encroachment）分支。
    # 1.0 = 默认（Rib 与热收支封顶取大者，即 A1）；0.0 = 只用 Richardson 数法（A2）。
    pbl_conv_on: float = 1.0
    # 逆温层强度 γ [K m-1]，encroachment 用。v5 的 4.0e-3 与 v6 提升后的 HFX
    # （见 F3）搭配会把白天混合层抬得过高（域平均达 WRF 的 1.17~1.25 倍）。
    # 6.5e-3 经联合（标定日 + 样本外）标定选出：它是唯一能在「日均值」与
    # 「午后峰值」两项上都优于 v5 的取值。更大的 γ（如 1.1e-2）可再降 3%
    # 总误差，但会把 10/25 午后峰值压到比 v5 更低，故不作为默认。
    pbl_inv_strength: float = 6.5e-3
    pbl_decay_hours: float = 2.0      # 夜间累积加热的衰减时间尺度 [h]
    # 夜间地表逆温：本方案没有辐射模块，夜间 TSK≈T2，Rib 会给出 700 m 的"无逆温"
    # 边界层（基准 70~280 m）。用给地表一个等效降温补出逆温。
    # v6【F5】：v5 的亏损是常数 1.0 K，使夜间 Rib 参考不随时间变化 -> 夜间 PBLH
    # 被"钉死"（实测 10/24 全天 224~240 m、10/25 234~242 m，而基准 250~330 m 且
    # 有演变）。v6 改为向最大值松弛的一阶过程：日落后由 0 逐渐加深，
    # 日出后快速回到 0；并按 10 m 风速做机械混合削弱（风大->夜间混合强->逆温弱）。
    pbl_night_dtheta_max: float = 1.2   # 夜间等效位温亏损可达的最大值 [K]
    pbl_night_relax_hours: float = 3.0  # 夜间向最大值松弛的时间尺度 [h]
    pbl_night_recover_hours: float = 1.0  # 白天回到 0 的时间尺度 [h]
    pbl_night_wind_ref: float = 3.0     # 机械混合开始削弱逆温的参考风速 [m s-1]
    pbl_night_wind_scale: float = 2.0   # 风速削弱的 e 折尺度 [m s-1]
    # 白天用第一模式层作 Rib 参考（TSK 比 T2 高 3~5 K，直接当地表参考会虚不稳定）；
    # 夜间用上面补出的地表位温作参考。
    pbl_use_surface_ref: bool = True
    meas_height: float = 10.0        # T2/U10/Q2 的代表高度 [m]
    mol_min_abs: float = 1.0         # |L| 下限，避免 RMOL 爆炸 [m]
    hfx_clip: tuple = (-600.0, 800.0)
    lh_clip: tuple = (0.0, 700.0)
    # 地表能量闭合：陆地感热+潜热之和上限 = 净辐射 * (1 - ground_heat_frac)
    ground_heat_frac: float = 0.10
    flux_scale_clip: tuple = (0.05, 1.50)

    # --- v3.2：2 m 湿度的稳定边界层近地增强 ---
    # 辐射逆温中近地面水汽堆积（露水/辐射雾），最低层 RH 不足以代表 2 m RH。
    # 用"逆温强度 -> 向饱和目标靠拢"的参数化补足；白天逆温为 0 时不影响 v3.1 行为。
    q2_inv_rh_target: float = 0.95   # 逆温时 2m RH 的增强目标
    q2_inv_weight: float = 0.6       # 达到最大逆温时的靠拢权重（0=不增强，1=完全到目标）
    q2_inv_scale: float = 3.0        # 达到最大权重所需的逆温差 [K]


@dataclass
class Config:
    template_nc: str = TEMPLATE_NC
    pangu_dir: str = PANGU_1H_DIR
    out_dir: str = OUT_DIR
    out_prefix: str = "wrfout_d01_pangu"
    hours: List[int] = field(default_factory=lambda: list(range(0, 24)))
    switches: Switches = field(default_factory=Switches)
    params: Params = field(default_factory=Params)


# ---------------------------------------------------------------------------
# USGS 24 类土地利用查表（MMINLU="USGS"，ISWATER=16，ISURBAN=1，ISICE=24）
# 数值取自 WRF/Noah 陆面方案的典型分类值，用于无陆面模式时的诊断。
# 索引 0 为占位（WRF 类别从 1 开始）。
# ---------------------------------------------------------------------------
LU_NAMES: List[str] = [
    "n/a",
    "Urban and Built-Up Land",
    "Dryland Cropland and Pasture",
    "Irrigated Cropland and Pasture",
    "Mixed Dryland/Irrigated Cropland",
    "Cropland/Grassland Mosaic",
    "Cropland/Woodland Mosaic",
    "Grassland",
    "Shrubland",
    "Mixed Shrubland/Grassland",
    "Savanna",
    "Deciduous Broadleaf Forest",
    "Deciduous Needleleaf Forest",
    "Evergreen Broadleaf Forest",
    "Evergreen Needleleaf Forest",
    "Mixed Forest",
    "Water Bodies",
    "Herbaceous Wetland",
    "Wooded Wetland",
    "Barren or Sparsely Vegetated",
    "Herbaceous Tundra",
    "Wooded Tundra",
    "Mixed Tundra",
    "Bare Ground Tundra",
    "Snow or Ice",
]

Z0_TABLE: Dict[int, float] = {  # 粗糙度长度 [m]
    1: 0.50, 2: 0.10, 3: 0.10, 4: 0.10, 5: 0.10, 6: 0.15, 7: 0.12, 8: 0.05,
    9: 0.06, 10: 0.15, 11: 0.80, 12: 0.80, 13: 1.00, 14: 1.20, 15: 0.90,
    16: 1.0e-4, 17: 0.10, 18: 0.20, 19: 0.05, 20: 0.05, 21: 0.20, 22: 0.10,
    23: 0.05, 24: 1.0e-3,
}

ALBEDO_TABLE: Dict[int, float] = {  # 短波反照率
    1: 0.15, 2: 0.17, 3: 0.18, 4: 0.18, 5: 0.18, 6: 0.16, 7: 0.19, 8: 0.22,
    9: 0.20, 10: 0.20, 11: 0.16, 12: 0.14, 13: 0.12, 14: 0.12, 15: 0.13,
    16: 0.08, 17: 0.14, 18: 0.14, 19: 0.25, 20: 0.15, 21: 0.15, 22: 0.15,
    23: 0.25, 24: 0.55,
}

LAI_TABLE: Dict[int, float] = {  # 叶面积指数 [m2 m-2]，年代表值
    1: 1.0, 2: 1.5, 3: 2.5, 4: 2.5, 5: 2.0, 6: 3.0, 7: 1.5, 8: 0.7,
    9: 1.0, 10: 2.0, 11: 5.0, 12: 5.0, 13: 5.5, 14: 5.5, 15: 5.0,
    16: 0.0, 17: 2.5, 18: 4.5, 19: 0.5, 20: 0.7, 21: 1.5, 22: 1.2,
    23: 0.3, 24: 0.0,
}

VEGFRA_TABLE: Dict[int, float] = {  # 植被覆盖度 [%]
    1: 10.0, 2: 80.0, 3: 85.0, 4: 85.0, 5: 80.0, 6: 80.0, 7: 80.0, 8: 60.0,
    9: 75.0, 10: 75.0, 11: 90.0, 12: 90.0, 13: 95.0, 14: 95.0, 15: 90.0,
    16: 0.0, 17: 75.0, 18: 90.0, 19: 25.0, 20: 55.0, 21: 70.0, 22: 65.0,
    23: 10.0, 24: 0.0,
}


def table_to_array(table: Dict[int, float], ncat: int = 24) -> np.ndarray:
    """把 1..ncat 的查表字典转成 numpy 数组（索引 0 复用第 1 类）。"""
    arr = np.zeros(ncat + 1, dtype=np.float64)
    for k, v in table.items():
        arr[k] = v
    arr[0] = arr[1]
    return arr

# ==========================================================================
# 模块：grid.py
# ==========================================================================
# 模板网格读取。
#
# 以 wrfout_d01.nc 为模板，提供：
#   * 三套水平目标点（质量点 / U 点 / V 点）的经纬度
#   * 静态场（地形、土地利用、map factor、科氏参数、eta 层定义、土壤参数）
#   * 全部全局属性（供 write_wrfout 原样复制）






def cone_constant(truelat1: float, truelat2: float) -> float:
    """Lambert 圆锥常数 n（两者相等时退化为 sin(lat1)）。"""
    if abs(truelat1 - truelat2) < 1.0e-6:
        return float(np.sin(np.radians(truelat1)))
    return float(
        np.log(np.cos(np.radians(truelat1)) / np.cos(np.radians(truelat2)))
        / np.log(
            np.tan(np.pi / 4.0 + np.radians(truelat2) / 2.0)
            / np.tan(np.pi / 4.0 + np.radians(truelat1) / 2.0)
        )
    )


class GridTemplate:
    """封装模板 wrfout 网格与静态场。

    所有静态量在实例化时一次性读出并缓存在内存（域仅 99x99，开销可忽略）。
    """

    def __init__(self, path: str = None):
        self.path = path or TEMPLATE_NC
        if not os.path.isfile(self.path):
            raise FileNotFoundError("模板文件不存在: %s" % self.path)

        ds = nc.Dataset(self.path)

        # --- 全局属性 ---
        self.global_attrs: Dict[str, Any] = {}
        for name in ds.ncattrs():
            val = ds.getncattr(name)
            if isinstance(val, np.ndarray):
                val = val.tolist()
            elif isinstance(val, np.generic):
                val = val.item()
            self.global_attrs[name] = val

        # --- 维度 ---
        self.nx = len(ds.dimensions["west_east"])              # 99
        self.ny = len(ds.dimensions["south_north"])            # 99
        self.nz = len(ds.dimensions["bottom_top"])             # 34
        self.nzp = len(ds.dimensions["bottom_top_stag"])       # 35
        self.ns = len(ds.dimensions["soil_layers_stag"])       # 2
        self.nx_stag = len(ds.dimensions["west_east_stag"])    # 100
        self.ny_stag = len(ds.dimensions["south_north_stag"])  # 100

        self.times: List[str] = [b"".join(t).decode() for t in ds.variables["Times"][:]]

        # --- 水平坐标 ---
        self.xlat = self._get(ds, "XLAT")
        self.xlong = self._get(ds, "XLONG")
        self.xlat_u = self._get(ds, "XLAT_U")
        self.xlong_u = self._get(ds, "XLONG_U")
        self.xlat_v = self._get(ds, "XLAT_V")
        self.xlong_v = self._get(ds, "XLONG_V")

        # --- 静态地表场 ---
        self.hgt = self._get(ds, "HGT")
        self.landmask = self._get(ds, "LANDMASK")
        self.lu_index = self._get(ds, "LU_INDEX")
        self.isltyp = self._get(ds, "ISLTYP")
        # IVGTYP 在转换结果中可能不存在（MCIP 不需要它），退化为 LU_INDEX
        self.ivgtyp = self._get_opt(ds, "IVGTYP", self.lu_index)
        self.mapfac_m = self._get(ds, "MAPFAC_M")
        self.mapfac_u = self._get(ds, "MAPFAC_U")
        self.mapfac_v = self._get(ds, "MAPFAC_V")
        self.f_cor = self._get(ds, "F")
        self.sinalpha_ref = self._get(ds, "SINALPHA")
        self.cosalpha_ref = self._get(ds, "COSALPHA")

        # --- 垂直坐标与静态廓线 ---
        self.znw = np.asarray(ds.variables["ZNW"][0], dtype=np.float64)
        self.znu = np.asarray(ds.variables["ZNU"][0], dtype=np.float64)
        self.p_top = float(np.asarray(ds.variables["P_TOP"][0]))
        zeros_soil = np.zeros(len(ds.dimensions["soil_layers_stag"]), dtype=np.float64)
        self.zs = (np.asarray(ds.variables["ZS"][0], dtype=np.float64)
                   if "ZS" in ds.variables else zeros_soil)
        self.dzs = (np.asarray(ds.variables["DZS"][0], dtype=np.float64)
                    if "DZS" in ds.variables else zeros_soil)

        # --- 土壤量：取模板时段的时间平均，作为"气候常值" ---
        self.soil_moisture_mean = np.asarray(
            ds.variables["SMOIS"][:], dtype=np.float64
        ).mean(axis=(0, 2, 3))
        self.soil_temp_mean = np.asarray(
            ds.variables["TSLB"][:], dtype=np.float64
        ).mean(axis=(0, 2, 3))

        ds.close()

        # --- 投影参数 ---
        self.dx = float(self.global_attrs["DX"])
        self.dy = float(self.global_attrs["DY"])
        self.truelat1 = float(self.global_attrs["TRUELAT1"])
        self.truelat2 = float(self.global_attrs["TRUELAT2"])
        self.stand_lon = float(self.global_attrs["STAND_LON"])
        self.map_proj = int(self.global_attrs["MAP_PROJ"])
        self.cone = cone_constant(self.truelat1, self.truelat2)

    # -- 内部工具 ---------------------------------------------------------
    @staticmethod
    def _get(ds: nc.Dataset, name: str) -> np.ndarray:
        """读取第一个时次的 2D 场并转为普通 float64 数组。"""
        return np.asarray(ds.variables[name][0], dtype=np.float64)

    @staticmethod
    def _get_opt(ds: nc.Dataset, name: str, default):
        """可选变量：不存在时返回 default。"""
        if name not in ds.variables:
            return np.asarray(default, dtype=np.float64)
        return np.asarray(ds.variables[name][0], dtype=np.float64)

    # -- 旋转因子 ---------------------------------------------------------
    def rotation_sincos(self, lat: np.ndarray, lon: np.ndarray):
        """返回 WRF 约定的 (SINALPHA, COSALPHA)。

        经验证与模板文件的 SINALPHA/COSALPHA 完全一致：
            COSALPHA =  cos(cone * (lon - STAND_LON))
            SINALPHA = -sin(cone * (lon - STAND_LON))
        对质量点、U 点、V 点都可由各自的经纬度直接求值。
        """
        angle = self.cone * np.radians(lon - self.stand_lon)
        return -np.sin(angle), np.cos(angle)

    def rotation_at_mass_points(self):
        return self.rotation_sincos(self.xlat, self.xlong)

    def rotation_at_u_points(self):
        return self.rotation_sincos(self.xlat_u, self.xlong_u)

    def rotation_at_v_points(self):
        return self.rotation_sincos(self.xlat_v, self.xlong_v)

    def validate_rotation(self) -> float:
        """与模板自带 SINALPHA/COSALPHA 比对，返回最大绝对偏差。"""
        sa, ca = self.rotation_at_mass_points()
        return float(
            max(np.abs(sa - self.sinalpha_ref).max(), np.abs(ca - self.cosalpha_ref).max())
        )

    # -- 便捷属性 ---------------------------------------------------------
    @property
    def shape(self):
        return (self.ny, self.nx)

    @property
    def shape_u(self):
        return self.xlat_u.shape

    @property
    def shape_v(self):
        return self.xlat_v.shape

    def global_attrs_copy(self) -> Dict[str, Any]:
        """深拷贝一份全局属性，供输出文件使用。"""
        out: Dict[str, Any] = {}
        for k, v in self.global_attrs.items():
            out[k] = list(v) if isinstance(v, list) else v
        return out

    def summary(self) -> str:
        return (
            "模板 %s\n"
            "  网格 %d x %d x %d（面层 %d），soil_layers=%d\n"
            "  投影 MAP_PROJ=%d  DX=DY=%.0f m  CEN=(%.3f, %.3f)  STAND_LON=%.3f\n"
            "  XLAT %.3f..%.3f  XLONG %.3f..%.3f  HGT %.1f..%.1f m\n"
            "  P_TOP=%.0f Pa  cone=%.6f  |SINALPHA 校验偏差|=%.2e\n"
            "  土壤时间平均：SMOIS=%s  TSLB=%s"
            % (
                self.path,
                self.nx, self.ny, self.nz, self.nzp, self.ns,
                self.map_proj, self.dx,
                self.global_attrs["CEN_LAT"], self.global_attrs["CEN_LON"], self.stand_lon,
                self.xlat.min(), self.xlat.max(), self.xlong.min(), self.xlong.max(),
                self.hgt.min(), self.hgt.max(),
                self.p_top, self.cone, self.validate_rotation(),
                np.round(self.soil_moisture_mean, 4), np.round(self.soil_temp_mean, 2),
            )
        )

# ==========================================================================
# 模块：horiz_interp.py
# ==========================================================================
# 水平插值与风场旋转。
#
# 盘古源场是 0.25 度全球规则经纬网格（lat 90 -> -90 共 721 点，lon 0.125 -> 359.875
# 共 1440 点），目标是 WRF Lambert 投影上的三套交错网格。规则网格到任意点的双线性
# 插值可完全向量化，并且权重只与目标点有关，因此对每个目标网格预计算一次权重，
# 之后所有变量、所有时次复用。




# 源网格坐标（与 config 保持一致）
SRC_LAT = SRC_LAT0 - SRC_DLAT * np.arange(SRC_NLAT)
SRC_LON = SRC_LON0 + SRC_DLON * np.arange(SRC_NLON)


class BilinearMapper:
    """把源 2D/3D 场双线性插值到一组固定目标经纬度点。

    源场形状为 (..., nlat, nlon)，输出形状为 (...,) + self.shape。
    """

    def __init__(self, tgt_lat: np.ndarray, tgt_lon: np.ndarray, name: str = "target",
                 window=None):
        self.name = name
        self.shape = np.shape(tgt_lat)
        self.npts = int(np.prod(self.shape))

        lat = np.asarray(tgt_lat, dtype=np.float64).ravel()
        lon = np.asarray(tgt_lon, dtype=np.float64).ravel()

        # 纬度递减 -> 索引递增
        fi = (SRC_LAT0 - lat) / SRC_DLAT
        fi = np.clip(fi, 0.0, SRC_NLAT - 1.0 - 1e-9)
        self.i0 = np.floor(fi).astype(np.intp)
        di = fi - self.i0
        self.i1 = self.i0 + 1

        # 经度环绕
        fj = np.mod((lon - SRC_LON0) / SRC_DLON, SRC_NLON)
        self.j0 = np.floor(fj).astype(np.intp)
        dj = fj - self.j0
        self.j1 = np.mod(self.j0 + 1, SRC_NLON)

        self.w00 = (1.0 - di) * (1.0 - dj)
        self.w01 = (1.0 - di) * dj
        self.w10 = di * (1.0 - dj)
        self.w11 = di * dj

        # 目标点是否落在源网格内（含 0.25 度边缘容差）
        self.inside = lat <= SRC_LAT0 + 1e-9

        # 可选：预先裁剪的源窗口 (ilat0, ilat1, ilon0, ilon1)，半开区间
        self.window = None
        self.window_ok = False
        self.window_shape = None
        if window is not None:
            i0w, i1w, j0w, j1w = (int(v) for v in window)
            inside_window = (
                (self.i0 >= i0w) & (self.i1 < i1w)
                & (self.j0 >= j0w) & (self.j1 < j1w)
            ).all()
            if inside_window:
                self.window = (i0w, i1w, j0w, j1w)
                self.window_ok = True
                self.window_shape = (i1w - i0w, j1w - j0w)
                self.i0w, self.i1w = self.i0 - i0w, self.i1 - i0w
                self.j0w, self.j1w = self.j0 - j0w, self.j1 - j0w

    def __call__(self, src: np.ndarray) -> np.ndarray:
        """对源场做双线性插值。

        src 的最后两维可以是完整的 (721, 1440)，也可以是裁剪窗口的大小。
        """
        s = np.asarray(src)
        if self.window_ok and s.shape[-2:] == self.window_shape:
            i0, i1, j0, j1 = self.i0w, self.i1w, self.j0w, self.j1w
        elif s.shape[-2:] == (SRC_NLAT, SRC_NLON):
            i0, i1, j0, j1 = self.i0, self.i1, self.j0, self.j1
        else:
            raise ValueError(
                "%s: 源场末两维 %s 既不是完整网格 (%d, %d) 也不是裁剪窗口 %s"
                % (self.name, s.shape[-2:], SRC_NLAT, SRC_NLON,
                   self.window_shape)
            )
        out = (
            self.w00 * s[..., i0, j0]
            + self.w01 * s[..., i0, j1]
            + self.w10 * s[..., i1, j0]
            + self.w11 * s[..., i1, j1]
        )
        return out.reshape(s.shape[:-2] + self.shape)


def source_window(lat_min: float, lat_max: float, lon_min: float, lon_max: float,
                  margin: int = 2):
    """按目标域经纬度范围算出源网格裁剪窗口（含 margin 个格点的余量）。"""
    i_hi = int(np.floor((SRC_LAT0 - lat_max) / SRC_DLAT)) - margin
    i_lo = int(np.ceil((SRC_LAT0 - lat_min) / SRC_DLAT)) + margin
    j_lo = int(np.floor((lon_min - SRC_LON0) / SRC_DLON)) - margin
    j_hi = int(np.ceil((lon_max - SRC_LON0) / SRC_DLON)) + margin
    i0 = max(i_hi, 0)
    i1 = min(i_lo + 1, SRC_NLAT)
    j0 = j_lo
    j1 = j_hi + 1
    if j0 < 0 or j1 > SRC_NLON:
        # 跨越经度 0 度，放弃裁剪
        return (0, SRC_NLAT, 0, SRC_NLON)
    return (i0, i1, j0, j1)


def build_mappers(grid, window=None):
    """按模板网格构造三套插值器：(质量点, U 点, V 点)。"""
    return (
        BilinearMapper(grid.xlat, grid.xlong, "mass", window),
        BilinearMapper(grid.xlat_u, grid.xlong_u, "u-stag", window),
        BilinearMapper(grid.xlat_v, grid.xlong_v, "v-stag", window),
    )


# ---------------------------------------------------------------------------
# 风场旋转：earth-relative -> grid-relative
# ---------------------------------------------------------------------------
def rotate_earth_to_grid(u: np.ndarray, v: np.ndarray, sinalpha: np.ndarray,
                         cosalpha: np.ndarray):
    """把地球相对风分量旋转到投影网格坐标。

    采用 WRF/WPS 的约定（已用模板文件验证 SINALPHA = -sin(cone*(lon - STAND_LON))、
    COSALPHA = cos(...)）：

        u_grid =  u_earth * cosalpha + v_earth * sinalpha
        v_grid = -u_earth * sinalpha + v_earth * cosalpha

    几何自检：在标准经线以东的点，真实北向在网格坐标中应为"左上方向"
    （x 分量为负），上式在 lon > STAND_LON（alpha > 0，SINALPHA < 0）时给出
    u_grid(北向) = SINALPHA < 0 ✓。
    """
    return u * cosalpha + v * sinalpha, -u * sinalpha + v * cosalpha


def rotate_grid_to_earth(u: np.ndarray, v: np.ndarray, sinalpha: np.ndarray,
                         cosalpha: np.ndarray):
    """rotate_earth_to_grid 的逆变换。"""
    return u * cosalpha - v * sinalpha, u * sinalpha + v * cosalpha

# ==========================================================================
# 模块：vert_interp.py
# ==========================================================================
# 垂直重建：13 层等压面 -> 34 层地形跟随 eta。
#
# 关键关系（已用模板 wrfout_d01.nc 逐点验证）：
#
#     p_mid(k)  = P_TOP + (MUB + MU) * ZNU(k)        # 质量层，k = 1..34
#     p_face(k) = P_TOP + (MUB + MU) * ZNW(k)        # 面层，  k = 1..35
#     phi_face(1) = g * HGT
#     phi_face(k+1) = phi_face(k) - Rd * Tv_mid(k) * (ln p_face(k+1) - ln p_face(k))
#
# 用模板自身的 T/QVAPOR 做这套静力积分，可复现模板位势高度：顶层平均误差约 10 m
# （占 20 km 柱深的 0.05%），见 verify_vertical_scheme()。






# ---------------------------------------------------------------------------
# 基础换算
# ---------------------------------------------------------------------------
def mixing_ratio_from_specific_humidity(q: np.ndarray) -> np.ndarray:
    """比湿 -> 混合比（WRF 的 QVAPOR 是混合比）。"""
    q = np.clip(q, 0.0, 0.999)
    return q / (1.0 - q)


def specific_humidity_from_mixing_ratio(qv: np.ndarray) -> np.ndarray:
    return qv / (1.0 + qv)


def potential_temperature(t: np.ndarray, p: np.ndarray) -> np.ndarray:
    """温度 -> 位温 [K]。"""
    return t * (P0 / p) ** RDOVCP


def density(p: np.ndarray, tv: np.ndarray) -> np.ndarray:
    """湿空气密度 [kg m-3]（用 g/m3 的湿空气状态方程 p = rho Rd Tv）。"""
    return p / (RD * np.maximum(tv, 1.0))


def virtual_temperature(t: np.ndarray, q: np.ndarray) -> np.ndarray:
    """虚拟温度（q 为比湿）。"""
    return t * (1.0 + 0.608 * q)


# ---------------------------------------------------------------------------
# 地表气压：静力下延
# ---------------------------------------------------------------------------
def _gather_columns(field: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """按 idx (ny,nx) 沿第 0 维取值，返回 (ny,nx)。"""
    return np.take_along_axis(field, idx[None, :, :], axis=0)[0]


def surface_pressure(
    phi: np.ndarray,
    t: np.ndarray,
    q: np.ndarray,
    hgt: np.ndarray,
    plev_pa: np.ndarray = PLEV_PA,
    lapse: float = 0.0065,
) -> Tuple[np.ndarray, np.ndarray]:
    """由盘古位势场静力下延到地形高度求地表气压。

    做法：先在每列找出"地形以上最低的那一层" k*，再从该层按固定温度递减率
    (lapse) 向地面外推温度，并做静力积分：

        p_sfc = p_k* * (Tv_sfc / Tv_k*)^(g / (Rd * lapse))

    参数
    ----
    phi : (nlev, ny, nx) 位势 [m2 s-2]
    t   : (nlev, ny, nx) 温度 [K]
    q   : (nlev, ny, nx) 比湿 [kg kg-1]
    hgt : (ny, nx) 地形高度 [m]

    返回
    ----
    p_sfc : (ny, nx)  [Pa]
    k_low : (ny, nx)  使用的源层索引（便于诊断）
    """
    nlev = phi.shape[0]
    z = phi / G
    tv = t * (1.0 + 0.608 * np.clip(q, 0.0, 1.0))

    valid = z > hgt[None, :, :]
    if not valid.any(axis=0).all():
        raise ValueError("存在整列都在地形以下的网格点，无法确定地表气压")

    # 地形以上最低的有效层。PLEV_PA 按气压递减（即高度递增）排列，
    # 因此索引 0 是最底层，最早满足 z > hgt 的那个索引就是"地形以上最低层"。
    idx = np.where(valid, np.arange(nlev)[:, None, None], nlev + 1).min(axis=0)

    zk = _gather_columns(z, idx)
    tvk = _gather_columns(tv, idx)
    pk = plev_pa[idx]

    dz = np.maximum(zk - hgt, 0.0)
    tv_sfc = tvk + lapse * dz
    expon = G / (RD * lapse)
    p_sfc = pk * (tv_sfc / np.maximum(tvk, 1.0)) ** expon

    # 合理性裁剪（地形高度错配/极端层结时的保护）
    p_sfc = np.clip(p_sfc, 40000.0, 109000.0)
    return p_sfc, idx


def reduce_to_msl(p_sfc: np.ndarray, t2: np.ndarray, hgt: np.ndarray,
                  q2: Optional[np.ndarray] = None) -> np.ndarray:
    """把地面气压归算到海平面（用于与盘古 MSL 做一致性校核）。"""
    tv = t2 * (1.0 + 0.608 * (0.0 if q2 is None else np.clip(q2, 0.0, 1.0)))
    return p_sfc * np.exp(G * hgt / (RD * np.maximum(tv, 1.0)))


# ---------------------------------------------------------------------------
# 等压面 -> eta 层插值
# ---------------------------------------------------------------------------
def interp_logp(
    field: np.ndarray,
    p_src: np.ndarray,
    p_tgt: np.ndarray,
    below: str = "edge",
    lapse: float = 0.0065,
) -> np.ndarray:
    """在 log(p) 坐标上把等压面场插值到目标气压。

    参数
    ----
    field : (nlev, ny, nx) 源场
    p_src : (nlev,) 源层气压 [Pa]，可递增或递减
    p_tgt : (ntgt, ny, nx) 目标气压 [Pa]
    below : 目标气压大于最低源层（即地形以下）时的处理方式
            'edge' 取最低层值；'lapse' 温标外推；'zero' 置 0

    返回
    ----
    (ntgt, ny, nx)
    """
    if p_src[0] > p_src[-1]:
        ps = p_src[::-1]
        fs = field[::-1]
    else:
        ps = p_src
        fs = field

    lp = np.log(ps)
    lpt = np.log(np.maximum(p_tgt, 1.0))

    idx = np.searchsorted(lp, lpt)
    # p_tgt 大于最低源层气压 => 落在最低层之下（地形以下）
    below_mask = lpt > lp[-1] + 1e-9
    idx = np.clip(idx, 1, ps.size - 1)

    lo = idx - 1
    hi = idx
    f_lo = np.take_along_axis(fs, lo, axis=0)
    f_hi = np.take_along_axis(fs, hi, axis=0)
    l_lo = lp[lo]
    l_hi = lp[hi]
    w = np.clip((lpt - l_lo) / np.maximum(l_hi - l_lo, 1e-12), 0.0, 1.0)
    out = f_lo + w * (f_hi - f_lo)

    if below_mask.any():
        # 注意：上面把数组反转成了"气压递增"，因此最低层是 fs[-1]/ps[-1]。
        # 早先误用 fs[0]/ps[0]（= 50 hPa 顶层），会把平流层位温填进最低几层，
        # 导致 MCIP/CMAQ 拿到 ~390 K 的近地面位温并在 CAL_CFRAC_3D 崩溃。
        edge = np.broadcast_to(fs[-1], out.shape)
        if below == "zero":
            fill = np.zeros_like(out)
        elif below == "lapse":
            # 以最低源层为基准做温标外推：T(p) = T_bottom * (p / p_bottom)^(Rd*lapse/g)
            ratio = (p_tgt / ps[-1]) ** (RD * lapse / G)
            fill = fs[-1] * ratio
        else:
            fill = edge
        out = np.where(below_mask, fill, out)
    return out


def to_u_stag(field: np.ndarray) -> np.ndarray:
    """质量点场 -> U 交点（west_east_stag）。"""
    out = np.empty(field.shape[:-1] + (field.shape[-1] + 1,), dtype=np.float64)
    out[..., 1:-1] = 0.5 * (field[..., :-1] + field[..., 1:])
    out[..., 0] = field[..., 0]
    out[..., -1] = field[..., -1]
    return out


def to_v_stag(field: np.ndarray) -> np.ndarray:
    """质量点场 -> V 交点（south_north_stag）。"""
    out = np.empty(
        field.shape[:-2] + (field.shape[-2] + 1, field.shape[-1]), dtype=np.float64
    )
    out[..., 1:-1, :] = 0.5 * (field[..., :-1, :] + field[..., 1:, :])
    out[..., 0, :] = field[..., 0, :]
    out[..., -1, :] = field[..., -1, :]
    return out


# ---------------------------------------------------------------------------
# eta 坐标与位势
# ---------------------------------------------------------------------------
def build_eta(psfc: np.ndarray, znw: np.ndarray, znu: np.ndarray,
              p_top: float) -> Dict[str, np.ndarray]:
    """构造地形跟随 eta 坐标下的气压场。

    采用"无扰动"分裂：MU = 0，MUB = PSFC - P_TOP，从而
        PB(k) = P_TOP + MUB * ZNU(k)，P = 0，P + PB 即质量层总气压。
    MCIP 读取的正是 P + PB，因此该写法与 WRF 完全等价。
    """
    mub = psfc - p_top
    pb = p_top + mub[None, :, :] * znu[:, None, None]
    p_mid = pb.copy()
    p_face = p_top + mub[None, :, :] * znw[:, None, None]
    return {
        "mu": np.zeros_like(psfc),
        "mub": mub,
        "p": np.zeros_like(pb),
        "pb": pb,
        "p_mid": p_mid,
        "p_face": p_face,
    }


def geopotential_faces(p_face: np.ndarray, tv_mid: np.ndarray,
                       hgt: np.ndarray) -> np.ndarray:
    """由面气压与整层虚拟温度静力积分位势（bottom_top_stag 层）。"""
    nzp = p_face.shape[0]
    phi = np.empty_like(p_face)
    phi[0] = G * hgt
    lnp = np.log(p_face)
    for k in range(nzp - 1):
        phi[k + 1] = phi[k] - RD * tv_mid[k] * (lnp[k + 1] - lnp[k])
    return phi


# ---------------------------------------------------------------------------
# 连续方程诊断垂直速度
# ---------------------------------------------------------------------------
def divergence(u_stag: np.ndarray, v_stag: np.ndarray, mapfac_m: np.ndarray,
               mapfac_u: np.ndarray, mapfac_v: np.ndarray,
               dx: float, dy: float) -> np.ndarray:
    """质量点上的水平散度 [s-1]（含 map factor）。

    u_stag : (nz, ny, nx+1)   V 分量对应 (nz, ny+1, nx)
    """
    ufac = u_stag / mapfac_u[None, :, :]
    vfac = v_stag / mapfac_v[None, :, :]
    dudx = (ufac[:, :, 1:] - ufac[:, :, :-1]) / dx
    dvdy = (vfac[:, 1:, :] - vfac[:, :-1, :]) / dy
    return mapfac_m[None, :, :] ** 2 * (dudx + dvdy)


def diagnose_omega(
    div: np.ndarray,
    p_face: np.ndarray,
    psfc: np.ndarray,
    dpsfc_dt: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """由水平散度沿柱积分求 omega [Pa s-1]。

    连续方程在气压坐标下为 ``d(omega)/dp = -div``，等价于

        omega(p) = omega_sfc + ∫_p^{p_s} div dp'

    即自地面向上逐层累加 ``div * (p_face(k) - p_face(k+1))``（层厚为正）。
    低层辐合（div < 0）会给出一致上升运动（omega < 0）。

    最后施加"随气压线性分布"的质量订正，使模式顶 omega 精确回到 0，
    同时保持地面值与地表气压倾向一致。

    返回 (omega_face, omega_mid)。
    """
    nz = div.shape[0]
    width = p_face[:-1] - p_face[1:]                     # (nz, ny, nx) 正值
    omega_f = np.empty((nz + 1,) + div.shape[1:], dtype=np.float64)
    omega_f[0] = dpsfc_dt
    for k in range(nz):
        omega_f[k + 1] = omega_f[k] + div[k] * width[k]

    # 质量订正：地面因子为 0（不改变边界值），模式顶因子为 1
    p_top = p_face[-1]
    factor = (psfc[None, :, :] - p_face) / np.maximum(
        (psfc - p_top)[None, :, :], 1.0
    )
    omega_f = omega_f - omega_f[-1][None, :, :] * factor

    omega_mid = 0.5 * (omega_f[:-1] + omega_f[1:])
    return omega_f, omega_mid


def vertical_velocity(omega_f: np.ndarray, p_face: np.ndarray,
                      tv_face: np.ndarray) -> np.ndarray:
    """w = -omega / (rho * g)，rho = p / (Rd * Tv)。"""
    rho = p_face / (RD * np.maximum(tv_face, 1.0))
    return -omega_f / (rho * G)


# ---------------------------------------------------------------------------
# 自检：用模板自身的温湿场复现其位势高度
# ---------------------------------------------------------------------------
def verify_vertical_scheme(grid) -> str:
    """在模板文件上验证本节实现，返回文字报告。"""
    import netCDF4 as nc

    ds = nc.Dataset(grid.path)
    it = 0
    mub = np.asarray(ds.variables["MUB"][it], dtype=np.float64)
    mu = np.asarray(ds.variables["MU"][it], dtype=np.float64)
    p = np.asarray(ds.variables["P"][it], dtype=np.float64)
    pb = np.asarray(ds.variables["PB"][it], dtype=np.float64)
    ph = np.asarray(ds.variables["PH"][it], dtype=np.float64)
    phb = np.asarray(ds.variables["PHB"][it], dtype=np.float64)
    t = np.asarray(ds.variables["T"][it], dtype=np.float64)
    qv = np.asarray(ds.variables["QVAPOR"][it], dtype=np.float64)
    qv = specific_humidity_from_mixing_ratio(qv)
    ds.close()

    eta = build_eta(
        psfc=grid.p_top + mub + mu,
        znw=grid.znw,
        znu=grid.znu,
        p_top=grid.p_top,
    )
    theta = t + 300.0
    ta = theta * (eta["p_mid"] / P0) ** RDOVCP
    tv = ta * (1.0 + 0.608 * qv)
    phi = geopotential_faces(eta["p_face"], tv, grid.hgt)

    zref = (phb + ph) / G
    zrec = phi / G
    err = zrec - zref
    thickness = float((zref[-1] - zref[0]).mean())
    return (
        "垂直方案自检（模板 it=0）：\n"
        "  面层高度最大偏差 %.2f m，顶层平均偏差 %.2f m，柱深 %.0f m（相对 %.2e）\n"
        "  PB 重建校验：P_TOP+MUB*ZNU 与模板 PB 最大偏差 %.4f Pa"
        % (
            np.abs(err).max(),
            err[-1].mean(),
            thickness,
            np.abs(err).max() / thickness,
            np.abs(grid.p_top + mub[None, :, :] * grid.znu[:, None, None] - pb).max(),
        )
    )

# ==========================================================================
# 模块：cloud_precip.py
# ==========================================================================
# 云水/雨水诊断与水汽通量辐合降水估计。
#
# 盘古输出没有任何水凝物与降水，MCIP 又强制要求 QCLOUD/QRAIN/RAINC/RAINNC，
# 因此这里用最简的诊断方案：
#
# * QCLOUD：RH 阈值方案 —— 相对湿度超过临界值后把超额水汽凝结为云水。
# * QRAIN ：由云水按经验阈值自动转化（Kessler 型）。
# * 降水   ：整层水汽通量辐合 × 降水效率，累积为 RAINC/RAINNC（单位 mm）。





E0 = 6.112          # hPa
ALPHA_BOLTON = 17.67
BETA_BOLTON = 29.65


def saturation_vapor_pressure(t: np.ndarray) -> np.ndarray:
    """Bolton (1980) 饱和水汽压 [hPa]，t 为温度 [K]。"""
    return E0 * np.exp(ALPHA_BOLTON * (t - 273.15) / (t - BETA_BOLTON))


# ---------------------------------------------------------------------------
# v3.1 新增：冰面饱和水汽压与自动切换
# ---------------------------------------------------------------------------
def saturation_vapor_pressure_ice(t: np.ndarray) -> np.ndarray:
    """Tetens 冰面饱和水汽压 [hPa]，t 为温度 [K]（适用 t <= 273.15 K）。

    与 Bolton 液面公式配对使用：
        液面: 6.112·exp[17.67·(T−273.15)/(T−29.65)]
        冰面: 6.112·exp[22.46·(T−273.15)/(T−272.62)]
    冰面 e_s 比液面低（−20℃ 约低 20%），是冷层 RH 偏低的根源。
    本修复中 Q2 默认不用它（2 m 空气的相对湿度通常相对液面定义），
    但保留给冷层 RH/云量诊断用。
    """
    return E0 * np.exp(22.46 * (t - 273.15) / (t - 272.62))


def saturation_vapor_pressure_auto(t: np.ndarray,
                                   use_ice: bool = False) -> np.ndarray:
    """按温度自动选择液面/冰面饱和水汽压 [hPa]。"""
    es_l = saturation_vapor_pressure(t)
    if not use_ice:
        return es_l
    es_i = saturation_vapor_pressure_ice(t)
    return np.where(t < 273.15, es_i, es_l)


def vapor_pressure(p: np.ndarray, q_specific: np.ndarray) -> np.ndarray:
    """由比湿反算水汽压 [hPa]。"""
    q = np.clip(q_specific, 0.0, 0.999)
    return q * p / (EPSILON + (1.0 - EPSILON) * q) / 100.0


def relative_humidity(p: np.ndarray, t: np.ndarray, q_specific: np.ndarray) -> np.ndarray:
    """相对湿度（0~1.2，允许轻微过饱和）。"""
    es = np.maximum(saturation_vapor_pressure(t), 1e-6)
    return np.clip(vapor_pressure(p, q_specific) / es, 0.0, 1.2)


def saturation_specific_humidity(t: np.ndarray, p: np.ndarray) -> np.ndarray:
    """饱和比湿 [kg/kg]。"""
    es = saturation_vapor_pressure(t) * 100.0
    return EPSILON * es / np.maximum(p - (1.0 - EPSILON) * es, 1.0)


def saturation_mixing_ratio(t: np.ndarray, p: np.ndarray) -> np.ndarray:
    """饱和混合比 [kg/kg]（WRF 的 QVAPOR/Q2 用混合比）。"""
    es = saturation_vapor_pressure(t) * 100.0
    return EPSILON * es / np.maximum(p - es, 1.0)


def _rh_crit(p: np.ndarray, prm: Params, t: np.ndarray = None) -> np.ndarray:
    """临界相对湿度随高度线性增长（低层 rhc_base -> 高空 rhc_top）。

    v3 新增：温度低于 0℃ 时按冰面饱和下调 rhc（最多 ice_rh_reduction），
    否则本方案在冷层几乎不产云，QICE 恒为 0（v2 实测 QI 域均 7.5e-10，
    基准 1.1e-6）。
    """
    frac = np.clip((p - 30000.0) / (100000.0 - 30000.0), 0.0, 1.0)
    rhc = prm.qc_rh_crit_top + (prm.qc_rh_crit_base - prm.qc_rh_crit_top) * frac
    if t is not None:
        cold = np.clip((273.15 - t) / max(prm.ice_rh_dt, 1e-6), 0.0, 1.0)
        rhc = rhc - prm.ice_rh_reduction * cold
    return np.clip(rhc, 0.3, 0.99)


def cloud_fraction(p: np.ndarray, rh: np.ndarray, prm: Params,
                   t: np.ndarray = None) -> np.ndarray:
    """由相对湿度诊断次网格云量 [0,1]（v3）。

    阈值用随高度变化、且随温度（冰面）下调的 rhc；
    对 (rh-rhc) 取 cf_power 次幂，便于统一调节云量与云水。
    """
    rhc = _rh_crit(p, prm, t)
    cf = np.clip((rh - rhc) / np.maximum(1.0 - rhc, 1e-3), 0.0, 1.0)
    return np.clip(cf ** prm.cf_power, 0.0, 1.0)


def cloud_water(p: np.ndarray, t: np.ndarray, q_specific: np.ndarray,
                prm: Params, cf: np.ndarray = None) -> np.ndarray:
    """诊断云水混合比 [kg/kg]（v2）。

    网格平均云水 = 次网格云量^qc_cf_power × 云内凝结量参考值。

    * v1 用 ``qs*(rh-rhc)/(1-rhc)``，等价于把整格饱和水汽都当云水
      （量级 1e-2，被 qc_max=3e-3 截断），域均 3e-4 kg/kg；
      而 WRF 实况域均约 3e-6、云内约 1.5e-4，云光学厚度约 7。
    * v2 直接用「云内凝结量」的经验量级（qc_incloud_ref，默认 0.2 g/m3）
      乘云量的高次幂（水凝物在云区集中），域均落在 1e-6~1e-5、云内约 1e-4，
      使 CMAQ 的云光学厚度回到物理区间（o(1~10)），不再压死光解。
    """
    rh = relative_humidity(p, t, q_specific)
    if cf is None:
        cf = cloud_fraction(p, rh, prm, t)
    shape = 0.6 + 0.4 * np.clip((p - prm.qc_p_top_cut) / 60000.0, 0.0, 1.0)
    qc = (cf ** prm.qc_cf_power) * prm.qc_incloud_ref * shape
    qc = np.where(p < prm.qc_p_top_cut, 0.0, qc)
    qc = np.where(qc < prm.qc_min, 0.0, qc)
    return np.clip(qc, 0.0, prm.qc_max)


def ice_water(qc: np.ndarray, t: np.ndarray,
              prm: Params) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """按温度把云水分为液水/冰/雪/霰，返回 (qc_liquid, qice, qsnow, qgraup)。

    MCIP 要求 QICE 与 QSNOW 同时存在（nqspecies 不能为 3），有无 QGRAUP 均可。
    写成 5 类可让 CMAQ 用冰相云光学与温度加权（CAL_CFRAC_3D 的 WEIGHT）。
    """
    w = np.clip((prm.ice_t_warm - t) / max(prm.ice_t_warm - prm.ice_t_cold, 1e-6), 0.0, 1.0)
    q_ice_tot = qc * w
    qsnow = q_ice_tot * prm.ice_snow_frac
    qgraup = q_ice_tot * prm.graupel_frac
    qice = q_ice_tot - qsnow - qgraup
    return qc * (1.0 - w), qice, qsnow, qgraup


def rain_water(qc: np.ndarray, prm: Params) -> np.ndarray:
    """由液水云水自动转化诊断雨水混合比 [kg/kg]。"""
    qr = prm.rain_autoconv_coef * np.maximum(qc - prm.rain_autoconv_thresh, 0.0)
    return np.clip(qr, 0.0, prm.rain_max)


def cloud_optical_depth(qc: np.ndarray, qice: np.ndarray, dz: np.ndarray,
                        air_density: np.ndarray, prm: Params) -> np.ndarray:
    """层云光学厚度（与 CMAQ CLOUD_OPTICS 的 ext=3LWC/(2·rho_w·re) 一致）。

    τ_k = 1.5 · (q_c·ρ·Δz) / (ρ_w·r_eff)
    """
    rho_w = 1000.0                                    # kg m-3
    tau = 1.5 * (qc * air_density * dz) / (rho_w * prm.reff_liquid)
    tau = tau + 1.5 * (qice * air_density * dz) / (rho_w * prm.reff_ice)
    return np.maximum(tau, 0.0)


def column_cloud_fraction(cf: np.ndarray, p_mid: np.ndarray) -> np.ndarray:
    """整层云量：1 - Π(1 - cf_k)（随机重叠假设）。"""
    return 1.0 - np.prod(1.0 - np.clip(cf, 0.0, 1.0), axis=0)


# ---------------------------------------------------------------------------
# 降水：整层水汽通量辐合
# ---------------------------------------------------------------------------
def moisture_divergence(u_stag: np.ndarray, v_stag: np.ndarray, q_mid: np.ndarray,
                        mapfac_m: np.ndarray, mapfac_u: np.ndarray,
                        mapfac_v: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """质量点上 ∇·(qV) [s-1]（q 为比湿）。"""
    q = np.clip(q_mid, 0.0, 0.2)
    q_u = to_u_stag(q)                    # (nz, ny, nx+1)
    q_v = to_v_stag(q)                    # (nz, ny+1, nx)
    fu = q_u * u_stag / mapfac_u[None, :, :]
    fv = q_v * v_stag / mapfac_v[None, :, :]
    dudx = (fu[:, :, 1:] - fu[:, :, :-1]) / dx         # (nz, ny, nx)
    dvdy = (fv[:, 1:, :] - fv[:, :-1, :]) / dy         # (nz, ny, nx)
    return mapfac_m[None, :, :] ** 2 * (dudx + dvdy)


def precipitation_rate(u_stag: np.ndarray, v_stag: np.ndarray, q_mid: np.ndarray,
                       p_face: np.ndarray, mapfac_m: np.ndarray, mapfac_u: np.ndarray,
                       mapfac_v: np.ndarray, dx: float, dy: float,
                       prm: Params, rh: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
    """由水汽通量辐合估计降水（v6）。

    返回 (rate_mm_per_hour, moisture_convergence)，其中

        MFC = -(1/g) * Σ_k ∇·(qV)_k * W_k        [kg m-2 s-1]
        W_k = p_face(k) − p_face(k+1) > 0

    辐合时 ∇·(qV) < 0，故 MFC > 0（整层水汽收入）。

    v6【F4】：v5 对任何 MFC>0 的格点都按常数 precip_efficiency 直接出水，
    缺少湿度判据，水汽通量辐合的数值噪声于是造成"全域均匀毛毛雨"
    （10/24 日累计 1.822 mm vs 基准 0.531 mm，逐小时恒在 0.04~0.09 mm/h）。
    这里加两道闸门：

    1) 柱相对湿度 gate：按水汽权重求整层相对湿度 ``rh_col``，低于
       ``precip_rh_gate[0]`` 完全不产水，到 ``[1]`` 才完全放开；
    2) 毛毛雨截断：``rate < precip_drizzle_cut`` 直接置零。
    """
    div_qv = moisture_divergence(
        u_stag, v_stag, q_mid, mapfac_m, mapfac_u, mapfac_v, dx, dy
    )
    width = p_face[:-1] - p_face[1:]                  # (nz, ny, nx), 正值
    mfc = -(div_qv * width).sum(axis=0) / G    # kg m-2 s-1
    rate = prm.precip_efficiency * np.maximum(mfc, 0.0) * 3600.0  # mm h-1

    if rh is not None:
        # 水汽加权的柱相对湿度（只关心含水量大的层次）
        wcol = width * q_mid
        denom = np.maximum(wcol.sum(axis=0), 1e-12)
        rh_col = (np.clip(rh, 0.0, 1.5) * wcol).sum(axis=0) / denom
        lo, hi = prm.precip_rh_gate
        gate = np.clip((rh_col - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
        rate = rate * gate

    rate = np.where(rate < prm.precip_drizzle_cut, 0.0, rate)
    return np.clip(rate, 0.0, prm.precip_cap), mfc

# ==========================================================================
# 模块：radiation.py
# ==========================================================================
# 地表短波/长波辐射诊断。
#
# MCIP 必需 SWDOWN（向下短波）与 GLW（向下长波），盘古均无，故：
#
# * SWDOWN：由太阳天顶角算晴空辐照，再按诊断云量衰减。
# * GLW   ：Brutsaert 有效发射率（依赖近地面水汽压与气温）乘以 Stefan-Boltzmann，
#           再按云量做增强。






def solar_declination(dt: datetime) -> float:
    """太阳赤纬 [rad]（Cooper 1969 近似）。"""
    doy = dt.timetuple().tm_yday
    return np.radians(23.44) * np.sin(2.0 * np.pi * (284.0 + doy) / 365.0)


def equation_of_time(dt: datetime) -> float:
    """时差 [min]（Spencer 1971 近似）。"""
    doy = dt.timetuple().tm_yday
    b = 2.0 * np.pi * (doy - 1) / 365.0
    return 229.18 * (
        0.000075
        + 0.001868 * np.cos(b)
        - 0.032077 * np.sin(b)
        - 0.014615 * np.cos(2 * b)
        - 0.040849 * np.sin(2 * b)
    )


def cos_solar_zenith(dt: datetime, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """太阳天顶角余弦（dt 为 UTC 时刻）。"""
    dec = solar_declination(dt)
    eot = equation_of_time(dt) / 60.0                      # [h]
    utc_hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    solar_time = utc_hour + lon / 15.0 + eot               # 真太阳时
    hour_angle = np.radians((solar_time - 12.0) * 15.0)
    latr = np.radians(lat)
    cosz = np.sin(latr) * np.sin(dec) + np.cos(latr) * np.cos(dec) * np.cos(hour_angle)
    return np.clip(cosz, -1.0, 1.0)


def boundary_layer_rh(rh: np.ndarray, p_mid: np.ndarray,
                      prm: Params) -> np.ndarray:
    """边界层相对湿度（气压加权均值，p > prm.aer_bl_top）[0~1.2]。

    v7【F7-1】用作霾湿增长的代理量：边界层内湿度越高，吸湿增长越强、
    气溶胶消光越大；高 RH 同时与静稳/污染累积高度相关，故可粗代霾负荷。
    rh/p_mid: (nz, ny, nx) -> (ny, nx)。
    """
    mask = p_mid > prm.aer_bl_top
    w = np.where(mask, p_mid, 0.0)
    num = np.where(mask, rh * w, 0.0).sum(axis=0)
    den = w.sum(axis=0)
    out = np.where(den > 1e-6, num / np.maximum(den, 1e-6), rh[0])
    return np.clip(out, 0.0, 1.2)


def aerosol_optical_depth(rh_bl: np.ndarray, prm: Params) -> np.ndarray:
    """低层湿度驱动的气溶胶光学厚度（霾湿增长）[-]。

    tau_aer = aer_tau_max * clip((rh_bl-aer_rh_thresh)
                                 /(aer_rh_max-aer_rh_thresh),0,1)^aer_power

    线性段之外截断：低于阈值为 0（晴好日不受影响，保住 v6 的晴空短波标定），
    高于 aer_rh_max 取满值 aer_tau_max。
    """
    if not prm.aer_use:
        return np.zeros_like(rh_bl)
    span = max(prm.aer_rh_max - prm.aer_rh_thresh, 1e-6)
    frac = np.clip((rh_bl - prm.aer_rh_thresh) / span, 0.0, 1.0)
    return np.clip(prm.aer_tau_max * frac ** prm.aer_power, 0.0, prm.aer_tau_max_cap)


def shortwave_down(dt: datetime, lat: np.ndarray, lon: np.ndarray,
                   cld_frac: np.ndarray, prm: Params,
                   tau_cloud: np.ndarray = None,
                   tau_aer: np.ndarray = None) -> np.ndarray:
    """向下短波辐射 [W m-2]（v6）。

    有云光学厚度时按 Beer 定律做云衰减（与 CMAQ 的光解衰减用同一套云水），
    否则退化为「按云量线性衰减」的简化式。

    v6【F1】：v3 引入的 ``tau_in = tau_col / cld`` 把**网格平均**柱光学厚度
    放大成"云内光学厚度"，放大倍数 1/cld（cld=0.1 时 ×10、cld=0.03 时 ×33）。
    但 CMAQ 的 ``ext = 3·LWC/(2·rho_w·re)`` 用的本就是网格平均 LWC，因此
    ``tau_col`` 已经是与光解自洽的网格平均量，不该再被云量除。
    该除法造成的结果是 V5 的云量/云水/光学厚度全面少于 WRF
    （CLDTOT 0.675、QCLOUD 0.437、TAU 0.738），SWDOWN 反而低 18.5%
    —— 两者方向相反，只能是衰减公式的问题。

    v6 只对 tau_col 做斜程（1/cosz）放大，并保留
    ``atten = (1-cld) + cld·exp(-tau_eff)`` 的云量加权结构：
    破碎云中无云的那部分天空仍按晴空透过。
    """
    cosz = np.maximum(cos_solar_zenith(dt, lat, lon), 0.0)
    clear = SOLAR_CONST * cosz * prm.sw_clear_transmissivity
    cld = np.clip(cld_frac, 0.0, 1.0)
    slant = 1.0 / np.maximum(cosz, prm.sw_slant_floor)
    if tau_cloud is not None and prm.sw_use_tau:
        tau_eff = np.clip(tau_cloud * slant, 0.0, prm.sw_tau_eff_max)
        atten_cld = (1.0 - cld) + cld * np.exp(-tau_eff)
    else:
        atten_cld = 1.0 - prm.sw_cloud_albedo * cld
    # v7【F7-1】气溶胶衰减：霾在边界层内混合均匀 -> 对**整片天空**衰减，
    # 与只衰减其覆盖份额的云不同，故与云衰减**相乘**而非相加。
    atten_aer = 1.0
    if tau_aer is not None and prm.aer_use:
        tau_a = np.clip(tau_aer * slant, 0.0, prm.aer_tau_max_cap)
        atten_aer = np.exp(-tau_a)
    return np.maximum(clear * atten_cld * atten_aer, 0.0)


def effective_emissivity(t2: np.ndarray, e_hpa: np.ndarray,
                         prm: Params) -> np.ndarray:
    """Brutsaert (1975) 晴空有效发射率。"""
    eps = 1.24 * (np.maximum(e_hpa, 0.01) / np.maximum(t2, 1.0)) ** (1.0 / 7.0)
    return np.clip(eps, prm.lw_emiss_floor, 1.0)


def longwave_down(t2: np.ndarray, e_hpa: np.ndarray, cld_frac: np.ndarray,
                  prm: Params) -> np.ndarray:
    """向下长波辐射 [W m-2]。"""
    eps_clear = effective_emissivity(t2, e_hpa, prm)
    cld = np.clip(cld_frac, 0.0, 1.0)
    eps_eff = eps_clear + (1.0 - eps_clear) * cld
    return np.maximum(eps_eff * STEFAN_BOLTZMANN * t2 ** 4, 0.0)


def hour_to_datetime(start: datetime, hour_index: int) -> datetime:
    return start + timedelta(hours=int(hour_index))

# ==========================================================================
# 模块：land.py
# ==========================================================================
# 陆面量诊断。
#
# 盘古只有 2 m 气温与 10 m 风，没有陆面模式输出。这里按"查表 + 气候常值"补齐
# MCIP 需要的陆面量：
#
# * TSK / ALBEDO / SNOWC / SEAICE：由 2 m 气温与土地利用类型诊断
# * SMOIS / TSLB / ISLTYP：土壤湿度取气候常值（模板时段平均），土壤温度表层跟随 TSK，
#   深层取气候常值
# * ZNT / LAI / VEGFRA / CANWAT：按 USGS 24 类土地利用查表






def box_smooth(field: np.ndarray, n: int = 9) -> np.ndarray:
    """n x n 的均匀滑动平均（用于给水面温度去日变化）。"""
    if n <= 1:
        return field
    k = n // 2
    padded = np.pad(field, k, mode="edge")
    out = np.zeros_like(field)
    for i in range(n):
        for j in range(n):
            out += padded[i:i + field.shape[0], j:j + field.shape[1]]
    return out / float(n * n)


def surface_temperature(t2: np.ndarray, landmask: np.ndarray, prm: Params) -> np.ndarray:
    """地表温度 [K]：陆地为 2 m 气温；水面用平滑后的场（削弱虚假日变化）。"""
    smoothed = box_smooth(t2, 9)
    tsk = np.where(landmask > 0.5, t2, smoothed)
    return np.clip(tsk, 200.0, 340.0)


def snow_cover(tsk: np.ndarray, prm: Params) -> np.ndarray:
    """积雪覆盖度（0/1）。"""
    return (tsk < prm.snowc_t_thresh).astype(np.float64)


def blend_land_water(tsk_land: np.ndarray, t2: np.ndarray,
                     landmask: np.ndarray) -> np.ndarray:
    """陆地点用能量平衡诊断的 TSK，水点用平滑后的 2 m 气温。

    水面热容量极大，不存在陆地那种日间"皮层升温"；直接套用能量平衡会凭空
    造出 5~10 K 的虚假升温，导致潜热通量失真。
    """
    return np.where(landmask > 0.5, tsk_land, box_smooth(t2, 9))


def skin_temperature(t2: np.ndarray, q2: np.ndarray, u10: np.ndarray,
                     v10: np.ndarray, psfc: np.ndarray, swdown: np.ndarray,
                     glw: np.ndarray, albedo_field: np.ndarray, z0: np.ndarray,
                     landmask: np.ndarray, beta: np.ndarray,
                     prm: Params) -> np.ndarray:
    """由线性化地表能量平衡诊断皮层温度 TSK [K]。

    盘古没有陆面模式，若直接取 ``TSK = T2M`` 则地气温差为零、感热通量恒为 0，
    会连带使 CMAQ 的 w* (对流速度尺度) 失去意义。这里改用一次线性化的
    地表能量平衡求解 TSK 相对 T2 的偏差 x：

        (1-α)·S↓ + ε·L↓ - ε·σ·T2⁴ - 4ε·σ·T2³·x
            = ρ·cp·CH·U·x + ρ·Lv·CH·U·β·(dq_sat/dT)·x

    其中 CH 取中性块体输送系数、β 为蒸发效率（水面为 1）。
    解的物理量级：晴天正午陆地约 +3~8 K，夜间约 -1~-3 K。

    v6【F3】：β 改由 evaporation_efficiency（阻抗法）传入，与 surface_fluxes
    共用同一个 β，避免"能量平衡的 β"与"通量的 β"不一致。
    """
    eps = prm.emissivity
    t2v = t2 * (1.0 + 0.608 * np.clip(q2 / (1.0 + q2), 0.0, 0.1))
    rho = psfc / (RD * np.maximum(t2v, 1.0))
    speed = np.maximum(np.sqrt(u10 ** 2 + v10 ** 2), 0.5)
    lnz0 = np.log(prm.meas_height / np.clip(z0, 1.0e-4, 5.0))
    ch = KARMAN ** 2 / np.maximum(lnz0 ** 2, 1.0)

    q_sat = saturation_mixing_ratio(t2, psfc)
    dqsdt = q_sat * LV / (RV * np.maximum(t2, 1.0) ** 2)

    rnet = (
        (1.0 - albedo_field) * swdown
        + eps * glw
        - eps * STEFAN_BOLTZMANN * t2 ** 4
    )
    denom = (
        4.0 * eps * STEFAN_BOLTZMANN * t2 ** 3
        + rho * speed * (CP * ch + LV * ch * beta * dqsdt)
    )
    delta = np.clip(rnet / np.maximum(denom, 1.0), prm.tsk_delta_clip[0],
                    prm.tsk_delta_clip[1])
    return t2 + delta


def albedo(lu_index: np.ndarray, snowc: np.ndarray,
           prm: Params) -> np.ndarray:
    """短波反照率（土地利用查表 + 积雪修正）。"""
    table = table_to_array(ALBEDO_TABLE)
    base = table[np.clip(lu_index.astype(np.intp), 0, table.size - 1)]
    return np.where(snowc > 0.5, prm.albedo_snow, base)


def sea_ice(tsk: np.ndarray, landmask: np.ndarray, prm: Params) -> np.ndarray:
    """海冰覆盖度（0/1，仅水面且地表温度低于阈值时）。"""
    return ((landmask < 0.5) & (tsk < prm.snowc_t_thresh)).astype(np.float64)


def roughness(lu_index: np.ndarray) -> np.ndarray:
    """动力学粗糙度长度 [m]。"""
    table = table_to_array(Z0_TABLE)
    return table[np.clip(lu_index.astype(np.intp), 0, table.size - 1)]


def leaf_area_index(lu_index: np.ndarray) -> np.ndarray:
    table = table_to_array(LAI_TABLE)
    return table[np.clip(lu_index.astype(np.intp), 0, table.size - 1)]


def vegetation_fraction(lu_index: np.ndarray) -> np.ndarray:
    """植被覆盖度 [%]（WRF 的 VEGFRA 为百分数）。"""
    table = table_to_array(VEGFRA_TABLE)
    return table[np.clip(lu_index.astype(np.intp), 0, table.size - 1)]


def canopy_water(shape, prm: Params) -> np.ndarray:
    """冠层含水量 [kg m-2]，无陆面模式时取常数。"""
    return np.full(shape, prm.canopy_wetness, dtype=np.float64)


def soil_moisture(grid, like: np.ndarray) -> np.ndarray:
    """土壤体积含水量 [m3 m-3]，层内取模板时段平均的气候常值。

    like 仅用于确定水平形状。
    """
    ns = grid.ns
    out = np.empty((ns,) + like.shape, dtype=np.float64)
    for k in range(ns):
        out[k] = grid.soil_moisture_mean[k]
    return out


def soil_temperature(grid, tsk: np.ndarray) -> np.ndarray:
    """土壤温度 [K]：表层跟随 TSK，深层取气候常值，水面直接用 TSK。"""
    ns = grid.ns
    out = np.empty((ns,) + tsk.shape, dtype=np.float64)
    out[0] = tsk
    for k in range(1, ns):
        out[k] = grid.soil_temp_mean[k]
    return out


def soil_type(grid) -> np.ndarray:
    """土壤类型（静态，取模板）。"""
    return grid.isltyp.astype(np.float64)


def two_meter_mixing_ratio(psfc: np.ndarray, t2: np.ndarray,
                           p_low: np.ndarray, t_low: np.ndarray,
                           q_low: np.ndarray,
                           use_ice: bool = False,
                           prm: "Params" = None) -> np.ndarray:
    """诊断 2 m 混合比 [kg/kg]（v3.2：e 守恒 + 稳定边界层近地增强）。

    旧版（v3）``Q2 = RH(最低层) × q_sat(T2, PSFC)`` 有三个压低高值的来源：

    1) **最低层 RH ≠ 2 m RH**。最低质量层离地几十米。清晨辐射逆温时，
       2 m 处在逆温层内接近饱和（RH 0.95~1.0），而最低层在逆温顶以上
       更干（RH 0.7~0.85）。用最低层 RH 代 2 m RH，清晨峰值低 15~25%。
    2) **``q_sat(T2)`` 是硬上限**。若盘古 T2 在清晨偏低 1~2 K（AI 模型
       对逆温层结平滑），``q_s(T2)`` 低 6~13%，Q2 被这个天花板压住。
    3) **``RH × q_s`` 近似偏低 1~3%**。精确式 ``qv = εe/(p−e)`` 的修正
       因子 ``(p−e_s)/(p−RH·e_s)`` > 1。

    v3.1 改为「近地层水汽压守恒」+ 精确混合比公式：

        e_low = RH(最低层) × e_s,l(T_low)       最低层水汽压 [Pa]
        e_2m  = min(e_low, 0.99·e_s(T2))        2 m 饱和（留 1% 过饱和余量）
        Q2    = ε·e_2m / (p_sfc − e_2m)         精确混合比

    v3.2 在 v3.1 基础上再补一块：稳定边界层里，辐射逆温使近地面因辐射冷却
    产生露水/辐射雾，2 m 处水汽堆积，RH 高于最低模式层。用「逆温强度 →
    向饱和目标靠拢」的参数化补足这一段：

        inv   = clip((T_low − T2) / q2_inv_scale, 0, 1)
        rh_2m = e_2m / e_s(T2)
        rh_2m ← rh_2m + q2_inv_weight · inv · (q2_inv_rh_target − rh_2m)
        rh_2m ← clip(rh_2m, 0, 0.99)            留 1% 过饱和余量
        e_2m  = rh_2m · e_s(T2)

    白天（T_low ≤ T2）inv = 0，完全退回 v3.1 行为；夜间逆温 3 K 时把
    2 m RH 向 0.95 靠拢 60%（默认）。这样：高湿（清晨）时段 +10~25%，
    低湿（白天）时段 +0%。

    参数
    ----
    psfc  : (ny, nx) 地表气压 [Pa]
    t2    : (ny, nx) 2 m 气温 [K]
    p_low : (ny, nx) 最低质量层气压 [Pa]
    t_low : (ny, nx) 最低质量层温度 [K]
    q_low : (ny, nx) 最低质量层比湿 [kg/kg]
    use_ice : 是否在 T<0℃ 时用冰面饱和做 2 m 上限。2 m 空气的相对湿度
              通常相对液面定义（空气中的水汽压可超过冰面饱和），默认 False。
    prm   : Params 实例，提供 v3.2 的三个 q2_inv_* 系数；None 时跳过 v3.2 增强
              （即退回 v3.1）。

    返回
    ----
    (ny, nx) 2 m 混合比 [kg/kg]
    """
    # 最低层水汽压 [Pa]：RH(液面) × e_s(液面)，与"面"无关（e 是物理量）
    rh_low = relative_humidity(p_low, t_low, q_low)      # 0~1.2
    es_low = saturation_vapor_pressure(t_low) * 100.0    # hPa -> Pa
    e_low = np.clip(rh_low, 0.0, 1.0) * es_low

    # 近地层水汽压守恒 -> 2 m 水汽压 = 最低层水汽压
    # 上限：2 m 饱和水汽压（留 1% 过饱和余量，避免除零）
    es_2m = saturation_vapor_pressure_auto(t2, use_ice=use_ice) * 100.0
    e_2m = np.minimum(e_low, 0.99 * es_2m)

    # v3.2：稳定边界层内近地面水汽增强
    # ---------------------------------------------------------------
    # 辐射逆温中（T_low > T2），近地面因辐射冷却导致水汽凝结/堆积，
    # 2 m 处的 RH 明显高于最低模式层。用"按逆温强度向饱和目标靠拢"
    # 近似这一段物理过程；白天（T_low <= T2）权重为 0，完全退回 v3.1。
    if prm is not None:
        inv = np.clip((t_low - t2) / max(prm.q2_inv_scale, 1e-6), 0.0, 1.0)
        rh_2m = e_2m / np.maximum(es_2m, 1e-6)
        rh_enh = rh_2m + prm.q2_inv_weight * inv * (prm.q2_inv_rh_target - rh_2m)
        rh_enh = np.clip(rh_enh, 0.0, 0.99)    # 保留 1% 过饱和余量
        e_2m = rh_enh * es_2m

    # 精确混合比 qv = ε·e/(p−e)
    q2 = EPSILON * e_2m / np.maximum(psfc - e_2m, 1.0)
    return np.clip(q2, 0.0, 0.05)

# ==========================================================================
# 模块：pbl.py
# ==========================================================================
# 边界层高度与地表湍流通量诊断。
#
# * PBLH ：总体 Richardson 数临界值法。
# * UST/HFX/LH/RMOL：Monin-Obukhov 相似理论 + 块体空气动力学，迭代求解稳定度。
#
# 注意 MCIP 会把 RMOL 取倒数得到 L（见 rdwrfem.f90:1275），因此这里输出的是 1/L。





EPS_ZETA = 1.0e-6


def psi_m(zeta: np.ndarray) -> np.ndarray:
    """动量相似函数（Businger-Dyer）。"""
    z = np.clip(zeta, -10.0, 1.0)
    unstable = z < 0.0
    x = (1.0 - 16.0 * np.minimum(z, 0.0)) ** 0.25
    psi_unstable = (
        2.0 * np.log((1.0 + x) / 2.0)
        + np.log((1.0 + x * x) / 2.0)
        - 2.0 * np.arctan(x)
        + np.pi / 2.0
    )
    psi_stable = -5.0 * np.maximum(z, 0.0)
    return np.where(unstable, psi_unstable, psi_stable)


def psi_h(zeta: np.ndarray) -> np.ndarray:
    """热量/水汽相似函数。"""
    z = np.clip(zeta, -10.0, 1.0)
    unstable = z < 0.0
    x = (1.0 - 16.0 * np.minimum(z, 0.0)) ** 0.25
    psi_unstable = 2.0 * np.log((1.0 + x * x) / 2.0)
    psi_stable = -5.0 * np.maximum(z, 0.0)
    return np.where(unstable, psi_unstable, psi_stable)


def _first_crossing(z: np.ndarray, v: np.ndarray, thr: np.ndarray) -> np.ndarray:
    """v(z) 自下向上首次超过 thr 的高度（线性插值），未超过返回 NaN。

    z, v: (nz,ny,nx)；thr: (ny,nx)。
    """
    above = v > thr[None, :, :]
    nz = v.shape[0]
    hit = above.any(axis=0)
    idx = np.where(hit, above.argmax(axis=0), nz - 1)
    i0 = np.maximum(idx - 1, 0)
    v0 = np.take_along_axis(v, i0[None], axis=0)[0]
    v1 = np.take_along_axis(v, idx[None], axis=0)[0]
    z0 = np.take_along_axis(z, i0[None], axis=0)[0]
    z1 = np.take_along_axis(z, idx[None], axis=0)[0]
    frac = np.clip((thr - v0) / np.maximum(v1 - v0, 1e-12), 0.0, 1.0)
    h = z0 + frac * (z1 - z0)
    return np.where(hit, h, np.nan)


def pbl_height(z_mid: np.ndarray, thv_mid: np.ndarray, u_mid: np.ndarray,
               v_mid: np.ndarray, prm: Params, thv_sfc: np.ndarray = None,
               hfx: np.ndarray = None, h_conv: np.ndarray = None) -> np.ndarray:
    """边界层高度 [m]（v2）。

    取以下两支的较大者，避免 v1 在「弱风 + 高地形」处退化到 pbl_min
    （v1 实测太原一带全天贴 50 m，而基准 300~1430 m）：

    1) 总体 Richardson 数法：Rib 以**地表**位温（由 TSK 推得）为参考，且风速取
       max(|V|, pbl_wind_floor)，避免静风时 Rib 爆炸；
    2) 对流边界层用 encroachment（Carson 1973）解：h = sqrt(2·H/γ)。
       其中 H 为当日累计的地表加热 ∫HFX/(ρcp)dt [K·m]，γ 为逆温层强度。
       该支只依赖地表热通量、不依赖分辨很粗的局地位温廓线，弱风时也能给出
       合理的白天混合层（实测 v1 的失败主要来自弱风使 Rib 爆炸）。
    """
    ref = thv_sfc if (thv_sfc is not None and prm.pbl_use_surface_ref) else thv_mid[0]
    speed = np.maximum(np.sqrt(u_mid ** 2 + v_mid ** 2), prm.pbl_wind_floor)
    speed2 = speed ** 2
    zs = z_mid[1:]                                      # 搜索层高度
    # 只在地表 ~ prm.pbl_max 之间搜索
    z_ok = zs <= prm.pbl_max
    rib = G * zs * (thv_mid[1:] - ref[None, :, :]) / (ref[None, :, :] * speed2[1:])
    exceeded = (rib > prm.pbl_rib_crit) & z_ok

    nz = rib.shape[0]
    found = exceeded.any(axis=0)
    idx = np.where(exceeded, np.arange(nz)[:, None, None], nz).min(axis=0)
    idx_g = np.minimum(idx, nz - 1)

    zk = np.take_along_axis(zs, idx_g[None, :, :], axis=0)[0]
    ribk = np.take_along_axis(rib, idx_g[None, :, :], axis=0)[0]
    idx_prev = np.maximum(idx_g - 1, 0)
    zk_prev = np.take_along_axis(zs, idx_prev[None, :, :], axis=0)[0]
    rib_prev = np.take_along_axis(rib, idx_prev[None, :, :], axis=0)[0]
    # 地面到第一层之间 Rib 由 0 线性增长
    z_below = np.where(idx_g == 0, 0.0, zk_prev)
    rib_below = np.where(idx_g == 0, 0.0, rib_prev)

    frac = np.clip(
        (prm.pbl_rib_crit - rib_below) / np.maximum(ribk - rib_below, 1e-12), 0.0, 1.0
    )
    pbl_ri = z_below + frac * (zk - z_below)
    # 搜索范围内始终未超过临界值 -> 视为深混合层，取上限高度
    pbl_ri = np.where(found, pbl_ri, np.minimum(zs[-1], prm.pbl_max))

    # 对流边界层（encroachment）：与风速无关，修正弱风/粗廓线导致的塌陷
    pblh = pbl_ri
    if h_conv is not None and hfx is not None and prm.pbl_conv_on > 0:
        use = (hfx > prm.pbl_hfx_thresh) & np.isfinite(h_conv)
        pblh = np.where(use, np.maximum(pbl_ri, h_conv), pbl_ri)
    return np.clip(pblh, prm.pbl_min, prm.pbl_max)


def surface_radiation(t2: np.ndarray, tsk: np.ndarray, albedo: np.ndarray,
                      swdown: np.ndarray, glw: np.ndarray,
                      prm: Params) -> np.ndarray:
    """地表净辐射 [W m-2]（用于湍流通量的能量闭合）。"""
    eps = prm.emissivity
    return (
        (1.0 - albedo) * swdown
        + eps * glw
        - eps * STEFAN_BOLTZMANN * tsk ** 4
    )


def close_surface_energy(hfx: np.ndarray, lh: np.ndarray, rnet: np.ndarray,
                         landmask: np.ndarray, prm: Params):
    """按地表能量平衡等比缩放感热/潜热（保持 Bowen 比）。

    块体公式与地表能量平衡是两套独立估算，二者可能矛盾（例如大气很干时
    潜热会远超净辐射）。这里把「感热 + 潜热」按同一比例压缩到
    ``净辐射 - 土壤热通量`` 以内，既闭合能量收支又保留 Bowen 比。

    仅在白天（rnet>0 且通量向上）时缩放，夜间保持原值。
    """
    ground = np.where(landmask > 0.5, prm.ground_heat_frac * rnet, 0.0)
    avail = rnet - ground
    total = hfx + lh
    apply = (total > 1.0) & (avail > 0.0)
    scale = np.clip(avail / np.maximum(total, 1.0),
                    prm.flux_scale_clip[0], prm.flux_scale_clip[1])
    return (np.where(apply, hfx * scale, hfx),
            np.where(apply, lh * scale, lh))


# ---------------------------------------------------------------------------
# v6【F3】：Jarvis (1976) 型冠层阻抗 -> 蒸发效率 beta
# ---------------------------------------------------------------------------
def canopy_resistance(swdown: np.ndarray, t2: np.ndarray, q2: np.ndarray,
                      psfc: np.ndarray, lai: np.ndarray, vegfra: np.ndarray,
                      soil_moisture_top: np.ndarray, prm: Params) -> np.ndarray:
    """冠层（气孔）阻抗 rs [s m-1]，Jarvis (1976) 乘积型响应函数。

    v5 的蒸发效率 ``beta = clip(SMOIS[0]/0.50, 0.1, 1)`` 恒为 0.637：既不随
    光照/水汽亏缺/物候变化，也没有气孔阻抗。而 terra Noah LSM 的蒸腾受
    rs 与空气动力学阻抗 ra 串联限制。10 月底华北植被凋零、LAI 低，
    真实 rs 应远大于"湿土上限"对应的值 -> 实际 beta 应明显小于 0.637。

    三项胁迫均为「阻抗放大因子」（越不利 -> rs 越大 -> beta 越小）：

    * f_par  ：光照。夜间/阴天气孔近乎关闭；``swdown >= rs_par_light`` 时为 1。
    * f_vpd  ：水汽亏缺。空气越干，气孔越关闭。
    * f_theta：土壤水。低于 rs_theta_crit 后线性减小到凋萎点。

    冠层阻抗 = rs_min / LAI_eff · f_par · f_vpd · f_theta，
    LAI_eff 由 LAI × 植被覆盖度得到（稀疏植被的有效蒸腾面积）。
    """
    lai_eff = np.maximum(lai * np.clip(vegfra / 100.0, 0.0, 1.0), prm.rs_lai_floor)
    rs = prm.rs_min / lai_eff

    # 光照（用短波近似光合有效辐射）
    par = np.maximum(swdown, 0.0)
    f_par = ((1.0 + prm.rs_par_coef * prm.rs_par_light)
             / (1.0 + prm.rs_par_coef * par))

    # 水汽亏缺 [kPa]
    q_spec = np.clip(q2, 0.0, 0.05) / (1.0 + np.clip(q2, 0.0, 0.05))
    e_a = vapor_pressure(psfc, q_spec)                       # [hPa]
    es_t2 = np.maximum(saturation_vapor_pressure(t2), 0.0)   # [hPa]
    vpd = np.maximum(es_t2 - e_a, 0.0) / 10.0                # hPa -> kPa
    f_vpd = 1.0 + prm.rs_vpd_coef * vpd

    # 土壤水胁迫
    th = np.clip(soil_moisture_top, 0.0, 1.0)
    wet = np.clip(
        (th - prm.rs_theta_wilt) / max(prm.rs_theta_crit - prm.rs_theta_wilt, 1e-6),
        0.0, 1.0,
    )
    f_theta = 1.0 / np.clip(wet, prm.rs_wet_floor, 1.0)

    rs = rs * f_par * f_vpd * f_theta
    return np.clip(rs, prm.rs_floor, prm.rs_ceiling)


def evaporation_efficiency(speed: np.ndarray, z0: np.ndarray,
                           rs: np.ndarray, landmask: np.ndarray,
                           prm: Params) -> np.ndarray:
    """地表蒸发效率 beta [-]（v6【F3】）。

    阻抗串联网络：陆地 ``beta = r_a/(r_a + r_s)``，其中
    ``r_a = 1/(C_H·U)`` 为空气动力学阻抗。rs→0（湿密植被）时 beta→1
    （潜在蒸发）；rs 增大则蒸腾受限，多余能量改以感热释放，Bowen 比升高。
    水面无气孔限制，beta = 1。
    """
    lnz0 = np.log(prm.meas_height / np.clip(z0, 1.0e-4, 5.0))
    ch = KARMAN ** 2 / np.maximum(lnz0 ** 2, 1.0)
    ra = 1.0 / np.maximum(ch * np.maximum(speed, 0.1), 1e-6)
    beta_land = ra / np.maximum(ra + rs, 1e-6)
    return np.where(landmask > 0.5,
                    np.clip(beta_land, prm.beta_min, prm.beta_max), 1.0)


def surface_fluxes(u10: np.ndarray, v10: np.ndarray, t2: np.ndarray,
                   q2: np.ndarray, psfc: np.ndarray, tsk: np.ndarray,
                   z0: np.ndarray, landmask: np.ndarray,
                   beta: np.ndarray, prm: Params) -> Dict[str, np.ndarray]:
    """块体方法 + 相似理论求地表通量与稳定度。

    返回 dict：ust [m/s]、hfx [W m-2]、lh [W m-2]、rmol [m-1]、mol [m]。
    所有通量均为向上为正。
    """
    z = prm.meas_height
    q2 = np.clip(q2, 0.0, 0.05)
    z0 = np.clip(z0, 1.0e-4, 5.0)

    theta_air = t2 * (P0 / psfc) ** RDOVCP
    q2_spec = q2 / (1.0 + q2)
    thv_air = theta_air * (1.0 + 0.608 * q2_spec)

    # 地表饱和混合比；v6【F3】陆地折减改用阻抗法得到的 beta
    # （由 evaporation_efficiency 计算后传入，见文件头 F3 说明）。
    q_sat_sfc = saturation_mixing_ratio(tsk, psfc)
    q_sfc = beta * q_sat_sfc
    theta_sfc = tsk * (P0 / psfc) ** RDOVCP
    thv_sfc = theta_sfc * (1.0 + 0.608 * q_sfc / (1.0 + q_sfc))

    d_theta = theta_sfc - theta_air
    d_q = q_sfc - q2

    speed = np.maximum(np.sqrt(u10 ** 2 + v10 ** 2), 0.1)
    lnz0 = np.log(z / z0)
    rho = psfc / (RD * thv_air)

    # 迭代稳定度
    zeta = np.zeros_like(speed)
    ust = np.zeros_like(speed)
    tst = np.zeros_like(speed)
    qst = np.zeros_like(speed)
    mol = np.full_like(speed, 1.0e6)
    for _ in range(6):
        ust = KARMAN * speed / np.maximum(lnz0 - psi_m(zeta), 0.5)
        tst = -KARMAN * d_theta / np.maximum(lnz0 - psi_h(zeta), 0.5)
        qst = -KARMAN * d_q / np.maximum(lnz0 - psi_h(zeta), 0.5)
        # L = u*^2 * thv / (kappa * g * theta*)；theta* 为负时 L 为负（不稳定）
        tst_safe = np.where(np.abs(tst) < 1e-8, 1e-8, tst)
        mol = ust ** 2 * thv_air / (KARMAN * G * tst_safe)
        sign = np.where(mol >= 0.0, 1.0, -1.0)
        mol = sign * np.maximum(np.abs(mol), prm.mol_min_abs)
        zeta = z / mol

    hfx = -rho * CP * ust * tst
    lh = -rho * LV * ust * qst
    hfx = np.clip(hfx, prm.hfx_clip[0], prm.hfx_clip[1])
    lh = np.clip(lh, prm.lh_clip[0], prm.lh_clip[1])
    ust = np.clip(ust, 0.01, 3.0)
    rmol = 1.0 / mol

    return {"ust": ust, "hfx": hfx, "lh": lh, "rmol": rmol, "mol": mol}

# ==========================================================================
# 模块：write_wrfout.py
# ==========================================================================
# 把转换结果写成 MCIP 可读的伪 wrfout 文件。
#
# 变量清单严格对应 MCIP V4.4 的读取需求（见 docs/pangu_mcip_field_diff.md）：
#
# * 无条件必需：Times / U V W PH PHB P PB T QVAPOR QCLOUD QRAIN /
#   MU MUB PSFC MAPFAC_M HGT SWDOWN GLW XLAT XLONG LU_INDEX LANDMASK HFX LH UST
#   PBLH TSK ALBEDO SNOWC SEAICE / ZNU ZNW P_TOP / RAINC RAINNC
# * 条件必需（本方案全部提供）：T2 Q2 U10 V10 RMOL LAI CANWAT VEGFRA ZNT
#   SMOIS TSLB ISLTYP；lpv>0 时的 F
# * 刻意不写：LANDUSEF（避免依赖 geo_em，MCIP 仅告警）、CLDFRA（可选）、
#   QICE/QSNOW/QGRAUP（避免 nqspecies==3 触发 graceful_stop）




# 维度代码 -> 维度名
DIM_MAP = {
    "T": "Time",
    "DS": "DateStrLen",
    "Z": "bottom_top",
    "ZS": "bottom_top_stag",
    "Y": "south_north",
    "X": "west_east",
    "YS": "south_north_stag",
    "XS": "west_east_stag",
    "S": "soil_layers_stag",
}

DIMS_SIZE_KEY = {
    "Time": None,            # UNLIMITED
    "DateStrLen": "dstrlen",
    "bottom_top": "nz",
    "bottom_top_stag": "nzp",
    "south_north": "ny",
    "west_east": "nx",
    "south_north_stag": "ny_stag",
    "west_east_stag": "nx_stag",
    "soil_layers_stag": "ns",
}

# 变量定义：(dtype, 维度代码)
VAR_SPECS: Dict[str, tuple] = {
    "Times": ("S1", ("T", "DS")),
    # --- 静态/坐标 ---
    "XLAT": ("f4", ("T", "Y", "X")),
    "XLONG": ("f4", ("T", "Y", "X")),
    "XLAT_U": ("f4", ("T", "Y", "XS")),
    "XLONG_U": ("f4", ("T", "Y", "XS")),
    "XLAT_V": ("f4", ("T", "YS", "X")),
    "XLONG_V": ("f4", ("T", "YS", "X")),
    "SINALPHA": ("f4", ("T", "Y", "X")),
    "COSALPHA": ("f4", ("T", "Y", "X")),
    "MAPFAC_M": ("f4", ("T", "Y", "X")),
    "MAPFAC_U": ("f4", ("T", "Y", "XS")),
    "MAPFAC_V": ("f4", ("T", "YS", "X")),
    "HGT": ("f4", ("T", "Y", "X")),
    "LANDMASK": ("f4", ("T", "Y", "X")),
    "LU_INDEX": ("f4", ("T", "Y", "X")),
    "F": ("f4", ("T", "Y", "X")),
    # --- 垂直坐标 ---
    "ZNU": ("f4", ("T", "Z")),
    "ZNW": ("f4", ("T", "ZS")),
    "P_TOP": ("f4", ("T",)),
    # --- 三维动力学/热力 ---
    "U": ("f4", ("T", "Z", "Y", "XS")),
    "V": ("f4", ("T", "Z", "YS", "X")),
    "W": ("f4", ("T", "ZS", "Y", "X")),
    "PH": ("f4", ("T", "ZS", "Y", "X")),
    "PHB": ("f4", ("T", "ZS", "Y", "X")),
    "P": ("f4", ("T", "Z", "Y", "X")),
    "PB": ("f4", ("T", "Z", "Y", "X")),
    "T": ("f4", ("T", "Z", "Y", "X")),
    "QVAPOR": ("f4", ("T", "Z", "Y", "X")),
    "QCLOUD": ("f4", ("T", "Z", "Y", "X")),
    "QRAIN": ("f4", ("T", "Z", "Y", "X")),
    # v2 新增冰相水凝物：MCIP 需 QICE+QSNOW 成对出现（nqspecies=4），再加 QGRAUP 为 5
    "QICE": ("f4", ("T", "Z", "Y", "X")),
    "QSNOW": ("f4", ("T", "Z", "Y", "X")),
    "QGRAUP": ("f4", ("T", "Z", "Y", "X")),
    # --- 柱压 ---
    "MU": ("f4", ("T", "Y", "X")),
    "MUB": ("f4", ("T", "Y", "X")),
    "PSFC": ("f4", ("T", "Y", "X")),
    # --- 降水 ---
    "RAINC": ("f4", ("T", "Y", "X")),
    "RAINNC": ("f4", ("T", "Y", "X")),
    # --- 辐射 ---
    "SWDOWN": ("f4", ("T", "Y", "X")),
    "GLW": ("f4", ("T", "Y", "X")),
    # --- 近地面 ---
    "T2": ("f4", ("T", "Y", "X")),
    "Q2": ("f4", ("T", "Y", "X")),
    "U10": ("f4", ("T", "Y", "X")),
    "V10": ("f4", ("T", "Y", "X")),
    # --- 陆面 ---
    "TSK": ("f4", ("T", "Y", "X")),
    # 模板 SF_SURFACE_PHYSICS = 7（Pleim-Xiu），MCIP 会置 ifmolpx=.TRUE. 并强制读取 QFX
    "QFX": ("f4", ("T", "Y", "X")),
    "ALBEDO": ("f4", ("T", "Y", "X")),
    "SNOWC": ("f4", ("T", "Y", "X")),
    "SEAICE": ("f4", ("T", "Y", "X")),
    "LAI": ("f4", ("T", "Y", "X")),
    "CANWAT": ("f4", ("T", "Y", "X")),
    "VEGFRA": ("f4", ("T", "Y", "X")),
    "ZNT": ("f4", ("T", "Y", "X")),
    "ISLTYP": ("i4", ("T", "Y", "X")),
    "SMOIS": ("f4", ("T", "S", "Y", "X")),
    "TSLB": ("f4", ("T", "S", "Y", "X")),
    "ZS": ("f4", ("T", "S")),
    "DZS": ("f4", ("T", "S")),
    # --- 湍流 ---
    "UST": ("f4", ("T", "Y", "X")),
    "HFX": ("f4", ("T", "Y", "X")),
    "LH": ("f4", ("T", "Y", "X")),
    "PBLH": ("f4", ("T", "Y", "X")),
    "RMOL": ("f4", ("T", "Y", "X")),
    # --- 可选 ---
    "CLDFRA": ("f4", ("T", "Z", "Y", "X")),
}

TIME_DEPENDENT = set(VAR_SPECS)


class WrfoutWriter:
    """创建并填充伪 wrfout 文件。

    用法::

        with WrfoutWriter(path, grid, ntimes=24, start_time="2025-06-03_00:00:00") as w:
            w.write_time(0, "2025-06-03_00:00:00", fields)
    """

    def __init__(self, path: str, grid, ntimes: int, start_time: str,
                 variables: Optional[Dict[str, tuple]] = None):
        self.path = path
        self.grid = grid
        self.ntimes = int(ntimes)
        self.start_time = start_time
        self.specs = dict(VAR_SPECS if variables is None else variables)
        self._vars: Dict[str, Any] = {}
        self.ds: Optional[nc.Dataset] = None

    # -- 上下文管理 -------------------------------------------------------
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def open(self):
        d = os.path.dirname(os.path.abspath(self.path))
        if d:
            os.makedirs(d, exist_ok=True)
        self.ds = nc.Dataset(self.path, "w", format="NETCDF3_64BIT_OFFSET")
        self._create_dims()
        self._create_global_attrs()
        self._create_vars()
        return self

    def close(self):
        if self.ds is not None:
            self.ds.close()
            self.ds = None

    # -- 内部 -------------------------------------------------------------
    def _create_dims(self):
        sizes = {
            "Time": None,
            "DateStrLen": 19,
            "bottom_top": self.grid.nz,
            "bottom_top_stag": self.grid.nzp,
            "south_north": self.grid.ny,
            "west_east": self.grid.nx,
            "south_north_stag": self.grid.ny_stag,
            "west_east_stag": self.grid.nx_stag,
            "soil_layers_stag": self.grid.ns,
        }
        for name, size in sizes.items():
            if size is None:
                self.ds.createDimension(name, None)
            else:
                self.ds.createDimension(name, int(size))

    def _create_global_attrs(self):
        attrs = self.grid.global_attrs_copy()
        # 时间戳统一改为本次预报的起始时刻
        attrs["START_DATE"] = self.start_time
        attrs["SIMULATION_START_DATE"] = self.start_time
        # 显式关闭混合垂直坐标（wrfversion(18:19) >= "V9" 时 MCIP 会强校验）
        attrs.setdefault("HYBRID_OPT", -1)
        if attrs["HYBRID_OPT"] > 0:
            attrs["HYBRID_OPT"] = 0
        # JULYR/JULDAY/GMT 与起始时刻保持一致
        try:
            y, md, hm = self.start_time.split("_")
            attrs["JULYR"] = int(y[:4])
            attrs["GMT"] = float(int(hm[:2]) % 24)
        except (ValueError, IndexError):
            pass
        for key, val in attrs.items():
            self.ds.setncattr(key, val)

    def _create_vars(self):
        tmpl = None
        try:
            tmpl = nc.Dataset(self.grid.path)
        except OSError:
            tmpl = None
        for name, (dtype, dims) in self.specs.items():
            dim_names = tuple(DIM_MAP[d] for d in dims)
            var = self.ds.createVariable(name, dtype, dim_names)
            if tmpl is not None and name in tmpl.variables:
                for att in tmpl.variables[name].ncattrs():
                    try:
                        var.setncattr(att, tmpl.variables[name].getncattr(att))
                    except (AttributeError, RuntimeError):
                        pass
            self._vars[name] = var
        if tmpl is not None:
            tmpl.close()

    # -- 写入 -------------------------------------------------------------
    def write_time(self, it: int, time_str: str, fields: Dict[str, np.ndarray]):
        """写入第 it 个时次。fields 中的键必须是 VAR_SPECS 里的变量名。"""
        if self.ds is None:
            raise RuntimeError("writer 尚未打开")
        assert len(time_str) == 19, "Times 必须为 19 字符：%r" % time_str
        self._vars["Times"][it, :] = np.array(list(time_str), dtype="S1")
        for name, data in fields.items():
            if name not in self._vars:
                raise KeyError("输出变量未定义: %s" % name)
            arr = np.asarray(data)
            self._vars[name][it, ...] = arr

# ==========================================================================
# 模块：run_pangu2wrf.py
# ==========================================================================
# 主流程入口：盘古逐小时预报 -> MCIP 可读的伪 wrfout。
#
# 用法示例::
#
#     # 自检（不产出文件）
#     python3 run_pangu2wrf.py --selftest
#
#     # 转换 2025-06-03 起报的前 24 小时
#     python3 -m pangu2wrf.run_pangu2wrf         --pangu-dir ../GFS/PANGU_2025-06-03/pangu_1h         --out ../../pangu_wrfout/wrfout_d01_pangu_2025-06-03.nc         --start-hour 1 --count 24
#
# 每个时次的处理链：
#     读 npy -> 水平插值 -> 风旋转 -> 静力下延求 PSFC -> 重建 eta（P/PB/PH/PHB）
#     -> 连续方程诊断 W -> 云水/降水/辐射/陆面/湍流诊断 -> 写盘





UP = {name: i for i, name in enumerate(UPPER_CHANNELS)}
SF = {name: i for i, name in enumerate(SURFACE_CHANNELS)}

# 开关 -> 受控变量
SWITCH_VARS = {
    "provide_t2_u10_v10": ("T2", "U10", "V10"),
    "provide_q2": ("Q2",),
    "provide_soil": ("SMOIS", "TSLB", "ISLTYP"),
    "provide_znt": ("ZNT",),
    "provide_lai": ("LAI",),
    "provide_vegfra": ("VEGFRA",),
    "provide_canwat": ("CANWAT",),
    "provide_rmol": ("RMOL",),
    "provide_cldfra": ("CLDFRA",),
}


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def parse_start_time(pangu_dir: str, override: Optional[str]) -> datetime:
    """确定小时序号 0 所对应的 UTC 时刻。"""
    if override:
        return datetime.strptime(override, "%Y-%m-%d_%H:%M:%S")
    base = os.path.basename(os.path.abspath(pangu_dir.rstrip("/")))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", base)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    raise SystemExit(
        "无法从目录名 %r 推断起报时刻，请用 --start-time YYYY-MM-DD_HH:MM:SS 指定" % base
    )


def upper_path(pangu_dir: str, hour: int) -> str:
    return os.path.join(pangu_dir, "upper_%03d.npy" % hour)


def surface_path(pangu_dir: str, hour: int) -> str:
    return os.path.join(pangu_dir, "surface_%03d.npy" % hour)


def require_files(pangu_dir: str, hours: List[int]):
    missing = []
    for h in hours:
        for fn in (upper_path(pangu_dir, h), surface_path(pangu_dir, h)):
            if not os.path.isfile(fn):
                missing.append(fn)
    if missing:
        raise SystemExit(
            "缺少输入文件（%d 个），例如：\n  %s\n请先用 02_inference_01.py 生成逐小时场。"
            % (len(missing), "\n  ".join(missing[:5]))
        )


def interp_mid_to_face(field_mid: np.ndarray) -> np.ndarray:
    """把质量层场插值到面层（首末层保持，内部取平均）。"""
    nz = field_mid.shape[0]
    out = np.empty((nz + 1,) + field_mid.shape[1:], dtype=np.float64)
    out[0] = field_mid[0]
    out[-1] = field_mid[-1]
    out[1:-1] = 0.5 * (field_mid[:-1] + field_mid[1:])
    return out


# ---------------------------------------------------------------------------
# 单个时次：读取与水平插值
# ---------------------------------------------------------------------------
class PanguHour:
    """一个时次插值到目标网格后的盘古场（质量点 13 层 + 地表）。"""

    __slots__ = ("phi", "tk", "q", "u", "v", "msl", "u10", "v10", "t2m",
                 "u_u", "v_u", "u_v", "v_v")

    def __init__(self, phi, tk, q, u, v, msl, u10, v10, t2m, u_u, v_u, u_v, v_v):
        self.phi, self.tk, self.q = phi, tk, q
        self.u, self.v = u, v
        self.msl, self.u10, self.v10, self.t2m = msl, u10, v10, t2m
        self.u_u, self.v_u, self.u_v, self.v_v = u_u, v_u, u_v, v_v


def load_hour(pangu_dir: str, hour: int, grid: GridTemplate, mappers,
              window) -> PanguHour:
    """读取并水平插值一个时次。"""
    m_mass, m_u, m_v = mappers
    up = np.load(upper_path(pangu_dir, hour), mmap_mode="r")
    sf = np.load(surface_path(pangu_dir, hour), mmap_mode="r")

    i0, i1, j0, j1 = window
    up = np.asarray(up[:, :, i0:i1, j0:j1], dtype=np.float64)
    sf = np.asarray(sf[:, i0:i1, j0:j1], dtype=np.float64)

    # 风：先插到交错点，再按该点的旋转角转到网格坐标
    u_e_u, v_e_u = m_u(up[UP["u"]]), m_u(up[UP["v"]])
    u_e_v, v_e_v = m_v(up[UP["u"]]), m_v(up[UP["v"]])
    sa_u, ca_u = grid.rotation_at_u_points()
    sa_v, ca_v = grid.rotation_at_v_points()
    u_u, v_u = rotate_earth_to_grid(u_e_u, v_e_u, sa_u, ca_u)
    u_v, v_v = rotate_earth_to_grid(u_e_v, v_e_v, sa_v, ca_v)

    return PanguHour(
        phi=m_mass(up[UP["z"]]), tk=m_mass(up[UP["t"]]), q=m_mass(up[UP["q"]]),
        u=m_mass(up[UP["u"]]), v=m_mass(up[UP["v"]]),
        msl=m_mass(sf[SF["msl"]]), u10=m_mass(sf[SF["u10"]]),
        v10=m_mass(sf[SF["v10"]]), t2m=m_mass(sf[SF["t2m"]]),
        u_u=u_u, v_u=v_u, u_v=u_v, v_v=v_v,
    )


def load_surface_pressure(pangu_dir: str, hour: int, grid: GridTemplate,
                          mappers, window) -> np.ndarray:
    """只算某个时次的地表气压（用于气压倾向项）。"""
    m_mass = mappers[0]
    up = np.load(upper_path(pangu_dir, hour), mmap_mode="r")
    i0, i1, j0, j1 = window
    up = np.asarray(up[:, :, i0:i1, j0:j1], dtype=np.float64)
    phi = m_mass(up[UP["z"]])
    tk = m_mass(up[UP["t"]])
    q = m_mass(up[UP["q"]])
    psfc, _ = surface_pressure(phi, tk, q, grid.hgt)
    return psfc


# ---------------------------------------------------------------------------
# 静态输出场
# ---------------------------------------------------------------------------
def build_static_fields(grid: GridTemplate, prm: Params) -> Dict[str, np.ndarray]:
    sa, ca = grid.rotation_at_mass_points()
    lu = grid.lu_index
    return {
        "XLAT": grid.xlat, "XLONG": grid.xlong,
        "XLAT_U": grid.xlat_u, "XLONG_U": grid.xlong_u,
        "XLAT_V": grid.xlat_v, "XLONG_V": grid.xlong_v,
        "SINALPHA": sa, "COSALPHA": ca,
        "MAPFAC_M": grid.mapfac_m, "MAPFAC_U": grid.mapfac_u, "MAPFAC_V": grid.mapfac_v,
        "HGT": grid.hgt, "LANDMASK": grid.landmask, "LU_INDEX": lu, "F": grid.f_cor,
        "ZNU": grid.znu, "ZNW": grid.znw, "P_TOP": np.float64(grid.p_top),
        "ZS": grid.zs, "DZS": grid.dzs,
        "ISLTYP": grid.isltyp.astype(np.int32),
        "LAI": leaf_area_index(lu),
        "VEGFRA": vegetation_fraction(lu),
        "CANWAT": canopy_water(grid.shape, prm),
    }


# ---------------------------------------------------------------------------
# 单时次转换
# ---------------------------------------------------------------------------
def convert_hour_core(cur: PanguHour, dt_hours: float, dt_utc: datetime,
                      grid: GridTemplate, prm: Params,
                      switches: Switches) -> Dict[str, Any]:
    """把一个时次的盘古场算到"还差跨时次状态"的程度（阶段 A）。

    本函数**只依赖当前时次的输入**，因此可以在多进程里并行执行。产出两类东西：

    * 输出 fields 所需的绝大多数中间量（PSFC/eta/插值场/云/辐射/湍流通量/...）；
    * 三个跨时次递推（RAINC/RAINNC 累加、夜间 dtheta 松弛、白天累积加热）
      各自所需的**逐点系数**，以及 omega 诊断的前置量。

    真正依赖跨时次状态的收尾（垂直速度 W、PBLH、累积降水）留给
    :func:`convert_hour_tail`，两者之间由 :func:`advance_carry` 推进累加器。
    """
    # 1) 地表气压（静力下延）
    psfc, _ = surface_pressure(cur.phi, cur.tk, cur.q, grid.hgt)

    # 2) eta 坐标
    eta = build_eta(psfc, grid.znw, grid.znu, grid.p_top)
    p_mid, p_face = eta["p_mid"], eta["p_face"]

    # 3) 温湿风插到 eta 质量层
    t_mid = interp_logp(cur.tk, PLEV_PA, p_mid, below="lapse")
    q_mid = np.clip(
        interp_logp(cur.q, PLEV_PA, p_mid, below="edge"), 0.0, 0.05
    )
    u_mid = interp_logp(cur.u, PLEV_PA, p_mid, below="edge")
    v_mid = interp_logp(cur.v, PLEV_PA, p_mid, below="edge")

    # 交错点上的风（用于散度/水汽通量辐合，以及 U/V 输出）
    p_mid_u = to_u_stag(p_mid)
    p_mid_v = to_v_stag(p_mid)
    u_u_mid = interp_logp(cur.u_u, PLEV_PA, p_mid_u, below="edge")
    v_v_mid = interp_logp(cur.v_v, PLEV_PA, p_mid_v, below="edge")

    theta_mid = potential_temperature(t_mid, p_mid)
    tv_mid = t_mid * (1.0 + 0.608 * q_mid)

    # 4) 位势（PH=0, PHB=phi，供 MCIP 用 PH+PHB）
    phi_face = geopotential_faces(p_face, tv_mid, grid.hgt)

    # 5) 垂直速度的前置量（omega 本身依赖地表气压倾向，留给 tail）
    tv_face = interp_mid_to_face(tv_mid)
    div = divergence(
        u_u_mid, v_v_mid, grid.mapfac_m, grid.mapfac_u, grid.mapfac_v, grid.dx, grid.dy
    )
    z_face = phi_face / G
    z_mid = 0.5 * (z_face[:-1] + z_face[1:])
    dz = np.maximum(z_face[1:] - z_face[:-1], 1.0)
    rho_mid = density(p_mid, tv_mid)

    # 6) 云量 / 云水 / 冰相（v2：次网格云量 + 物理量级云水）
    rh = relative_humidity(p_mid, t_mid, q_mid)
    cf = cloud_fraction(p_mid, rh, prm, t_mid)           # 3D 次网格云量
    qc_all = cloud_water(p_mid, t_mid, q_mid, prm, cf=cf)
    qc, qice, qsnow, qgraup = ice_water(qc_all, t_mid, prm)   # qc 变为液水
    qr = rain_water(qc, prm)

    # 7) 降水（逐时累积，mm）；按强度拆分为对流性 RAINC / 大尺度 RAINNC
    #    v6【F4】：传入 rh 以启用柱相对湿度 gate + 毛毛雨截断
    rate, _ = precipitation_rate(
        u_u_mid, v_v_mid, q_mid, p_face,
        grid.mapfac_m, grid.mapfac_u, grid.mapfac_v, grid.dx, grid.dy, prm,
        rh=rh,
    )
    conv_frac = np.clip(rate / (2.0 * max(prm.precip_conv_thresh, 1e-6)), 0.0, 1.0)
    # 本时次对两个累积量的贡献（纯加法，与合并顺序无关）
    d_rainc = rate * conv_frac * dt_hours
    d_rainnc = rate * (1.0 - conv_frac) * dt_hours

    # 8) 辐射（与云水自洽：同一条云光学厚度同时用于 CMAQ 光解与 SWDOWN）
    cld = column_cloud_fraction(cf, p_mid)
    tau_col = cloud_optical_depth(qc, qice + qsnow + qgraup, dz, rho_mid, prm).sum(axis=0)
    # v7【F7-1】气溶胶光学厚度：低层湿度驱动的霾湿增长（对整片天空衰减）
    rh_bl = boundary_layer_rh(rh, p_mid, prm)
    tau_aer = aerosol_optical_depth(rh_bl, prm)
    swdown = shortwave_down(dt_utc, grid.xlat, grid.xlong, cld, prm,
                            tau_cloud=tau_col, tau_aer=tau_aer)
    t2 = cur.t2m
    # v3.2：Q2 传入 prm，启用稳定边界层近地湿度增强（白天自动退回 v3.1）
    q2 = two_meter_mixing_ratio(
        psfc, t2, p_mid[0], t_mid[0], q_mid[0], prm=prm,
    )
    e_hpa = vapor_pressure(psfc, q2 / (1.0 + q2))
    glw = longwave_down(t2, e_hpa, cld, prm)

    # 9) 陆面：TSK（能量平衡）-> 积雪/反照率 -> 海冰 -> 土壤
    lu = grid.lu_index
    znt = roughness(lu)
    smo = soil_moisture(grid, t2)
    # v6【F3】：Jarvis 冠层阻抗 -> 蒸发效率 beta。skin_temperature 与
    # surface_fluxes 共用同一个 beta，保证能量平衡与湍流通量自洽。
    speed10 = np.sqrt(cur.u10 ** 2 + cur.v10 ** 2)
    rs = canopy_resistance(
        swdown, t2, q2, psfc, leaf_area_index(lu), vegetation_fraction(lu),
        smo[0], prm,
    )
    beta = evaporation_efficiency(speed10, znt, rs, grid.landmask, prm)
    albedo = _land_albedo(lu, np.zeros_like(t2), prm)
    if switches.tsk_energy_balance:
        tsk = blend_land_water(
            skin_temperature(
                t2, q2, cur.u10, cur.v10, psfc, swdown, glw, albedo, znt,
                grid.landmask, beta, prm,
            ),
            t2, grid.landmask,
        )
    else:
        tsk = surface_temperature(t2, grid.landmask, prm)
    snowc = snow_cover(tsk, prm)
    albedo = _land_albedo(lu, snowc, prm)
    if switches.tsk_energy_balance:
        # 用积雪修正后的反照率再解一次（一次迭代即收敛）
        tsk = blend_land_water(
            skin_temperature(
                t2, q2, cur.u10, cur.v10, psfc, swdown, glw, albedo, znt,
                grid.landmask, beta, prm,
            ),
            t2, grid.landmask,
        )
        snowc = snow_cover(tsk, prm)
    seaice = sea_ice(tsk, grid.landmask, prm)
    tsb = soil_temperature(grid, tsk)

    # 10) 湍流通量（先算通量，再用通量/地表位温求 PBLH）
    thv_mid = theta_mid * (1.0 + 0.608 * q_mid)
    flux = surface_fluxes(
        u10=cur.u10, v10=cur.v10, t2=t2, q2=q2, psfc=psfc, tsk=tsk, z0=znt,
        landmask=grid.landmask, beta=beta, prm=prm,
    )
    # 地表能量闭合：把 感热+潜热 压到净辐射以内（保持 Bowen 比）
    rnet = surface_radiation(t2, tsk, albedo, swdown, glw, prm)
    flux["hfx"], flux["lh"] = close_surface_energy(
        flux["hfx"], flux["lh"], rnet, grid.landmask, prm
    )

    u10g, v10g = rotate_earth_to_grid(
        cur.u10, cur.v10, *grid.rotation_at_mass_points()
    )

    # --- 跨时次递推的逐点系数（供 advance_carry 就地推进）---
    # Rib 的参考位温：白天取第一模式层（避免 TSK 虚暖）；夜间给一个等效地表降温。
    day = flux["hfx"] > prm.pbl_hfx_thresh
    night = flux["hfx"] <= prm.pbl_hfx_thresh
    # v6【F5】：夜间亏损不再取常数 pbl_night_dtheta，而是向目标值松弛的一阶
    # 过程——日落后从 0 加深、日出后迅速回到 0，使夜间 PBLH 有真实演变；
    # 并按 10 m 风速做机械混合削弱（风大 -> 夜间混合强 -> 逆温弱）。
    wind_damp = np.exp(
        -np.maximum(speed10 - prm.pbl_night_wind_ref, 0.0)
        / max(prm.pbl_night_wind_scale, 1e-6)
    )
    target = np.where(day, 0.0, prm.pbl_night_dtheta_max * wind_damp)
    tau_h = np.where(day, prm.pbl_night_recover_hours, prm.pbl_night_relax_hours)
    relax = 1.0 - np.exp(-dt_hours / np.maximum(tau_h, 1e-3))
    # 对流边界层：累计地表加热 H = ∫ HFX/(ρcp) dt [K·m]，h = sqrt(2H/γ)
    dt_s = dt_hours * 3600.0
    heat_dt = np.maximum(flux["hfx"], 0.0) / (rho_mid[0] * CP) * dt_s
    decay_night = np.exp(
        -dt_s / (max(prm.pbl_decay_hours, 1e-3) * 3600.0)
    )

    return dict(
        psfc=psfc, eta=eta, p_mid=p_mid, p_face=p_face, div=div, tv_face=tv_face,
        t_mid=t_mid, q_mid=q_mid, u_mid=u_mid, v_mid=v_mid,
        u_u_mid=u_u_mid, v_v_mid=v_v_mid, theta_mid=theta_mid, thv_mid=thv_mid,
        phi_face=phi_face, z_mid=z_mid, cf=cf, qc=qc, qr=qr, qice=qice,
        qsnow=qsnow, qgraup=qgraup, cld=cld, tau_col=tau_col, swdown=swdown,
        glw=glw, t2=t2, q2=q2, u10g=u10g, v10g=v10g, tsk=tsk, albedo=albedo,
        snowc=snowc, seaice=seaice, znt=znt, smo=smo, tsb=tsb, flux=flux,
        day=day, target=target, relax=relax,
        night=night, heat_dt=heat_dt, decay_night=decay_night,
        d_rainc=d_rainc, d_rainnc=d_rainnc,
        qvapor=mixing_ratio_from_specific_humidity(q_mid),
        rate_max=float(rate.max()),
    )


def advance_carry(core: Dict[str, Any], rain_acc: np.ndarray,
                  pbl_acc: Optional[np.ndarray],
                  dtheta_acc: Optional[np.ndarray],
                  prm: Params,
                  ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """就地推进三个跨时次累加器（阶段 B：串行，但极廉价）。

    只涉及若干 ``(ny,nx)`` 数组的乘加，开销远小于阶段 A 的整层插值，
    因此在多进程流水线里放到主进程串行做也不成为瓶颈。

    返回 ``(thv_sfc, h_conv)``——tail 求 PBLH 所需的两个量。

    这里的表达式与串行版逐字相同（例如 ``pbl_acc += heat; pbl_acc[night] *= decay``
    而不是等价的合并写法），以保证并行结果与串行结果逐位一致。
    """
    rain_acc[0] = rain_acc[0] + core["d_rainc"]
    rain_acc[1] = rain_acc[1] + core["d_rainnc"]

    if dtheta_acc is None:
        dtheta = np.where(core["day"], 0.0, prm.pbl_night_dtheta_max)
    else:
        dtheta_acc[...] = dtheta_acc + (core["target"] - dtheta_acc) * core["relax"]
        dtheta = dtheta_acc
    thv_sfc = core["thv_mid"][0] - dtheta

    h_conv = None
    if pbl_acc is not None:
        pbl_acc += core["heat_dt"]
        pbl_acc[core["night"]] *= core["decay_night"]
        h_conv = np.sqrt(2.0 * np.maximum(pbl_acc, 0.0)
                         / max(prm.pbl_inv_strength, 1e-6))
    return thv_sfc, h_conv


def convert_hour_tail(core: Dict[str, Any], prev_psfc: Optional[np.ndarray],
                      rain_acc: np.ndarray, thv_sfc: np.ndarray,
                      h_conv: Optional[np.ndarray], dt_hours: float,
                      grid: GridTemplate, prm: Params,
                      ) -> Tuple[Dict[str, np.ndarray], Dict[str, float]]:
    """阶段 C：只算那些依赖跨时次状态的输出（W / PBLH / RAINC / RAINNC）。

    同样可以并行——进入本函数时累加器已由 :func:`advance_carry` 推进到当前时次。
    """
    psfc = core["psfc"]
    dpsfc_dt = (np.zeros_like(psfc) if prev_psfc is None
                else (psfc - prev_psfc) / (dt_hours * 3600.0))
    omega_f, omega_mid = diagnose_omega(core["div"], core["p_face"], psfc, dpsfc_dt)
    w_face = vertical_velocity(omega_f, core["p_face"], core["tv_face"])
    pblh = pbl_height(core["z_mid"], core["thv_mid"], core["u_mid"], core["v_mid"],
                      prm, thv_sfc=thv_sfc, hfx=core["flux"]["hfx"], h_conv=h_conv)

    flux = core["flux"]
    fields: Dict[str, np.ndarray] = {
        # 气压与位势
        "MU": core["eta"]["mu"], "MUB": core["eta"]["mub"],
        "P": core["eta"]["p"], "PB": core["eta"]["pb"],
        "PSFC": psfc, "PH": np.zeros_like(core["phi_face"]),
        "PHB": core["phi_face"],
        # 风
        "U": core["u_u_mid"], "V": core["v_v_mid"], "W": w_face,
        # 热力与水汽
        "T": core["theta_mid"] - 300.0,
        "QVAPOR": core["qvapor"],
        "QCLOUD": core["qc"], "QRAIN": core["qr"],
        "QICE": core["qice"], "QSNOW": core["qsnow"], "QGRAUP": core["qgraup"],
        # 降水（v2：对流性/大尺度分开累积）
        "RAINC": rain_acc[0].copy(), "RAINNC": rain_acc[1].copy(),
        # 辐射
        "SWDOWN": core["swdown"], "GLW": core["glw"],
        # 近地面
        "T2": core["t2"], "Q2": core["q2"],
        "U10": core["u10g"], "V10": core["v10g"],
        # 陆面
        "TSK": core["tsk"], "ALBEDO": core["albedo"], "SNOWC": core["snowc"],
        "SEAICE": core["seaice"],
        "ZNT": core["znt"], "SMOIS": core["smo"], "TSLB": core["tsb"],
        # 湍流
        "UST": flux["ust"], "HFX": flux["hfx"], "LH": flux["lh"],
        "PBLH": pblh, "RMOL": flux["rmol"],
        # 湿通量（模板 SF_SURFACE_PHYSICS=7 -> ifmolpx，MCIP 强制读取 QFX）
        "QFX": flux["lh"] / LV,
        # 可选（v2 默认写入：MCIP 会据此输出 CFRAC_3D，CMAQ 光解直接采用，
        # 不再用 QC 反推云量，避免云量与云水不一致）
        "CLDFRA": core["cf"],
    }

    stats = {
        "psfc": psfc.mean(),
        "t2": core["t2"].mean(),
        "tsk": core["tsk"].mean(),
        "pblh": pblh.mean(),
        "swdown": core["swdown"].mean(),
        "glw": core["glw"].mean(),
        "rain": core["rate_max"],
        "qc": float(core["qc"].max()),
        "qc_mean": float(core["qc"].mean()),
        "cf": float(core["cf"].mean()),
        "tau": float(core["tau_col"].max()),
        "qice": float(core["qice"].max()),
        "w": float(np.abs(w_face).max()),
        "ust": flux["ust"].mean(),
        "hfx": flux["hfx"].mean(),
        "lh": flux["lh"].mean(),
    }
    return fields, stats


def convert_hour(cur: PanguHour, prev_psfc: Optional[np.ndarray], dt_hours: float,
                 dt_utc: datetime, grid: GridTemplate, prm: Params,
                 switches: Switches,
                 rain_acc: np.ndarray, pbl_acc: np.ndarray = None,
                 dtheta_acc: np.ndarray = None
                 ) -> Tuple[Dict[str, np.ndarray], np.ndarray, Dict[str, float]]:
    """把一个时次的盘古场转换成 WRF 变量字典。

    串行入口，等价于 ``convert_hour_core -> advance_carry -> convert_hour_tail``。
    并行脚本 ``pangu2wrf_par.py`` 把这三步打散到多进程流水线中执行；
    由于重活被隔离在 core 与 tail 里，那里的时间序列与原串行版完全一致。

    v6 新增跨时次状态 ``dtheta_acc``（夜间等效地表位温亏损 [K]），
    与 ``pbl_acc`` 一样由调用方持有并就地更新，见文件头 F5。
    """
    core = convert_hour_core(cur, dt_hours, dt_utc, grid, prm, switches)
    thv_sfc, h_conv = advance_carry(core, rain_acc, pbl_acc, dtheta_acc, prm)
    fields, stats = convert_hour_tail(
        core, prev_psfc, rain_acc, thv_sfc, h_conv, dt_hours, grid, prm
    )
    return fields, rain_acc, stats


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
def selftest(grid: GridTemplate, prm: Params) -> int:
    print(grid.summary())
    print()
    print(verify_vertical_scheme(grid))
    print()

    window = source_window(
        grid.xlat.min(), grid.xlat.max(), grid.xlong.min(), grid.xlong.max()
    )
    mappers = build_mappers(grid, window)
    print("源窗口 (ilat0,ilat1,ilon0,ilon1) =", window)

    src_lat = SRC_LAT0 - SRC_DLAT * np.arange(SRC_NLAT)
    src_lon = SRC_LON0 + SRC_DLON * np.arange(SRC_NLON)
    LAT, LON = np.meshgrid(src_lat, src_lon, indexing="ij")
    f = 3.0 * LAT + 5.0 * LON
    i0, i1, j0, j1 = window
    fwin = f[i0:i1, j0:j1]
    for name, m in zip(("mass", "u-stag", "v-stag"), mappers):
        exp = 3.0 * (grid.xlat if name == "mass" else
                     grid.xlat_u if name == "u-stag" else grid.xlat_v) + \
              5.0 * (grid.xlong if name == "mass" else
                     grid.xlong_u if name == "u-stag" else grid.xlong_v)
        err = np.abs(m(fwin) - exp).max()
        print("  双线性 %-7s shape %-10s 裁剪窗口内线性场还原最大误差 %.3e"
              % (name, m.shape, err))
    return 0


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="盘古 -> 伪 wrfout 转换")
    ap.add_argument("--pangu-dir", default=PANGU_1H_DIR, help="逐小时 npy 所在目录")
    ap.add_argument("--out", default=None, help="输出 nc 文件路径")
    ap.add_argument("--template", default=TEMPLATE_NC, help="模板 wrfout 文件")
    ap.add_argument("--start-hour", type=int, default=1, help="起始小时序号（默认 1）")
    ap.add_argument("--count", type=int, default=24, help="输出时次数（默认 24）")
    ap.add_argument("--step", type=int, default=1,
                    help="输入文件的小时间隔（默认 1；现有 6 小时数据用 6）")
    ap.add_argument("--dt-hours", type=float, default=None,
                    help="相邻时次的时间间隔 [h]，默认等于 --step")
    ap.add_argument("--start-time", default=None,
                    help="小时序号 0 对应的 UTC 时刻，格式 YYYY-MM-DD_HH:MM:SS")
    ap.add_argument("--selftest", action="store_true", help="只做自检，不产出文件")
    ap.add_argument("--param", action="append", default=[], metavar="NAME=VALUE",
                    help="覆盖 Params 中的经验系数（可重复），例如 "
                         "--param qc_incloud_ref=1.5e-4 --param pbl_min=20")
    args = ap.parse_args(argv)

    prm = Params()
    if args.param:
        for item in args.param:
            if "=" not in item:
                ap.error("--param 需为 NAME=VALUE 形式：%r" % item)
            name, value = item.split("=", 1)
            name = name.strip()
            if not hasattr(prm, name):
                ap.error("Params 中没有 %r" % name)
            cur = getattr(prm, name)
            try:
                if isinstance(cur, bool):
                    new = value.strip().lower() in ("1", "true", "yes", "on")
                elif isinstance(cur, tuple):
                    new = tuple(float(x) for x in value.split(","))
                elif isinstance(cur, int):
                    new = int(float(value))
                else:
                    new = float(value)
            except Exception:
                ap.error("无法解析 %s=%s" % (name, value))
            setattr(prm, name, new)
            print("[param] %s = %r" % (name, new))
    grid = GridTemplate(args.template)

    if args.selftest:
        return selftest(grid, prm)

    print(grid.summary())
    print()

    if args.step < 1:
        parser_error = "--step 必须 >= 1"
        ap.error(parser_error)
    dt_hours = float(args.step if args.dt_hours is None else args.dt_hours)
    hours = [args.start_hour + i * args.step for i in range(args.count)]
    require_files(args.pangu_dir, hours)
    t0 = parse_start_time(args.pangu_dir, args.start_time)

    # 输出文件路径
    if args.out:
        out_path = args.out
    else:
        out_path = os.path.join(
            OUT_DIR, "wrfout_d01_pangu_%s.nc" % t0.strftime("%Y-%m-%d")
        )

    window = source_window(
        grid.xlat.min(), grid.xlat.max(), grid.xlong.min(), grid.xlong.max()
    )
    mappers = build_mappers(grid, window)

    # 变量清单（按开关裁剪）
    specs = dict(VAR_SPECS)
    switches = Switches()
    disabled = set()
    for flag, names in SWITCH_VARS.items():
        if not getattr(switches, flag):
            disabled.update(names)
    for name in disabled:
        specs.pop(name, None)

    static_fields = build_static_fields(grid, prm)
    static_fields = {k: v for k, v in static_fields.items() if k in specs}

    first_time = (t0 + timedelta(hours=hours[0])).strftime("%Y-%m-%d_%H:%M:%S")
    print("输入目录 :", args.pangu_dir)
    print("输出文件 :", out_path)
    print("时次      : %s ... %s（共 %d 个，起始序号 %d）"
          % (t0 + timedelta(hours=hours[0]),
             t0 + timedelta(hours=hours[-1]), len(hours), hours[0]))
    print("裁剪窗口  :", window)
    print("输出变量  : %d 个%s" % (len(specs), ("（已关闭：%s）" % ",".join(sorted(disabled)))
                                  if disabled else ""))

    rain_acc = np.zeros((2,) + grid.shape, dtype=np.float64)   # [RAINC, RAINNC] 累积
    pbl_acc = np.zeros(grid.shape, dtype=np.float64)           # 对流边界层累积加热 [K·m]
    dtheta_acc = np.zeros(grid.shape, dtype=np.float64)        # v6：夜间地表等效位温亏损 [K]
    prev_psfc = None
    if args.start_hour - args.step >= 0:
        prev_hour = args.start_hour - args.step
        if os.path.isfile(upper_path(args.pangu_dir, prev_hour)):
            print("预取第 %d 小时地表气压用于气压倾向项 ..." % prev_hour)
            prev_psfc = load_surface_pressure(
                args.pangu_dir, prev_hour, grid, mappers, window
            )
        else:
            print("警告：缺少第 %d 小时输入，首个时次的气压倾向项按 0 处理（w 会略偏小）"
                  % prev_hour)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with WrfoutWriter(out_path, grid, len(hours), first_time,
                                   variables=specs) as writer:
        for n, h in enumerate(hours):
            dt_utc = t0 + timedelta(hours=h)
            cur = load_hour(args.pangu_dir, h, grid, mappers, window)
            fields, rain_acc, stats = convert_hour(
                cur, prev_psfc, dt_hours, dt_utc, grid, prm, switches, rain_acc,
                pbl_acc, dtheta_acc,
            )
            prev_psfc = fields["PSFC"]
            fields = {k: v for k, v in fields.items() if k in specs}
            fields.update(static_fields)
            time_str = dt_utc.strftime("%Y-%m-%d_%H:%M:%S")
            writer.write_time(n, time_str, fields)
            print(
                "[%2d/%2d] %s  PSFC %7.1f hPa  T2 %5.2f C  TSK %5.2f C  PBLH %6.1f m  "
                "SWDOWN %6.1f  GLW %6.1f  HFX %6.1f  LH %6.1f  Pmax %5.2f mm/h  "
                "cf %.3f  qc %.2e(%.2e)  tau %5.1f  |w| %5.2f  u* %5.3f"
                % (n + 1, len(hours), time_str, stats["psfc"] / 100.0,
                   stats["t2"] - 273.15, stats["tsk"] - 273.15, stats["pblh"],
                   stats["swdown"], stats["glw"], stats["hfx"], stats["lh"],
                   stats["rain"], stats["cf"], stats["qc"], stats["qc_mean"],
                   stats["tau"], stats["w"], stats["ust"])
            )

    size_mb = os.path.getsize(out_path) / 1024.0 ** 2
    print("\n完成：%s（%.1f MB，%d 个时次）" % (out_path, size_mb, len(hours)))
    print("该文件可直接作为 run_mcip_pangu.csh 的 InMetFiles。")
    return 0



# 去前缀时的命名冲突别名（同名局部变量会遮蔽这些函数）
_land_albedo = albedo

# ==========================================================================
# 模块：validate.py
# ==========================================================================
# 转换结果与 MCIP 输出的校验工具。
#
# 两类检查：
#
# 1. **往返一致性**（round trip）：把写出的伪 wrfout 与 MCIP 生成的
#    METCRO2D/METCRO3D 逐变量对照，确认 MCIP 读到的就是我们写进去的量。
# 2. **基线对照**：把盘古链路的 MCIP 输出与「原始 wrfout 跑 MCIP」的结果做
#    统计对比。注意二者时间不同（盘古示例数据 2025-06，模板 wrfout 2025-11），
#    因此只比较量级与分布是否落在合理区间，不做逐点差异。
#
# 用法::
#
#     python3 validate.py                      # 用默认路径
#     python3 validate.py --mcip-dir ../../mcip/PANGU99 --appl pangu01                         --wrfout ../../pangu_wrfout/wrfout_d01_pangu_2025-06-03.nc                         --baseline-dir ../../mcip/baseline_wrf --baseline-appl wrfbase





_PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def read_var(path: str, name: str, it: int = 0) -> np.ndarray:
    """读取 I/O API 输出变量的第 it 个时次，自动压掉长度为 1 的 LAY 维。"""
    d = nc.Dataset(path)
    try:
        var = d.variables[name]
        arr = (np.asarray(var[it], dtype=np.float64) if var.ndim == 4
               else np.asarray(var[...], dtype=np.float64))
        if arr.ndim == 3 and arr.shape[0] == 1:
            arr = arr[0]
    finally:
        d.close()
    return arr


def find_offset(mcip_ht: np.ndarray, domain_ht: np.ndarray) -> Tuple[int, int]:
    """在源网格中定位 MCIP 输出子域的左上角（通过地形场匹配）。"""
    ny, nx = mcip_ht.shape
    best = (0, 0)
    best_err = None
    for a in range(0, domain_ht.shape[0] - ny + 1):
        for b in range(0, domain_ht.shape[1] - nx + 1):
            err = float(np.abs(domain_ht[a:a + ny, b:b + nx] - mcip_ht).mean())
            if best_err is None or err < best_err:
                best, best_err = (a, b), err
    return best


def crop(field: np.ndarray, offset: Tuple[int, int], ny: int, nx: int) -> np.ndarray:
    a, b = offset
    if field.ndim == 2:
        return field[a:a + ny, b:b + nx]
    return field[..., a:a + ny, b:b + nx]


def read_vglvls(path: str) -> np.ndarray:
    """读取 IOAPI 文件的层界面 sigma（VGLVLS：地面 1.0 -> 模式顶 0.0）。"""
    d = nc.Dataset(path)
    try:
        v = np.atleast_1d(np.asarray(d.getncattr("VGLVLS"), dtype=np.float64))
    finally:
        d.close()
    v = v.reshape(-1)
    # 个别 MCIP 版本把 VGLVLS 写成字符串，这里做一次兜底解析
    if v.size == 0:  # pragma: no cover - 仅防御
        raise SystemExit("无法读取 %s 的 VGLVLS 属性" % path)
    return v


def vinterp(field: np.ndarray, sig_src: np.ndarray, sig_dst: np.ndarray) -> np.ndarray:
    """把 field 沿第 0 维（垂直）线性插值到目标 sigma 层。

    sigma 采用 WRF/MCIP 的地形跟随定义 ``(p - p_top) / (p_sfc - p_top)``，
    底层约为 1、顶层约为 0（递减）。源/目标的排列方向会自动处理，
    落到源层范围之外的目标层按最近端点截断（np.interp 的语义）。
    """
    xs = np.asarray(sig_src, dtype=np.float64).reshape(-1)
    xd = np.asarray(sig_dst, dtype=np.float64).reshape(-1)
    ys = np.asarray(field, dtype=np.float64)
    if ys.shape[0] != xs.size:
        raise ValueError("垂直层数 %d 与 sigma 层数 %d 不一致"
                         % (ys.shape[0], xs.size))
    if xs[0] > xs[-1]:                     # 统一成递增，便于 searchsorted
        xs, ys = xs[::-1], ys[::-1]
    flip_dst = xd[0] > xd[-1]
    xq = xd[::-1] if flip_dst else xd

    k = np.clip(np.searchsorted(xs, xq) - 1, 0, xs.size - 2)
    dx = np.maximum(xs[k + 1] - xs[k], 1e-30)
    w = ((xq - xs[k]) / dx).reshape((-1,) + (1,) * (ys.ndim - 1))
    out = ys[k] * (1.0 - w) + ys[k + 1] * w
    return out[::-1] if flip_dst else out


def diff_stats(got: np.ndarray, exp: np.ndarray) -> Dict[str, float]:
    d = np.asarray(got, dtype=np.float64) - np.asarray(exp, dtype=np.float64)
    scale = max(float(np.abs(exp).mean()), 1e-12)
    return {
        "mean_got": float(np.mean(got)),
        "mean_exp": float(np.mean(exp)),
        "max_abs": float(np.abs(d).max()),
        "mean_abs": float(np.abs(d).mean()),
        "rel": float(np.abs(d).mean() / scale),
    }


# ---------------------------------------------------------------------------
# 1) 往返一致性
# ---------------------------------------------------------------------------
def roundtrip(wrfout: str, mcip_dir: str, appl: str, it: int = 0) -> List[str]:
    grid = GridTemplate(wrfout)
    cro2d = os.path.join(mcip_dir, "METCRO2D_%s.nc" % appl)
    cro3d = os.path.join(mcip_dir, "METCRO3D_%s.nc" % appl)
    gridcro = os.path.join(mcip_dir, "GRIDCRO2D_%s.nc" % appl)
    for p in (cro2d, cro3d, gridcro):
        if not os.path.isfile(p):
            raise SystemExit("缺少 MCIP 输出文件: %s" % p)

    ht = read_var(gridcro, "HT")
    ny, nx = ht.shape
    off = find_offset(ht, grid.hgt)

    # MCIP 的垂直层：VGLVLS 给出 NLAYS+1 个层界面 sigma（地面 1.0 -> 模式顶 0.0）
    nlay = read_var(cro3d, "PRES").shape[0]
    vgl = read_vglvls(cro3d)
    if vgl.size != nlay + 1:
        raise SystemExit("VGLVLS 层数 %d 与 METCRO3D 的 LAY=%d 不匹配" % (vgl.size, nlay))
    sig_mid = 0.5 * (vgl[:-1] + vgl[1:])   # 层中心 sigma
    sig_fac = vgl[1:]                       # 层界面 sigma（去掉地面那一个）

    ds = nc.Dataset(wrfout)
    def w(name, it_=it):
        return np.asarray(ds.variables[name][it_], dtype=np.float64)
    psfc, t2, q2 = w("PSFC"), w("T2"), w("Q2")
    u10, v10 = w("U10"), w("V10")
    swdown, glw = w("SWDOWN"), w("GLW")
    albedo = w("ALBEDO")
    hfx, lh, ust, pblh, rmol = w("HFX"), w("LH"), w("UST"), w("PBLH"), w("RMOL")
    tsk, snowc, seaice, znt = w("TSK"), w("SNOWC"), w("SEAICE"), w("ZNT")
    lai, vegfra = w("LAI"), w("VEGFRA")
    smo, tsb, isltyp = w("SMOIS"), w("TSLB"), w("ISLTYP")
    pres = w("P") + w("PB")
    theta = w("T") + 300.0
    ta = theta * (pres / P0) ** RDOVCP
    qv_mix = w("QVAPOR")
    phi = w("PH") + w("PHB")
    zf = phi / G
    zh = 0.5 * (zf[:-1] + zf[1:])
    # 垂直坐标：wrfout 的层中心/层界面 eta（与 MCIP 的地形跟随 sigma 同一定义）
    eta_mid = w("ZNU")      # (bottom_top,)       层中心，底层 ~1 -> 顶层 ~0
    eta_fac = w("ZNW")      # (bottom_top_stag,)  层界面，地面 ~1 -> 模式顶 0
    ds.close()

    lines = []
    lines.append("MCIP 输出子域左上角偏移 (row, col) = %s，子域 %d x %d" % (off, ny, nx))
    lines.append("")
    lines.append("METCRO2D 往返一致性：")
    lines.append("  %-10s %-26s %-14s %-14s %-12s" % ("变量", "MCIP 变量", "MCIP 均值", "写入均值", "平均绝对差"))
    pairs_2d = [
        ("PSFC", "PRSFC", psfc), ("T2", "TEMP2", t2), ("Q2", "Q2", q2),
        ("sqrt(U10^2+V10^2)", "WSPD10", np.hypot(u10, v10)),
        ("SWDOWN", "RGRND", swdown), ("GLW", "GLW", glw),
        ("HFX", "HFX", hfx), ("LH", "LH", lh),
        ("UST", "USTAR", ust), ("PBLH", "PBL", pblh),
        ("TSK", "TEMPG", tsk), ("SNOWC", "SNOCOV", snowc),
        ("SEAICE", "SEAICE", seaice), ("ZNT", "ZRUF", znt),
        ("LAI", "LAI", lai), ("VEGFRA/100", "VEG", vegfra / 100.0),
        ("SWDOWN*(1-albedo)", "GSW", swdown * (1.0 - albedo)),
        ("SMOIS(1)", "SOIM1", smo[0]), ("TSLB(1)", "SOIT1", tsb[0]),
    ]
    for label, mname, arr in pairs_2d:
        got = read_var(cro2d, mname)
        st = diff_stats(got, crop(arr, off, ny, nx))
        lines.append("  %-10s %-26s %14.4f %14.4f %12.3e"
                     % (label, mname, st["mean_got"], st["mean_exp"], st["mean_abs"]))

    lines.append("")
    lines.append("METCRO3D 往返一致性：")
    lines.append("  wrfout 是 WRF 模板的 %d 层，MCIP 已按 ctmlays 塌缩到 %d 层。" % (eta_mid.size, nlay))
    lines.append("  故 wrfout 剖面先按地形跟随 sigma 线性插值到 MCIP 的层上再比对")
    lines.append("  （层中心用中点 sigma，层界面用 MCIP 的层界面 sigma）。")
    lines.append("  ZH/ZF 由 MCIP 自行按静力方程从 PSFC/T 积分得到（离地高度），")
    lines.append("  与我们的 (PH+PHB)/g 减去地形高度对比，可同时验证 P/PB/T 与 PH/PHB 的自洽性。")
    hgt = grid.hgt
    for label, mname, arr, sig_src, sig_dst in [
        ("P+PB", "PRES", pres, eta_mid, sig_mid),
        ("TA", "TA", ta, eta_mid, sig_mid),
        ("QVAPOR", "QV", qv_mix, eta_mid, sig_mid),
        ("(PH+PHB)/g 面层 - HGT", "ZF", zf[1:] - hgt, eta_fac[1:], sig_fac),
        ("(PH+PHB)/g 中层 - HGT", "ZH", zh - hgt, eta_mid, sig_mid),
    ]:
        got = read_var(cro3d, mname)
        exp = vinterp(crop(arr, off, ny, nx), sig_src, sig_dst)
        st = diff_stats(got, exp)
        lines.append("  %-22s %-6s %14.4f %14.4f %12.3e"
                     % (label, mname, st["mean_got"], st["mean_exp"], st["mean_abs"]))
    return lines


# ---------------------------------------------------------------------------
# 2) 与基线（原始 wrfout 的 MCIP 结果）做统计对照
# ---------------------------------------------------------------------------
BASELINE_FIELDS = ["PRSFC", "TEMP2", "Q2", "WSPD10", "PBL", "GSW", "GLW", "HFX",
                   "LH", "USTAR", "TEMPG", "VEG", "LAI", "ZNT", "SEAICE"]


def compare_baseline(mcip_dir: str, appl: str, base_dir: str, base_appl: str) -> List[str]:
    a = os.path.join(mcip_dir, "METCRO2D_%s.nc" % appl)
    b = os.path.join(base_dir, "METCRO2D_%s.nc" % base_appl)
    if not (os.path.isfile(a) and os.path.isfile(b)):
        return ["（未找到基线 MCIP 输出，跳过对照）"]

    lines = []
    lines.append("与基线（原始 wrfout 驱动 MCIP）的统计对照：")
    lines.append("  注意：两者时间不同（盘古示例为 2025-06-03，模板 wrfout 为 2025-11-02），")
    lines.append("        仅比较量级与分布是否落在合理区间，不构成逐点对比。")
    lines.append("")
    lines.append("  %-10s %12s %12s %12s %12s %12s %12s"
                 % ("变量", "盘古均值", "基线均值", "盘古最小", "基线最小", "盘古最大", "基线最大"))
    # 模板 wrfout 的第 0 个时次诊断量全为 0（WRF 初始化产物），基线取第 4 个时次
    base_it = 4
    for name in BASELINE_FIELDS:
        try:
            va = read_var(a, name)
            vb = read_var(b, name, base_it)
        except (KeyError, IndexError):
            continue
        lines.append("  %-10s %12.4f %12.4f %12.4f %12.4f %12.4f %12.4f"
                     % (name, va.mean(), vb.mean(), va.min(), vb.min(), va.max(), vb.max()))
    return lines


# ---------------------------------------------------------------------------
def validate_main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="转换结果校验")
    ap.add_argument("--wrfout", default=os.path.join(
        _PROJECT, "pangu_wrfout", "wrfout_d01_pangu_2025-06-03.nc"))
    ap.add_argument("--mcip-dir", default=os.path.join(_PROJECT, "mcip", "PANGU99"))
    ap.add_argument("--appl", default="pangu01")
    ap.add_argument("--baseline-dir", default=os.path.join(
        _PROJECT, "mcip", "baseline_wrf"))
    ap.add_argument("--baseline-appl", default="wrfbase")
    ap.add_argument("--out", default=None, help="把报告写入该文件")
    args = ap.parse_args(argv)

    lines = ["# 盘古 -> MCIP 链路校验报告", ""]
    lines += roundtrip(args.wrfout, args.mcip_dir, args.appl)
    lines.append("")
    lines += compare_baseline(args.mcip_dir, args.appl, args.baseline_dir,
                              args.baseline_appl)
    report = "\n".join(lines)
    print(report)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(report + "\n")
        print("\n报告已写入 %s" % args.out)
    return 0




# ==========================================================================
# 单文件版命令行入口
# ==========================================================================
def _env(*names):
    """取第一个非空环境变量。"""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def _gfs_root():
    return _env("PANGU_GFS_ROOT") or "/home/ubuntu01/sdb/Pangu_AQF/MIDDLE_DATA"


def _pangu_dir_from_domain(domain):
    return os.path.join(_gfs_root(), domain, "pangu")


def _flatten_stage(argv):
    """把 --stage 从参数里摘出来，返回 (剩余参数, 模式)。"""
    stage = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--stage":
            stage = argv[i + 1] if i + 1 < len(argv) else "convert"
            i += 2
            continue
        if a.startswith("--stage="):
            stage = a.split("=", 1)[1]
            i += 1
            continue
        rest.append(a)
        i += 1
    return rest, stage


def _has(argv, flag):
    return any(a == flag or a.startswith(flag + "=") for a in argv)


def _expand_days(argv):
    """--days N -> --start-hour 0 --count N*24（用户显式给出的则不动）。"""
    days = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--days":
            days = int(argv[i + 1])
            i += 2
            continue
        if a.startswith("--days="):
            days = int(a.split("=", 1)[1])
            i += 1
            continue
        rest.append(a)
        i += 1
    if days is None:
        env_days = _env("RUN_DAYS")
        if env_days:
            days = int(env_days)
    if days is not None:
        if not _has(rest, "--count"):
            rest += ["--count", str(days * 24)]
        if not _has(rest, "--start-hour"):
            rest += ["--start-hour", "0"]
    return rest


def cli(argv=None):
    """入口：用环境变量补齐路径/时段类参数，再交给各自的参数解析器。"""
    argv = list(sys.argv[1:] if argv is None else argv)
    argv, stage = _flatten_stage(argv)
    if stage == "validate":
        return validate_main(argv)
    if stage not in (None, "convert", "selftest", "auto"):
        raise SystemExit("未知 --stage %r（可选 convert / selftest / validate）" % stage)
    if stage == "selftest" and "--selftest" not in argv:
        argv.append("--selftest")
    argv = _expand_days(argv)

    domain = _env("DomainName", "DOMAIN_NAME")
    add = []
    if not _has(argv, "--pangu-dir"):
        pdir = _env("PANGU_DIR")
        if not pdir and domain:
            pdir = _pangu_dir_from_domain(domain)
        if pdir:
            add += ["--pangu-dir", pdir]
    if not _has(argv, "--template"):
        tpl = _env("PANGU_TEMPLATE")
        if tpl:
            add += ["--template", tpl]
    if not _has(argv, "--start-time"):
        st = _env("PANGU_START_TIME")
        if not st:
            day = _env("START_DAY")
            if not day and domain:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", domain)
                day = m.group(1) if m else None
            if day:
                st = "%s_00:00:00" % day
        if st:
            add += ["--start-time", st]
    if not _has(argv, "--out") and "--selftest" not in argv:
        out = _env("PANGU_OUT")
        if not out and domain:
            out = os.path.join(_pangu_dir_from_domain(domain),
                               "wrfout_d01_%s.nc" % domain)
        if out:
            add += ["--out", out]
    if not _has(argv, "--start-hour"):
        add += ["--start-hour", _env("START_HOUR") or "1"]
    if not _has(argv, "--count"):
        add += ["--count", _env("RUN_COUNT") or "24"]
    return main(add + argv)


if __name__ == "__main__":
    sys.exit(cli())