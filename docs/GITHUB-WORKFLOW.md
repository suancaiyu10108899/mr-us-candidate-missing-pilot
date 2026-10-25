# 第一次参与本项目的 Git / PR 操作指南

读者：第一次使用 GitHub 合作的同学。本文帮助你交付自己的工作，不要求背命令。角色和验收约定以 [CONTRIBUTING](../CONTRIBUTING.md) 为准，科学定义以 [PROTOCOL](../PROTOCOL.md) 为准。

## 1. 先分清这些词

| 名称 | 在这里做什么 |
|---|---|
| 仓库 / clone | GitHub 保存共同历史；clone 在自己电脑建立副本 |
| Issue | 任务、认领人、计划、状态和交付链接 |
| 分支 | 自己推进改动的一条版本线，不是另一个数据包 |
| commit | 本地保存一个可追溯的改动；别人此时还看不到 |
| push | 把本地提交上传到自己的远端分支；此时还没有合并 |
| PR | Pull Request，请求审查并把一组改动合入目标分支 |
| base / compare | base 是想合入哪里，compare 是自己的改动来自哪里 |
| CI | 自动运行仓库已经提交的检查，不会自动替你补测试 |
| review / merge | 审查提出意见或批准；merge 才把改动整合进共同分支 |
| 输入 release | 固定数据包版本，与 GitHub 页面上的 Release 功能不是同一个概念 |

## 2. 认领任务，确认数据接收

