Pudao PFSB · Formal Lane MVP 规格（SMT 校验）
版本：v0-MVP
状态：可实现 / 已配套示例与测试
范围：仅覆盖形式化通道（Formal Lane）——用 SMT 求解器（Z3）对“策略 DSL/IR”进行规约一致性、安全边界与流程时序（有限步）校验。
显式不包含：因果推断、CausalScore、全量仿真、运行时 LTL 模型检验。

0. 背景与目标
朴道 PFSB 的核心流程遵循 Sense → Think → Simulate → Act → Learn。
MVP 阶段，我们将“策略能否进入 Simulate”的唯一门槛定义为Formal Gate：


给定一份策略（Strategy IR），将其编译为 SMT 约束；


由 Z3 判断是否存在满足所有不变式与安全边界的赋值。


通过（SAT）→ 允许进入仿真；不通过（UNSAT/UNKNOWN）→ 退回修改。



1. 范围与架构
1.1 作用域（本版只做 Formal）

输入：StrategySpec/DSL（YAML/JSON）
输出：{allow, status, reasons, details} 的结构化结果与证据日志

1.2 组件与流转
StrategySpec (YAML/JSON)
      ↓ 解析 & JSON Schema 校验
Strategy IR (Pydantic 模型)
      ↓ 不变式规则（Python）与 SMT 编码（Z3 AST）
Z3 求解器（sat / unsat / unknown）
      ↓
Formal Gate 输出（JSON）  →  Evidence（NDJSON）


2. 术语


StrategySpec/DSL：用户/UI/Chat 产生的策略描述，面向人/工具可读。


Strategy IR：内部统一结构（JSON/Pydantic），SMT 编码的直接输入。


Guardrails：策略硬边界（法定最小限速、相邻段速差上限等）。


Formal Gate：形式化门禁；MVP 中由 Z3 提供可满足性背书。


I1–I7：MVP 的七类不变式约束（见 §5）。



3. Strategy IR（MVP 最小子集）

Schema 文件：pudao/dsl/strategy_schema.json
模型类：pudao/dsl/models.py::StrategyIR

{
  "strategy_id": "string",
  "version": "string",
  "scope": {
    "roadchain_id": "string",
    "segments": ["string"],
    "ramps": ["string"],
    "vms": ["string"]
  },
  "actions": [
    {
      "type": "vsl | ramp_metering | ramp_closure | vms_message",
      "segment_id": "string",
      "ramp_id": "string",
      "vms_id": "string",
      "value": 80,
      "veh_per_hour": 400,
      "ttl_s": 300,
      "max_duration_s": 600,
      "condition": "string",
      "text": "string"
    }
  ],
  "guardrails": {
    "min_vsl": 60,
    "max_vsl": 100,
    "max_delta": 20,
    "max_changes_per_5min": 2,
    "max_ramp_queue": 300,
    "max_closure_s": 900,
    "always_keep_emergency_lane_free": true
  },
  "rollout": {
    "mode": "immediate | canary",
    "max_revert_time_s": 600
  },
  "metadata": {
    "author": "string",
    "source": "string",
    "rationale": "string"
  }
}


说明：


condition 在 MVP 中不做语义解析（仅作标签），后续可升级；


Schema 允许 additionalProperties: true，便于增量演化。




4. 示例（可直接用于测试）
4.1 VSL 正例
examples/strategy-chengdu-ring-vsl.yaml
strategy_id: "cd-ring-vsl-ampeak-001"
version: "0.1.0"
scope:
  roadchain_id: "rc-cd-ring-se"
  segments: ["cd-se-101", "cd-se-102", "cd-se-103", "cd-se-104"]
actions:
  - type: "vsl"
    segment_id: "cd-se-101"
    value: 80
  - type: "vsl"
    segment_id: "cd-se-102"
    value: 80
  - type: "vsl"
    segment_id: "cd-se-103"
    value: 70
  - type: "vsl"
    segment_id: "cd-se-104"
    value: 70
guardrails:
  min_vsl: 60
  max_vsl: 100
  max_delta: 20
  max_changes_per_5min: 2
  always_keep_emergency_lane_free: true
rollout:
  mode: "canary"
  max_revert_time_s: 600
metadata:
  author: "ops-chengdu"
  source: "ui-form"

