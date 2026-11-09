# 通过反向 SSH 隧道使用 SCP

> 适用范围：设备网络和 Dropbear/SSH 可用，但设备不在 server 的同一网段。
> 由 client（串口/网线所在的机器）建立 SSH 反向隧道，server 只访问自己的
> `127.0.0.1`，不要把设备 SSH 暴露到公网。

## 拓扑

```text
server: scp/ssh -> 127.0.0.1:<remote-port>
          |
          |  SSH -R 127.0.0.1:<remote-port>:<device-ip>:<device-ssh-port>
          v
client: ssh.exe / ssh  ---Ethernet/Wi-Fi/USB gadget--->  device:<device-ssh-port>
```

- `<remote-port>`：server 回环上的入口，例如 `2222`。
- `<device-ip>`：设备当前地址，重刷镜像后可能变化。
- `<device-ssh-port>`：设备 SSH 端口，通常是 `22`。
- server 的监听应绑定 `127.0.0.1`；不要绑定 `0.0.0.0` 或公网地址。

## 正常传文件

从 server 执行：

```bash
scp -O -P <remote-port> ./firmware.bin root@127.0.0.1:/tmp/
ssh -p <remote-port> root@127.0.0.1
```

要点：

- Dropbear 通常只支持 legacy SCP，必须加 `-O`。
- `scp` 的端口参数是大写 `-P`；`ssh` 是小写 `-p`。
- 设备用户不一定是 `root`，按实际镜像替换。
- 传完后用设备侧 `sha256sum` 或 `md5sum` 校验，不要只看 `scp` 的进度条。

## 重刷镜像后的恢复顺序

重刷会同时影响设备 IP、Dropbear 主机密钥和授权公钥，按下面顺序排查，避免在错误层反复试。

### 1. 串口确认设备身份和当前 IP

先通过串口进入设备 root shell，确认目标没有接错：

```bash
hostname
id -un
ip -br addr
ip route
```

如果设备 IP 与 client 侧反向隧道的 `<device-ip>` 不一致，先更新 client 的隧道目标。
不要假设重刷后还是旧地址。

### 2. 从 client 确认到设备 SSH 端口可达

在 client 上检查路由和端口：

```bash
ping <device-ip>
nc -vz <device-ip> <device-ssh-port>
```

Windows 可以用：

```powershell
Test-NetConnection <device-ip> -Port <device-ssh-port>
```

如果 client 是通过 USB 网卡直连设备，还要确认 client 网卡有同网段地址。
例如设备是 `<device-ip>/24`，client 网卡需要有同网段且不冲突的地址（如 `<client-ip>/24`）。

### 3. 恢复 Dropbear 主机密钥

新镜像的 `/etc/dropbear` 可能为空。检查并生成：

```bash
systemctl status dropbear.socket --no-pager
ls -l /etc/dropbear
systemctl start dropbearkey.service
systemctl restart dropbear.socket
ls -l /etc/dropbear/dropbear_rsa_host_key
```

`socket` 处于 `active (listening)` 不代表主机密钥已经存在；连接时 Dropbear
可能因为缺少 host key 直接关闭连接。

### 4. 恢复 server 的 authorized_keys

在设备上把需要发起 scp 的 server 公钥加入 root 的 authorized_keys：

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
KEY='<server-public-key>'
grep -qxF "$KEY" /root/.ssh/authorized_keys 2>/dev/null || \
  printf '%s\n' "$KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
wc -l /root/.ssh/authorized_keys
```

每台 server 都要加入自己的公钥。只复制公钥，不要把私钥写到设备或日志里。
如果镜像使用非 root 用户，替换 `/root/.ssh` 和登录用户。

### 5. 清理 server 上的旧 host key

设备重刷后 Dropbear host key 会变化，server 的 `known_hosts` 会报
`REMOTE HOST IDENTIFICATION HAS CHANGED`。在每台 server 上删除旧入口：

```bash
ssh-keygen -R '[127.0.0.1]:<remote-port>'
```

下一次连接会写入新的 host key。不要用 `StrictHostKeyChecking=no` 长期绕过；
那会掩盖中间人风险。

### 6. 端到端验证

先在 server 上验证 SSH：

```bash
ssh -o BatchMode=yes -p <remote-port> root@127.0.0.1 'hostname; id -un'
```

再做真实 SCP 和哈希校验：

```bash
head -c 4096 /dev/urandom > /tmp/scp-test.bin
sha256sum /tmp/scp-test.bin
scp -O -P <remote-port> -o BatchMode=yes /tmp/scp-test.bin root@127.0.0.1:/tmp/scp-test.bin
ssh -o BatchMode=yes -p <remote-port> root@127.0.0.1 \
  'sha256sum /tmp/scp-test.bin; wc -c /tmp/scp-test.bin'
```

两边 SHA256 和字节数一致才算通过。建议再用 1 MiB 文件测一次，确认不是只有小文件能过。

## 常见报错

| 现象 | 优先检查 |
| --- | --- |
| `Connection refused` | server 的 `127.0.0.1:<remote-port>` 没有监听；反向隧道未建立或目标 IP/端口变了 |
| `Connection closed` / `ssh_exchange_identification` | Dropbear socket 没起来，或 `/etc/dropbear` 缺 host key |
| `Permission denied (publickey)` | server 公钥没写入设备 `authorized_keys`，或目录/文件权限不对 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 设备重刷后 host key 变化，清理 server 的旧 known_hosts 条目 |
| `scp: protocol error` / `sftp: not found` | Dropbear 不支持 SFTP，改用 `scp -O` |
| `No route to host` / `Network is unreachable` | client 到 `<device-ip>` 没有路由，或 USB 网卡没有同网段地址 |
| `scp` 成功但设备文件不完整 | 检查设备磁盘空间、`df -h`，并在设备侧做 SHA256/MD5 校验 |

## 已验证记录

2026-11-09 在现有双 server 反向隧道环境验证：

- 两台 server 均能通过 `ssh -p <remote-port>` 以 key 登录设备；
- 两台 server 的 4 KiB `scp -O` 传输均返回 0，设备侧 SHA256 与源文件一致；
- 1 MiB 文件传输返回 0，设备侧 SHA256 一致，字节数为 `1048576`；
- 重启串口代理后，串口 raw 通道仍能执行 `hostname` / `id -un`。

## 与串口 `sdb push` 的关系

- 设备网络/SSH 可用：优先用反向隧道 `scp`，吞吐量远高于串口。
- 网络不通、Dropbear 未起来、或设备只能靠串口救急：再用 `sdb push` / `sdb pull`。
- 两条通道不要同时操作设备文件系统；先确认没有其他传输在写同一路径。
