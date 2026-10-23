# 贡献指南（Contributing Guide）

本仓库收集 Codex skills。`main` 有保护：任何改动都必须走 PR，CI 全绿后用 **Rebase and merge** 合入。

## 1. 开发环境

| 组件 | 要求 |
| --- | --- |
| 校验与门禁 | Python 3.8+（只用标准库） |
| shell 脚本 | bash（Windows 上 Git Bash 即可） |

```bash
git clone git@github.com:cadywang/skills.git
cd skills
bash tools/dev-setup.sh      # 开启 format.signOff + 安装 commit-msg 钩子
```

## 2. 提交前必须本地通过

```bash
python3 tools/check-skills.py
python3 tests/test_check_skills.py
python3 tests/test_check_commits.py
python3 tests/test_check_pr.py
```

## 3. 提交规范（Linux 内核风格 + DCO）

* 格式：`<subsystem>: <祈使句摘要>`，不超过 72 列，结尾不加句号；
* subsystem 例如 `skill:`、`tools:`、`docs:`、`ci:`、`repo:`；
* 正文说明 what/why，72~75 列折行；不要用 `feat:` / `fix:` 这类 conventional-commit 标签；
* 每个提交带 `Signed-off-by:`（`git commit -s`，`tools/dev-setup.sh` 之后会自动加）。

> 仓库只允许 **Rebase and merge**，PR 里的提交会原样落到 `main`，所以提交信息必须一开始就写对。
> 网页端 squash 合并会把 PR 标题写成提交标题——这也是标题同样要按内核规范的原因。

## 4. 代码与文档风格

* 文档中文、代码与注释英文；文件为 UTF-8（无 BOM）+ LF；
* 一个 skill 一个目录：`skills/<name>/SKILL.md`，`name` 必须等于目录名，`description` 写清触发场景；
* 不提交密钥、口令、内网地址或临时产物；路径用 `<client>` 这类占位符；
* 工具只依赖 Python 标准库；修改 `tools/` / `tests/` 时同步更新自测。

## 5. PR 流程

1. 从 `main` 切分支（`skill/<name>`、`tools/<what>`）；
2. 开 PR：标题用内核规范，按模板勾选「合并前清单」（`pr-gate` 强制校验）；
3. 等 3 个必需检查全绿：`Hygiene (encoding, line endings, syntax)`、
   `Skills (layout, front matter)`、`PR gate (title + merge checklist)`；
4. 维护者 **Rebase and merge**（线性历史，合并后自动删除分支）。

## 6. 许可

提交即表示同意你的贡献在 MIT 许可下发布（见 `LICENSE`）。
