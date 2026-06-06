# evidence-quality-signals.yml schema

## 目的

mainline-analysis 子 agent 在抽取 evidence-matrix.md 内容的同时产出该 yaml，供 3a subagent 做"证据交叉验证"复审。

## 产出位置

`patent/<patent-slug>/evidence/evidence-quality-signals.yml`（与 evidence-matrix.md 同级）

## schema

```yaml
generated_at: <YYYY-MM-DD>
schema_version: v1

ip_evidence_map:
  - ip_id: <IP-XX>
    evidence_anchors:
      - source: <M-编号>
        source_type: <七档之一>
        confidence: <三档之一>
        verbatim_length: <字数整数>
        anchor_path: <evidence-matrix.md#m-xx>
    cross_source_count: <整数>
    independent_source_count: <整数>
    role_in_claim: <use 字段值，对齐 prior-art>

aggregate_signals:
  total_ips: <整数>
  ips_with_high_tier_only: <整数>
  ips_with_only_low_tier: <整数>
  ips_with_single_source: <整数>
  ips_below_cross_verification_threshold: <整数>
```

## source_type 七档（描述资料形式）

| source_type | 含义 |
|---|---|
| executable-source | 可直接编译/运行的源码 |
| code-fragment | 源码片段（截图、节选、对话粘贴） |
| runtime-data | 可读到具体数值的运行时数据、日志、benchmark |
| data-visualization | 图表（带数值或带坐标轴） |
| design-document | 设计文档、技术报告（叙述性） |
| paper-or-spec | 公开论文、行业规范 |
| narrative | 叙述性资料（会议纪要、口头描述、笔记） |

## confidence 三档（描述可信度，与 source_type 解耦）

| confidence | 判据 |
|---|---|
| high | 可独立验证：第三方拿到这份资料能复现相同结论 |
| medium | 可读但不完整：能看出技术意图与关键结论，但缺独立验证渠道 |
| low | 间接呈现：原文残缺、需要二次解读，或抽取过程本身有损 |

## 关键纪律：不查文件后缀，按内容判

例：

- .png 含完整可读的源码函数体 → source_type=code-fragment, confidence=low（呈现方式有损）
- .png 是 benchmark 折线图带坐标轴和数值 → source_type=data-visualization, confidence=medium
- .pdf 是公司内部技术报告含完整数据 → source_type=design-document, confidence=medium
- .pdf 是公开论文 → source_type=paper-or-spec, confidence=high
- .docx 是会议纪要 → source_type=narrative, confidence=low
- 对话粘贴的代码片段 → source_type=code-fragment, confidence=low（来源已脱离原文件）

## 子 agent 强制思考四步

抽取 subagent 给每条 IP 标 confidence 时，必须依次回答：

1. 这份资料的内容是源码、数据、文档、还是叙述？→ source_type
2. 第三方拿到这份资料能不能独立复现结论？→ 若能 → high
3. 内容完整但缺独立验证渠道？→ medium
4. 内容残缺或经过有损呈现？→ low

不允许跳过这四步直接拍 confidence。

## cross_source_count 与 independent_source_count 规则

- `cross_source_count`：不同 source_type 计为不同来源；同 source_type 不同文件计为不同来源；同文件不同 verbatim 片段计为同一来源
- `independent_source_count`：跨"来源者"独立才算（用户提供 + 项目仓库 + 公开文档 = 不同来源者）；同一作者的不同文件不算独立

## aggregate_signals 计算规则

- `ips_with_high_tier_only`：该 IP 的所有 anchor confidence 都是 high
- `ips_with_only_low_tier`：该 IP 的所有 anchor confidence 都是 low
- `ips_with_single_source`：cross_source_count == 1
- `ips_below_cross_verification_threshold`：cross_source_count < 2 或 independent_source_count < 2
