# 项目工程规范总纲

本项目采用严格的**“全局通用宪法 + 语言专属细则”**管理模式。以下规则适用于所有代码生成、审查与重构任务。

---

## 一、全局通用原则（适用于所有语言与框架）

### 1. 核心命名与语言底线

- **绝对的英文命名**：**严禁使用拼音、中英混搭**。所有的类、变量、函数、数据库字段必须使用准确的英文单词。
- **规范化文档与中文注释**：**代码逻辑段落、类/函数文档必须使用中文**。在编写任何**类**和**函数/方法**时，**必须强制包含完整的文档字符串（Docstring）**，详细写明**类介绍、函数介绍、所有传入参数及返回值说明**。原则：除了说明参数与逻辑用途，更要解释核心逻辑**“为什么（Why）”**这么做。
- **技术债管理**：所有待办或待修复必须规范标记，如 `# TODO(优化/张三): 待XX优化` 或 `// FIXME(Bug/李四): 暂作兼容，需修复XX`。

### 2. 架构整洁与反“屎山”原则

- **物理文件拆分与模块化**：**坚决杜绝把大量代码、类或函数挤在一个文件里！** 必须按照业务逻辑或功能模块，将其合理切分到不同的物理文件和目录中，保持单个文件体量克制。
- **代码排版与层级清晰**：代码的缩进和逻辑块层级必须极其明显。不同逻辑段落之间必须适当留白（空行），坚决抵制互相挤作一团、缺乏可读性的代码排版。
- **防御性嵌套（卫语句）**：严禁“箭头型”深层嵌套代码。必须通过 `return`、`continue` 进行**异常/前置条件提前拦截**。最高嵌套层级要求<=3级。
- **单一职责（SRP）**：每个函数/方法限制在 **50行以内**，超过必须抽离。拒绝全能上帝类（God Class）。
- **杜绝硬编码（Magic Number）**：所有状态码、特殊字符串、配置项必须提取为常量（`UPPER_SNAKE_CASE`）、枚举（Enum）或环境变量。

### 3. 防御性编程与日志基线

- **底层排错日志（大厂运维标准）**：生产代码**绝对禁止**使用 `print()` 或 `console.log()`。必须走专用的 Logger，并在一切关键路径、状态切换、外部请求处打印详细的上下文日志。**每一条后端日志必须显式包含 `[类名] [方法名]` 前缀**。严格区分级别：`ERROR`（必须携带 `exc_info=True` 抓取完整堆栈并附带异常对象和上下文变量）, `WARN`, `INFO`（关键流转）, `DEBUG`（详细数据的抓取与调试）。
- **不要吞没异常**：严禁裸捕获异常并 `pass`。捕获异常后必须记录详细日志或向上传递。

### 4. 线程模型与解耦

- **分层架构**：界面/接口层（UI/Controller）与底层核心计算层（Service/Component）**必须物理分离**。
- **非阻塞主线程**：耗时的网络请求、大文件IO、高密度计算强迫放入**异步任务、线程池、协程**处理，严防UI卡死或主线程霸占。

### 5. 产物管理与测试痕迹清理（阅后即焚）

- **绝不遗留测试垃圾**：如果在研发解决问题的过程中，我为你生成了用于快速推理、执行验证结果、或者调试排错的**临时脚本文件、假数据文件、Mock JSON 等**，一旦问题排查完毕得出正确结论，**必须主动将这些临时文件彻底删除**。
- **保持提交纯净**：绝对禁止将带有 `test_xxx`（非官方单元测试）、`temp_run.py` 等非工程规划内的临时文件推进主代码库，保持项目工作区绝对干净。

### 6. 依赖管理与包配置

- **及时同步依赖文件**：如果有任何新增的第三方依赖包（如 `requirements.txt` / `package.json` / `pom.xml`）被引入项目中，**必须同步、及时地将其添加进对应的依赖管理文件**，绝不允许出现“本地代码跑得通，拉取代码后找不到包”的依赖缺失情况。

### 7. 命名美学与去脚本化 (Naming Aesthetics)

- **杜绝“脚本味”**：文件与目录命名必须清晰、精准地收敛于业务域或架构职责。严禁出现 `do_stuff.py`, `temp_run.js`, `test1.py`, `my_script.ts` 等随意的低级命名。
- **生态系统一致性**：文件名必须高度遵循技术栈的约定基准。Python 等后端资源坚决执行下划线 `snake_case.py`；前端组件坚守大驼峰 `PascalCase.vue`；项目公共文档采用短横线 `kebab-case.md`。整个项目保持工程级别的克制、优雅与专业感。

### 8. 数据库迁移强制闭环 (Migration Closure)

- **开发端必须完成迁移**：凡是涉及 Django Model 字段/索引/约束/`choices`/`Meta` 变更的改动，**必须在开发环境同步完成 `python manage.py makemigrations` 与 `python manage.py migrate` 两步**，验证迁移文件可正确生成并已落库后才能视为任务完成。
- **禁止把"待生成迁移"留到生产端**：严禁仅修改 Model 就提交代码、把 `makemigrations` 推给生产环境执行。生产端只允许执行 `git pull` + `migrate` 应用既有迁移文件，绝不应自行生成新的迁移文件。
- **迁移链同步前置检查**：在开发端生成新迁移前，**必须先确认本地与生产端的迁移链是否对齐**（对比最新 migration 文件名/编号）。若不对齐，先 `git pull` 同步生产端迁移文件，再 `makemigrations`，确保新迁移的 `dependencies` 挂在正确的最新节点上，避免出现同号分叉或孤儿 merge 文件。
- **提交清单**：变更 Model 时，commit 必须同时包含 ① Model 文件 ② 新生成的 `xxxx_*.py` 迁移文件，缺一不可。

> **注意**：针对特定的编程语言（Python, Vue/TS, Java, Markdown等）以及项目的架构目录规范，请自动读取并在上下文中合并 `.github/instructions/` 目录下的对应细化强约束指令。

---

## 二、AI 编码行为铁律（Andrej Karpathy Skills 进阶版）

> **来源**：Andrej Karpathy 对 AI 编程 Agent 常见问题的深刻洞察，由社区提炼为可执行的行为约束。原始 4 条铁律 + 社区 8 条进阶规则，共 12 条。目标：**把 AI 从"会错得很勤奋"变成"精准、克制、可验证"的工程伙伴。**

---

### 核心 4 条铁律（Karpathy 原版）