4.2 事故应急正例（fixed）
examples/strategy-cd-ring-incident-rm-vms-fixed.yaml
strategy_id: "cd-ring-incident-rm-vms-001-fixed"
version: "0.1.0"
scope:
  roadchain_id: "rc-cd-ring-ne"
  segments: ["cd-ne-201", "cd-ne-202"]
  ramps: ["ramp-ne-201-in", "ramp-ne-202-in"]
  vms: ["vms-ne-201-main", "vms-ne-150-bypass"]
actions:
  - type: "ramp_metering"
    ramp_id: "ramp-ne-201-in"
    veh_per_hour: 400
  - type: "ramp_closure"
    ramp_id: "ramp-ne-202-in"
    max_duration_s: 600
  - type: "vms_message"
    vms_id: "vms-ne-201-main"
    text: "前方事故，减速慢行，请勿占用应急车道"
  - type: "vms_message"
    vms_id: "vms-ne-150-bypass"
    text: "前方绕城缓行，建议经XX绕行"
guardrails:
  min_vsl: 60
  max_vsl: 100
  max_delta: 20
  max_closure_s: 900
  always_keep_emergency_lane_free: true
rollout:
  mode: "immediate"
  max_revert_time_s: 600
metadata:
  author: "tmc-chengdu"
  source: "runbook-template"


对比用负例（互斥）：同一 ramp-ne-202-in 同时出现 ramp_metering 与 ramp_closure，应判 UNSAT。


5. 不变式（I1–I7）

实现位置：pudao/smt/invariants.py（Python 快速判错） + pudao/smt/encoder.py（Z3 编码）
求解：pudao/smt/solver.py 汇总 reasons 与 SMT 结果

I1. 结构与引用合法性


目标：防止“错 ID/错字段/空根”等。


要点：


根为对象；必填字段非空；动作类型属于枚举；


segment_id/ramp_id/vms_id 均在 ID Registry 中；


基本域约束：ttl_s>0、max_revert_time_s>0 等。




失败码：schema_violation, invalid_reference。


I2. 空间平滑（相邻段速差）


目标：消除“锯齿限速”。


约束：对相邻 (i,j)：|vsl_i - vsl_j| ≤ max_delta。


失败码：spatial_smoothness_violated。


邻接表：MVP 硬编码（cd-se-101..104），后续读取静态拓扑。


I3. 时间平滑与防抖动（MVP 有限步）


目标：避免单策略内“多值冲突/往返闪烁”。


约束：同一 segment_id 不允许多条不同 vsl 值并存；
可选一致性检查：max_changes_per_5min 与 ttl_s 不相悖。


失败码：temporal_stability_violated。


I4. 安全边界不变式


目标：不产生“明显违法/危险配置”。


约束：min_vsl ≤ value ≤ max_vsl；禁止 vsl=0 伪装封路；
always_keep_emergency_lane_free=true 时不允许修改应急车道（MVP 不提供该动作）。


失败码：safety_bounds_violated。


I5. 回滚可行性（可恢复性）


目标：高风险动作必须可在有限时间内恢复。


约束：若出现 ramp_closure 等强干预，则
rollout.max_revert_time_s 必填且 ≤ guardrails.max_closure_s（若配置）。


失败码：rollback_missing_or_infinite。


I6. 互斥动作冲突


目标：同一对象同一策略内不得收互斥指令。


示例：同一 ramp_id 的 ramp_metering 与 ramp_closure 互斥；
同一 vms_id 的多条 vms_message 互斥（MVP 不引入优先级）。


形式化：对对象 o、互斥集 {a1,a2,...}：Σ is_applied(a_i,o) ≤ 1。


失败码：mutually_exclusive_actions。


I7. 控制流时序不变式（有限步）


目标：基本流程正确：有应答/有失败处理/封闭有限时。


约束（MVP 静态版）：


发 apply 的策略（rollout.mode=immediate/canary）若含封闭/强干预，则必须具备回滚（见 I5）；


任一 ramp_closure 必须带 max_duration_s 且 ≤ guardrails.max_closure_s。




失败码：flow_invariants_violated。



备注：I3 面向“数值-时间”；I7 面向“流程-时序”。MVP 不引入 LTL 工具，仅做有限步充要条件的静态可行性检查。


6. SMT 后端与环境


Solver：Z3（z3-solver>=4.12,<5）


绑定：Python（首选），保留 Go/Java 扩展空间


依赖：pydantic<2（使用 v1 API）、PyYAML、jsonschema、pytest（dev）


安装与运行（包模式）：
pip install -e ".[dev]"
pudao formal check -f examples/strategy-chengdu-ring-vsl.yaml
pytest -vv


