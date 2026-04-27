#!/usr/bin/env python3
"""
OOTD VibeScout - Vibe-to-Query cross-platform outfit search translator.
"""

import json
import hashlib
import os
import re
import subprocess
from urllib.parse import quote_plus

import gradio as gr
from PIL import Image


MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
APP_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7874"))
ANALYSIS_CACHE = {}


DEFAULT_ANALYSIS = {
    "vibe_keywords": ["待识别"],
    "style_summary": "模型未返回完整风格摘要。",
    "material_and_cut": "模型未返回完整材质与廓形信息。",
    "styling_context": "模型未返回完整适配场景。",
    "core_formula": [
        {
            "category": "单品",
            "item": "模型未返回完整单品配方",
            "cn_keywords": ["穿搭灵感"],
            "en_keywords": ["outfit inspiration"],
        },
    ],
    "xhs_query": "穿搭灵感",
    "instagram_query": "outfit inspiration",
    "instagram_hashtags": ["ootd", "outfitinspiration"],
    "avoid_clone_tip": "保留整体氛围，替换一到两个关键单品形成个人版本。",
}


def save_temp_image(image_file):
    if image_file is None:
        return None
    temp_path = "/tmp/ootd_temp.jpg"
    if isinstance(image_file, Image.Image):
        image_file.convert("RGB").save(temp_path, "JPEG")
    else:
        Image.open(image_file).convert("RGB").save(temp_path, "JPEG")
    return temp_path


