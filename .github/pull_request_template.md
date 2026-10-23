<!--
CI 门禁（勿删）：

  * 「合并前清单」小节里的每一项都由 .github/workflows/pr-gate.yml 强制校验，少勾一项就不能合并；
    改这里的条目等于改门禁，而模板本身也要走 PR。
  * PR 标题同样要符合内核规范 `<subsystem>: <祈使句摘要>`（仓库只允许 Rebase and merge，
    标题是检索入口；万一有人改回 squash 就会写进历史）。
  * 「变更类型」「影响面清单」是多选，照实勾选即可，不要求全部勾上。

完整规则见 REVIEW_POLICY.md。
-->

## 变更说明

<!-- 新增/修改了哪个 skill？解决什么问题？ -->

## 变更类型

- [ ] 新增 skill
- [ ] 修改 / 删除已有 skill
- [ ] 工具 / 校验脚本（`tools/`、`tests/`）
- [ ] 文档 / 仓库治理

## 影响面清单

- [ ] `skills/<name>/`
- [ ] `tools/` / `tests/`
- [ ] `README.md` / `CONTRIBUTING.md` / `REVIEW_POLICY.md`
- [ ] CI / 治理文件（`.github/`、`governance/`）

## 测试

```bash
python3 tools/check-skills.py        # skills/* 的目录与 front matter
python3 tests/test_check_skills.py   # skill 校验器自测
python3 tests/test_check_commits.py  # commit 门禁自测
python3 tests/test_check_pr.py       # PR 门禁自测
```

把上面的输出贴在这里（或说明为何不适用）：

## 合并前清单

> CI 强制逐条勾选（`pr-gate`）：**少一项就不能合并**。

- [ ] `tools/check-skills.py` 通过（新增/修改的 skill 目录与 front matter 都合规）
- [ ] 新增 skill 的 `name` 与目录名一致，`description` 写清了触发场景
- [ ] 文件为 UTF-8（无 BOM）+ LF
- [ ] 未提交密钥、口令、内网地址或临时产物（`__pycache__/`、`*.log`）
- [ ] 每个 commit 遵循内核规范：`<subsystem>: 祈使句摘要`、正文 72 列折行，并带 `Signed-off-by:`（`git commit -s`）
- [ ] PR 标题遵循内核规范 `<subsystem>: 祈使句摘要>`
- [ ] 改动了工具 / 校验 / CI 时，对应自测已更新并通过
- [ ] 面向使用者的行为有变化时，`README.md` 已同步更新

## 关联 Issue

<!-- 例：Closes #12 -->
