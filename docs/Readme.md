
# Pudao PFSB — Formal Lane MVP

> 朴道平台控制平面（PFSB）的最小可用版本：对**策略 DSL**进行**形式化规约校验**（SMT/Z3），作为进入仿真/执行前的**必经Formal Gate**。
> 设计背景与理念见设计蓝图文档（v2）：[《朴道平台全局设计蓝图》](/mnt/data/朴道平台全局设计蓝图 v2-gpt5-think.docx)

## ✨ 功能要点

* **策略 DSL/IR**：统一的 JSON/YAML 结构，强 Schema 校验（JSON Schema + Pydantic）。
* **不变式 I1–I7**：结构合法性、空间平滑、时间稳定、安全边界、回滚可行性、互斥冲突、控制流时序（有限步）。
* **SMT 求解（Z3）**：将策略约束编译到 SMT，产出 `sat/unsat/unknown`。
* **证据落盘（Evidence）**：每次校验输出**绝对时间戳**与**阶段耗时**（解析/约束/SMT/汇报），写入 NDJSON。
* **CLI + 测试**：一条命令校验策略；配套 5 条最小 TDD 用例保障回归质量。

---

## 🚀 快速开始

### 1) 环境要求

* Python **3.9+**
* 操作系统：macOS / Linux / Windows（均支持）
* 需能安装 `z3-solver`

### 2) 安装

```bash
# 建议先创建虚拟环境
pip install -e ".[dev]"
```

> 依赖要点：
>
> * `z3-solver>=4.12,<5`
> * `pydantic>=1.10,<2`（本版使用 v1 API）
> * `PyYAML`、`jsonschema`、`pytest`（dev）

### 3) 运行一次校验

```bash
# 查看命令
pudao --help

# 校验示例策略（VSL 正例）
pudao formal check -f examples/strategy-chengdu-ring-vsl.yaml
```

示例输出（节选）：

```json
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
  },
  "timestamps": {
    "start_utc": "2025-11-17T15:42:10.312Z",
    "parse_end_utc": "2025-11-17T15:42:10.317Z",
    "smt_start_utc": "2025-11-17T15:42:10.319Z",
    "smt_end_utc": "2025-11-17T15:42:10.331Z",
    "end_utc": "2025-11-17T15:42:10.336Z"
  },
  "timings_ms": {
    "parse_ms": 5.25,
    "invariants_ms": 3.02,
    "smt_ms": 12.05,
    "solver_ms": 16.21,
    "report_ms": 3.29,
    "total_ms": 24.75
  }
}
```

---

## 📂 目录结构

```
pudao/
  cli/
    pudao_cli.py              # CLI 入口（pudao formal check）
  dsl/
    strategy_schema.json      # JSON Schema
    models.py                 # Pydantic IR 模型
    parser.py                 # 解析 + Schema 校验 + BOM 兼容
    id_registry.py            # 资源白名单/ID 注册（MVP 内存版）
  smt/
    invariants.py             # I1–I7 Python 侧快速判错
    encoder.py                # Z3 编码
    solver.py                 # 汇总求解 + 细粒度计时（SMT/不变式/总耗时）
  gate/
    formal_gate.py            # Formal Gate 对外接口（含证据落盘）
  evidence/
    evidence.py               # Evidence NDJSON 工具
examples/
  strategy-chengdu-ring-vsl.yaml
  strategy-cd-ring-incident-rm-vms.yaml      # 互斥负例
  strategy-cd-ring-incident-rm-vms-fixed.yaml# 修正版正例（如已添加）
tests/
  test_formal_basic.py        # 5 条最简 TDD 用例
docs/
  formal-lane-mvp.md
  tests-formal-lane-tdd.md
```

---

## 🧾 DSL & Schema（摘要）

* **入口格式**：YAML/JSON；根节点必须是对象。
* **核心字段**：`strategy_id, version, scope{segments/ramps/vms}, actions[...], guardrails, rollout, metadata`
* **动作类型**：`vsl | ramp_metering | ramp_closure | vms_message`
* **示例**：`examples/strategy-chengdu-ring-vsl.yaml`

---

## 🧩 不变式 I1–I7（MVP）

* **I1 结构与引用**：根为对象、字段完整、ID 合法（见 `id_registry`），域值范围正确。
* **I2 空间平滑**：相邻段 `|ΔV| ≤ max_delta`（邻接表 MVP 硬编码）。
* **I3 时间稳定**：同段不出现多值冲突，可选与 `max_changes_per_5min` 一致性检查。
* **I4 安全边界**：`min_vsl ≤ value ≤ max_vsl`，禁止用 `vsl=0` 代替封路。
* **I5 回滚可行性**：强干预（如 ramp_closure）要求有限回滚时间，与 `guardrails.max_closure_s` 一致。
* **I6 互斥冲突**：同一对象不得同时下互斥指令（如同一 ramp 同时 metering+closure）。
* **I7 控制流时序（有限步）**：含封闭/强干预须具备回滚；`ramp_closure` 须有时限且在上限内。

