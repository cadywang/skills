# 审查与合并规则（REVIEW_POLICY）

> 一句话：**`main` 上的任何改动都必须来自 PR；CI 全绿、模板清单逐条勾选后，用 Rebase and merge 合入。**

## 一、三道闸门

| 闸门 | 位置 | 拦什么 | 能不能绕过 |
| --- | --- | --- | --- |
| ① 分支保护 | `governance/branch-protection.json` + `repository-settings.json`（由 `tools/create-github-repo.ps1` 施加） | 直推 `main`、强推、删分支、检查未绿就合并、用 Squash 压掉提交 | 不能：`enforce_admins: true`，管理员也一样 |
| ② 自动校验 | `.github/workflows/ci.yml` + `pr-gate.yml` | 编码/行尾/语法、skill 目录与 front matter、commit 规范 + DCO、PR 标题与清单 | 不能：改 CI 自己也要走同一个 PR 流程 |
| ③ 人工审查 | PR 本身 | 维护者看过 diff 与自测输出 | 单人模式下维护者即作者（GitHub 不允许自批），不设强制批准数 |

## 二、必需检查

| 检查 | 来自 | 查什么 |
| --- | --- | --- |
| `Hygiene (encoding, line endings, syntax)` | `ci.yml` | BOM/CRLF、Python/shell 语法、YAML、commit 规范 + DCO |
| `Skills (layout, front matter)` | `ci.yml` | `skills/*` 的目录结构、`SKILL.md` front matter、校验器自测 |
| `PR gate (title + merge checklist)` | `pr-gate.yml` | PR 标题内核规范 + 模板「合并前清单」是否逐条勾选 |

`strict: true`：PR 必须追上最新 `main` 才能合并。仓库只允许 **Rebase and merge**（不要 Squash）。

## 三、补丁必须保持同步

| 改了 | 必须同时改 |
| --- | --- |
| `skills/<name>/` | `README.md` 的 skill 表（新增/删除时）与该 skill 自己的 `references/` |
| `tools/` / `tests/` | 对应的自测与 `README.md` 的「本地校验」 |
| 门禁 / 规则（CI、PR 模板、`governance/`） | `README.md`、`CONTRIBUTING.md`、本文件 |
| skill 依赖的桥代码（`devctl.py`、`agent/`） | 到 [serial-debug-bridge](https://github.com/cadywang/serial-debug-bridge) 提对应 PR |

## 四、本地自查

```bash
python3 tools/check-skills.py
python3 tests/test_check_skills.py
python3 tests/test_check_commits.py
python3 tests/test_check_pr.py
python3 tools/check-commits.py --all
bash tools/dev-setup.sh          # 一次性：开启 sign-off + 安装提交钩子
```
