# 等面积薄膜形状比较

本目录实现 [已确认的仿真计划](../../refine-logs/EXPERIMENT_PLAN.md)。输入使用教学参数 Ms=3×10⁵ A/m、A=5×10⁻¹² J/m、Ku=8×10⁴ J/m³，厚度 4 nm，目标面积 40,000 nm²。方形 200×200 nm，圆半径约 112.838 nm，长方形 400×100 nm。边界开放，零温，无缺陷、无 DMI。

## 当前结果与运行状态

- [status.json](status.json)：批次当前阶段，失败时包含原因。
- [RESULTS.md](RESULTS.md)：从已完成算例生成的报告；缺失的数值检验会明确列为待完成。
- [analysis/results.json](analysis/results.json)：可机读的验证与翻转区间。
- [环境说明](ENVIRONMENT.md)：本机路径、依赖和验证命令。
- [环境验证结果](validation/environment_witness.json)、[状态继承校验](validation/history_check.json)。

## 复现与继续

工作目录为项目根目录。完整执行命令：

```powershell
./.venv/Scripts/python.exe simulations/shape_comparison/run_campaign.py --phase all
```

可分阶段执行 `--phase primary`（2 nm 静态、多初态、完整回线）、`--phase verification`（1 nm、场步、停止阈值、扰动）、`--phase report`（生成报告与验收状态）。报告命令不启动 OOMMF。

实际顺序为：2 nm 主实验与代表翻转快照 → 2 nm 场步/阈值/扰动验证 → 1 nm 静态、零场与完整回线 → 1 nm 翻转区复核。运行 `progress.py` 可生成含当前路径和已完成场点数的进度快照；`status.json` 记录批次阶段。

要以无窗口后台进程启动并保存总日志，在项目根目录执行 `./simulations/shape_comparison/start_campaign.ps1`。启动信息在 `launch.json`，实际控制进程状态在 `controller.json`；脚本检测到已有控制进程时拒绝重复启动。失败时保留日志并停止依赖它的后续计算。

同名已完成结果仅在输入配置、前驱状态校验和与 MIF 校验和一致且数值检查通过时复用。求解器成功而分析未完成的目录会重新分析。失败或中断的算例保留，先查看 `console.log`、`run.json` 和输入，再决定另建 run_id 重算；不自动清空目录。

**仅启动一个计算批次。** 启动器沿用 OOMMF 的 `-kill all` 生命周期选项，串行清理该用户的 OOMMF 服务，不适合与其他 OOMMF 作业同时运行。报告与读取状态可以并行。

## 记录与验证

每个 `runs/<run_id>/` 保存：

- `config.json`、`geometry.json`、`input.mif`、`initial.omf`：物理参数、实际磁性体积、外场路径、初态及可直接运行的输入。
- `run.json`、`console.log`：命令、退出码、耗时、PID 与运行日志。
- `.odt`、各阶段 `.omf/.ohf`：收敛表、磁化、退磁场及总有效场。
- `summary.json`：逐阶段磁性体积平均、能量、独立 LLG 右端、固定场能量下降及校验结果。

`config.json` 中的 `mif_sha256` 对生成的 UTF-8、LF 换行文本计算，便于 Windows 换行转换后的重用检查。`audit_outputs.py` 另记录实际落盘文件的字节 SHA256，并核对实际外场、Zeeman 能量、初态校验和和跨场点的检查点来源；结果见 `analysis/output_audit.json`。

`trajectories/` 保存每形状下降支首个翻转场点的重放与中间磁化快照。重放仅增加输出频率，单独核对最终磁化与原算例的一致性；`interrupted/` 中的中断记录不参与统计。

场量统一采用 b=μ₀Hext（T）配置、转换为 Hext（A/m）输入。固定磁化只计算退磁项并固定磁性单元；弛豫与回线加入交换、各向异性及外场项。多阶段 MIF 在内部继承磁化；从磁化文件重启与连续运行已通过独立比对。回线数据按实际磁性掩膜重新平均，避免圆外真空稀释平均值。

随机初态由固定物理坐标上的 Fourier 扰动构成，种子 11/22/33，在 1 nm 与 2 nm 网格取样同一物理场。双畴初态使用 mz=tanh(x/13 nm)、my=sech(x/13 nm)。这是初态敏感性测试，不是热噪声或基态搜索证明。

翻转区加密从原回线转变前两点的保存状态出发，重算局部细场步并沿该支路继续至饱和。原始完整回线与加密支路分别保留。扰动检验使用三个横向幅度，完整记录检验前后磁化；报告中的失败项必须解释或继续计算，不能自动忽略。

原始无扰动回线出现了对称性驻点，因此正式曲线统一采用 `*_loop_seeded` 协议：在外场与上一态平均磁化反向的每个点，对继承状态施加 ε=10⁻³ 横向扰动后弛豫。同向区间连续推进，反向区间逐点保存前驱状态。细网格和场步复核使用相同协议，三幅度检验单独输出。完整理由和诊断见 [实施记录](DECISIONS.md)。

## 环境恢复

依赖固定在 [requirements.txt](requirements.txt)，机器配置在 [env-spec.json](env-spec.json)。OOMMF 压缩包来自 [NIST 官方下载页](https://math.nist.gov/oommf/software-20.html)，SHA256 与历史记录一致。`.tools` 和 `.venv` 属于本地工具目录，不随 Git 保存。换机器时更新 Tcl 路径并重新执行环境验证。

运行器使用 Windows 受限令牌降低子进程权限，保持 OOMMF 原始管理员检查；该机制详见 ENVIRONMENT.md。数值模拟完全使用 CPU。


## 个别算例的迭代预算

默认阶段迭代上限保持 100000。经原始轨迹核查后，个别未收敛算例可在 iteration_budget_overrides.json 中按完整 run_id 登记更高预算及理由；非默认值写入该算例 config.json，并与 MIF 核对。提高预算不改变停止阈值，触及上限而停止指标未达标仍为失败。修改已存在算例预算前须归档失败现场，从已通过前驱重算，禁止改写既有通过结果。历史失败保留在 interrupted/，最终审计须连同 DECISIONS.md 一并解释。