#### 铁律 1：编码前先思考（Think Before Coding）

> **不要假设。不要隐藏困惑。呈现权衡。**

**强制行为**：

- 不确定时必须停下来**问**，不能猜
- 存在多种理解时**列出选项**让用户选
- 有更简单的方案时**主动说出来**
- 困惑时**停止并提问**

**禁止行为**：

- ❌ 瞎猜需求、不确认就开写
- ❌ 隐藏不确定性，假装理解了模糊需求
- ❌ 自作主张选择技术方案而不告知替代选项

**标准输出格式**：

```text
【理解】任务是什么
【假设】我的假设是什么
【边界】需要注意的边界条件
【待确认】需要用户澄清的问题
```

---

#### 铁律 2：简洁优先（Simplicity First）

> **用最少的代码解决问题。不要过度推测。**

**强制行为**：

- 不加未被要求的功能（YAGNI — You Ain't Gonna Need It）
- 不给一次性代码创建抽象层
- 不加没人要求的"灵活性"和"可配置性"
- **200 行能写成 50 行？重写！**
- 单个函数/方法 ≤ 50 行
- 不创建不必要的抽象类（除非 ≥3 个具体实现）

**禁止行为**：

- ❌ 过度工程化，100 行能搞定的写成 1000 行
- ❌ 为"未来可能需要"提前设计扩展点
- ❌ 堆砌设计模式只为"看起来很专业"

**检验标准**：资深工程师看了会不会说"这太复杂了"？

---

#### 铁律 3：精准修改（Surgical Changes）

> **只碰必须碰的。只清理自己造成的混乱。**

**强制行为**：

- 一次变更聚焦单一目标
- 匹配现有代码风格（不要单方面分叉命名/格式）
- 每一行改动都能追溯到用户原始请求

**禁止行为**：

- ❌ "顺手优化"相邻代码、注释、格式
- ❌ 重构没坏的东西
- ❌ 删除已有注释（除非是明显的调试残留）
- ❌ 批量 reformat 未修改的代码
- ❌ 修一个 bug 顺带重构半个文件

**发现死代码/坏味道时**：**提一句就行，别动手删。** 让用户决定是否清理。

---

#### 铁律 4：目标驱动执行（Goal-Driven Execution）

> **定义成功标准。循环验证直到达成。**

**强制行为**：

- "修 bug" → **先写能复现 bug 的测试，再让它通过**
- "加验证" → **先写无效输入的测试用例，再让它通过**
- "重构" → **确保所有已有测试仍然通过**
- 多步骤任务必须列出每步的验证标准

**标准格式**：

```text
步骤 1：[操作] → 验证：[检查项]
步骤 2：[操作] → 验证：[检查项]
步骤 3：[操作] → 验证：[检查项]
```

**禁止行为**：

- ❌ 说"完成了"但没有验证证据
- ❌ 不提供测试通过的输出
- ❌ 未经验证就声称任务完成

---

### 社区进阶 8 条规则（60k+ Stars 社区共创）

#### 进阶 5：确定性优先（Deterministic First）

> **确定性操作用普通代码，AI 仅用于判断类任务。**

- 分类、起草、摘要、抽取、语义判断 → 可以用 AI
- 数学计算、字符串格式化、日期运算、类型转换 → **必须用普通代码**
- 不要拿 AI 做计算器、不要拿 AI 做类型转换器

**检查**：如果一段逻辑可以用确定性的 3 行代码写完，绝不让 AI 去"推理"它。

---

#### 进阶 6：Token 预算硬限制（Declare Budgets, Halt On Breach）

> **每步/每管线/每天设定 token 预算，超支立即停止。**

- 单任务 ≤ 4000 token
- 单 session ≤ 30000 token
- 超支时：停止、总结已完成内容、请示用户是否继续
- **不设预算的 AI 会无休止地"优化"下去**

---

#### 进阶 7：人在回路（Human-In-The-Loop）

> **破坏性操作必须人工审批。**

以下操作**绝对禁止**自动执行，必须先请示：
- 发送邮件、短信、推送通知
- 更新 CRM、数据库生产表、支付系统
- 删除文件（非临时文件）、删除分支、强制推送
- 调用外部付费 API
- 发布到生产环境

**流程**：AI 提出操作计划 → 人工审批 → AI 执行 → AI 报告结果

---

#### 进阶 8：AI 输出必须校验（Validate AI Output Against Schema）

> **AI 输出必须通过结构校验，不匹配则重试或停止。**

- 凡是需要结构化输出的任务，**必须先定义 Schema**
- 输出不匹配 Schema → 重试 1 次 → 仍不匹配 → 停止并报告
- 禁止"差不多就行"——格式错误会级联放大

---

#### 进阶 9：写代码前先读懂（Read Before Writing）

> **先理解现有代码的输入、输出、调用链，再动手写。**

- 读目标文件的 exports、直接 caller、共用 utility
- 读同一板块内相邻文件，理解命名惯例和数据流
- **禁止**只看了文件名就开始写代码
- **禁止**只看函数签名就假设它"应该"做什么

---

#### 进阶 10：测试验证意图而非行为（Test Intent, Not Behavior）

> **业务逻辑改变时测试会失败才算合格的测试。**

- ❌ 坏的测试：验证"返回值为 `{status: 200}`"——这是测框架，不是测业务
- ✅ 好的测试：验证"当用户余额不足时，订单状态为 `REJECTED`"——业务意图
- 如果改了一行业务逻辑而测试全绿，那测试是废的

---

#### 进阶 11：多步骤任务设检查点（Checkpoint Multi-Step Tasks）

> **每完成一个步骤，总结"做了什么、验证了什么、还剩什么"。**

**标准格式**：

```text
✅ 已完成：[步骤描述]
🔍 已验证：[验证结果]
⏳ 剩余：[待完成步骤]
⚠️ 风险：[当前发现的问题]
```

**禁止**一路闷头执行到底，5 步之后用户已经不知道 AI 在干什么。

---

#### 进阶 12：失败要大声揭露（Fail Loudly）

> **预设"主动揭露不确定"，不要"藏起不确定"。**

- 遇到不确定 → **主动标记**，不要默默跳过
- 修改可能影响其他模块 → **主动列出影响范围**
- 方案有已知风险 → **主动声明风险**
- **宁可多报 3 个假警报，也绝不漏报 1 个真问题**

---

### Karpathy 原则 vs 传统开发的范式转换

