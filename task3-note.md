# Task3学习笔记（工具调用）

> 本笔记是基于Datawhale开源课程[Agentic‑AI](https://github.com/datawhalechina/agentic-ai) 的@kangxun 个人学习笔记

### 实践总结

#### 1. LLM调用工具实践

**实践场景**：`运用LLM调用天气、写文本、生成二维码。` </br>
**实践结论**：多工具协作中，GPT类效果更好，遵循工具调用路径完成任务，Qwen-3-VL会陷入死循环，仅调用QR-code生成，其他任务未完成。</br>

**aisuite客户端优势**：支持一次性传入多个工具列表（其内部实现了Json Schema）；而自定义工具，得人工编写函数的描述Json Schema。</br>

---

#### 2. 模拟邮件系统的实践

* ​**搭建**​：在 ​**虚拟邮件服务器**，通过LLM进行邮件操作（增、删、改、查）
* **示例**

```
User: "I will be back in 10 mins" email to kid@example.com, the subject is "time schedule".
```
LLM 能自动识别：

| 任务             | 参数                            |
| ------------------ | --------------------------------- |
| **收件人** | `kid@example.com`           |
| **主题**   | `time schedule`             |
| **正文**   | `I will be back in 10 mins` |

随后调用对应的 **send\_email** 工具完成发送。

---

## 1️⃣ 工具使用的基本流程

```
用户提问 → LLM 判断需要调用的工具 → 调用工具 → 工具返回结果 → LLM 将结果作为上下文 → 给用户最终答案
```

### 常见工具

* ​**数据库访问**​（SQL/NoSQL）
* ​**网络搜索**​（Web、搜索引擎）
* ​**日历/时间查询**​（获取当前时间、时区转换）

> 实际使用时，往往会出现 ​**工具链**​（比如：先调用天气 API → 天气数据写到文件）。



## 2️⃣ 核心实现步骤

1. **开发者** 编写好工具的 ​**函数实现**​（包括输入/输出、异常处理）。
2. ​**系统提示词**​（system prompt）告知模型可用工具及调用方式，例如：
   ```
   You have access to a tool called get_current_time. To use it, return the following exactly:
   FUNCTION: get_current_time()
   ```
3. ​**执行工具**​，获取返回值（如时间字符串）。
4. **将结果** 作为上下文重新喂给 LLM，完成对用户的最终回答。



## 3️⃣ aisuite 中的工具描述（JSON Schema）

### 无参函数示例

```
{
  "type": "function",
  "function": {
    "name": "get_current_time",
    "description": "Returns the current time as a string",
    "parameters": {}
  }
}
```

### 带参函数示例

```
{
  "type": "function",
  "function": {
    "name": "get_current_time",
    "description": "Returns current time for the given time zone",
    "parameters": {
      "timezone": {
        "type": "string",
        "description": "The IANA time zone string, e.g., 'America/New_York' or 'Pacific/Auckland'."
      }
    }
  }
}
```

> ​**要点**​：
> 
> * `name` 必须与实际实现的函数名保持一致。
> * `description` 用于帮助 LLM 理解功能。
> * `parameters` 按 **JSON Schema** 规范描述每个字段的类型与含义。



## 4️⃣ 扩展：安全执行代码的工具

| 工具                        | 特点                                                      | 风险/防护                                  |
| ----------------------------- | ----------------------------------------------------------- | -------------------------------------------- |
| **Python `exec`** | 直接执行字符串代码                                        | 高风险（可能删除文件）           |
| **Docker / E2B**      | 在容器中隔离执行环境                                      | 有效降低系统级风险，适合不可信代码         |



## 5️⃣ 工具调用可增加反思

代码报错 → 将错误信息 + 原问题交回 LLM → 生成修正版代码



## 6️⃣ MCP（Model Context Protocol）概念

* ​**目标**​：为 **LLM** 提供统一的外部工具/数据访问方式，避免每个应用都要单独实现 M 个 API 调用。
* ​**结构**​：
  1. ​**客户端**​（如 Claude、ChatGPT）
     描述：能够访问外部工具、数据的应用程序
     * 发送访问请求给 MCP 服务器。
     * 接收MCP服务器的返回。
  2. ​**服务器**​（如 GitHub）
     描述：`提供工具和软件源的软件服务。
     * 接受MCP客户端的数据请求。
     * 工具调用结果返回给MCP客户端。
* ​**使用示例**​（Claude 查询 GitHub Pull Request）
  1. 用户提问：`“有哪些最新的 Pull Request?”`
  2. Claude 识别出 **GitHub** 访问请求。
  3. Claude 向 **GitHub** 服务器发送请求（包含 repo、时间范围等参数）。
  4. **GitHub** 服务器返回最新 PR 列表给Claude。
  5. Claude 将PR结果返回给 LLM，最终给用户回答。

> 通过 MCP，**工具数量**从 `m × n` 降至 `m + n`，显著降低开发与维护成本。



### 📌 小结

* **aisuite** 让工具函数的 **JSON Schema** 直接交给 LLM，省去手动包装的繁琐。
* **多工具协作** 需要模型具备良好的 **规划与调度** 能力，GPT 系列表现更稳健。
* **安全执行** 代码时推荐使用容器化（Docker/E2B）或专用沙箱，避免 `exec` 带来的系统风险。
* **MCP** 为 LLM 与外部工具之间提供统一协议，显著提升可扩展性与复用性。
