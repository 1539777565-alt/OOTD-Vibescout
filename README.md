# OOTD VibeScout

OOTD VibeScout 是一个面向内容社区穿搭决策的多模态 AI 搜索策略工具。它不做传统“找同款”，而是把用户上传的穿搭图片解析为风格 DNA、单品配方和跨平台搜索入口，帮助用户从“我喜欢这个感觉”快速过渡到“我知道该怎么搜、怎么替换、怎么搭”。

## 痛点挖掘与竞品分析

年轻用户在穿搭决策中真正缺的不是图片供给，而是从抽象审美到可执行搜索之间的翻译能力。项目围绕真实穿搭场景拆解了三类核心需求：

- 抽象审美难以描述：用户能感知“松弛感”“清冷感”“City Boy”等氛围，却很难把视觉感受拆成材质、廓形、场景和搜索关键词。
- 不同经济需求带来替换诉求：同一套穿搭对不同用户可能意味着找平替、找高质感升级款、找通勤可穿版本，而不是只要原图同款。
- 求异心理强于复刻心理：年轻用户往往排斥一比一照搬，更希望保留整体 Vibe，同时替换单品、降低撞款概率，形成自己的搭配表达。

在竞品分析上，传统电商“以图搜图”更擅长 SKU 层面的像素级匹配，适合找同款商品，但很难理解“氛围相似、价格不同、单品可替换”的审美意图。小红书、Instagram 等内容社区虽然有大量穿搭灵感，但检索高度依赖用户自己会描述风格，且中英文平台存在审美语义断层。

因此，本项目将业务切入点从“找同款”升级为“找同频氛围”，用多模态模型完成视觉审美的语义降维，再生成可解释、可调整、可点击的搜索策略。

## 产品方案

1. 输入层：用户上传一张穿搭图片，无需预先知道风格名或商品名。
2. 认知层：MiniMax VLM 将图片拆解为风格关键词、材质剪裁、穿搭场景和可复用单品配方。
3. 策略层：系统把模型输出转译为小红书中文搜索词和 Instagram 英文 hashtag，覆盖“整体氛围”和“单品拆解”两类路径。
4. 执行层：输出跨平台搜索入口，帮助用户按不同预算、不同场景和不同复刻程度继续探索。

项目本质上是一个 `Vibe-to-Query Translator`：把非结构化图片审美转成结构化搜索策略。相比直接爬取某几篇笔记，它更适合作为可演示、可解释、可扩展的 AI PM 项目：既体现了用户洞察和竞品差异，也展示了多模态理解、Prompt 约束、搜索链路设计和产品结果呈现能力。

## Demo Walkthrough

1. 上传穿搭图，一键生成跨平台搜索方案。

<img src="assets/demo/01-upload.png" alt="上传穿搭图" width="100%">

2. VLM 将图片拆解为风格 DNA，而不是只做同款识别。

<img src="assets/demo/02-style-dna.png" alt="风格 DNA 分析" width="100%">

3. 输出可搜索的单品配方，把抽象审美落到具体关键词。

<img src="assets/demo/03-formula.png" alt="可搜索穿搭配方" width="100%">

4. 小红书入口按“氛围”和“单品”拆开，避免长句搜索跑偏。

<img src="assets/demo/04-xhs-entry.png" alt="小红书拆解式搜索入口" width="100%">

5. Instagram 入口同步拆成 vibe hashtag 和单品 hashtag。

<img src="assets/demo/05-ins-entry.png" alt="Instagram 拆解式搜索入口" width="100%">

6. 单品关键词可直接跳转到小红书，查购买线索与上身图。

<img src="assets/demo/06-xhs-item-result.png" alt="小红书单品搜索结果" width="100%">

7. 氛围关键词用于找整体穿搭参考。

<img src="assets/demo/07-xhs-vibe-result.png" alt="小红书氛围搜索结果" width="100%">

8. 英文 vibe hashtag 用于补充全球风格参考。

<img src="assets/demo/08-ins-vibe-result.png" alt="Instagram vibe 搜索结果" width="100%">

9. 英文单品 hashtag 用于查局部廓形、材质和造型方式。

<img src="assets/demo/09-ins-item-result.png" alt="Instagram 单品搜索结果" width="100%">

## 本地运行

```bash
cd /path/to/OOTD-Vibescout
./ootd/bin/python ootd/app.py
```

如果 `7874` 端口被占用：

```bash
GRADIO_SERVER_PORT=7875 ./ootd/bin/python ootd/app.py
```

如需真实调用 VLM，可以设置环境变量；如果未设置，应用会尝试读取 OpenClaw 本地配置 `~/.openclaw/config/minimax.json`：

```bash
export MINIMAX_API_KEY="your_api_key"
./ootd/bin/python ootd/app.py
```

如果两处都没有 API Key，应用会明确提示缺少密钥，不会返回固定兜底结果。这样可以保证面试演示时每次上传图片都是真实 VLM 解析。
