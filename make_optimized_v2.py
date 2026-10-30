#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""以 论文_优化稿.docx 为基础，按《核对事项报告》逐项修正，生成 论文_优化稿v2.docx。

v2 的修改内容以**红色字体**标出（新增段落整段红，局部替换只红改动部分），
便于与《论文_优化稿》逐处对照；定稿前可将红色统一改回黑色。

修改点与《核对事项报告》§9 的清单一一对应，全部集中在本脚本，便于复核。
"""
import copy
import os

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor, Pt
from docx.text.paragraph import Paragraph
from docx.text.run import Run

PAPER = '/home/ubuntu01/sda/AI2MCIP/paper'
SRC = os.path.join(PAPER, '论文_优化稿.docx')
DST = os.path.join(PAPER, '论文_优化稿v2.docx')

MINUS = '\u2212'          # 与正文一致的减号
RED = RGBColor(0xFF, 0x00, 0x00)


# ---------------------------------------------------------------- 基础操作
def set_text(p, text):
    """保留首个 run 的字体，替换整段文字。"""
    if not p.runs:
        p.add_run(text)
        return
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._element.getparent().remove(r._element)


def _color(p, red=True):
    for r in p.runs:
        r.font.color.rgb = RED if red else RGBColor(0, 0, 0)


def set_red(p, text):
    """整段替换并标红。"""
    set_text(p, text)
    _color(p, True)


def clone_run_after(run, text, red):
    el = copy.deepcopy(run._element)
    for child in list(el):
        if child.tag == qn('w:t'):
            el.remove(child)
    run._element.addnext(el)
    nr = Run(el, run._parent)
    nr.text = text
    if red:
        nr.font.color.rgb = RED
    return nr


def replace_span(p, old, new):
    """只把 old→new 的改动部分标红；若跨 run 则退化为整段标红。"""
    for r in p.runs:
        if old in r.text:
            before, after = r.text.split(old, 1)
            r.text = before
            nr = clone_run_after(r, new, True)
            if after:
                clone_run_after(nr, after, False)
            return True
    if old in p.text:
        set_red(p, p.text.replace(old, new, 1))
        return True
    raise KeyError('段落内未找到 %r' % old)


def append_red(p, extra):
    """在段末追加红色文字（原有文字不变）。"""
    clone_run_after(p.runs[-1], extra, True)


def find(doc, sub, nth=0):
    hits = [p for p in doc.paragraphs if sub in p.text]
    if len(hits) <= nth:
        raise KeyError('未找到目标段落：%r（命中 %d 处）' % (sub, len(hits)))
    return hits[nth]


def insert_par_after(anchor, donor, text, red=True, size=None):
    el = copy.deepcopy(donor._p)
    anchor._p.addnext(el)
    p = Paragraph(el, anchor._parent)
    set_text(p, text)
    _color(p, red)
    if size:
        for r in p.runs:
            r.font.size = size
    return p


# ---------------------------------------------------------------- 正文修改
def edit_body(doc):
    log = []

    # 0. 修订说明（红色）
    title_en = find(doc, 'A Standardized AI-to-MCIP Adapter')
    donor = find(doc, '关键词：AI 气象大模型')
    insert_par_after(title_en, donor,
                     '说明：本稿中红色字体为相对《论文_优化稿》的修改或新增内容，黑色为原文；'
                     '定稿前可将红色统一改回黑色并删除本行。', red=True, size=Pt(9))
    log.append('顶部：修订说明（红）')

    # 1. 中文摘要：样本口径 + 拼写（局部标红）
    p = find(doc, '各链条采用统一网格、排放与化学机制')
    replace_span(p, '均完成9天积分。',
                 '除 FengWu 与 FengYuan 末小时缺测外均完成 9 天积分，跨链比较采用共同有效样本掩膜（N=2996）。')
    replace_span(p, 'Pang-Weatheru', 'Pangu-Weather')
    log.append('摘要：样本口径与拼写（局部红）')

    # 2. 英文摘要：样本口径（局部标红）
    p = find(doc, 'All chains complete nine days')
    replace_span(p, 'All chains complete nine days on a common grid with identical emissions and chemistry.',
                 'All chains run for nine days on a common grid with identical emissions and chemistry, and '
                 'cross-chain comparisons use a common valid mask (N = 2996) because the last hourly record '
                 'is missing for two chains.')
    log.append('Abstract：样本口径（局部红）')

    # 3. 2.1 配置：WRF 物理、IC/BC、预热（新增段，整段红）
    anchor = find(doc, '模拟域覆盖京津冀及周边')
    insert_par_after(anchor, anchor,
                     'WRF 采用 V3.9.1.1，物理选项为 WSM6 微物理、RRTMG 长波/短波、YSU 边界层、MM5 相似理论近地面层、'
                     'Noah 陆面与 Kain–Fritsch 积云（据本次运行的 namelist.input 与 rsl 日志）。需要注意，适配器的模板 wrfout '
                     '声明为 Pleim–Xiu 陆面/近地面层与 ACM2 边界层（SF_SURFACE_PHYSICS=7 等），因此两条路径向 MCIP 声明的'
                     '物理方案并不相同，这一差异在 2.3 节作为归因的限定条件说明。化学初边界条件采用 CMAQ 默认 profile'
                     '（ICON/BCON 的 _profile 文件），5 条链条相同；CTL 自 10 月 18 日起算（约 10 天预热），AI 链条自 10 月 27 日'
                     '起算（1 天预热），预热长度不对称的影响见 4.4 节。')
    log.append('2.1：新增 WRF 物理/IC-BC/预热段（整段红）')

    # 4. 2.1 逐小时化说明：拼写与措辞（局部红）
    p = find(doc, 'FengWu与FengYang')
    replace_span(p, 'FengWu与FengYang', 'FengWu 与 FengYuan')
    replace_span(p, '填补成逐小时气象预测', '插值为逐小时气象场')
    log.append('2.1：修正拼写与措辞（局部红）')

    # 5. 2.3 对照框架：物理声明差异（段末追加红字）
    p = find(doc, '对照框架。以CTL为基准')
    append_red(p, '此外，CTL 的 WRF 运行使用 YSU/Noah，而适配器链条声明为 PX/ACM2，二者向 MCIP 声明的物理方案不同，'
                  '故 CTL 与 ERA5-ADP 的差异中还包含陆面与边界层方案声明的差异。')
    log.append('2.3：补充物理方案声明差异（段末红）')

    # 6. 3.1 标题与正文（整段重写，红）
    h = find(doc, '接口输出被 MCIP/CMAQ 无错误消费')
    set_red(h, '3.1 接口输出被 MCIP/CMAQ 解析与执行')
    p = find(doc, '适配器链条的中间文件与CTL链条的WRF输出均被 MCIP 解析成功')
    set_red(p, '适配器链条的中间文件与 CTL 链条的 WRF 输出均被 MCIP 解析成功；ICON/BCON/OCEAN 与 CCTM 均能启动并产出结果。'
               '需要说明的是，FengWu 与 FengYuan 两条链的伪 wrfout 只有 240 个时次（应为 241），其 11 月 4 日的 '
               'METCRO3D 仅含 00—23 UTC，CCTM 在 23:06 因无法插值 DENS 而中止，末小时（11-04 23 UTC）缺失；'
               '因此本文的跨链比较统一采用共同有效样本掩膜（N=2996，见表 5 注）。')
    log.append('3.1：标题与正文重写（红）')

    # 7. 3.2 数值闭合与 PM2.5 口径（新增段，整段红）
    anchor = find(doc, '与 CTL 的一致性/差异性')
    insert_par_after(anchor, anchor,
                     '数值闭合与 PM2.5 统计口径。就接口输出的自洽性而言，ΣΔp 与 PSFC−P_TOP 之差为 0（由构造保证），'
                     '用同一离散公式回算位势的最大残差为 0.25 m（float32 存储舍入），改用面间梯形积分后最大差 42.8 m、'
                     '平均 1.7 m，模式顶 |W| 为 0（ω 质量订正生效）。上述检查只证明数值闭合，不构成对观测的独立验证。'
                     'PM2.5 并非对气溶胶物种的简单求和，而是按模态质量与粒径分数加权：'
                     'PM25_TOT = ATOTI·PM25AT + ATOTJ·PM25AC + ATOTK·PM25CO；按该式复算与 CMAQ 输出的比值为 1.04'
                     '（R = 0.996），粗模态仅约 6% 计入 PM2.5，若直接对全部气溶胶物种求和将高估约 2.1 倍。')
    log.append('3.2：新增数值闭合与 PM2.5 口径段（整段红）')

    # 8. 3.4 实验 B：KZ0UT 作用范围（段末红）
    p = find(doc, '实验 B：KZMIN vs KZ0UT')
    append_red(p, '默认方案中 500 m 以上各层的最小 Kz 恒为 0.01 m²·s⁻¹，KZ0UT 将其一并提高到 1.0 m²·s⁻¹，'
                  '因此该实验同时改变了高空层，而不只是近地层。')
    log.append('3.4：补充 KZ0UT 高空影响（段末红）')

    # 9. 3.4 第一点：取整说明（局部红）
    p = find(doc, '第一，CCTM扩散设置具有明显敏感性')
    replace_span(p, '改变KZ设置使NMB变化约22.3个百分点',
                 '改变KZ设置使NMB变化约22.3个百分点（由未取整值计算为22.349个百分点；按表4取整值相减为22.4）')
    log.append('3.4：22.3/22.4 取整说明（局部红）')

    # 10. 表 5 注（整段重写，红）
    p = find(doc, '理论样本数为14城市×216 h')
    set_red(p, '注：5 条链条统一采用共同有效样本掩膜 N = 2996。理论样本数为 14 城市 × 216 h = 3024；'
               '扣除观测缺测 1 个时次（2025-10-28 10 UTC，14 个样本）与 FengWu/FengYuan 末小时缺失'
               '（2025-11-04 23 UTC，14 个样本）后取交集，即为表中样本数。')
    log.append('表5注：共同掩膜 N=2996（红）')

    # 11. 4.1 第三点：11-04 观测口径 + 拼写（局部红）
    p = find(doc, 'FengYuan 的 RMSE（56.8）与 Pangu 相近')
    replace_span(p, 'PanguWeather', 'Pangu-Weather')
    replace_span(p, '观测为 68.7 μg·m-3',
                 '观测为 70.2 μg·m-3（该链可用的 23 个时次为 68.7 μg·m-3）')
    log.append('4.1：11-04 口径与拼写（局部红）')

    # 12. 4.2 通风相关（整段重写，红）
    p = find(doc, '通风通道的相关证据')
    new_text = p.text.replace(
        '（4 条链条在9天窗口内的有效配对样本共28个（完整组合为36个；有效样本筛选规则需结合统计脚本核对），图 8a），'
        '二者呈负相关（r = -0.43）：通风偏强对应 PM₂.₅ 偏低；把横轴换成 PBLH 偏差后相关性略强（r = -0.44，图 8b），'
        '换成风速偏差则略弱（r = -0.35）。',
        '（4 条链条 × 9 天共 36 个配对样本，ERA5-ADP 作为参考组不进入相关，图 8a），二者呈负相关'
        '（r = %s0.38，n = 36；逐链 r 为 %s0.34 ~ %s0.57）：通风偏强对应 PM₂.₅ 偏低；把横轴换成 PBLH 偏差后'
        '相关性相近（r = %s0.36，图 8b），换成 10 m 风速偏差亦为 r = %s0.38；三者量级相当，仅凭这组相关无法区分 '
        'PBLH 与风速的相对贡献。由于同一天内各链共享同一气象背景，按日整簇重采样得到的 95%% 置信区间为 '
        '%s0.63 ~ +0.03，考虑日际相关后该关系尚不显著，宜作为方向一致的证据而非定量因果证据。'
        % (MINUS, MINUS, MINUS, MINUS, MINUS, MINUS))
    if '这一排序本身就有信息量' in new_text:
        new_text = new_text.split('这一排序本身就有信息量')[0].rstrip()
    set_red(p, new_text)
    log.append('4.2：r 与显著性改写（整段红）')

    # 13. 图 8 图注：标红提示本图已重绘
    p = find(doc, '图 8 偏差归因')
    _color(p, True)
    log.append('图8 图注：标红（图已按 36 样本重绘）')

    # 14. 结论：样本口径（局部红）
    p = find(doc, '接口在 MCIP 消费层面完全可行')
    replace_span(p, '5 条链条均连续稳定积分 9 天',
                 '4 条链条完整积分 9 天，FengWu 与 FengYuan 因伪 wrfout 少 1 个时次而缺失末小时（见 3.1 节），'
                 '跨链比较采用共同掩膜 N=2996')
    log.append('结论1：样本口径（局部红）')

    # 15. 结论：软化强归因（局部红）
    p = find(doc, 'AI 场驱动的 CMAQ 在本过程中的表现')
    replace_span(p, '首先取决于近地面风场与边界层高度的偏差方向',
                 '与近地面风场和边界层高度的偏差方向一致（尚不能证明因果）')
    log.append('结论2：软化强归因（局部红）')

    # 16. 数据与代码可用性（整段重写，红）
    p = find(doc, '适配器代码、5 条链条的运行脚本')
    set_red(p, '适配器代码、5 条链条的运行脚本、站点提取与统计脚本、以及本文全部图件的数据中间产品均在本地仓库中提供'
               '（paper/scripts/、paper/data/）。绘图脚本按图拆分于 paper/scripts/pics/（图 1—图 10 各一个独立脚本，'
               '公共设置见 figs_common.py），并提供一键重建脚本 make_figs.sh（数据提取—指标计算—图件绘制—文档生成），'
               '按 paper/scripts/README.md 即可复现图 1—图 10 与本文统计表。观测数据来自中国环境监测总站城市空气质量'
               '逐小时发布数据；ERA5 来自 ECMWF；AI 场分别由 Pangu-Weather（1/3/6/24 h 权重）、FengWu（fengwu_v2）'
               '与 FengYuan（short/medium 两段 ONNX）推理得到。受许可限制，本地路径不构成公开可获取；投稿前将把代码、'
               '统计中间产品与图示文件归档到公共仓储（Zenodo/Figshare）并给出 DOI，AI 权重按各自许可条款说明获取方式。')
    log.append('数据与代码可用性（整段红）')

    # 17. 图 7 图注：PM2.5 口径（局部红）
    p = find(doc, '图 7 2025-10-30（峰值日）14 城市平均垂直廓线')
    replace_span(p, '（由 CGRID 中 AE6 气溶胶质量物种求和）',
                 '（由 CGRID 的 AE6 气溶胶按模态粒径分数加权求和，口径同 3.2 节）')
    log.append('图7 图注：口径（局部红）')

    # 18. 4.4 局限：四点→五点 + 新增第五条（局部红）
    p = find(doc, '本文的结论受四点限制')
    replace_span(p, '四点限制', '五点限制')
    append_red(p, '第五，化学初边界条件采用 CMAQ 默认 profile 而非常规全球模式场，CTL 的预热（约 10 天）长于 AI 链条（1 天），'
                  '且 CTL 的 WRF 物理声明（YSU/Noah）与适配器链条（PX/ACM2）不同，这些都会影响链条间差异的解释；'
                  '后续需统一预热长度并增加 AI→WRF 对照分支。')
    log.append('4.4：新增第五条局限（局部红）')

    return log


# ---------------------------------------------------------------- 表格修改
def edit_tables(doc):
    log = []
    t5 = doc.tables[4]      # 表 5：PM2.5 统计
    new = {
        1: ['2996', '%s16.8' % MINUS, '%s26.9' % MINUS, '37.0', '50.1', '0.35', '0.58', '0.21'],
        2: ['2996', '+11.1', '+17.9', '35.0', '47.4', '0.65', '0.79', '0.79'],
        3: ['2996', '%s7.1' % MINUS, '%s11.4' % MINUS, '43.1', '58.1', '0.26', '0.56', '0.24'],
        4: ['2996', '+2.4', '+3.8', '29.9', '40.1', '0.64', '0.80', '0.60'],
        5: ['2996', '+6.0', '+9.6', '42.0', '56.8', '0.37', '0.63', '0.39'],
    }
    for ri, vals in new.items():
        row = t5.rows[ri]
        for ci, v in enumerate(vals, start=1):
            set_red(row.cells[ci].paragraphs[0], v)
    log.append('表5：共同掩膜数值（红）')

    t6 = doc.tables[5]      # 表 6：分阶段 NMB
    for row in t6.rows:
        for c in row.cells:
            if 'Pangu-Weater' in c.text:
                set_red(c.paragraphs[0], c.text.replace('Pangu-Weater', 'Pangu-Weather'))
    log.append('表6：拼写（红）')

    t3 = doc.tables[3]      # 表 4：敏感性
    hdr = t3.rows[0].cells[5]
    if '未取整' not in hdr.text:
        set_red(hdr.paragraphs[0], hdr.text.strip() + '（未取整计算）')
    log.append('表4：表头注明未取整（红）')
    return log


# ---------------------------------------------------------------- 附录
APPENDIX = {
    '核对事项': '附录 A 核对事项与处理说明（不属于研究结论）',
    '本节为作者核对清单': '本附录列出自查清单及 v2 稿的处理方式；所列数字与表述均已按仓库数据核对，但不构成新的研究结论。',
    '统计样本：核对3024': '统计样本：3024 = 14 城市 × 216 h；观测缺 2025-10-28 10 UTC 使全部链条为 3010；'
                        'FengWu/FengYuan 另缺 11-04 23 UTC，故为 2996。v2 统一采用共同掩膜 N = 2996 重算表 5。',
    '时间口径：统一UTC': '时间口径：模型为 UTC、观测为北京时，已按 +8 h 对齐；日均按 UTC 日统计；11-04 观测 24 h 均值为 70.2、'
                       'FengYuan 可用的 23 个时次为 68.7，正文已分别注明；P4 标注为 11-03—11-04（至 11-05 00 UTC）。',
    '可复现配置：补充MCIP版本': '可复现配置：MCIP V4.4；WRF V3.9.1.1，物理为 WSM6/RRTMG/YSU/MM5 相似理论/Noah/KF（2.1 节）；'
                            'AI 权重版本见 2.1 节与数据可用性说明；IC/BC 为 CMAQ 默认 profile；CTL 预热约 10 天、AI 链 1 天（2.1、4.4 节）。',
    '接口契约：补充64个变量': '接口契约：64 个变量的维度与来源见表 1；其中 17 个变量未写 units 属性，接口对缺时次不做插值（缺时次即报错），'
                          '已列入后续修正与附录说明。',
    '物理验证：提供静力平衡': '物理验证：ΣΔp 与 PSFC−P_TOP 之差为 0，静力回算最大残差 0.25 m，换积分方式最大 42.8 m/平均 1.7 m，'
                          '模式顶 |W| = 0；PM2.5 按模态粒径分数加权复算与 CMAQ 输出的比值为 1.04（R = 0.996）（3.2 节）。'
                          '这些属数值闭合，不能替代独立观测验证。',
    '机制验证：优先补充独立风速': '机制验证：缺少独立 PBLH 与风廓线观测，4.2 节仅报告方向一致的证据；AI→WRF 对照、变量替换与过程收支列为后续工作。',
    '敏感性配置：核对KZMIN': '敏感性配置：日志确认 KZMIN=Y 与 KZ0UT 两种设置；默认方案 500 m 以上各层最小 Kz 恒为 0.01 m²·s⁻¹，'
                          'KZ0UT 全层为 1.0；ΔNMB = 22.3 由未取整值计算（按表 4 取整值相减为 22.4）。',
    '参考文献与开放性：逐条核验': '参考文献与开放性：20 条文献经 Crossref/DataCite/DOAJ/期刊官网核验；本地路径不构成公开获取，'
                             '投稿前提供代码与数据的归档 DOI。',
}


def edit_appendix(doc):
    n = 0
    for p in doc.paragraphs:
        for key, new in APPENDIX.items():
            if p.text.strip().startswith(key):
                set_red(p, new)
                n += 1
                break
    return n


# ---------------------------------------------------------------- 图 8 替换
def replace_fig8(doc):
    png = os.path.join(PAPER, 'figures', 'fig8_attribution.png')
    if not os.path.exists(png):
        return '图8：未找到新图，跳过'
    cap = None
    for p in doc.paragraphs:
        if p.text.strip().startswith('图 8 偏差归因'):
            cap = p
            break
    if cap is None:
        return '图8：未找到图注，跳过'
    prev = cap._p.getprevious()
    while prev is not None:
        blips = prev.xpath('.//a:blip')
        if blips:
            rid = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            part = doc.part.related_parts[rid]
            part._blob = open(png, 'rb').read()
            return '图8：已替换为 36 样本版本'
        prev = prev.getprevious()
    return '图8：图注前未找到图片'


def main():
    doc = Document(SRC)
    log = edit_body(doc)
    log += edit_tables(doc)
    n = edit_appendix(doc)
    log.append('附录：核对事项 → 处理说明（%d 段，红）' % n)
    log.append(replace_fig8(doc))

    # 统一拼写
    typos = {'PanguWeather': 'Pangu-Weather', 'Pang-Weatheru': 'Pangu-Weather',
             'Pangu-Weater': 'Pangu-Weather', 'FengYang': 'FengYuan'}
    fixed = 0
    for par in doc.paragraphs:
        for a, b in typos.items():
            if a in par.text:
                replace_span(par, a, b)
                fixed += 1
    log.append('统一拼写：%d 处（红）' % fixed)

    doc.save(DST)
    print('saved:', DST)
    for i, item in enumerate(log, 1):
        print('  %2d. %s' % (i, item))


if __name__ == '__main__':
    main()
