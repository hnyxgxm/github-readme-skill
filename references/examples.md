# 范例清单：14 个项目学什么、不学什么

2026-10-29 通过 GitHub contents API 读取了以下项目的完整 README 源文，并记录首屏、章节顺序、安装位置和证据类型。star 数为当日 API 返回值。这是组织方式的参考，不是质量认证，也不冻结它们的安装命令；采用任何命令前重新核实发布物。

## 采样方法

- 选不同交付物（CLI、TUI、库、框架、桌面、Web、平台、模型、Agent Skill），不选同一品类里最像的几个。
- 篇幅从 17 行到 663 行都有，避免只看到“标准长相”。
- 读完整文件，不只看标题和徽章；先看首屏能否说清用途，再看安装在第几节、证据是什么。
- 记录“值得学”的是结构选择，“别照搬”的是依赖其规模、社区或文档站的条件。

## 总表

| 项目 | 类型 | star | 行数 | 形态 |
| --- | --- | --- | --- | --- |
| astral-sh/uv | CLI | 91.3k | 326 | 路由页（文档站 + 功能清单） |
| BurntSushi/ripgrep | CLI | 69.5k | 541 | 中间态（仓库内 GUIDE） |
| jesseduffield/lazygit | TUI | 83.5k | 663 | 手册 |
| fastapi/fastapi | Web 框架 | 104.3k | 533 | 路由页 + 长示例 |
| colinhacks/zod | TS 库 | 44.2k | 218 | 路由页 |
| zed-industries/zed | 桌面 App | 92.4k | 48 | 路由页 |
| excalidraw/excalidraw | Web App | 134.8k | 124 | 中间态 |
| supabase/supabase | 托管平台 | 114.3k | 288 | 路由页 |
| karpathy/nanoGPT | 研究 / 训练 | 64.2k | 234 | 手册 |
| ggml-org/llama.cpp | 推理引擎 | 132.7k | 134 | 中间态 |
| shadcn-ui/ui | 组件库 | 126.8k | 17 | 路由页 |
| vercel-labs/skills | Agent Skill CLI | 37.0k | 122 | 中间态 |
| huggingface/transformers | 模型库 | 168.3k | 74 | 路由页 |
| simonw/llm | CLI + 插件 | 12.7k | 409 | 路由页 + 长参考 |

## 逐个看

- **uv**（326 行，8 个 H2）：一句定位后立刻给基准图和说明，Highlights 每条带锚点，Installation 是第 2 节。学“承诺 → 证据 → 上手”之间没有形容词；不学它把全部子命令特性铺进 README——它有独立文档站兜底。
- **ripgrep**（541 行，正文用 `###` 而非 H2）：首屏 quick links 第一个就是 Installation，正文安装排得很后也不影响上手。学“参考型长文靠 quick links 分流”；不学不用 H2 分层——GitHub 大纲里看不出结构，只有极短或极稳定的文档才这么写。
- **lazygit**（663 行，13 个 H2 + TOC）：Elevator Pitch 用第一人称讲痛点，Features 每条一个 H3 加一张动图，Alternatives 单独成节。学能力与边界并列；不学 TOC、赞助区和 13 个 H2 的密度——小项目会过载。
- **fastapi**（533 行，11 个 H2）：Opinions 一节直接谈设计立场，示例从最小到升级形成链条。学立场可以被写出来；不学首屏上半的赞助商与纪录片推广。
- **zod**（218 行，4 个 H2）：What is Zod、Features、Installation、Basic usage 四段就够，深度全在文档站。学路由页的克制；不学特性段里的营销形容词，那部分要换成行为描述。
- **zed**（48 行，1 个 H2）：徽章、一句定位、下载与各平台包管理器、平台可用性（包括“Web 还没有，去这条讨论跟踪”）、开发与许可。学“平台边界写进首屏”；不学用大量 `###` 代替分层——它内容少才成立。
- **excalidraw**（124 行，8 个 H2）：在线入口 excalidraw.com 先于本地启动，集成方列表说明生态。学托管产品先给可用入口；不学把截图全部外链托管，仓库内项目要能离线看到关键图。
- **supabase**（288 行，5 个 H2，0 个徽章）：能力清单每项挂 Docs，社区渠道按“Best for”分工，语言切换放在底部 Translations。学 0 徽章也能立住：清单加出处就够；不学 160 行的 How it works——那是文档的活。
- **nanoGPT**（234 行，10 个 H2）：首屏横幅直接写弃用并指向后继项目，install → quick start → reproducing → baselines 一条复现链。学状态写得显眼；不学图放在名称与定位之间。
- **llama.cpp**（134 行，6 个 H2）：Quick start 是第 1 节，6 个徽章全是 release、nightly、CI 这类可判断的信息，另设 Supported backends。学入口最先、徽章只留功能性；不学把维护者 PR 链接和封面大图堆进首屏。
- **shadcn/ui**（17 行，3 个 H2）：一句、首屏图、Docs、Contributing、License，其余全部交出去。学路由页的下限；不学在文档站不完整时照抄 17 行。
- **vercel-labs/skills**（122 行，10 个 H2）：一条 `npx skills add` 加 `-g` 作用域说明，客户端差异靠 `-a` 参数和 Supported Agents 列表，其他命令进表格。学“一个方法、多个参数”；不学把补充命令都堆在安装段。
- **transformers**（74 行，无 Markdown H2）：顶部 HTML 语言条列出 20 种语言，6–7 个徽章全为版本、CI、许可、文档在线状态、DOI，正文全部交给文档站。学语言条的完整与可维护性；不学 20 种语言的维护成本。
- **simonw/llm**（409 行，3 个 H2）：Quick start 给安装命令和第一个请求，Project news 记录动态，Contents 做目录。学“CLI + 插件”项目的分流；不学在没有文档站时照搬 409 行。

## 跨样本结论

- 14 个首屏都只有四类信息：名称、一句定位、徽章或出处，以及一个动作、证据或导航入口。顺序不同，成分没变。
- 形态决定下限，不决定上限：17 行的 shadcn 和 48 行的 zed 都有独立文档站，uv 同样有文档站却写到 326 行，因为它保留了完整功能清单；663 行的 lazygit 则把文档留在仓库里。
- 安装位置可以很后，但首屏必须能到达：ripgrep 靠 quick links，zed 和 llama.cpp 直接把安装放前面。
- 证据类型跟着交付物走：基准表（uv、llama.cpp）、界面（zed、excalidraw）、调用与输出（zod）、复现链（nanoGPT）、命令（skills）。
- `<details>` 在 14 份里只出现 3 次（fastapi 2 次、skills 1 次），且都收可选内容；折叠不是首屏的常规手段。
- 徽章从 0 到 6 个都有，supabase 一个都没有仍然清楚；徽章是判断材料，不是专业感的必需品。

## 不要从这些样本推出什么

- 不要按章节数对齐大项目。它们有文档站、社区渠道和发布流水线支撑那些章节；个人项目照搬会得到一堆空标题。
- 不要复制它们的定位句。那些句子依赖各自的生态位置，换个项目名就失去意义。
- 不要因为某项目用了某种排版就当作标准。居中、分隔线、HTML 语言条都是可选手段，先解决主次和分流。
- 这些是源文，不是渲染结果；图片是否加载、窄屏是否可读，仍需在目标平台实际查看。
