Pudao Formal Lane · 最简 TDD 用例（5 条）

目的：以最小集用例验证 Formal Gate（SMT/Z3）在 MVP 阶段对 I1–I7 关键不变式的把关能力。
运行入口：pudao formal check -f <strategy.yaml>（或 pytest）。

术语：
status ∈ {sat,unsat,unknown}；allow = true 仅当 status="sat" 且无致命问题。
reasons 为违规原因字符串列表；details.Ix 为各不变式子结果（ok|fail）。

公共前提

资源/示例位于：

examples/strategy-chengdu-ring-vsl.yaml

examples/strategy-cd-ring-incident-rm-vms.yaml

CLI 或测试调用统一产出 JSON，断言从中读取。

T-001｜VSL 正例（应通过）

目标不变式：I1/I2/I3/I4/I5/I6/I7 全部满足

输入策略：examples/strategy-chengdu-ring-vsl.yaml（不改动）

期望输出：

status = "sat"，allow = true

reasons = []

details.* = "ok"

T-002｜事故策略含互斥动作（应拒绝）

该用例验证 I6 互斥：同一匝道同时配置 ramp_metering 与 ramp_closure。

目标不变式：I6

输入策略：examples/strategy-cd-ring-incident-rm-vms.yaml（原样：ramp-ne-202-in 既有 metering 又有 closure）

期望输出：

status = "unsat"，allow = false

reasons 含："mutually_exclusive_actions"（示例：mutually_exclusive_actions: ramp ramp-ne-202-in metering+closure）

details.I6_conflict = "fail"

T-003｜非法 segment_id（应拒绝）

该用例验证 I1 结构与引用合法性。

目标不变式：I1

输入策略：以 strategy-chengdu-ring-vsl.yaml 为基，将一个 segment_id 改为不存在的（如 cd-se-999）。

测试中通常写入临时文件：examples/tmp-invalid.yaml

期望输出：

status = "unsat"，allow = false

reasons 含："invalid_reference"（指明非法 ID）

details.I1_structure = "fail"

T-004｜相邻段速差超限（应拒绝）

该用例验证 I2 空间平滑。

目标不变式：I2

输入策略：以 strategy-chengdu-ring-vsl.yaml 为基，把某一段的 VSL 改为极端值（如 70 → 40），触发与相邻段的 |Δ| > max_delta。

测试中通常写入临时文件：examples/tmp-vsl-bad.yaml

期望输出：

status = "unsat"，allow = false

reasons 含："spatial_smoothness_violated"

details.I2_spatial = "fail"

T-005｜存在 ramp_closure 但无有效回滚（应拒绝）

该用例验证 I5 回滚可行性 / I7 控制流时序（有限步）。

目标不变式：I5（必要时 I7）

输入策略：以 strategy-cd-ring-incident-rm-vms.yaml 为基，删除 rollout.max_revert_time_s（或将其设成极大、超出 guardrails.max_closure_s）。

测试中通常写入临时文件：examples/tmp-no-rollback.yaml

期望输出：

status = "unsat"，allow = false

reasons 含："rollback_missing_or_infinite"（或伴随 flow_invariants_violated）

details.I5_rollback = "fail"（若同时违反 I7，details.I7_flow = "fail"）

运行建议

逐条运行：

pytest -vv -k test_vsl_strategy_happy_path
pytest -vv -k test_incident_strategy_happy_path     # 该用例期望 unsat
pytest -vv -k test_invalid_segment_id
pytest -vv -k test_spatial_smoothness_violation
pytest -vv -k test_closure_without_rollback


或批量运行：

pytest -vv


说明：本文件仅覆盖“最简 5 条”基线用例，确保 MVP 的 Formal Gate 能筛出最典型问题；更多扩展（条件互斥正例、时间片建模等）请另行补充到后续用例集。