7. CLI 与输出格式
7.1 命令
# 运行 Formal 校验
pudao formal check -f <path/to/strategy.yaml>

7.2 输出（示例）
{
  "allow": true,
  "status": "sat",
  "reasons": [],
  "details": {
    "I1_structure": "ok",
    "I2_spatial": "ok",
    "I3_temporal": "ok",
    "I4_safety": "ok",
    "I5_rollback": "ok",
    "I6_conflict": "ok",
    "I7_flow": "ok"
  }
}

失败示例：
{
  "allow": false,
  "status": "unsat",
  "reasons": [
    "mutually_exclusive_actions: ramp ramp-ne-202-in metering+closure"
  ],
  "details": {
    "I1_structure": "ok",
    "I2_spatial": "ok",
    "I3_temporal": "ok",
    "I4_safety": "ok",
    "I5_rollback": "ok",
    "I6_conflict": "fail",
    "I7_flow": "ok"
  }
}


8. 目录结构建议
pudao/
  dsl/         # DSL/IR & Schema & ID Registry
  smt/         # Z3 编码与不变式
  gate/        # Formal Gate 封装
  cli/         # 命令行入口
examples/      # 可运行样例
tests/         # TDD 用例
docs/          # 本文档与测试清单


9. TDD 测试映射（摘要）

详见 docs/tests-formal-lane-tdd.md（对应我们在对话中已给出的清单）。这里给核心映射：



T-001：VSL 正例 → sat/allow=true


T-101：非法 segment_id → unsat/invalid_reference


T-201：邻接速差超标 → unsat/spatial_smoothness_violated


T-301：同段多值冲突 → unsat/temporal_stability_violated


T-401：低于法定下限 → unsat/safety_bounds_violated


T-501：closure 无回滚 → unsat/rollback_missing_or_infinite


T-601：ramp metering+closure → unsat/mutually_exclusive_actions


T-701：closure 有时限且可回滚（正例）→ sat



10. 配置与可扩展点


邻接关系（I2）：MVP 硬编码在 invariants.py/encoder.py，后续改为从“拓扑服务/静态表”加载。


ID Registry（I1）：MVP 以内存白名单，后续接入真实资源注册中心。


条件互斥（I6 扩展）：后续可通过 phase/priority/condition 轻量表达，或引入可验证的布尔表达式子集。


时间不变式：I3 可升级为离散时间片建模；I7 可接入 LTL/模型检验 做全路径验证。


Evidence：当前为 NDJSON 追记；后续对接 PFSB 统一证据仓。



11. 已知限制


不解析 condition 的语义，默认视为标签；


不做运行时日志的在线 LTL 监控；


邻接/ID 由内存表驱动；


Z3 仅编码了“最小可满足约束”，多数可读的错误首先由 Python 不变式检查直接给出。



12. 安全与治理


所有拒绝（UNSAT/UNKNOWN）均不允许进入仿真/执行；


Formal Gate 的结论与约束摘要均写入 Evidence，供审计与追责；


不可跳过：任何“直接生效”的策略必须先过 Formal（I7 集成约束）。



13. 完成定义（DoD）


对“VSL 正例 / 事故应急正例（fixed）”返回 sat/allow=true；


在典型违规（ID 非法、速差超标、互斥、无回滚、越界值）返回 unsat 且 reasons 明确；


CLI 可用、测试可跑、Evidence 可落；


约束实现与本文档一致，代码中注明 I1–I7 的对应关系。



14. 路线图（出 MVP 后）


条件互斥语义：解析受限布尔表达式或引入 phase/priority。


拓扑/资源服务化：邻接关系、ID Registry 从服务拉取。


时间扩展：I3 引入离散时间片；I7 引入 LTL 模型检验（SPIN/NuSMV/PRISM）。


与 Simulate/Act 编排联动：Formal 通过策略进入自动仿真/回归；失败自动生成修复建议。


治理与审计：Formal/Evidence 与权限、审计、回滚脚本打通。



15. 附：快速命令清单
# 安装（开发模式）
pip install -e ".[dev]"

# 运行 Formal 校验
pudao formal check -f examples/strategy-chengdu-ring-vsl.yaml
pudao formal check -f examples/strategy-cd-ring-incident-rm-vms-fixed.yaml

# 运行测试
pytest -vv


维护人：Pudao Platform · PFSB 小组
变更记录：


v0-MVP：首版发布。支持 I1–I7、Z3、CLI、样例与 TDD 映射。


