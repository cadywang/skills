# 进入 LK/Realtek 控制台

> 适用范围：本文的 USB rescue、分区偏移和 `rtkemmc` 流程在 51 server / RTK1761（Prince）环境验证。其他板型必须重新核对分区表、块号和镜像布局，禁止直接复用本文数值。

适用于需要绕过 Linux、进入 bootloader 做恢复、写 BCB、从 USB 启动 rescue 或重刷分区的场景。

## 先确认

进入 LK 前先确认目标设备和当前槽：

```bash
S="$HOME/.codex/skills/serial-debug-bridge/scripts/sdb"
$S info
$S exec 'uname -a; hostname; cat /proc/cmdline'
```

重启和写 flash 都是破坏性操作，必须先取得用户确认。DTR `reset` 在部分板子上没有接到复位脚；此时最终仍需要现场断电再上电。

## 用 raw 串口进入 LK

协议模式 `sdb shell` 会在 LK 启动阶段产生严重输入反压：ESC/q 往往直到 Linux
`login:` 才送达。因此进入 bootloader 时必须在 **client 侧使用 raw agent**。

### 1. client 切换到 raw agent

先停止协议模式 agent，然后启动 raw 模式。Windows/COM3 示例：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <client>\agent\serial_agent.ps1 `
  -Port COM3 -Baud 460800 -TcpPort 17801 -Raw
```

如果 raw agent 通过反向隧道/端口转发暴露给 server，以实际监听地址为准。本环境实测可用的
地址是 `SDB_TCP` 配置中的端点（例如 `127.0.0.1:7801`）。

### 2. server 侧启动 raw helper

```bash
RAW="$HOME/.codex/skills/serial-debug-bridge/scripts/sdb-enter-lk-raw.py"
python3 "$RAW" --tcp 127.0.0.1:17801 --timeout 600 --log /tmp/lk-console.log
```

helper 打印 `POWER-CYCLE NOW` 后，请现场给板子断电再上电。它会持续发送 ESC 并高速
排空固件启动日志；捕获 `Realtek>` 后停止 ESC，转而把 stdin/stdout 透明转发到串口。

成功标志：

```text
*** ESC Pressed ***
Enter Console...
Realtek>
[RAW_LK_CONSOLE_READY]
```

进入 LK 后建议先发一个空行，再输入命令，避免空闲后首字节丢失：

```text
boot ru
```

### 3. 完成 LK 操作后恢复协议 agent

raw 模式没有协议通道，`sdb exec/push/pull` 在 raw 会话期间不可用。完成后：

1. `Ctrl+C` 退出 raw helper；
2. 在 client 上停止 raw agent；
3. 重新启动协议模式 agent。

## 常见误判

- 不要在协议模式 `sdb shell` 中反复 warm reboot 抢 ESC；
- `reset` 只拉 DTR，很多板子的 DTR 没接复位脚；
- LK 的 `Reboot-Action=RESET_ACTION_RESCUE` 只设置启动策略，不保证进入交互 console；
- 如果日志显示 ESC 在 Linux 启动后才成批出现，就是协议通道反压，不是 LK 不响应。

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

注意：**LK 没有 BusyBox `dd`**。需要写 eMMC 时使用 `rtkemmc`；需要 `dd` 时先 `boot ru` 进入 USB rescue，再在 rescue shell 中执行。

`fatload` 是把 USB 文件读入 RAM，之后用 `rtkemmc write` 写入。大文件需要足够 RAM，并且写之前必须核对目标块号。

```text
fatload usb 0:1 0x30000000 rtk-ota-local/rootfs_b_new.ext4
rtkemmc write uda 0x30000000 0x160000 0x20000000
```

`0x160000` 是绝对 UDA 块号，不是分区编号。Linux 下可先核对：

```bash
cat /sys/class/block/mmcblk0p30/start
cat /sys/class/block/mmcblk0p30/size
```

## USB rescue + dd

需要直接从 USB 镜像写块设备时，优先用 rescue：

```text
boot ru
```

### Prince/RTK1761 整盘 WIC 强制流程

