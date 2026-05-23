---
name: local-skill
description: >
  列出 ~/.claude/skill-registry.md 中所有本地 skill，让用户挑一个加载。
  当用户说"列出本地 skill"、"local skill"等时使用。
---

# Local Skill

交互式从本地注册表挑选并加载 skill。

## 安装（首次加载时自动执行）

每次加载本 skill 时，先检查以下三项是否就绪，**缺哪项补哪项**，全部就绪则跳过：

### 1. Hook 脚本

检查 `~/.claude/hooks/register-skill.py` 是否存在。
若不存在，将本 skill 目录下的 `register-skill.py` 复制过去：

```bash
mkdir -p ~/.claude/hooks
cp <skill_dir>/register-skill.py ~/.claude/hooks/register-skill.py
```

其中 `<skill_dir>` 是本 SKILL.md 所在目录。

### 2. Stop Hook 配置

读取 `~/.claude/settings.json`，检查 `hooks.Stop` 中是否已包含 `register-skill.py` 的命令。
若不存在，用 Edit 工具将以下 hook 条目添加到 `hooks.Stop` 数组中（若 `hooks` 或 `Stop` 键不存在则创建）：

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 ~/.claude/hooks/register-skill.py"
    }
  ]
}
```

### 3. 注册表文件 & CLAUDE.md

- 检查 `~/.claude/skill-registry.md` 是否存在，若不存在则创建空注册表：

```markdown
# Local Skill Registry

| Skill | Path | Description |
|-------|------|-------------|
```

- 检查 `~/.claude/CLAUDE.md` 全文是否已有 `## Local Skill Registry` 段落。若没有，在末尾追加：

```markdown

## Local Skill Registry

[~/.claude/skill-registry.md](skill-registry.md)
```

### 4. 注册 `/local-skill` 命令

```markdown
---
description: 列出本地 skill 注册表，挑一个加载
---

调用 `local-skill` skill：读取 `~/.claude/skill-registry.md`，把所有 skill 列给用户选，根据用户选择加载对应的 SKILL.md 并按其指令执行。

具体流程参见 `~/.claude/skills/local-skill/SKILL.md`。
```

安装完成后输出一行确认：`local-skill 环境已就绪。`

---

## 执行流程

### 步骤 1：读取注册表

```
Read ~/.claude/skill-registry.md
```

注册表是 markdown 表格，每行格式：
`| `<project>:<skill-name>` | `<absolute-path>` | <description> |`

跳过表头/分隔行，按出现顺序提取所有条目（编号从 1 开始）。

### 步骤 2：展示列表

以编号列表呈现给用户，每条一行（不要再展开多行，保持紧凑）：

```
1. browser_work:daily-report-comment — 自动化飞书日报审核 (~/browser_work/skill/daily-report-comment/SKILL.md)
2. codegraph:publish — 发布 codegraph npm 包 (~/codegraph/.claude/skills/publish/SKILL.md)
...
```

路径用 `~` 缩写 `$HOME` 前缀，保持紧凑。

### 步骤 3：让用户选择

- **条目 = 1**：直接用纯文本提示「只有一个 skill：`<skill_id>`，要加载吗？」，等用户确认。
- **2 ≤ 条目 ≤ 4**：用 `AskUserQuestion` 工具，每个 skill 作为一个 option（label 用 skill_id，description 用注册表描述）。
- **条目 > 4**：用纯文本提示「请回复编号或 skill_id」，然后等用户回复。

### 步骤 4：加载选中的 skill

用步骤 1 解析出的 path，调用 `Read` 工具读取该 SKILL.md。

读完后：
- 一句话确认：`已加载 \`<skill_id>\``
- 按 SKILL.md 的指令继续，或等用户进一步指示

## 注意

- 注册表里若没有任何条目，告知用户「注册表为空，先用某个 skill 触发自动注册」即可，不要自己造数据。
- 不要修改注册表，只读不写。
