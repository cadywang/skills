# Codex Skills（cadywang 的 skill 合集）

> 把散落在各个项目里的 Codex skill 收拢到一处：**一个 skill 一个目录**，
> 装进 `~/.codex/skills/` 就能被 Codex 直接调用。

## 目录结构

```
skills/
└── <skill-name>/
    ├── SKILL.md          # 必需：front matter（name/description）+ 使用说明
    ├── scripts/          # 可选：可执行脚本
    ├── references/       # 可选：排障手册、协议等长文档
    └── assets/           # 可选：模板、示例文件
```

`SKILL.md` 的最小格式：

```markdown
---
name: my-skill
description: 一句话说明它做什么、什么时候该用（写给模型看的触发条件）。
---

# my-skill

## 怎么用

...
```

`name` 必须与目录名**完全一致**，`description` 不能为空——这两条由 CI 校验。

## 安装 / 卸载

```powershell
# Windows：把仓库里的某个 skill 复制进 Codex 的技能目录
Copy-Item -Recurse -Force .\skills\my-skill "$env:USERPROFILE\.codex\skills\"
```

```bash
# Linux / macOS
cp -r skills/my-skill ~/.codex/skills/
```

卸载就是删掉 `~/.codex/skills/<skill-name>/`；更新就是重新覆盖复制。

### `serial-debug-bridge` 额外需要 `devctl.py`

`serial-debug-bridge` 的 `scripts/sdb` 会按 `$SDB_DEVCTL` → `~/serial-debug-bridge/devctl.py`
→ `./cli/devctl.py` 的顺序找 `devctl.py`（它属于桥仓库，不属于本 skill）：

```bash
mkdir -p ~/serial-debug-bridge
curl -fsSL https://raw.githubusercontent.com/cadywang/serial-debug-bridge/main/cli/devctl.py \
  -o ~/serial-debug-bridge/devctl.py
# 或者 clone 整个仓库，然后 export SDB_DEVCTL=/path/to/cli/devctl.py
```

## 本仓库托管的 skill

| skill | 目录 | 用途 |
| --- | --- | --- |
| `serial-debug-bridge` | `skills/serial-debug-bridge/` | 在 server 侧通过串口桥操作嵌入式设备：执行命令、传文件、复位、交互控制台、链路排障 |

> skill 只负责「怎么用」；真正干活的 `agent/` 与 `devctl.py` 在
> [cadywang/serial-debug-bridge](https://github.com/cadywang/serial-debug-bridge)。
> `scripts/sdb` 需要那个仓库的 `devctl.py`，安装时一并放好（见下）。

## 外部托管的 skill（catalog）

这些 skill 仍以**源仓库**为唯一真源（避免两份副本漂移），本仓库只做索引：

| skill | 位置 | 用途 |
| --- | --- | --- |
| `cadywang-blog` | [cadywang.github.io → `skill/cadywang-blog`](https://github.com/cadywang/cadywang.github.io/tree/main/skill/cadywang-blog) | 把一次工作整理成中文技术博客，走 PR 并触发发布 |

> 想把某个 skill 也搬进来（由本仓库做唯一真源）时：把目录复制进 `skills/`，
> 再把源仓库里的那份删掉或改成指向本仓库，避免两份实现各改各的。

## 新增一个 skill

```bash
mkdir -p skills/<name>
$EDITOR skills/<name>/SKILL.md      # 按上面的最小格式
python3 tools/check-skills.py       # 本地校验，CI 跑同一套
```

提交（本仓库合并方式为 **Rebase and merge**，保持线性历史）：

```bash
git switch -c skill/<name>
git add skills/<name>
git commit -s -m "skill: add <name>"
git push -u origin skill/<name>
```

开 PR → CI 绿 → Rebase and merge。

## 约定

* 文档中文、代码与注释英文；文件为 UTF-8（无 BOM）+ LF。
* 不提交密钥、口令、内网地址等敏感信息。
* skill 里的命令要能复制即用；路径用占位符（如 `<client>`），不要写死某台机器。
* 一个 skill 只做一件事；触发条件写在 `description` 里，写清楚"什么时候用它"。

## 本地校验

```bash
python3 tools/check-skills.py        # 校验 skills/* 的目录与 front matter
python3 tests/test_check_skills.py   # 校验器自身的自测
```

## 许可证

MIT，见 [LICENSE](LICENSE)。
