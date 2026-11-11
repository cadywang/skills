# 把 serial-debug-bridge 的 bug 交回上游

只有确认是桥自身缺陷时才走本文。设备重启、端口被占、登录提示符、线路质量等问题先按 `troubleshooting.md` 排查。

## 1. 先给最小复现

记录：

- 触发命令和完整参数
- 期望结果
- 实际输出和退出码
- agent 日志；Windows agent 用 `-LogFile` 保存
- `sdb-check.sh` 输出

不少看似桥 bug 的问题，最后是设备重启或端口被其他进程抢占。

## 2. 改代码要成对改

桥仓库有两套等价实现，修改时必须同步：

- `agent/serial_agent.ps1` 与 `agent/serial_agent.py`
- `cli/devctl.ps1` 与 `cli/devctl.py`
- 涉及协议时同步 `PROTOCOL.md`

本工具支持 PowerShell 与 Python 交叉使用，只改一套会造成平台行为漂移。

## 3. 先跑自测

```bash
powershell -File tests/selftest.ps1
powershell -File tests/selftest.ps1 -Codec hex
python3 tests/test_e2e.py
python3 tests/test_e2e.py --agent-args "--codec hex"
```

有条件再跑：

```bash
bash tests/verify-live.sh <client>:<port>
```

## 4. 按仓库规范提交

- 从 `main` 切分支。桥仓库用 `agent/...` 或 `cli/...`；本 skill 仓库用 `skill/...`。
- 使用内核风格 commit：`<subsystem>: <祈使句摘要>`。
- 正文每行不超过 72 列。
- 使用 `git commit -s`，带 `Signed-off-by:`。
- 提交 PR，并在 PR 中贴最小复现和自测输出。

## 5. 没有写权限时

把 `git diff` 保存为 `fix.patch`，连同最小复现、日志和自测输出一起交给维护者。

## 6. 只能临时绕过时

在结果里写清楚：

- 绕过了什么
- 为什么必须绕过
- 风险是什么
- 建议的修复方向

不要只留一个隐式 workaround，让下一个使用者再踩同一个坑。

## 仓库约定

补丁必须走 PR，CI 全绿后由维护者合并；`main` 不接受直接推送，两套实现与文档必须同步修改。

详见：

- serial-debug-bridge 仓库的 `REVIEW_POLICY.md`
- serial-debug-bridge 仓库的 `CONTRIBUTING.md`
- 本 skill 仓库根目录的 `README.md`
