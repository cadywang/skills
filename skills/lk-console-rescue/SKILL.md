---
name: lk-console-rescue
description: 进入 Realtek LK 控制台或 USB rescue，使用 rtkemmc、boot ru、dd 处理 BCB、eMMC、分区和 WIC 镜像校验。适用于需要绕过 Linux、抢 LK 启动窗口、写入 bootloader、从 USB rescue 恢复开发板，或处理 Realtek/RTK 板型刷写问题的场景。
metadata:
  short-description: 进入 Realtek LK 与 USB rescue
---

# lk-console-rescue

## 边界

用于：

- 需要进入 `Realtek>` LK 控制台。
- 需要用 `boot ru` 进入 USB rescue。
- 需要 `rtkemmc` 读写 eMMC、回写 BCB、处理分区或校验 WIC 镜像。
- Linux 已不可启动，需要从 bootloader 或 rescue 恢复。

不用于：

- 只想在 Linux 下执行普通命令、传小文件或复位：使用 `serial-debug-bridge`。
- 设备 SSH 可用且只需传大文件：使用 `reverse-ssh-scp`。

## 安全前提

重启、写 flash、`rtkemmc write`、`dd`、回写 BCB 都可能让设备无法启动。

- 执行前必须取得用户明确确认。
- 先确认板型、目标设备、当前槽位、分区表和镜像哈希。
- 本文的 USB rescue、分区偏移和 `rtkemmc` 流程只在 51 server / RTK1761（Prince）验证。
- 其他板型必须重新核对分区表、块号和镜像布局，禁止直接复用本文数值。
- 写错或回读不一致时停在 rescue shell，不要直接 reboot。

## 先确认目标

```bash
S="$HOME/.codex/skills/serial-debug-bridge/scripts/sdb"
$S info
$S exec "uname -a; hostname; cat /proc/cmdline"
```

如果 Linux 已不可用，至少先确认串口端点、client 串口号和板型。

## 进入 LK

协议模式 `sdb shell` 在 LK 启动阶段会产生输入反压，ESC/q 可能直到 Linux `login:` 才送达。
进入 bootloader 必须在 **client 侧使用 raw agent**。

### 1. 切换 raw agent

先停止协议模式 agent，再在 client 启动 raw 模式。Windows/COM3 示例：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <client>\agent\serial_agent.ps1 `
  -Port COM3 -Baud 460800 -TcpPort 17801 -Raw
```

### 2. 启动 raw helper

```bash
RAW="$HOME/.codex/skills/lk-console-rescue/scripts/sdb-enter-lk-raw.py"
python3 "$RAW" --tcp 127.0.0.1:17801 --timeout 600 --log /tmp/lk-console.log
```

helper 打印 `POWER-CYCLE NOW` 后，现场给板子断电再上电。
捕获 `Realtek>` 后它会停止发送 ESC，并把 stdin/stdout 透明转发到串口。

成功标志：

```text
*** ESC Pressed ***
Enter Console...
Realtek>
[RAW_LK_CONSOLE_READY]
```

进入 LK 后先发一个空行，再输入命令，避免空闲后的首字节丢失。

## LK 常用命令

```text
help
version
usb start
fatload usb 0:1 0x30000000 <file-or-path>
rtkemmc read  uda <mem_addr> <blk_addr> <byte_size>
rtkemmc write uda <mem_addr> <blk_addr> <byte_size>
rtkemmc erase <from_blk> <to_blk>
hexdump <addr> <bytes>
boot ru
reboot
```

LK 没有 BusyBox `dd`。需要在 rescue shell 执行 `dd` 时先 `boot ru`。

## USB rescue 与写盘

1. 确认 U 盘镜像文件名、大小和 SHA256。
2. 确认 `/dev/mmcblk0` 是目标 eMMC，不是 U 盘或主机磁盘。
3. 按 WIC 的真实字节数写入，不用近似 MiB/GiB 偏移。
4. 写后 `sync`，按风险选择关键区域校验或全量回读 SHA256。
5. 回读不一致时禁止 reboot，先停在 rescue shell 分析。

完整命令、Prince/RTK1761 整盘 WIC 流程、BCB 回写、分区提取和校验分级见
`references/lk-console.md`。

## 恢复协议模式

raw 模式没有协议通道，`sdb exec/push/pull` 在 raw 会话期间不可用。完成后：

1. `Ctrl+C` 退出 raw helper。
2. 在 client 停止 raw agent。
3. 重新启动协议模式 agent。

## 常见误判

- 不要在协议模式 `sdb shell` 中反复 warm reboot 抢 ESC。
- `reset` 只拉 DTR，很多板子的 DTR 没有接复位脚。
- LK 的 `Reboot-Action=RESET_ACTION_RESCUE` 只设置启动策略，不保证进入交互 console。
- ESC 在 Linux 启动后才成批出现，通常是协议通道反压，不是 LK 不响应。
