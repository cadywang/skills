---
name: serial-debug-bridge
description: 通过 serial-debug-bridge 在 server 侧操作接在 client 串口上的嵌入式开发板：链路检查、命令执行、交互 shell、串口 push/pull、复位和基础排障。适用于串口不在本机，或需要 sdb/devctl/serial_agent、COM/ttyUSB、TCP/SSH 的场景；不用于设备 SSH 大文件传输或 bootloader/分区刷写。
metadata:
  short-description: 通过远端串口操作嵌入式开发板
---

# serial-debug-bridge

## 边界

用于：

- 串口接在另一台 client 上，server 通过 devctl/agent 访问。
- 在开发板上执行命令、读取控制台、传小文件、复位或检查链路。
- 排查 agent、端口、登录提示符、串口被占用等桥接问题。

不要用于：

- 设备 SSH 已可用且要传大文件：使用 `reverse-ssh-scp`。
- 进入 LK、USB rescue、写 eMMC/BCB/WIC：使用 `lk-console-rescue`。

## 心智模型

```
server: devctl --TCP 或 SSH--> client: serial_agent --UART--> 开发板
```

串口插在哪台机器上，`serial_agent` 就在哪台机器上运行（下文称 **client**）。
server 上的 `sdb` 把命令和文件交给 agent，agent 再读写串口。
设备控制台通常就是 root shell：能连上 agent 基本等于能完全控制设备。

## 推荐入口

```bash
S="$HOME/.codex/skills/serial-debug-bridge/scripts/sdb"

$S info                         # 代理与设备信息，不碰设备
$S exec "uname -a; id -un"      # 在设备执行，退出码来自设备命令
$S push ./fw.bin /tmp/fw.bin    # server -> 设备，设备侧 md5 校验
$S pull /etc/hostname ./h       # 设备 -> server，落盘后 md5 校验
$S md5 /tmp/fw.bin              # 设备侧 md5
$S reset                        # DTR 复位，先确认
$S shutdown                     # 结束 client 上的 agent，释放串口
$S shell                        # 交互控制台，仅 TCP；Ctrl+] 退出
```

直接调用 devctl 时需要自己拼端点参数：

```bash
python3 ~/serial-debug-bridge/devctl.py --tcp 127.0.0.1:17801 exec "uname -a"
```

## 端点解析

优先级：环境变量 > `SDB_CONFIG` 指定的配置文件 > 默认值。

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `SDB_TCP` | `127.0.0.1:17801` | 连接已监听的 agent |
| `SDB_SSH` | 空 | `user@host`，由 devctl 通过 SSH 拉起 agent |
| `SDB_PORT` / `SDB_BAUD` | `/dev/ttyUSB0` / `115200` | 仅 `SDB_SSH` 时使用 |
| `SDB_REMOTE_AGENT` | 空 | client 上的 agent 路径，仅 `SDB_SSH` |
| `SDB_TOKEN` | 空 | agent 用 `--auth` 启动时的口令 |
| `SDB_DEVCTL` | 见脚本 | devctl 路径 |
| `SDB_CONFIG` | `~/.config/serial-debug-bridge/target` | 会被 source |
| `SDB_TIMEOUT` | `180` | 外层硬超时秒数，`0` 关闭 |
| `SDB_EXTRA` | 空 | 附加 devctl 参数，按空格切分 |

## 开工检查

```bash
bash "$HOME/.codex/skills/serial-debug-bridge/scripts/sdb-check.sh"
bash "$HOME/.codex/skills/serial-debug-bridge/scripts/sdb-check.sh" --ports
$S exec "command -v busybox base64 openssl awk od md5sum"
```

`--ports` 用来发现端口被 VS Code 自动转发或其他进程抢占。
设备身份以 `uname -a` 和 `hostname` 为准，不要凭端点名称猜目标。

## 串口传输

- 网络/SSH 可用时，大文件优先走 `reverse-ssh-scp`；串口 `push` 是兜底。
- 串口速度约 1 到 1.2 KB/s。60 KB 约 50 秒，200 KB 约 3 分钟。
- 大文件先压缩再传：`$S exec "tar czf /tmp/a.tgz <path>"`，然后 `$S pull`。
- `push` 必须看到 `verified=True`；失败先重试，再考虑降波特率或换线。
- agent 单线程，不要并发发起多个 `sdb`。
- 传输超时：`SDB_TIMEOUT=0` 关闭外层超时，或 `SDB_EXTRA="-q" SDB_TIMEOUT=600`。

## 快速排障

| 现象 | 先做什么 |
| --- | --- |
| `agent closed the connection` 或莫名超时 | 跑 `sdb-check.sh --ports`，排查端口抢占；必要时改连 `127.0.0.2:port` |
| 设备停在 `login:` | 不要反复 `exec`；先通过 `$S shell` 或 raw 模式以 root 登录 |
| shell 提示符变成 `>` | 发送 Ctrl-C；必要时交互 shell 手动处理，`reset` 仅作兜底 |
| `verified=False` | 重试；持续失败则降波特率或先压缩文件 |
| agent 停不下来 / 串口 busy | 先 `$S shutdown`；连不上就到 client 跑 `stop-agent` 脚本 |

详细步骤、命令和日志判读：

- 普通排障、登录恢复、agent 进程：`references/troubleshooting.md`
- 确认是桥的 bug：`references/upstream-fixes.md`

## 安全

- `rm`、`dd`、写 flash、`reset`、刷固件前必须取得用户确认。
- 破坏性操作前先执行 `$S exec "uname -a; hostname"`，确认目标是预期设备。
- `push` 会覆盖目标路径，先检查目录和已有文件。
- 不要把 agent 端口暴露到公网；TCP 使用 `SDB_TOKEN` 或限制在 SSH/回环网络。
