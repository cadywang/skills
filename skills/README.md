# skills/

每个子目录就是一个 Codex skill，规则见根目录 [README.md](../README.md)。

已收录：

| skill | 说明 |
| --- | --- |
| `serial-debug-bridge` | 通用远端串口桥：连接检查、执行命令、push/pull、交互 shell、复位和基础排障；依赖 serial-debug-bridge 仓库的 `devctl.py` |
| `reverse-ssh-scp` | 设备 SSH 可用时，通过反向隧道用 `scp -O` 传文件，并恢复 host key、authorized_keys 和 known_hosts |
| `lk-console-rescue` | 进入 Realtek LK 或 USB rescue，处理 rtkemmc、BCB、eMMC 和 WIC 镜像校验；建议与 `serial-debug-bridge` 一起安装 |
| `kernel-misra-c` | 编写、修改或审查 C 代码时应用 Linux 内核 coding style 与 MISRA C 约束；强调项目配置、偏差记录和静态分析证据 |

`cadywang-blog` 仍在它的源仓库里，见根 README 的 catalog。要新增一个 skill：

```bash
mkdir -p skills/my-skill
$EDITOR skills/my-skill/SKILL.md
python3 tools/check-skills.py
```

CI 会拒绝这些情况：缺 `SKILL.md`、缺 `---` front matter、缺 `description`、
`name` 与目录名不一致、文件带 BOM。