| 传统开发 | Karpathy 模式 |
| ---------- | -------------- |
| 人写代码，AI 辅助检查 | AI 写代码，人审查决策 |
| 关注"怎么写" | 关注"写什么、为什么写" |
| 人从执行者变为架构师 | AI 从工具变为执行伙伴 |
| 测试验证代码正确性 | 测试验证业务意图不变 |
| 追求代码覆盖率 | 追求"改动最小、验证最准" |

---

### 安全与质量底线（不可协商）

- ❌ 永远不在代码中硬编码密钥（使用 `.env` 和环境变量）
- ✅ 所有用户输入必须验证和消毒
- ✅ 使用 OAuth2/JWT 标准认证，从不自己造轮子
- ✅ 上线前正确配置 CORS 和 HTTPS
- ✅ 审计依赖、锁定版本、避免不信任的包
- ✅ 人类审查每一块重要代码

### 避免 AI 死亡循环（Death Loop）

当 AI 反复修同一个 bug 却修不好时：
1. **停止** 让 Agent 继续尝试
2. **开启新对话**（清空已污染的上下文）
3. 描述具体 bug，先让它**评估报告**，不要直接修复
4. 确认根因被定位后，才允许写代码

---

## 三、Python & Django 后端专项架构与编程规范

> 适用于 `backend-master/` 下所有 `**/*.py` 文件

### 1. 结构与目录隔离规范

- **绝对路径模块导入**：**严禁使用相对路径导入**（如 `from . import xxx` 或 `from ..utils import xxx`）。无论是模块的导入还是函数的引用，**必须统一使用基于项目根目录的绝对路径导入**（例如 `from app.core.services.linkfox_client import LinkfoxClient`）。
- **文件与目录命名**：全小写单词，单词间必须使用下划线（如 `copywriting_view.py`）。
- **严格架构（MVP/MVC）**：
  - `views/` 目录：**仅**存放视图渲染、PyQt 信号绑定和调用逻辑，绝对禁止包含纯业务计算。
  - `components/` 或 `services/` 目录：负责纯粹业务逻辑，该目录**禁止**引入任何 Qt UI 库与控件。
  - `utils/` 目录：必须包含**无副作用的纯函数**或状态枚举。

### 2. 强类型约束与防屎山架构守则

- **Google Style 文档注释**：所有的函数和类**必须**使用符合 Google 规范的 Docstring 进行高度详尽的中文声明。
  1. 需要对函数或类的核心目的进行说明
  2. `Args:`：必须注明参数含义与类型。
  3. `Returns:`：必须提供详细的返回值含义与结构类型。
  4. 适用时提供 `Raises:` 说明错误场景，及 `Examples:` 提供示例代码。

  ```python
  def 获取用户数据(user_id: int, 缓存时间: int = 300) -> dict:
      """
      根据用户ID从数据库中获取用户详细信息。

      Args:
          user_id (int): 用户的唯一标识符。
          缓存时间 (int): 缓存有效期（秒），默认为 300。

      Returns:
          dict: 包含用户姓名、邮箱和注册时间的字典。若无则返回空字典 {}。

      Raises:
          ValueError: 当 user_id 为负数时抛出。

      Examples:
          >>> 用户信息 = 获取用户数据(123)
          >>> print(用户信息["name"])
      """
      pass
  ```

- **极度详尽的文档与中文注释**：**代码逻辑段落、类/函数文档必须使用中文**。在编写任何**类**和**函数/方法**时，**必须强制包含完整的文档字符串（Docstring）**。具体的注释格式和样例必须严格遵照对应语言的专项细则指引。
- **强制 Type Hints（类型约束）**：每个函数的入参、返回值、类属性，**必须**标注明确类型（如 `list[str]`, `Optional[dict[str, Any]]`）。严禁用 `Any` 铺满，强制兜底需要注释原因。
- **卫语句（Guard Clauses）**：在函数开头优先使用 `if not val: return`。严格控制 **3 层深度 `if`/`for` 嵌套**。
- **圈复杂度削减**：拒绝超长逻辑，方法写出超过 50 行必须抽取为 `私有方法 (_xxx)`。严防上帝类 (God Object)。
- **禁止长等号分隔注释**：严禁使用 `# ======` 这类视觉分隔型长注释。若需要保留段落说明，统一改为简洁单行注释，格式必须为 `# 主题：说明`，例如 `# UI装配：构建页面主体布局`。

### 3. PyQt/PySide 阻塞安全与 UI 无阻塞机制隔离（如适用）

- **绝对禁止阻塞 UI 线程**：后台网络请求、循环和耗时计算**必须**放在独立线程/协程中，**严禁**携带 `QLabel` 等 UI 对象穿越线程。
- **强制标准通信机制**：UI 更新唯一的合法途径是底层子线程发送 `QtCore.Signal` 后，由主线程槽函数重绘。

### 4. 鲁棒性网络、文件与日志原则

- **远离慢循环**：批量数据遍历请切片，严禁出现 `for` 多层嵌套和超大集合遍历。
- **安全释放的句柄**：读写文件强制用 `with open`，使用 `requests` **绝对不准不写** `timeout` 超时参数。
- **拒绝掩埋异常日志**：禁止出现 `try...except Exception: pass`。对于未知的报错，捕获后必须 `logger.error("操作失败，原因: %s", str(e), exc_info=True)` 将堆栈链路完全抛出。

---

## 四、前端专项规范 (Vue3 / TS / JS / HTML)

> 适用于 `vue3-element-admin-master/` 下所有 `**/*.{vue,js,ts,jsx,tsx,html}` 文件

### 1. 结构与格式原则 (Vue 3 范态)

- **绝对路径模块导入**：前台所有的组件、辅助方法与库的引入**严禁使用相对路径导入**（如 `import xxx from '../app/core/components/xxx'`）。**必须使用基于别名的绝对路径导入**（如 `import xxx from '@/app/core/components/xxx'` 等）。
- **激进的 Composition API**：强制废弃 `data()`, `methods` 等 Options API 写法。只能使用 `<script setup lang="ts">`。
- **响应式状态统一标准**：
  - 基础数据值使用 `ref`、层级较深对象用 `reactive`。
  - 需要解构的外部响应式结构必须使用 `toRefs`，防止解构后丢失响应式状态。

### 2. TypeScript 严格边界与文档标注

