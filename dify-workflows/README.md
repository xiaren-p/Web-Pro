# Dify 工作流配置

> 本目录存放 ERP AI 助手用到的 Dify 应用编排导出文件（DSL）。
> 修改后**重新导入 Dify** 即可生效，不需要改后端 / 前端代码。

## 文件清单

| 文件 | 用途 |
| ---- | ---- |
| [erp-ai-assistant.yml](erp-ai-assistant.yml) | ERP AI 助手主对话流，支持 `thinking_mode` 思考模式开关 |

## 关键设计：思考模式 (`thinking_mode`)

### 前后端契约

```text
前端点击「思考」chip
       ↓
ChatPanel.vue: thinkingEnabled.value = true
       ↓
POST /api/v2/ai/chat/  body.inputs = { thinking_mode: "on" | "off" }
       ↓
Django → DifyClient → POST /v1/chat-messages  inputs.thinking_mode
       ↓
Dify 工作流的「开始节点」收到变量 thinking_mode
       ↓
LLM 节点系统提示词通过 Jinja2 if/else 切换指令：
  on  → 输出 <think>推理过程</think> 答案
  off → 直接输出简洁答案
       ↓
前端 MessageItem.vue 解析 <think> 标签 → 折叠展示
```

### 变量定义（开始节点）

| 字段 | 值 |
| ---- | ---- |
| 变量名 | `thinking_mode` |
| 类型 | `select`（下拉选项） |
| 必填 | 否 |
| 默认值 | `off` |
| 选项 | `on` / `off` |

### 提示词模板（LLM 节点）

提示词使用 Jinja2 语法：

```jinja2
{% if thinking_mode == 'on' %}
（开启时的指令：要求输出 <think>...</think> + 答案）
{% else %}
（关闭时的指令：直接输出简洁答案，不要 <think> 标签）
{% endif %}
```

完整模板见 [erp-ai-assistant.yml](erp-ai-assistant.yml) 中 `nodes[].id == 'llm'` → `data.prompt_template[0].text` 字段。

## 如何导入到 Dify

1. 打开 Dify 后台 → **工作室**
2. 点 **创建应用** → 右上角 **导入 DSL 文件**
3. 选择 `erp-ai-assistant.yml`
4. 创建后进入应用 → 左侧菜单 **「访问 API」** → 复制 API 密钥
5. 把密钥填到服务器 `.env` 的 `DIFY_API_KEY`：

   ```bash
   DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxxx
   ```

6. 重启 Celery worker（让新 key 生效）：

   ```bash
   sudo systemctl restart celery-default celery-parallel celery-single
   ```

## 升级到真实推理模型（可选）

当前用 DeepSeek-V4-Flash + 提示词模拟思考。如果想接入真实推理模型（DeepSeek-R1 / Qwen3-Thinking 等），有两条路径：

### 路径 A：加条件分支节点（推荐）

在 Dify 编排页改造：

```text
开始 → IF/ELSE 节点 [thinking_mode == 'on']
        ├─ 是 → LLM-推理（DeepSeek-R1 / Qwen3-Thinking）→ 直接回复
        └─ 否 → LLM-普通（DeepSeek-V3）              → 直接回复
```

推理模型本身会输出 `<think>` 标签，前端无需改动。

### 路径 B：直接替换为推理模型

把现有 LLM 节点的 `model.name` 从 `deepseek-v4-flash` 改成 `deepseek-r1-distill-qwen-32b` 之类的推理模型。

提示词的 `if/else` 仍保留作为兜底——这样推理模型在 `thinking_mode=off` 时也会被强制约束不输出 `<think>` 标签。

## 修改提示词后的同步

**只改提示词**：

1. 在 Dify 编排页直接改 LLM 节点提示词
2. 点右上角「发布」
3. 完事——不需要重启 Django / Celery

**改了变量结构 / 节点拓扑**：

1. 改完后导出 DSL（Dify → 右上角 ⋯ → 导出 DSL）
2. 覆盖本目录下对应的 `.yml` 文件
3. `git commit` 留档

## 接 Plan Mode（结构化方案卡片）

如果以后要让 AI 输出 Plan 卡片（让用户勾选选项后确认执行业务），按 `CLAUDE.md` 第三章的 Plan Schema 约定，在提示词里追加：

```text
当你判断需要让用户做选择 / 确认时（如"创建采购单"、"调整广告预算"），
除了自然语言说明，必须额外输出一段 <plan>...</plan> 包裹的 JSON：

<plan>
{
  "title": "卡片标题",
  "description": "简短说明",
  "options": [
    {"key": "stable_id_1", "label": "用户看到的文案"},
    ...
  ],
  "multi_select": false,
  "allow_custom": true,
  "custom_field": {"key": "remark", "label": "备注", "placeholder": "选填"},
  "confirm_action": {"endpoint": "", "method": "POST", "button_text": "确认"},
  "cancellable": true
}
</plan>

约束：
- options 的 key 必须是英文 / 数字组合
- 一次回复最多输出 1 个 <plan>
- 不需要选择时不要输出 plan 标签
```

后端 `plan_translator.py` 会自动从 `<plan>...</plan>` 提取并归一化为前端 Schema。