打开自己的 [B #2](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues/2)、[C #3](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues/3) 或 [D #4](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues/4)，在右侧 **Assignees** 选择本人账号（或 **assign yourself**），即完成认领，无需 A 审批。在群里同步分工即可；多人想认领同一任务时先沟通，避免重复工作。

后续可在 Issue 简要记录下面的信息，按实际进度补充，不作为认领或开工的前置条件：

```text
GitHub 用户名 / 认领角色：
我理解的输入、输出与主要验收条件：
当前分支和 commit：
环境检查 / 输入包校验结果（未收到则如实写）：
准备先完成什么：
可投入时间 / 首次交付日期：
请求的复核角色：
```

B/C/D 都需开发输入包，D 另需评价参考包，按 [DATA-HANDOFF](../DATA-HANDOFF.md) 验证。没有科研包时仍可以认领并做人工开发；未收到就如实注明，不重新训练来补输入。PR 链接、测试结果和阻塞原因留在 Issue，方便后续接手。

assignee 表示负责完成任务的人，PR 的 reviewer 表示负责审查这次改动的人；两者分别设置。Issue 自行认领，PR 合并仍须至少一位非作者批准、CI 通过并解决审查讨论。

## 3. 在自己电脑安装与检查

先确认已有 Git 和 Python 3.10–3.12：

```powershell
git --version
python --version
```

如果默认 Python 是 3.13+，请选择已安装的受支持解释器创建环境，例如已有 Python 3.11 时用 `py -3.11 -m venv .venv`。不要在错误版本环境里反复安装。

首次取得当前 A 交付（已经 clone 的同学见下一节，不要在里面再 clone 一层）：

```powershell
git clone --branch codex/preexp-data https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot.git
cd mr-us-candidate-missing-pilot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m mrus_missing.cli status
git branch --show-current
git log -1 --oneline
```

Windows 全程直接调用虚拟环境里的 Python，无需运行 Activate.ps1。macOS/Linux 将 `.\.venv\Scripts\python.exe` 换成 `.venv/bin/python`。

成功标志：包安装成功；测试没有失败；你知道当前分支/commit；status 能区分当前 checkout 有无 B API。A 分支缺 B 时，相关人工接缝测试会明确 skipped，不表示 B 算法已通过。

首次 commit 前确认本仓 Git 作者身份；下面两项请填自己的值：

```powershell
git config --local user.name "你的姓名或GitHub用户名"
git config --local user.email "你在GitHub验证过的邮箱或账户页给出的noreply邮箱"
```

Git 作者邮箱影响提交能否关联账号；GitHub 登录决定推送权限。这两件事不同。

## 4. 在自己的分支开发

先运行 `git status`。若有未提交改动，先确认归属并保存到自己的任务分支；不要为了换分支执行 hard reset、覆盖文件或盲目清理。

当前 A PR #5 未合入 main 时，公共基线为 `origin/codex/preexp-data`。新建 C 分支的例子（仅尚无本人分支时）：

```powershell
git fetch origin
git switch --no-track -c codex/preexp-geometry origin/codex/preexp-data
```

D 使用 `codex/preexp-evaluation`；B 已有 `codex/preexp-matching`，不要重复新建。B 同步 A 更新的例子：

```powershell
git fetch origin
git switch codex/preexp-matching
git merge origin/codex/preexp-data
```

同步后，B 按 [匹配接入说明](MATCHING-INTEGRATION.md) 检查实际生产实现：没有第二候选或 `d2 ≤ eps` 时，`ratio` 和 `ratio_pass` 均为 `null`；记录生成器、writer 的字段校验及写出结果须一致。随后补齐 `tests/test_matching.py` 并运行专用测试和全套测试。A 的接口测试不能替代这些数值边界测试；旧结果在相应边界上会触发 `BACKEND_CONTRACT_ERROR`。

A PR #5 合入 main 后，共同基线改用 `origin/main`。已有本人分支通过 merge 同步，不重建仓库、不改写已推送历史。出现冲突时停下，记录冲突文件并与 A/相关作者确认，不默认覆盖另一方。

只改自己认领的模块和对应测试。A 维护公共输入/CLI/协议；跨模块改动先在 Issue 说明。

## 5. 提交实现和可复跑测试

测试源码是交付的一部分，必须进 Git；临时输出不是测试源码。测试应调用真正的生产函数，并覆盖协议边界。以 B 为例：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_matching.py -q
.\.venv\Scripts\python.exe -m pytest -q
git diff
git status
git add src/mrus_missing/matching tests/test_matching.py
git diff --cached
git commit -m "test: add reproducible matching boundary checks"
git push -u origin codex/preexp-matching
```

先真正创建/补齐 `tests/test_matching.py`，再运行以上命令。C/D 换成各自路径与分支。commit 信息描述实际改动，使用 new:/fix:/test:/docs: 等前缀。

检查暂存内容只包含打算交付的文件；科研数组、参考、ZIP、权重、私有路径和运行输出不进公共 Git。不要把所有文件盲目 `git add .`，也不要强制加入被忽略的数据。

成功标志：GitHub 上自己的分支出现这次 commit；并不是 main 已经更新。

## 6. 在网页开 Draft PR

1. 打开仓库的 **Pull requests → New pull request**，或推送后出现的 **Compare & pull request**。
2. 选择 base 和 compare。A PR #5 未合入时，B 选 base=`codex/preexp-data`、compare=`codex/preexp-matching`；确认差异只展示 B 的改动。这个过渡期先用草稿展示和讨论，不把 B 的 PR 提前合入 A 分支。A 合入后由 A 协调把 base 改为 main，按需同步共同基线，再检查 diff/CI；改 base 可能影响原来的审查评论。
3. 填标题和说明：解决什么问题、改了什么、输入/接口版本、实际测试命令与结果、未完成项。
4. 尚未完成时选 **Create draft pull request**。已具备审查条件时选 **Create pull request**。
5. 在对应 Issue 放 PR 链接和状态，写明约定的非作者复核角色。草稿达到交付条件后点击 **Ready for review**，再按下一节正式请求审查。

不要等所有代码完美才开草稿。PR 模板在 [.github/pull_request_template.md](../.github/pull_request_template.md)；模板进入默认 main 前，网页可能不自动填入，可手动复制。

Issue 包含后续科学交付时，代码初稿 PR 使用 `Refs #2` 等关联，不提前用 `Closes #2` 自动关闭整个任务。

## 7. 审查、返修、合并

PR 作者或 A 在右侧 **Reviewers** 选择约定的非作者账号，发出 review request；在群里说明分工不等于已经发出 GitHub 审查通知。具体模块负责人以 Issue assignee 和群内沟通为准，不根据某次 reviewer 身份推断其模块角色。审查者打开 PR 的 **Commits / Files changed / Checks**，核对当前最新 head 和该提交的 CI；旧提交上的检查或审查意见不能代替对更新内容的检查。

审查者先读 PR 目标和证据，再到 **Files changed** 看具体差异，并运行能够复跑的检查。不要只看 CI 绿灯。确认新增生产函数确实被专用测试覆盖。

- **Comment**：反馈意见，没有批准。
- **Request changes**：需要作者修复后复查。
- **Approve**：基于实际审查认可当前版本。

作者在同一个任务分支修复、commit、push，原 PR 会更新；无需每次返修重开 PR。作者或 A 在 Reviewers 中重新请求复核，审查者检查新 commit，更新结论。先前批准可能因新改动失效，需要重新审查。

工程审查首轮：B 审 A，C 审 B，D 审 C，A 审 D。D 对输入和科学评分的独立职责仍保留。审查不是必须批准；不懂的部分应指出，不能请 AI 代替本人承担确认。

main 要求非作者批准和 fixture-tests 通过。由 A 确认验收范围后执行合并；没有绕过保护的流程。合并后下游获取共同版本并确认能够消费产物，才算这阶段交付完成。PR 合并不自动等于科研结论成立。

## 8. 可选 gh / AI 辅助

Git 管代码版本，gh 是 GitHub 的命令行助手。网页可以完成 Issue/PR/review，不安装 gh 也能参与。

需要 gh 时按 [官方安装说明](https://github.com/cli/cli#installation) 安装，随后自己完成浏览器登录：

```powershell
gh auth login --web --git-protocol https
gh auth status
```

登录密码和 token 不交给群聊或 AI。AI 可以解释命令、检查 diff、协助编写测试和执行已明确的操作；每次操作前本人应知道分支、文件和目标。首次协作中，登录由本人完成，**Approve 由实际审查人理解改动后确认并操作，Merge 由 A 完成验收后确认并操作**。AI 的分析用于辅助判断，不能代替本人的审查结论或替其他账号批准。可选命令例子：

```powershell
gh pr create --base codex/preexp-data --head codex/preexp-matching --draft
gh pr view 5 --web
gh pr checks 5
```

## 9. 遇到阻塞怎么报告

发送命令、完整错误、当前分支/commit、Python 版本，以及数据包校验是否通过。不会 PR、缺依赖、没收到输入、算法检查失败是不同问题，分别说明。

`match-fixture` 报 B backend 不存在（退出3）：当前 checkout 尚未集成 B，实现不在这条分支。INVALID_INPUT（退出2）先核输入/配置版本，不修改 hash 让检查通过。BACKEND_CONTRACT_ERROR（退出4）交回 B/A 核接口，不把它误当作数据损坏或算法正常拒绝。数据校验失败则保留原包并向 A 反馈，不重新训练或替换数据。

权威操作说明：[创建 PR](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request)、[审查 PR](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request)、[gh 登录](https://cli.github.com/manual/gh_auth_login)。