- **JSDoc 注释标准**：不管是 JS 还是 TS，任何类或者对外函数**必须符合 JSDoc 标准的中文注释**
  1. 必须使用 `/** ... */` 块。
  2. `@param {Type} name`：对每一个参数注明其用途、结构与类型定义。
  3. `@returns {Type}`：标注明确的返回值含义描述。
  4. `@throws {Type}`：若能抛出异常必须注记。可附加 `@example` 提供调用样例。

  ```javascript
  /**
   * 计算购物车中商品的总价。主要用于核心结算拦截处理。
   *
   * @param {Array<Object>} 商品列表 - 购物车中的商品数组。
   * @param {number} 商品列表[].价格 - 单个商品的价格。
   * @param {number} 税率 - 税率参数（例如 0.08 代表 8%）。
   * @returns {number} 融合运费后的含税总价。
   * @throws {Error} 如果商品列表为空则抛出计算中断错误。
   *
   * @example
   * const 总金额 = 计算总价([{价格: 100}], 0.08);
   */
  function 计算总价(商品列表, 税率) { return 0; }
  ```

- **消灭 Any，推行类型守卫**：全量推翻使用 `any` 对象，如果有动态参数走 `unknown`，依靠联合类型和属性守护鉴别。

### 3. 可靠网络请求与全局化 (Axios)

- **状态熔断器机制**：任何发起后端通信的网络按钮触发前必定加锁 `loading.value = true`，严禁让服务器承受因重复点击诱发的高频脏数据。
- **全局拦截与日志追踪**：仅留下一级业务流拦截。`401/403/500` 全权收拢于 Axios Response Interceptors 统筹拦截打印异常。

### 4. 样式隔离与资源污染

- **局部防御**：绝大多数界面文件必须封闭在 `<style scoped lang="scss">` 里。如果有深度样式向下穿透的修改只能通过 `:deep()` 严格约束在父级范畴内。
- **命名的规范化**：导入组件采取大驼峰 `PascalCase`（`import UserCard`）；`<template>` 中引用的自定义标签强制为连字符小写体 `kebab-case`（如 `<user-card>`）。

### 5. 代码风格与 Lint 标准强制执行

- **ESLint 校验铁律**：Vue 和 TS 代码必须遵循项目的 ESLint 校验标准。
- **提交前检查**：提交代码或建议代码之前，必须确保不存在未使用的变量、未处理的警告，以及任何违反项目中 `eslint.config.ts` 规则的语法问题（例如缩进、尾逗号、分号等）。
- **禁止绕过 Lint**：严禁随意使用 `// eslint-disable-next-line`、`@ts-ignore` 等注释来掩盖语法错误或类型报错；如遇特殊情况确实需要使用，必须跟上清晰的 TODO 中文注释说明为什么绕过。
- **模板与标签规范**：Vue 模板中的指令（`v-if`, `v-for`, `@click` 等）排序和闭合规范，也应当遵循 Lint 标准，保持统一的阅读体验。

---

## 五、项目标准化工程目录结构 (Architecture Layout)

### 核心设计原则

为保持架构整洁，所有新建和重构的文件都需要同时检查三类规则：与文件所在目录直接对应的专用章节、本节的通用原则，以及"通用工程治理"板块。若规则发生冲突，以与文件所在目录直接对应的专用章节为准。第 3 节仅适用于新增或调整 `tests/` 下的测试文件。

| 文件位置 | 主要遵守章节 | 说明 |
| ---------- | ------------------ | ------ |
| `backend-master/` | 第 1 节 | 同时遵守本节通用原则与"通用工程治理"板块。 |
| `vue3-element-admin-master/` | 第 2 节 | 同时遵守本节通用原则与"通用工程治理"板块。 |
| `tests/` | 第 3 节 | 同时遵守本节通用原则与"通用工程治理"板块，不适用前后端目录放置规则。 |

- **架构基础**: 前后端分离，后端 Django，前端 Vue 3 + TypeScript。
- **强制对齐**: 新建的文件必须严格按架构规范的表格分类存放。
- **纯粹内聚**: 确保每个文件仅包含与其主要功能直接相关的代码；仅在当前文件内被调用、且只服务于该文件主流程的辅助函数可以保留在本文件中，若辅助函数会被多个文件复用，则必须迁移到对应的共享目录，不能继续留在当前文件中。

### 职责分离示例

- **允许（Acceptable）**：在 `api_v1/views/` 中编写仅处理 HTTP 输入/输出的路由函数；跨模块的通用工具函数统一放入全局 `utils/`。
- **禁止（Unacceptable）**：在 `api_v1/models/` 内编写复杂的业务计算，或在前端 `src/views/` 组件内直接夹带外部数据转换逻辑。

### 通用工程治理

以下规则适用于所有新建和重构的文件，用于保证目录职责清晰且不发生错位放置：

- **职责对号入座原则**
  - **核心要求**: 每次创建新文件时，必须核实该文件承载的职责，并归入对应的架构目录。
  - **禁止事项**: 绝不允许在项目根目录或者 `utils/` 等泛用型文件夹中丢弃混杂业务逻辑的孤立文件。
  - **示例**: 若新增用户过滤函数，应放在 `src/composables/`（前端逻辑复用） 或 `api_v1/services/`（后端业务逻辑），而不是根目录或全局 `utils/`。

- **职责归类铁律 (Responsibility-Bound Implementation)**
  - **核心要求**: 任何新增/修改的代码都**必须按职责归类落地**，绝不允许"一段代码直接落在最近的那个文件里就完事"。
    - 数据形态的字段映射、序列化输出、入参校验 → 必须放入 `serializers/`（前端 API 层放入 `src/api/` 对应模块）。
    - 数据库结构、字段、关联、索引、Manager → 必须放入 `models/`，不能在 view 或 service 里临时拼装。
    - 业务计算、跨模型聚合、外部调用 → 必须放入 `services/`，不能塞进 view。
    - 路由控制、HTTP 入参解析、HTTP 出参包装 → 仅放在 `views/`，不可掺入业务逻辑。
  - **禁止事项**: 禁止在 `views/` 里直接拼字典返回前端、禁止在 `models/` 里写跨表业务计算、禁止在前端 `views/` 组件里写格式化/换算/翻译/枚举映射等数据加工逻辑。
  - **执行检查**: 提交前自检每段新写的代码，逐句反问"这段属于 model / serializer / service / view / api / store / composable 哪一层"，归错位置必须先迁移再提交。