def image_digest(image_path):
    digest = hashlib.sha256()
    with open(image_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_json(text):
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def get_minimax_api_key():
    if MINIMAX_API_KEY:
        return MINIMAX_API_KEY

    config_path = os.path.expanduser("~/.openclaw/config/minimax.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as file:
                return json.load(file).get("api_key", "")
        except Exception:
            return ""

    return ""


def as_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,，、/|]+", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def normalize_hashtag(tag):
    tag = str(tag).replace("#", "").lower()
    tag = re.sub(r"[^a-z0-9_]", "", tag)
    return tag or "ootd"


def normalize_analysis(raw):
    data = dict(DEFAULT_ANALYSIS)
    if not isinstance(raw, dict):
        return data

    data["vibe_keywords"] = as_list(raw.get("vibe_keywords") or raw.get("Vibe_Keywords")) or data["vibe_keywords"]
    data["style_summary"] = raw.get("style_summary") or data["styleSummary"] or data["style_summary_cn"] or data["style_summary"]
    data["material_and_cut"] = raw.get("material_and_cut") or raw.get("Material_and_Cut") or data["material_and_cut"]
    data["styling_context"] = raw.get("styling_context") or raw.get("Styling_Context") or data["styling_context"]
    data["core_formula"] = raw.get("core_formula") or raw.get("Core_Formula") or data["core_formula"]
    data["xhs_query"] = raw.get("xhs_query") or raw.get("Search_Query") or data["xhs_query"]
    data["instagram_query"] = raw.get("instagram_query") or raw.get("English_Search_Query") or data["instagram_query"]
    data["instagram_hashtags"] = as_list(raw.get("instagram_hashtags") or raw.get("Instagram_Hashtags")) or data["instagram_hashtags"]
    data["avoid_clone_tip"] = raw.get("avoid_clone_tip") or raw.get("Avoid_Clone_Tip") or data["avoid_clone_tip"]
    return data


def call_minimax_vlm(image_path):
    if not image_path:
        return None
    api_key = get_minimax_api_key()
    if not api_key:
        raise RuntimeError("缺少 MINIMAX_API_KEY。请先在终端设置环境变量，再重新启动应用。")

    prompt = f"""你是一个懂小红书与 Instagram 审美语言的 AI Fashion PM。

请分析用户上传的穿搭图片，并解决一个核心痛点：
用户看得懂图片氛围，但说不出小红书中文搜索词，也不知道对应的 Instagram 英文风格标签。

产品默认目标：寻找同频穿搭氛围，同时拆解可复用的单品配方。

请只输出 JSON，不要输出 Markdown。保持简洁，core_formula 只输出 3 个最关键模块。字段如下：
{{
  "vibe_keywords": ["3-4 个中文风格词"],
  "style_summary": "一句话说明这套穿搭的风格 DNA，不要超过 45 字",
  "material_and_cut": "面料、剪裁、廓形判断，不要超过 45 字",
  "styling_context": "适合的真实生活场景，不要超过 35 字",
  "core_formula": [
    {{
      "category": "外套/内搭/下装/鞋履/配饰中的一种",
      "item": "可复用的单品配方，不要写具体品牌",
      "cn_keywords": ["2 个小红书中文关键词"],
      "en_keywords": ["1-2 个 Instagram 英文关键词"]
    }}
  ],
  "xhs_query": "一句适合小红书搜索的中文关键词，8-18 个字",
  "instagram_query": "one English query for Instagram search, 4-8 words",
  "instagram_hashtags": ["3-5 English hashtags without #"],
  "avoid_clone_tip": "如何保留氛围但避免完全照搬，不超过 45 字"
}}"""

    try:
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ootd-vibescout", "version": "1.0"},
            },
        }
        ready_req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        tool_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "understand_image",
                "arguments": {"prompt": prompt, "image_source": image_path},
            },
        }

        env = os.environ.copy()
        env["MINIMAX_API_KEY"] = api_key
        env["MINIMAX_API_HOST"] = "https://api.minimax.chat"

        process = subprocess.Popen(
            ["/Users/xiaohao/.local/bin/uvx", "minimax-coding-plan-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        try:
            stdout, stderr = process.communicate(
                input=json.dumps(init_req) + "\n" + json.dumps(ready_req) + "\n" + json.dumps(tool_req) + "\n",
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            raise RuntimeError("模型响应超时，请稍后重试或换一张更清晰的图片。") from exc

        for line in stdout.strip().splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("id") != 2:
                continue
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", str(payload["error"])))
            for item in payload.get("result", {}).get("content", []):
                if item.get("type") != "text":
                    continue
                raw = extract_json(item.get("text", ""))
                if raw:
                    return normalize_analysis(raw)

        if stderr.strip():
            raise RuntimeError(stderr.strip()[:600])
        raise RuntimeError("MCP understand_image 未返回有效 JSON。")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"VLM 解析失败：{exc}") from exc


def compact_terms(terms, limit=2):
    compacted = []
    for term in terms:
        term = str(term).strip()
        if term and term not in compacted:
            compacted.append(term)
        if len(compacted) >= limit:
            break
    return compacted


def xhs_url(query):
    return f"https://www.xiaohongshu.com/search_result?keyword={quote_plus(query)}"


def instagram_tag_url(tag):
    return f"https://www.instagram.com/explore/tags/{normalize_hashtag(tag)}/"


def first_meaningful_vibe(vibe_keywords):
    for keyword in vibe_keywords:
        if keyword and keyword != "待识别":
            return keyword
    return "穿搭氛围"


def build_search_cards(analysis):
    vibe = first_meaningful_vibe(analysis["vibe_keywords"])
    hashtags = [normalize_hashtag(tag) for tag in analysis["instagram_hashtags"]]
    cards = [
        {
            "platform": "小红书",
            "kind": "vibe",
            "title": "通过氛围找穿搭",
            "query": f"{vibe} 穿搭 氛围感",
            "url": xhs_url(f"{vibe} 穿搭 氛围感"),
            "reason": "先用最核心的 vibe 标签找整体参考，避免长句搜索把结果带偏。",
        },
        {
            "platform": "Instagram",
            "kind": "vibe",
            "title": "Explore Global Vibe",
            "query": f"#{hashtags[0]}",
            "url": instagram_tag_url(hashtags[0]),
            "reason": "用最接近整体氛围的英文标签进入 INS 视觉参考流。",
        },
    ]

    for item in analysis["core_formula"][:3]:
        category = item.get("category", "单品")
        cn_terms = compact_terms(item.get("cn_keywords", []), limit=2)
        en_terms = compact_terms(item.get("en_keywords", []), limit=1)

        if cn_terms:
            query = " ".join(cn_terms)
            cards.append(
                {
                    "platform": "小红书",
                    "kind": "item",
                    "title": f"寻找{category}单品",
                    "query": query,
                    "url": xhs_url(query),
                    "reason": "拆成单品关键词后搜索，适合找购买线索、上身图和搭配细节。",
                }
            )

        if en_terms:
            tag = normalize_hashtag(en_terms[0])
            cards.append(
                {
                    "platform": "Instagram",
                    "kind": "item",
                    "title": f"Find {category} Reference",
                    "query": f"#{tag}",
                    "url": instagram_tag_url(tag),
                    "reason": "用单品英文标签查局部廓形、配色和造型方式。",
                }
            )

    return cards


def formula_table(items):
    rows = ["| 模块 | 可复用配方 | 小红书关键词 | INS 关键词 |", "|---|---|---|---|"]
    for item in items[:5]:
        rows.append(
            "| {category} | {name} | {cn} | {en} |".format(
                category=item.get("category", "单品"),
                name=item.get("item", "—"),
                cn=" / ".join(item.get("cn_keywords", [])) or "—",
                en=" / ".join(item.get("en_keywords", [])) or "—",
            )
        )
    return "\n".join(rows)


def render_analysis(analysis):
    tags = " ".join([f"`{tag}`" for tag in analysis["vibe_keywords"]])
    return f"""### 风格 DNA

**痛点命中：** 这不是“找同款”问题，而是把看得懂但说不出的审美，翻译成两个平台都能搜的语言。

| 维度 | 结果 |
|---|---|
| Vibe 标签 | {tags} |
| 风格一句话 | {analysis["style_summary"]} |
| 材质与廓形 | {analysis["material_and_cut"]} |
| 适配场景 | {analysis["styling_context"]} |
| 产品目标 | 找同频氛围，并拆解可复用单品配方 |
| 避免照搬 | {analysis["avoid_clone_tip"]} |
"""


def render_links(cards):
    chunks = ["### 拆解式搜索入口"]
    for platform, intro in [
        ("小红书", "先看中文生活化穿搭，再按单品继续细搜。"),
        ("Instagram", "先看全球风格标签，再看单品廓形与造型方式。"),
    ]:
        platform_cards = [card for card in cards if card["platform"] == platform]
        if not platform_cards:
            continue
        chunks.append(
            f"""<div class="search-section">
<div class="section-head">
<h3>{platform}</h3>
<p>{intro}</p>
</div>
"""
        )
        for card in platform_cards:
            badge = "氛围" if card.get("kind") == "vibe" else "单品"
            chunks.append(
                f"""<div class="search-row">
<div>
<span class="badge">{badge}</span>
<b>{card["title"]}</b>
<p>{card["reason"]}</p>
</div>
<div class="search-action">
<code>{card["query"]}</code>
<a href="{card["url"]}" target="_blank">打开</a>
</div>
</div>"""
            )
        chunks.append(
            """</div>"""
        )
    return "\n\n".join(chunks)


def process_image(image_file):
    if image_file is None:
        return "### 风格 DNA\n\n请先上传一张穿搭图片。", "", ""

    try:
        temp_path = save_temp_image(image_file)
        cache_key = image_digest(temp_path)
        analysis = ANALYSIS_CACHE.get(cache_key)
        if analysis is None:
            analysis = call_minimax_vlm(temp_path)
            ANALYSIS_CACHE[cache_key] = analysis
        cards = build_search_cards(analysis)

        analysis_md = render_analysis(analysis)
        formula_md = "### 可搜索穿搭配方\n\n" + formula_table(analysis["core_formula"])
        links_md = render_links(cards)
        return analysis_md, formula_md, links_md
    except Exception as exc:
        return f"### 风格 DNA\n\n解析失败：{exc}", "", ""


theme = gr.themes.Default(primary_hue="stone", neutral_hue="slate")

custom_css = """
footer {display: none !important;}
body, html { background: #f7f4ef !important; }
.gradio-container { max-width: 1180px !important; margin: auto; padding-top: 28px; }
.main-title { text-align: center; margin-bottom: 4px; }
.gradio-row, .gradio-column, .gradio-group, .gradio-card { background: transparent !important; }
.markdown, .markdown * { color: #111827 !important; }
.search-section {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 14px 16px 6px;
    margin: 14px 0;
    background: #ffffff;
}
.section-head {
    border-bottom: 1px solid #eef2f7;
    margin-bottom: 6px;
    padding-bottom: 10px;
}
.section-head h3 { margin: 0 0 4px 0; font-size: 18px; }
.section-head p { margin: 0; color: #64748b !important; font-size: 14px; }
.search-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid #f1f5f9;
}
.search-row:last-child { border-bottom: 0; }
.search-row p {
    margin: 6px 0 0;
    color: #64748b !important;
    font-size: 14px;
}
.badge {
    display: inline-block;
    margin-right: 8px;
    padding: 2px 7px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #64748b !important;
    font-size: 12px;
    font-weight: 700;
}
.search-action {
    min-width: 220px;
    max-width: 320px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
}
.search-action a {
    flex: 0 0 auto;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 5px 12px;
    text-decoration: none !important;
}
code {
    background: #f1f5f9;
    border-radius: 6px;
    padding: 2px 6px;
    white-space: normal;
    line-height: 1.7;
}
a { color: #111827 !important; font-weight: 700; }
button { border-radius: 999px !important; }
@media (max-width: 760px) {
    .search-row { align-items: flex-start; flex-direction: column; }
    .search-action { min-width: 0; max-width: none; width: 100%; justify-content: space-between; }
}
"""


with gr.Blocks(theme=theme, css=custom_css) as demo:
    gr.Markdown("<h1 class='main-title'>OOTD VibeScout</h1>")

    with gr.Row():
        with gr.Column(scale=4):
            image_input = gr.Image(type="filepath", label="上传穿搭图片")
            analyze_btn = gr.Button("生成跨平台搜索方案", variant="primary", size="lg")

        with gr.Column(scale=6):
            analysis_output = gr.Markdown("### 风格 DNA\n\n等待上传图片分析。")
            formula_output = gr.Markdown("### 可搜索穿搭配方\n\n等待生成。")
            links_output = gr.Markdown("### 拆解式搜索入口\n\n等待生成。")

    analyze_btn.click(
        fn=process_image,
        inputs=[image_input],
        outputs=[analysis_output, formula_output, links_output],
    )


if __name__ == "__main__":
    print(f"-> http://localhost:{APP_PORT}")
    demo.launch(server_name="0.0.0.0", server_port=APP_PORT)