> SMT 端（Z3）用于**统一可满足性**判断；Python 端（`invariants.py`）用于高可读的快速失败原因。

---

## 🧪 测试（最简 5 用例）

运行：

```bash
pytest -vv -s
```

用例与期望（详见 `docs/tests-formal-lane-tdd.md`）：

1. **T-001**：VSL 正例 → `sat / allow=true`
2. **T-002**：事故策略含互斥动作（同一 ramp metering+closure）→ `unsat / mutually_exclusive_actions`
3. **T-003**：非法 `segment_id` → `unsat / invalid_reference`
4. **T-004**：相邻段速差超限 → `unsat / spatial_smoothness_violated`
5. **T-005**：存在 `ramp_closure` 但无回滚 → `unsat / rollback_missing_or_infinite`

> 测试中会打印每条用例的**开始/SMT开始/SMT结束/结束**时间戳与解析/SMT/总耗时；同时写入 Evidence（见下）。

---

## 🧾 Evidence（证据落盘）

每次 Formal 校验（无论成功失败）会自动将证据写入 **NDJSON**：

* 默认路径：`evidence/formal_timings.ndjson`
* 记录内容：

  * `run_id`、`ts_utc`、可选 `label`
  * `input`（路径、大小、sha256）
  * `verdict`（status/allow/top reason/details）
  * `timestamps`（start/parse_end/smt_start/smt_end/end）
  * `timings_ms`（parse/invariants/smt/solver/report/total）

可配置的环境变量：

```bash
# 自定义证据文件输出路径
export PFSB_EVIDENCE_FILE="reports/run_$(date +%Y%m%d_%H%M%S).ndjson"

# 固定本次运行批次ID，便于串联CI/日志
export PFSB_RUN_ID="ci-1234"

# 给本次批次打标签（如 unit-tests / smoke / nightly）
export PFSB_LABEL="unit-tests"
```

---

## 🛠️ CLI

```bash
# 校验一个策略文件
pudao formal check -f <path/to/strategy.yaml>

# 也可用 python -m 方式（不安装脚本时）
python -m pudao.cli.pudao_cli formal check -f examples/strategy-chengdu-ring-vsl.yaml
```

输出字段说明：

* `status`: `sat | unsat | unknown`
* `allow`: 仅当 `status="sat"` 且无致命问题时为 `true`
* `reasons`: 违规原因字符串列表
* `details`: 各不变式子结果（`ok|fail`）
* `timestamps` / `timings_ms`: 详见 Evidence 章节

---

## ❗排错指引

* **只跑到一个用例**：确认 `pytest -vv --collect-only` 能发现 5 条；检查是否启用了 `-k` 过滤或 `-x` 仅首失败。
* **Schema 提示根不是对象**：确认文件非空、编码为 UTF-8；MVP 解析已支持 `utf-8-sig`（BOM）。
* **Pydantic 报 v2 API**：本版依赖 v1，确保安装 `<2`。
* **Z3 安装失败**：升级 pip 或换 Python 版本（≥3.9）；国内网络可配置镜像源。

---

## 🗺️ 路线图（出 MVP 后）

* **符号规划器（确定性策略合成）**：将 Chat/意图转为 `intent.json` 后，用 Z3/CP/ASP 合成唯一策略，再走 Formal。
* **拓扑/资源服务化**：邻接关系、ID Registry 从服务动态加载。
* **时间扩展**：I3 引入离散时间片；I7 引入 LTL/模型检验工具做全路径验证。
* **仿真联动**：Formal 通过即自动触发 Simulate 回归；失败自动生成修复建议。
* **治理与审计**：证据与权限、回滚脚本、审计台账全面打通。

---

## 📚 参考

* 蓝图文档（v2）：[《朴道平台全局设计蓝图》](/mnt/data/朴道平台全局设计蓝图 v2-gpt5-think.docx)
* 规范文档：`docs/formal-lane-mvp.md`
* 测试说明：`docs/tests-formal-lane-tdd.md`

---

**维护人**：Pudao Platform · PFSB
**完成定义（DoD）**：5 条 TDD 全绿；CLI 可用；Evidence 落盘；与设计蓝图一致的 I1–I7 规则与 SMT 校验。