- **数据出口最终成形原则 (Backend-Finalized Payload)**
  - **核心要求**: 所有面向前端的接口返回数据**必须在后端完成清洗、转换、聚合、字段重命名、枚举翻译、单位换算、时间格式化、空值兜底**等全部加工动作；前端拿到响应后**必须可以直接渲染或绑定，不再做任何二次数据转换**。
    - 涉及枚举值翻译（如 `1 -> "已发布"`）必须在后端 serializer 或 service 层完成。
    - 金额、百分比、汇率、日期、时区等格式化必须在后端定型为前端可直接展示的字符串/数字。
    - 列表分页、排序、筛选、聚合统计必须在后端落定，前端只负责取值与展示。
  - **禁止事项**: 严禁前端用 `map / reduce / 自定义 formatter` 等方式补救后端给的"半成品"数据；严禁在前端 `views/`、`components/`、`composables/` 中编写业务字段重映射、字典翻译、跨字段衍生计算等逻辑。
  - **唯一例外**: 纯展示层 UI 状态（折叠/展开、本地排序高亮、纯前端选中态）和与后端无关的本地交互可以在前端处理，但**不得改变数据语义**。

---

### 1. 后端架构规约 (Django - `backend-master/`)

如当前任务位于 `backend-master/`，仅需遵守本节；本节只描述后端目录的放置规则与职责边界。

#### 核心配置与服务

| 目录/文件 | 核心职责与约束规范 |
| ---------- | ------------------ |
| `backend_master/` | 全局核心配置分发（如 `settings.py`, `urls.py`, `asgi.py` 等）。 |
| `openapi/` | 外部服务接口对接（如 HTTP 客户端、加密 `aes.py`）。 |
| `media/` / `templates/` | 静态上传文件与模板存放区。 |
| `scripts/` / `tools/` | 运维发布、数据库迁移工具脚本，不参与主干业务。 |

#### API 业务模块 (`api_v1/`)

| 目录/文件 | 核心职责与约束规范 |
| ---------- | ------------------ |
| `urls.py` | 业务路由分发；按业务板块拆分为 `urls/` 包，每个板块一个 `xxx_urls.py`。 |
| `models/` | 数据库 ORM 实体数据契约。**禁止**包含复杂的业务逻辑，仅保留模型关联和属性。 |
| `serializers/`| 序列化与反序列化、参数校验、DTO 层。 |
| `views/` | Controller 层，负责 HTTP 处理与参数解析。**严禁**大段业务运算或未经封装的外部调用。 |
| `services/` | 核心业务计算、外部调用，遵循"胖 Service / 瘦 Controller"原则。 |
| `middleware/` | HTTP 中间件；每个中间件类一个文件。 |
| `permissions/` | DRF 权限类；每个权限类一个文件。 |
| `auth/` | 认证后端类；每个认证类一个文件。 |
| `tasks.py`| 异步任务解耦与独立流程隔离。 |
| `management/` | 自定义 Django 管理命令和脚本。 |

#### API 执行模块 (`api_v2/`)

`api_v2` 是与 `api_v1` 对称的独立 Django App，专职**工作流任务调度与异步执行**，不承载数据 CRUD 职责。鉴权与 `api_v1` 完全共享，数据访问可直接导入 `api_v1` 的 models 与 services。

| 目录/文件 | 核心职责与约束规范 |
| ---------- | ------------------ |
| `urls.py` | 任务 API 路由：启动（POST）、查询（GET）、取消（POST）。 |
| `models/` | 仅存放 `WorkflowExecution` 等任务生命周期追踪模型。**禁止**存放业务数据模型。 |
| `serializers/` | 请求参数校验（`WorkflowStartSerializer`）与响应 DTO（`WorkflowExecutionSerializer`）。 |
| `views/` | Controller 层，仅做 HTTP 解析与结果包装。**严禁**在此处编写业务逻辑。 |
| `services/` | 核心业务：并发检查、入队、状态同步、取消。遵循"胖 Service / 瘦 Controller"原则。 |
| `tasks/` | Celery 异步任务定义。每个任务类型一个文件，均需继承 `task_base.WorkflowTask`。 |
| `permissions/` | 权限类；默认继承 `IsAuthenticated`，后续可按需扩展角色控制。 |
| `migrations/` | 数据库迁移文件，由 `makemigrations api_v2` 生成。 |

**两条 Celery 队列**：
- `single_thread_queue`（`concurrency=1`）：文件转换、AI 推理等须顺序执行的任务。
- `parallel_queue`（`concurrency=4`）：批量数据处理等可并行的任务。

**并发锁定机制**：`WorkflowService.create_and_enqueue` 在入队前检查同类型任务是否处于 `pending/running` 状态，若有则抛出 `ValueError`，视图层统一返回 `409 Conflict`。

#### 1.x 一类一文件铁律（Single-Class-Per-File）

**强制要求**：后端业务代码必须按"一个类 / 一个职责单位 → 一个独立 .py 文件"组织，**绝不允许**把多个 Model/Serializer/View/Middleware/Permission/AuthBackend 等核心类堆挤在同一个文件中。

| 类型 | 拆分粒度 | 命名规范 | 存放位置 |
| ------ | --------- | --------- | --------- |
| **Model**（`models.Model`）| 每个 Model 类一个文件 | `snake_case.py`（与表语义一致，例：`lx_order_profit.py`）| `api_v1/models/<板块>/xxx.py` |
| **Serializer**（`serializers.Serializer/ModelSerializer`）| 每个 Serializer 类一个文件 | `xxx_serializer.py` | `api_v1/serializers/<板块>/xxx_serializer.py` |
| **View / ViewSet**（FBV 或 CBV）| 每个视图类（CBV）或独立路由函数（FBV）一个文件；同一资源的 list/detail/create 等可合并到一个 ViewSet 文件 | `xxx_view.py` 或 `xxx_viewset.py` | `api_v1/views/<板块>/xxx_view.py` |
| **Middleware** | 每个中间件类一个文件 | `xxx_middleware.py` | `api_v1/middleware/xxx_middleware.py` |
| **Permission** | 每个权限类一个文件 | `xxx_permission.py` | `api_v1/permissions/xxx_permission.py` |
| **Authentication Backend** | 每个认证类一个文件 | `xxx_auth.py` | `api_v1/auth/xxx_auth.py` |
| **Service** | 每个服务类或一组高度内聚的函数一个文件 | `xxx_service.py` | `api_v1/services/<板块>/xxx_service.py` |
| **Consumer**（WebSocket）| 每个 Consumer 类一个文件 | `xxx_consumer.py` | `api_v1/consumers/xxx_consumer.py` |
| **Celery Task**（`api_v2`）| 每个任务函数一个文件，必须继承 `WorkflowTask` 基类 | `xxx_task.py` | `api_v2/tasks/xxx_task.py` |

