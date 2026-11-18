# 通过反向 SSH 隧道访问 adb server

> 适用场景：adb server 跑在 client（串口/设备 USB 所在的机器），server 不能直接访问
> client 的 `127.0.0.1:5037`。复用 client 已经建立的反向 SSH 隧道，把 adb server
> 暴露到 server 的回环地址。

## 拓扑

```text
server: adb -P 9000 -> 127.0.0.1:9000
          |
          |  SSH -R 127.0.0.1:9000:127.0.0.1:5037
          v
client: adb server 127.0.0.1:5037  ---USB--->  Android 设备
```

- `9000` 是 **server 回环上的入口**，不是 client 的端口。
- `5037` 是 client 上 adb server 的默认端口。
- 监听必须绑定 `127.0.0.1`，不要把 adb 暴露到局域网或公网。

## 关键原则：复用连接，不复用映射

现有反向隧道里的每条 `-R` 都是固定目标：

```text
-R 127.0.0.1:7801:127.0.0.1:7803       # 串口
-R 127.0.0.1:2222:192.168.100.10:22    # 设备 SSH
```

这些端口不能承载 adb 流量。SSH 允许同一条连接携带多个 `-R`，所以正确做法是
在**同一条常驻 SSH 连接**上再加一条：

```text
-R 127.0.0.1:9000:127.0.0.1:5037
```

不要在每个交互式 `~/.ssh/config` Host 里加 `RemoteForward 9000 ...`：每多开一个
SSH 会话都会尝试绑定同一个远端 9000，后面的会话只会打印 warning。

## 一次性验证

在 client 上启动 adb server：

```powershell
adb start-server
adb devices
Get-NetTCPConnection -LocalPort 5037 -State Listen
```

在 client 上临时建立反向隧道（保持这个会话不要退出）：

```bash
ssh -N -R 127.0.0.1:9000:127.0.0.1:5037 <user>@<server>
```

在 server 上确认并访问：

```bash
ss -lnt | grep ':9000'
adb -P 9000 devices
```

也可以使用环境变量：

```bash
ANDROID_ADB_SERVER_PORT=9000 adb devices
```

`adb -P 9000` 的 server 端只是 adb client，真正执行设备枚举的是 client 上的
adb server；设备仍然插在 client 上。

## 接入常驻 supervisor（推荐）

以 Windows 上的 `serial-debug-tunnels` 常驻 supervisor 为例，在 `<supervisor-root>\config.psd1` 增加：

```powershell
Tunnel = @{
    # ... 现有字段 ...
    RemoteAdbPort = 9000
    LocalAdbPort  = 5037
}
```

在 `<supervisor-root>\Start-SerialDebugTunnels.ps1` 的 `Get-ServerTunnelArgs` 里生成并追加参数：

```powershell
$adbForward = '127.0.0.1:{0}:127.0.0.1:{1}' -f `
    $config.Tunnel.RemoteAdbPort, $config.Tunnel.LocalAdbPort

return @(
    # ... 现有 ssh 参数 ...
    '-R', $serialForward,
    '-R', $scpForward,
    '-R', $adbForward,
    # ... 目标 user@host ...
)
```

还要更新 `Find-ManagedTunnelProcess` 的匹配条件，让 supervisor 不会继续
“收养”没有 adb 转发的旧隧道：

```powershell
$adbForward = '-R 127.0.0.1:{0}:127.0.0.1:{1}' -f `
    $config.Tunnel.RemoteAdbPort, $config.Tunnel.LocalAdbPort

$match = Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine.IndexOf($serialForward) -ge 0 -and
        $_.CommandLine.IndexOf($scpForward) -ge 0 -and
        $_.CommandLine.IndexOf($adbForward) -ge 0
    }
```

修改后重启 supervisor 或对应隧道。**不能热加**到已经运行的连接：
Windows OpenSSH 不支持 `ControlMaster`，只能用新的 ssh 进程重新建立。

## 为什么用 9000 而不是 5037

- server 本机可能已经运行自己的 adb server 并占用 `5037`；远端入口再用 5037 会冲突。
- `9000` 只是 server 回环上的转发入口，不与 server 的 adb server 抢默认端口。
- 如果 server 上确实没有 adb server，也可以改成
  `-R 127.0.0.1:5037:127.0.0.1:5037`，之后直接 `adb devices`；但更容易和本地
  adb 冲突，所以默认推荐 9000。

## 验证清单

在 server 上：

```bash
ss -lnt | grep ':9000'
adb -P 9000 devices
adb -P 9000 shell getprop ro.product.model
```

在 client 上：

```powershell
adb devices
```

两边看到的设备应该来自同一个 client adb server；server 的 `adb devices` 列表里
应该出现 client 上那台设备。若设备列表为空，先解决 USB/授权问题，再查隧道。

## 常见问题

| 现象 | 优先检查 |
| --- | --- |
| server 上 `adb devices` 连不上 | `ss -lnt | grep ':9000'`；client 上 `Get-NetTCPConnection -LocalPort 5037 -State Listen` |
| `failed to connect to '127.0.0.1:9000'` | client 的 adb server 没启动，或隧道没有 `-R 9000` |
| `adb server version doesn't match this client` | client/server 的 adb 版本不一致，统一 platform-tools 版本 |
| `device unauthorized` | 在 client/设备上确认 USB 调试授权；这不是隧道问题 |
| `cannot bind '127.0.0.1:9000'` | 9000 已被其他进程占用；换一个远端端口 |
| `Warning: remote port forwarding failed for listen port 9000` | 另一个 SSH 会话已经占着 9000；只保留一个常驻隧道，不要给每个会话加 RemoteForward |

## 安全

- 只绑定 `127.0.0.1`；adb server 没有内建认证，不能暴露到公网。
- 不需要 adb 时关闭隧道或停止 adb server，减少攻击面。
- 不要把 adb 私钥、设备授权文件或平台签名密钥写进仓库、日志或聊天记录。
- 先确认目标设备：`adb -P 9000 devices` 的设备序列号应与你实际要操作的设备一致。