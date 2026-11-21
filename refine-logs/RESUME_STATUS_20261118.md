# QAH 仿真恢复记录

记录时间：2026-11-18 13:37（Asia/Shanghai）。承接 [进度规划](PROGRESS_AND_NEXT_STEPS_20261118.md)，当前为 **P0 恢复完成、P1 计算中**；全计划尚未验收。

- 恢复前核对实际进程，没有残留 OOMMF、控制器或报告等待任务。
- 圆形 1 nm 前 40 个场点由 10 个已通过子算例组成；核对了原始磁化文件、输入校验和、前驱链和停止指标，并重新分析 s039，全部通过。
- s040 暂停现场完整移入 `simulations/shape_comparison/interrupted/circle_1nm_loop_seeded_s040_user_pause_resume_20261118_133651/`，附旧状态、日志及原心跳配置；未覆盖历史归档。
- 使用原启动脚本恢复串行队列。新 s040 与归档的 `config.json`、`geometry.json`、`input.mif`、`initial.omf` 逐字节校验和完全一致。
- 新 OOMMF 作业产生 ODT，13:37:52 已推进到第 400 步；最大 dm/dt 约 0.317 °/ns，仍未达到 0.01 °/ns，因此该场点仍是计算中。
- 启动进程 PID 13928、实际 Python 控制器 PID 32244；二者是虚拟环境启动器及其子进程，属于同一控制任务。报告等待进程 PID 6440（Python 子进程 8388）等待启动进程结束。PID 仅供本次记录，后续必须重新核对命令行及进程树。
- 原心跳 `qah` 已恢复，每 15 分钟按 P0–P4 检查。健康运行且无实质变化时保持安静；完成全部验证及交付后停用。

恢复证据：[前驱核对](../simulations/shape_comparison/validation/resume_preflight_20261118_133651.json)、[新输入与原始输出核对](../simulations/shape_comparison/validation/resume_verified_20261118.json)、[当前进度](../simulations/shape_comparison/live_progress.json)。总日志：`simulations/shape_comparison/campaign_20261118_133702.log`。

后续顺序保持原规划：圆形剩余 81 点 → 长方形 121 点 → 1 nm 六支场步和严格阈值验证 → 跨网格磁化与翻转模式核查及必要快照 → 独立输出审计、图表与中文结论。现有控制器自动执行至局部数值验证及报告；跨网格过程证据与最终清单仍须按 P3/P4 逐项落实，不能仅以汇总布尔值宣布完成。

2026-11-18 14:26（Asia/Shanghai）用户要求暂停：计算、报告等待任务及 qah 心跳均已停止。圆形 1 nm 已完成 98/121 点，s097（+0.14 T）为最近通过点；s098（+0.16 T）中断现场完整保留。当前状态 PAUSED，等待用户明确要求恢复。

2026-11-18 16:44（Asia/Shanghai）用户明确要求继续：核对圆形前 98 点、完整前驱链及 s097 原始输出通过；确认没有残留任务后，将 s098 暂停现场完整归档至 `interrupted/circle_1nm_loop_seeded_s098_user_pause_resume_20261118_164431/`。恢复原串行控制器（启动器 PID 27776、实际控制器 PID 35136）、报告等待任务及 qah 心跳。新的 s098 配置、几何、MIF、初始磁化与归档逐字节一致，已产生推进中的 ODT，仅有一个 OOMMF 作业。任务标题及说明中文核验正常。当前为 P1 计算中，全计划尚未验收；见 `validation/resume_verified_s098_20261118.json`，总日志为 `campaign_20261118_164447.log`。