**板块化分组原则**：
- 同一业务板块（如 ads、listing、user、crawler、notice、system 等）的多个文件，**必须**用同名子文件夹聚合：例如 `api_v1/models/ads/`、`api_v1/views/ads/`、`api_v1/serializers/ads/`。
- 板块子目录必须包含 `__init__.py`，且统一在 `__init__.py` 中显式 `from .xxx import XxxClass` 重导出，使外部仍可通过 `from api_v1.models import XxxModel` 访问。
- 跨板块共享的基础类（如 `BasePermission`、`BaseService`）放在 `api_v1/<类型>/common/` 下。

**禁止事项**：
- ❌ 禁止 `models.py`、`serializers.py`、`middleware.py`、`permissions.py` 等单一巨型文件继续承载多个核心类。
- ❌ 禁止在一个 `xxx_views.py` 中堆放数十个无关视图函数（旧式聚合方式必须按板块拆分）。
- ❌ 禁止在 Model/Serializer 文件中夹带 View 或 Service 逻辑。
- ❌ 禁止跨板块的"公共大杂烩"文件，如 `common_views.py` 装载所有杂项视图。

**例外（允许聚合的情况）**：
- 极小的常量/枚举集合（< 3 个常量）可统一放在 `api_v1/<板块>/constants.py`。
- 同一 ViewSet 内部的 list/create/retrieve/update/destroy 等 action 方法属于同一类，无需再拆。
- 紧密耦合、不会单独复用的内部辅助函数（私有 `_xxx`）可与主类同文件。

#### 1.y Model 文件优雅书写铁律（Elegant Model Style）

**适用范围**：`api_v1/models/` 下所有 `.py` 模型文件，无论 `managed=True` 还是 `managed=False`。该铁律是"一类一文件"之外的**书写风格强制规范**，目的是保证模型文件具备一眼可读、一眼可维护、一眼可审查的高质量观感。

##### 必须遵守（MUST）

1. **模块顶部 docstring**：每个 model 文件第一行必须为 `"""<业务用途简述>（<table_name>，可选 managed=False）。"""`，明确该模型的业务定位与表名。
2. **导入顺序**：标准库 → `django.*` → 项目内 `api_v1.*`，每组之间空一行；严禁任何相对导入（`from . import ...` / `from ..xxx import ...`）。
3. **类 docstring**：每个 Model 类紧跟一行简洁中文 docstring，描述其业务含义（如 `"""Listing 业务指标表。"""`）。
4. **字段多行展开**：所有字段定义**必须**采用多行参数格式，每个参数独占一行、以逗号结尾，闭合括号单独一行；**字段与字段之间必须空一行**。
5. **`verbose_name` 强制使用关键字参数**：禁止 `models.CharField("名称", max_length=...)` 这种位置参数写法，必须 `verbose_name="名称"`。
6. **枚举使用 Choices 类**：所有 `choices` 必须采用 `models.TextChoices` / `models.IntegerChoices` 子类承载，并放在该 model 文件顶部（紧随 import 之后、Model 定义之前）；不允许散落的 tuple `CHOICES = ((1, 'x'), ...)`。
7. **`Meta` 三件套**：`verbose_name`、`verbose_name_plural`、`ordering` 必须显式声明；`managed=False` 模型必须显式写出 `managed = False` 与 `db_table = "..."`。
8. **`__str__` 类型注解**：必须实现 `def __str__(self) -> str:`，返回该实体最具辨识度的字段，禁止裸返回 `self.id`。

##### 严禁事项（MUST NOT）

- ❌ 单行塞入多个参数的紧凑写法：`models.CharField(max_length=100, blank=True, default="", verbose_name="X")` 一行到底。
- ❌ 用 `help_text` 代替 `verbose_name` 充当中文标签。
- ❌ 在 model 文件中夹带 service / view / 复杂业务计算逻辑（仅允许 `@property`、`Manager`、轻量字段派生）。
- ❌ 重复定义 `class Meta`（必须合并为唯一一份）。
- ❌ 留有 `# ... rest is the same` / `# TODO 待补全字段` 等占位注释提交主干。

##### 标准范式（Reference Template）

```python
"""Listing 业务指标表（lx_listing_metrics，managed=False）。"""
from django.db import models

from api_v1.models.listing.lx_listing_info import LxListingInfo


class ListingStatus(models.IntegerChoices):
    """Listing 上架状态枚举。"""

    OFFLINE = 0, "下架"
    ONLINE = 1, "在售"


class LxListingMetrics(models.Model):
    """Listing 业务指标表。"""

    listing = models.OneToOneField(
        LxListingInfo,
        on_delete=models.DO_NOTHING,
        primary_key=True,
        db_column="listing_id",
        related_name="metrics",
        verbose_name="关联 Listing",
    )

    status = models.IntegerField(
        choices=ListingStatus.choices,
        default=ListingStatus.ONLINE,
        verbose_name="上架状态",
    )

    class Meta:
        managed = False
        db_table = "lx_listing_metrics"
        verbose_name = "Listing 业务指标表"
        verbose_name_plural = "Listing 业务指标表"

    def __str__(self) -> str:
        return f"LxListingMetrics<{self.pk}>"
```

##### 自检清单（Pre-commit Checklist）

- [ ] 模块顶部有业务用途 docstring？
- [ ] 类有中文 docstring？
- [ ] 每个字段是否多行展开、字段间空行？
- [ ] `verbose_name` 全部使用关键字参数？
- [ ] 是否所有 `choices` 都走 `TextChoices` / `IntegerChoices`？
- [ ] `Meta` 三件套齐全、无重复？
- [ ] `__str__` 是否带类型注解且返回有意义的字段？
- [ ] 是否清理了占位注释、调试残留？

---

### 2. 前端架构规约 (Vue 3 + TS - `vue3-element-admin-master/`)

如当前任务位于 `vue3-element-admin-master/`，仅需遵守本节；本节只描述前端目录的放置规则与职责边界。

#### 应用入口与视图

