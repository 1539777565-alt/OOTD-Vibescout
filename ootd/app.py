#!/usr/bin/env python3
"""
OOTD VibeScout - INS 风穿搭检索
"""

import json
import re
import os
import subprocess
import requests
import gradio as gr
from PIL import Image

MINIMAX_API_KEY = "sk-cp-eisa43u6xPF8Wuxb28chaca25VXeXj0tlf2MvJ1dsgvOsSMj0kG9m1y5oCw2wtlbOLjjSTuju0iZM4HwNJhT5qMsJPtvalGGzWte0pD3gOgMIJzgFOVvngY"


def save_temp_image(image_file):
    if image_file is None:
        return None
    temp_path = "/tmp/ootd_temp.jpg"
    if isinstance(image_file, Image.Image):
        image_file.save(temp_path, "JPEG")
    else:
        Image.open(image_file).save(temp_path, "JPEG")
    return temp_path


def call_mcp_understand_image(image_path):
    if not image_path:
        return None
    
    prompt = """你是一个顶级时尚买手。请分析这张穿搭图片，提取：
1. Vibe_Keywords: 3-5个核心情绪词
2. Material_and_Cut: 面料与剪裁
3. Styling_Context: 契合场景
4. Search_Query: 一句适合在小红书检索的中文短语（4-6个字）

JSON格式输出：
{"Vibe_Keywords": "xxx", "Material_and_Cut": "xxx", "Styling_Context": "xxx", "Search_Query": "xxx"}"""
    
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "ootd", "version": "1.0"}}}
    tool_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "understand_image", "arguments": {"prompt": prompt, "image_source": image_path}}}
    
    env = os.environ.copy()
    env["MINIMAX_API_KEY"] = MINIMAX_API_KEY
    env["MINIMAX_API_HOST"] = "https://api.minimax.chat"
    
    try:
        proc = subprocess.Popen(["/Users/xiaohao/.local/bin/uvx", "minimax-coding-plan-mcp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
        stdout, _ = proc.communicate(input=json.dumps(init_req) + "\n" + json.dumps(tool_req) + "\n", timeout=60)
        for line in stdout.strip().split("\n"):
            try:
                resp = json.loads(line)
                if resp.get("id") == 2 and "result" in resp:
                    for item in resp["result"].get("content", []):
                        if item.get("type") == "text":
                            m = re.search(r'\{[\s\S]*\}', item.get("text", ""))
                            if m:
                                return json.loads(m.group())
            except:
                continue
    except:
        pass
    
    return {"Vibe_Keywords": "简约, 气质, 高级", "Material_and_Cut": "未知", "Styling_Context": "日常", "Search_Query": "穿搭"}


def call_mcp_web_search(query):
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "ootd", "version": "1.0"}}}
    tool_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "web_search", "arguments": {"query": f"小红书 {query} 穿搭笔记"}}}
    
    env = os.environ.copy()
    env["MINIMAX_API_KEY"] = MINIMAX_API_KEY
    env["MINIMAX_API_HOST"] = "https://api.minimax.chat"
    
    try:
        proc = subprocess.Popen(["/Users/xiaohao/.local/bin/uvx", "minimax-coding-plan-mcp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
        stdout, _ = proc.communicate(input=json.dumps(init_req) + "\n" + json.dumps(tool_req) + "\n", timeout=30)
        for line in stdout.strip().split("\n"):
            try:
                resp = json.loads(line)
                if resp.get("id") == 2 and "result" in resp:
                    for item in resp["result"].get("content", []):
                        if item.get("type") == "text":
                            titles = re.findall(r'"title":\s*"([^"]+)"', item.get("text", ""))
                            if titles:
                                return [{"title": t[:50], "url": f"https://www.xiaohongshu.com/search_result?keyword={requests.utils.quote(t[:15])}&type=51"} for t in titles[:5]]
            except:
                continue
    except:
        pass
    return None


def process_image(image_file):
    if image_file is None:
        return "", ""
    
    try:
        temp_path = save_temp_image(image_file)
        vibe = call_mcp_understand_image(temp_path) or {"Vibe_Keywords": "时尚", "Material_and_Cut": "未知", "Styling_Context": "日常", "Search_Query": "穿搭"}
        
        query = vibe.get("Search_Query", "穿搭")
        results = call_mcp_web_search(query)
        
        if not results or len(results) < 3:
            results = [{"title": f"热门 {query}", "url": f"https://www.xiaohongshu.com/explore?q={requests.utils.quote(query)}"},
                      {"title": f"最新 {query}", "url": f"https://www.xiaohongshu.com/explore?q={requests.utils.quote(query)}"},
                      {"title": f"推荐 {query}", "url": "https://www.xiaohongshu.com/explore?q=" + requests.utils.quote(query)}]
        
        # 风格解析
        vibe_md = f"""### 🎨 风格解析

| 情绪关键词 | {vibe.get("Vibe_Keywords", "—")} |
|---|---|
| 面料与剪裁 | {vibe.get("Material_and_Cut", "—")} |
| 契合场景 | {vibe.get("Styling_Context", "—")} |
| 搜索关键词 | **{query}** |"""
        
        # 链接
        links_md = "### 🔗 小红书灵感\n\n"
        for i, r in enumerate(results[:4], 1):
            links_md += f"{i}. [{r['title']}]({r['url']})\n\n"
        
        return vibe_md, links_md
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ 出错: {e}", ""


# ==================== UI 骨架 ====================

# 1. 定义 ins 风亮色主题
ins_theme = gr.themes.Default(
    primary_hue="gray",
    neutral_hue="slate",
)

# 2. 隐藏底部水印 + 强制亮色
custom_css = """
footer {display: none !important;}
.gradio-container { max-width: 1100px !important; margin: auto; padding-top: 40px;}
body, html { background: #FAFAFA !important; }
.gradio-row, .gradio-column, .gradio-group, .gradio-card { background: #FFFFFF !important; }
.markdown { color: #111827 !important; }
h1, h2, h3, p, span, div { color: #111827 !important; }
a { color: #111827 !important; }
button { border-radius: 999px !important; }
"""

# 3. 构建左右分栏布局
with gr.Blocks(theme=ins_theme, css=custom_css) as demo:
    gr.Markdown("<h1 style='text-align: center; color: #111827; margin-bottom: 2rem;'>✨ OOTD VibeScout</h1>")
    
    with gr.Row():
        # 左侧：上传与操作区 (40%)
        with gr.Column(scale=4):
            image_input = gr.Image(type="filepath", label="上传穿搭图片", show_label=True)
            analyze_btn = gr.Button("🔍 提取 Vibe 并搜索", variant="primary", size="lg")
        
        # 右侧：展示区 (60%)
        with gr.Column(scale=6):
            vibe_output = gr.Markdown("### 🎨 视觉解构报告\n\n*等待上传图片分析...*")
            links_output = gr.Markdown("### 🔗 同频灵感穿搭链接\n\n*等待获取...*")
    
    # 事件绑定
    analyze_btn.click(fn=process_image, inputs=image_input, outputs=[vibe_output, links_output])

if __name__ == "__main__":
    print("→ http://localhost:7874")
    demo.launch(server_name="0.0.0.0", server_port=7874)
