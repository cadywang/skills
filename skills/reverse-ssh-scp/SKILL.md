---
name: reverse-ssh-scp
description: 通过 client 建立的 SSH 反向隧道，从 server 用 scp -O 向嵌入式开发板传文件或 ssh 登录。适用于设备不在 server 同网段但设备 Dropbear/SSH 可用，或重刷镜像后需要恢复设备 IP、host key、authorized_keys、known_hosts 的场景。
metadata:
  short-description: 反向 SSH 隧道与 SCP 传输
---

# reverse-ssh-scp

## 边界

用于：

- 设备有可用的 Dropbear/SSH，但 server 不能直接路由到设备。
- 需要比串口快几个数量级地传固件、日志或大文件。
- 重刷镜像后 scp 失效，需要恢复 IP、主机密钥、授权公钥或 known_hosts。

不用于：

- 设备网络未起来、Dropbear 不可用，只能靠串口救急：使用 `serial-debug-bridge`。
- 需要进入 LK、USB rescue 或写 eMMC：使用 `lk-console-rescue`。

## 拓扑

```text
server: scp/ssh -> 127.0.0.1:<remote-port>
      --SSH -R--> client -> <device-ip>:<device-ssh-port>
```

反向隧道由 client 建立，server 只访问自己的回环地址。不要把设备 SSH 暴露到公网。

## 正常传输

```bash
scp -O -P <remote-port> ./firmware.bin root@127.0.0.1:/tmp/
ssh -p <remote-port> root@127.0.0.1
```

要点：

- Dropbear 通常只支持 legacy SCP，`scp` 必须加 `-O`。
- `scp` 端口参数是大写 `-P`，`ssh` 是小写 `-p`。
- 设备用户不一定是 root，按实际镜像替换。
- 传完必须在设备侧做 `sha256sum` 或 `md5sum` 校验，不能只看进度条。

## 最小端到端验证

```bash
head -c 4096 /dev/urandom > /tmp/scp-test.bin
sha256sum /tmp/scp-test.bin
scp -O -P <remote-port> -o BatchMode=yes /tmp/scp-test.bin root@127.0.0.1:/tmp/scp-test.bin
ssh -o BatchMode=yes -p <remote-port> root@127.0.0.1 \
  "sha256sum /tmp/scp-test.bin; wc -c /tmp/scp-test.bin"
```

两边 SHA256 和字节数一致才算通过。再用 1 MiB 文件测一次，确认不是只有小文件能过。

## 重刷后的恢复顺序

1. 用串口确认目标：`hostname`、`id -un`、`ip -br addr`、`ip route`。
2. 在 client 上确认到设备 SSH 端口可达：`ping <device-ip>`、`nc -vz <device-ip> <device-ssh-port>`。
3. 修正 client 上反向隧道的目标 IP/端口。
4. 检查并生成 Dropbear host key：`systemctl status dropbear.socket`、`ls -l /etc/dropbear`、`systemctl start dropbearkey.service`。
5. 恢复 server 公钥到设备的 `authorized_keys`，权限为 `700` / `600`。
6. 清理 server 上的旧 known_hosts：`ssh-keygen -R "[127.0.0.1]:<remote-port>"`。
7. 重新跑上面的端到端验证。

完整命令、权限设置和验证流程见 `references/scp-reverse-tunnel.md`。

## 常见报错

| 现象 | 优先检查 |
| --- | --- |
| `Connection refused` | server 回环端口没有监听；反向隧道未建立或目标变了 |
| `Connection closed` / `ssh_exchange_identification` | Dropbear socket 没起来，或 `/etc/dropbear` 缺 host key |
| `Permission denied (publickey)` | server 公钥没写入设备 authorized_keys，或权限不对 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 设备重刷后 host key 变化，清理 server 旧 known_hosts |
| `scp: protocol error` / `sftp: not found` | Dropbear 不支持 SFTP，改用 `scp -O` |
| `No route to host` | client 到设备没有路由，或 USB 网卡没有同网段地址 |

## 安全

- 只有设备不在 server 同网段时才需要反向隧道；监听必须绑定回环地址。
- 不要长期使用 `StrictHostKeyChecking=no` 掩盖 host key 变化。
- 只把 server 公钥写入设备，不要把私钥写到设备、日志或仓库。
- 两条通道不要同时写同一设备路径；先确认没有传输在进行。