| 目录/文件 | 核心职责与约束规范 |
| ---------- | ------------------ |
| `src/main.ts` / `App.vue` | 应用骨架入口。 |
| `src/layouts/`| 框架结构层组件（侧边栏、Header 导航）。 |
| `src/router/` | 路由守卫与前端导航表。 |
| `src/views/` | 纯粹 UI 视图。**严禁**夹带前端数据聚合与外部转换逻辑。 |
| `src/components/` | 跨页面复用的原生 UI 和业务抽离组件。 |

#### 状态与数据管理

| 目录/文件 | 核心职责与约束规范 |
| ---------- | ------------------ |
| `src/api/` | 独立网络处理。所有的外部请求必须汇聚于此，**禁止**视图里直接写 Fetch。 |
| `src/store/` | Pinia 全局状态数据源。 |
| `src/composables/` | Vue 3 Hooks 组合逻辑。 |

#### 通用工具与配置

| 目录/文件 | 核心职责与约束规范 |
| ---------- | ------------------ |
| `src/utils/` | 纯函数、无业务强耦合的辅助工具。 |
| `src/types/` & `enums/` | TS 接口契约、字典常量与枚举。 |
| `src/assets/` & `styles/`| 静态资源与全局 CSS/SCSS。 |

#### 2.x 一文件一职责铁律（Single-Responsibility-Per-File）

**强制要求**：前端业务代码必须按"一个 SFC 组件 / 一个 Store / 一个 Composable / 一个 API 模块 → 一个独立文件"组织，**绝不允许**把多个无关组件、多个 Store、多个 API 域堆在同一个文件中。

| 类型 | 拆分粒度 | 命名规范 | 存放位置 |
| ------ | --------- | --------- | --------- |
| **页面视图（View）** | 每个路由页面一个 SFC；超过 300 行必须拆分子组件 | `PascalCase.vue`（与路由名对齐，如 `ListingDetail.vue`）| `src/views/<板块>/XxxPage.vue` 或 `src/views/<板块>/Xxx/index.vue` |
| **业务组件（Component）** | 每个组件一个 SFC，仅做 UI 与本地交互 | `PascalCase.vue` | `src/components/<板块或通用>/XxxCard.vue` |
| **Composable（Hook）** | 每个 `useXxx` 一个文件 | `camelCase.ts`，前缀 `use`（如 `useListingTable.ts`）| `src/composables/<板块>/useXxx.ts` |
| **Pinia Store** | 每个 store 一个文件 | `camelCase.ts`，后缀 `Store`（如 `userStore.ts`）| `src/store/modules/xxxStore.ts` |
| **API 模块** | 每个后端资源域一个文件 | `camelCase.ts`（如 `listing.ts`、`order.ts`）| `src/api/<板块>/xxx.ts` |
| **类型定义** | 每个领域模型一个文件 | `camelCase.ts` 或 `xxx.d.ts` | `src/types/<板块>/xxx.ts` |
| **枚举/字典** | 每个枚举一个文件 | `camelCase.ts` | `src/enums/<板块>/xxxEnum.ts` |

**板块化分组原则**：
- 同一业务板块（listing、ads、order、user 等）必须用同名子目录聚合：`src/views/listing/`、`src/api/listing/`、`src/composables/listing/`。
- 板块根目录可放 `index.ts` 做按需聚合导出，**禁止**桶文件（barrel）一次导出整个目录的命名星号 `export *`，必须显式 `export { useXxx } from './useXxx'`。
- 跨板块共享的基础组件/Hook 放在 `src/components/common/`、`src/composables/common/`。

#### 2.y SFC 文件优雅书写铁律（Elegant SFC Style）

**适用范围**：`vue3-element-admin-master/src/` 下所有 `.vue` 单文件组件。

##### 必须遵守（MUST）

1. **三段式顺序**：SFC 文件块顺序固定为 `<template>` → `<script setup lang="ts">` → `<style scoped lang="scss">`，不允许任何其他顺序或省略 lang 属性。
2. **强制 `<script setup lang="ts">`**：禁用 Options API（`data()` / `methods` / `mixins`）；禁止裸 `<script>` 不带 `setup`。
3. **顶部 JSDoc 文件注释**：每个 SFC 在 `<script setup>` 第一行必须有中文块注释，注明该组件的业务用途、所属板块。
4. **`<script>` 内部分区顺序**（自上而下）：
   1. 类型导入（`import type {...}`）
   2. 第三方库导入（vue / element-plus / pinia 等）
   3. 项目内绝对路径导入（`@/api/...`、`@/composables/...`、`@/components/...`）
   5. `defineProps` / `defineEmits` / `defineExpose` 声明
   6. 响应式状态（`ref` / `reactive` / `computed`）
   7. Composable / Store 调用
   8. 业务函数（事件处理 `handleXxx`、数据加载 `loadXxx`）
   9. 生命周期钩子（`onMounted` / `onBeforeUnmount`）
5. **`defineProps` 必须带 TS 泛型**：`defineProps<{ foo: string; bar?: number }>()`，禁止运行时对象字面量写法。
6. **`defineEmits` 必须显式签名**：`defineEmits<{ (e: 'change', value: string): void }>()`。
7. **样式作用域隔离**：所有 `<style>` 必须 `scoped lang="scss"`，跨组件穿透只允许 `:deep()`，并必须在父级选择器内。
8. **模板风格**：自定义组件标签使用 `kebab-case`（`<user-card />`），属性顺序遵循 `指令(v-if/v-for) → ref/key → props → 事件(@click)`。

##### 严禁事项（MUST NOT）

- ❌ 单 SFC 文件超过 **400 行**（含模板与样式）。超出必须拆 `components/` 子组件或抽 `composables/`。
- ❌ `<script setup>` 中出现网络请求 `fetch` / `axios` 直接调用，必须经 `src/api/` 封装。
- ❌ 视图层做字段重命名、枚举翻译、单位换算、金额格式化（违反"数据出口最终成形原则"）。
- ❌ 使用 `any`、`@ts-ignore`、`// eslint-disable` 静默错误（特殊场景必须紧跟中文 TODO 说明原因）。
- ❌ 相对路径导入（`../../api/xxx`），必须 `@/api/xxx`。
- ❌ 全局污染：在 `<style>` 漏写 `scoped`，或在 `main.ts` 之外注入全局样式 / 全局指令。

##### 标准范式（Reference Template）

