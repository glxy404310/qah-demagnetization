# 本机 CPU 环境验证

工作目录：`D:/Documents/qah-demagnetization`。

项目使用 `.venv` 的 Python 3.13.9、requirements.txt 中固定依赖、OOMMF 2.0b0 与 `D:/Git/mingw64/bin/tclsh.exe`（8.6.18）。求解器使用 8 CPU 线程。OOMMF 来源及 SHA256 见 env-spec.json。DLL 兼容名称副本仅位于 `.tools/oommf-runtime`。

在项目根目录的 PowerShell 原样执行：

```powershell
./.venv/Scripts/python.exe simulations/shape_comparison/validate_environment.py
```

预期退出码为 0，输出 `WITNESS OOMMF CPU: historical=50/50, pilots=2/2`。历史原始数据的副本每次重新分析；两个新求解器算例首次运行，后续调用复核已保存的输出。证据保存在 `simulations/shape_comparison/validation/environment_witness.json`。

`runtime.py` 创建受限令牌，将 Administrators SID 设为 deny-only 并移除特权；为当前用户创建私有窗口站/桌面和对象默认 DACL，以支持无窗口启动。未修改 OOMMF 管理员检查、系统账户或全局权限。依据：[NIST DLL 兼容说明](https://math.nist.gov/oommf/software-20.html)、[Microsoft 受限令牌接口](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken)。

硬件：AMD Ryzen 7 9700X，16 逻辑处理器，24,567,508,992 字节内存。验证只使用 CPU。新方形固定 z 磁化约 5.08 秒，零场弛豫约 9.62 秒；完整磁滞耗时需继续实测。