Prince/RTK1761 整盘烧录**禁止**使用以下自动安装入口：

```text
install.img
install-single.img
rtk_installer 自动执行脚本
```

必须在 LK 执行 `boot ru`，进入 `/ #` rescue shell 后手工 `dd`。

1. U 盘上不要保留 `install.img`。如果已存在，先移除；或在 rescue shell 中立即执行：

```sh
mv /mnt/usb/install.img /mnt/usb/install.img.disabled 2>/dev/null || true
```

2. 确认目标设备、U 盘文件和 WIC 哈希：

```sh
ls -l /mnt/usb/*.wic
sha256sum /mnt/usb/<your-image>.wic
```

3. 使用 WIC 实际字节数计算回读扇区数：

```text
sectors = WIC_bytes / 512
```

4. 整盘写入：

```sh
dd if=/mnt/usb/<your-image>.wic of=/dev/mmcblk0 bs=4M conv=fsync
sync
```

5. 回读 WIC 覆盖范围并校验 SHA256：

```sh
dd if=/dev/mmcblk0 bs=512 count=<WIC_sectors> 2>/dev/null | sha256sum
```

回读哈希必须与第 2 步 WIC 的 SHA256 完全一致。

6. 回读校验通过后再执行：

```sh
sync
reboot -f
```

补充要求：

* 不要在 rescue shell 中使用 `install.img` 自动 installer 写整盘。
* 不要用近似 MiB/GiB 偏移代替 WIC 的真实 512-byte 扇区数。
* 写入前必须确认 `/dev/mmcblk0` 是目标 eMMC，不能把 U 盘或主机磁盘当目标。
* 回读 SHA256 不一致时禁止 reboot 进入新系统，应停留在 rescue shell 分析。

### 分区/镜像提取

按 WIC 的真实 512-byte 扇区偏移提取分区并写入。
不要用近似 MiB 偏移，否则会得到 `yocto image is not fit`：

```sh
# 从 fullab WIC 提取 p29/rootfs 与 p26/yocto；以下是本板当前布局
dd if=/mnt/usb/core-image-prince-fullab.wic of=/mnt/usb/rtk-ota-local/rootfs_b.img \
  bs=512 skip=393216 count=1048576
dd if=/mnt/usb/core-image-prince-fullab.wic of=/mnt/usb/rtk-ota-local/yocto_b.img \
  bs=512 skip=336280 count=49152

# 写入非活动 B 槽
dd if=/mnt/usb/rtk-ota-local/rootfs_b.img of=/dev/mmcblk0p30 bs=1M count=512
dd if=/mnt/usb/rtk-ota-local/yocto_b.img of=/dev/mmcblk0p26 bs=512 count=49152
sync
sha256sum /dev/mmcblk0p30 /dev/mmcblk0p26
```

写之前检查：

- B 槽 rootfs 必须有独立 ext4 UUID，且不能带重复的 `rootfs_a` 标签；
- `yocto` 文件开头应是 FIT magic `d0 0d fe ed`；
- `sha256sum` 应与此前计算的 payload 一致；
- 只写非活动槽，不要把 A 槽 rootfs 直接克隆到 B 槽。

## 回写 BCB

rescue shell 可直接回写 USB 上的 512-byte BCB：

```sh
dd if=/mnt/usb/bcb_b.bin of=/dev/mmcblk0 bs=512 seek=153 count=1
sync
dd if=/dev/mmcblk0 bs=512 skip=153 count=1 2>/dev/null | hexdump -C -n 16
sync; reboot -f
```

期望 `BLK_INFO` 后的 32-bit flag：

- `0x00005687`：A 槽
- `0x00009527`：B 槽

若在 LK 中操作，也可用：

```text
usb start
fatload usb 0:1 0x30000000 bcb_b.bin 512
rtkemmc write uda 0x30000000 0x99 512
rtkemmc read  uda 0x31000000 0x99 512
hexdump 0x31000000 0x20
reboot
```

回读后再 reboot。若写错 BCB 或新槽无法启动，先停手，使用备份 BCB 回写 A 槽，再分析启动日志。
