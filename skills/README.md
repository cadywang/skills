# skills/

每个子目录就是一个 Codex skill，规则见根目录 [README.md](../README.md)。

已收录：

| skill | 说明 |
| --- | --- |
| `serial-debug-bridge` | server 侧串口调试；依赖 serial-debug-bridge 仓库的 `devctl.py` |

`cadywang-blog` 仍在它的源仓库里，见根 README 的 catalog。要新增一个 skill：

```bash
mkdir -p skills/my-skill
$EDITOR skills/my-skill/SKILL.md
python3 tools/check-skills.py
```

CI 会拒绝这些情况：缺 `SKILL.md`、缺 `---` front matter、缺 `description`、
`name` 与目录名不一致、文件带 BOM。
