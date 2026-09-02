#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题库校验：在部署前拦住会让页面出错或判分错误的改动。

检查项：
  选择题  每题至少 4 个选项、选项互不重复、答案下标在范围内、题干全库唯一
  填空题  文本中 ____ 的个数必须等于答案组数，且每组至少 1 个可接受答案
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

MCQ_RE = re.compile(r'\{c:"(.*?)",q:"(.*?)",o:\[(.*?)\],a:(\d+),e:"(.*?)"\}')
STR_RE = re.compile(r'"([^"]*)"')
FILL_RE = re.compile(
    r'\{c:"(.*?)",t:"(.*?)",\s*\n\s*q:"(.*?)",\s*\n\s*a:\[(.*?)\]\}', re.S
)
GROUP_RE = re.compile(r"\[[^\[\]]*\]")

errors = []
mcq_total = 0
seen_q = {}

for path in sorted(glob.glob(os.path.join(SITE, "bank-mcq-*.js"))):
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    items = MCQ_RE.findall(src)
    if not items:
        errors.append("%s: 没有解析出任何选择题，格式可能被改坏了" % name)
        continue
    # 条目数应与 "{c:" 出现次数一致，防止某题写错格式被静默跳过
    declared = src.count('{c:"')
    if declared != len(items):
        errors.append(
            "%s: 有 %d 条记录，但只有 %d 条能被解析，请检查格式"
            % (name, declared, len(items))
        )
    mcq_total += len(items)
    for _c, q, o, a, _e in items:
        opts = STR_RE.findall(o)
        where = "%s《%s》" % (name, q[:24])
        if len(opts) < 4:
            errors.append("%s: 只有 %d 个选项" % (where, len(opts)))
        if len(set(opts)) != len(opts):
            errors.append("%s: 存在完全相同的选项" % where)
        if int(a) >= len(opts):
            errors.append("%s: 答案下标 %s 越界" % (where, a))
        if q in seen_q:
            errors.append("%s: 题干与 %s 中的题重复" % (where, seen_q[q]))
        else:
            seen_q[q] = name

fill_path = os.path.join(SITE, "bank-fill.js")
with open(fill_path, encoding="utf-8") as fh:
    fill_src = fh.read()
fills = FILL_RE.findall(fill_src)
declared = fill_src.count('{c:"')
if declared != len(fills):
    errors.append(
        "bank-fill.js: 有 %d 条记录，但只有 %d 条能被解析，请检查格式"
        % (declared, len(fills))
    )
for _c, t, q, a in fills:
    blanks = q.count("____")
    groups = GROUP_RE.findall(a)
    if blanks != len(groups):
        errors.append(
            "bank-fill.js《%s》: %d 个空位对应 %d 组答案" % (t, blanks, len(groups))
        )
    for i, g in enumerate(groups):
        if not STR_RE.findall(g):
            errors.append("bank-fill.js《%s》: 第 %d 空没有可接受答案" % (t, i + 1))

# 试卷需要 28 选择 + 2 填空，题库必须够抽
if mcq_total < 28:
    errors.append("选择题不足 28 道，无法组卷（当前 %d 道）" % mcq_total)
if len(fills) < 2:
    errors.append("填空大题不足 2 道，无法组卷（当前 %d 道）" % len(fills))

print("选择题 %d 道，填空大题 %d 道" % (mcq_total, len(fills)))
if errors:
    print("\n题库校验未通过：")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
print("题库校验通过")