```vue
<template>
  <el-table v-loading="loading" :data="rows" :columns="columns" />
</template>

<script setup lang="ts">
/**
 * Listing 列表页：展示当前店铺下所有 Listing 的核心指标。
 * 所属板块：listing。
 */
import type { ListingRow } from '@/types/listing/listing'

import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { fetchListingPage } from '@/api/listing/listing'
import { useListingTable } from '@/composables/listing/useListingTable'

defineProps<{
  shopId: number
}>()

const loading = ref(false)
const rows = ref<ListingRow[]>([])

const { columns, pagination } = useListingTable()

async function handleLoad(): Promise<void> {
  if (loading.value) return
  loading.value = true
  try {
    rows.value = await fetchListingPage({ page: pagination.page })
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(handleLoad)
</script>

<style scoped lang="scss">
.listing-page {
  padding: 16px;
}
</style>
```

##### API 模块标准范式

```ts
/**
 * Listing 资源 API 模块：仅做请求封装，不做业务加工。
 */
import request from '@/utils/request'
import type { ListingRow, ListingQuery } from '@/types/listing/listing'

export function fetchListingPage(params: ListingQuery): Promise<ListingRow[]> {
  return request.get('/api/v1/listing/page', { params })
}
```

##### Composable 标准范式

```ts
/**
 * Listing 列表表格逻辑复用：仅承载视图无关的纯逻辑（列定义、分页状态）。
 */
import { reactive } from 'vue'

export function useListingTable() {
  const pagination = reactive({ page: 1, size: 20 })
  const columns = [
    { prop: 'msku', label: 'MSKU' },
    { prop: 'statusLabel', label: '状态' },
  ]
  return { columns, pagination }
}
```

##### 自检清单（Pre-commit Checklist）

- [ ] SFC 顺序为 `<template>` → `<script setup>` → `<style scoped>`？
- [ ] 顶部是否有中文 JSDoc 业务注释？
- [ ] 是否全部使用绝对路径 `@/...` 导入？
- [ ] `defineProps` / `defineEmits` 是否带 TS 泛型？
- [ ] 是否未在视图内做后端应该完成的格式化、翻译、聚合？
- [ ] 文件是否 ≤ 400 行？超长是否已拆子组件 / Composable？
- [ ] `<style>` 是否带 `scoped lang="scss"`？
- [ ] 是否无 `any` / `@ts-ignore` / `eslint-disable` 残留（或已附 TODO 说明）？

---

### 3. 测试规则

本节仅在创建或调整 `tests/` 下的测试文件时参考，用于避免把测试脚本或临时调试文件放入正式业务目录。

- **自动化与测试**
  - 📂 **`tests/`**: 专门存放自动化或单元测试脚本。严禁在正式代码主目录内抛填带有 `test_` 或 `temp_` 前缀的临时调试用脚本。

---

## 六、Markdown 文档专项规范

> 适用于所有 `**/*.md` 文件

本项目极其重视文档结构，文档是工程生命周期的基石。生成或重构任何 README、CHANGELOG、API Doc 或 ADR (架构决策) 时必须遵循以下铁律：

### 1. 中英混排与版面美学 (Typography)

- **空格隔离**：中文文字与英文单词、数字、关键符号（如外包代码块的小撇号 \`xxx\` ）之间，**绝对、必须**手动插入一个半角空格。禁止连板在一起降低可阅读性。
- **层级渐进**：使用标准 ATX 标题（形如 `# Heading`）。全文必须仅有一个 `# H1`，严禁跳级（例如从 `#` 直接跳到 `###`），不允许在标题末尾带冒号（`:`）。

### 2. 标准开源与商业级文档结构

- **README 标配六大块**：如需生成 `README.md`，必须包含以下标准化拓扑结构且按顺序列出：
  1. `<Title & Badges>` (项目名与徽章/状态图)
  2. `## 概述 (Overview)` (一句话讲明价值与特性)
  3. `## 环境依赖 (Prerequisites)` (列出 Python/Node 等最低兼容版本)
  4. `## 快速启动 (Getting Started & Install)` (如何 Clone、安装并 Run 起来)
  5. `## 配置与使用 (Configuration & Usage)`
  6. `## 核心架构 / 贡献指南 / 开源协议` (License/Maintainers)
- **更新日志规范**：任何变动记录必须遵循 `Keep a Changelog` 规范大纲。按照 `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security` 的业务域划分类别。

### 3. 代码片断与安全规约 (Code Blocks & Security)

- **高亮标明法**：任何放入文档片段的代码或配置，必须写明后缀。如 ````python`, ````yaml`, ````bash`。
- **消灭敏感硬编码**：文档绝不能含有真实的 API Keys、生产数据库账号、真实云服务器 IP，一律使用尖括号或 `YOUR_xxx` 宏替换说明，例如：`https://<YOUR_AWS_HOST>:<PORT>`。

### 4. 高级图表辅助说明 (Diagrams as Code)

- **一图胜千言**：当你（AI）需要给用户汇报复杂业务的"生命周期"、"线程流转"、"依赖链路"或"事件回调"时，请务必利用 Github Flavored Markdown (GFM) 原生支持的 **Mermaid.js**。
- **示例**：通过 ````mermaid \n flowchart TD \n / sequenceDiagram` 实时渲染时序交互与架构图，减少干干巴巴的冗长文字说明。

---

## 七、Git 提交与 Lint 规范

- **ESLint 校验铁律**：Vue 和 TS 代码必须遵循项目的 ESLint 校验标准。
- **提交前检查**：提交代码或建议代码之前，必须确保不存在未使用的变量、未处理的警告，以及任何违反项目中 `eslint.config.ts` 规则的语法问题（例如缩进、尾逗号、分号等）。
- **禁止绕过 Lint**：严禁随意使用 `// eslint-disable-next-line`、`@ts-ignore` 等注释来掩盖语法错误或类型报错；如遇特殊情况确实需要使用，必须跟上清晰的 TODO 中文注释说明为什么绕过。
- **变更 Model 时**：commit 必须同时包含 ① Model 文件 ② 新生成的 `xxxx_*.py` 迁移文件，缺一不可。
- **保持提交纯净**：绝对禁止将带有 `test_xxx`（非官方单元测试）、`temp_run.py` 等非工程规划内的临时文件推进主代码库。

---

## 八、冲突处理优先级

当规则发生冲突时，按以下优先级处理：

1. AI 编码行为铁律（第二章）—— 最高优先级，所有 AI 操作必须首先遵守
2. 文件所在目录的专用章节（`backend-master/` → 第三、五.1 章，`vue3-element-admin-master/` → 第四、五.2 章）
3. 全局通用原则（第一章）
4. 测试文件使用第五.3 章

---