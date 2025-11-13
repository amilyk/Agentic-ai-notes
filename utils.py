# === Standard Library ===
import os
import re
import json
import base64
import mimetypes
from pathlib import Path

# === Third-Party ===
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image  # (kept if you need it elsewhere)
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from html import escape

# === Env & Clients ===
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
zhipu_api_key = os.getenv("ZHIPU_API_KEY")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

# Both clients read keys from env by default; explicit is also fine:
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()
anthropic_client = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else Anthropic()
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
deepseek_client = OpenAI(api_key=deepseek_api_key,base_url=DEEPSEEK_BASE_URL) if deepseek_api_key else OpenAI()
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
zhipu_client = OpenAI(api_key=zhipu_api_key,base_url=ZHIPU_BASE_URL) if zhipu_api_key else OpenAI()

def zhipu_chat(model: str, prompt: str) -> str:
    """
    使用DeepSEEK AI 的 chat/completions 接口
    """
    resp = zhipu_client.chat.completions.create(
        model=model,                     # 例如 "glm-4", "glm-4-flash"
        messages=[
            {"role": "system", "content": "你是一个乐于助人的助手。"},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1024
    )
    return resp.choices[0].message.content

def deepseek_chat(model: str, prompt: str) -> str:
    """
    使用DeepSEEK AI 的 chat/completions 接口
    """
    resp = deepseek_client.chat.completions.create(
        model=model,                     # 例如 "deepseek-chat"
        messages=[
            {"role": "system", "content": "你是一个乐于助人的助手。"},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1024
    )
    # 兼容不同 SDK 版本的返回字段
    # 1.x 版：resp.choices[0].message.content
    # 0.28 版（旧版）可能是 resp.choices[0].text
    return resp.choices[0].message.content

def get_response(model: str, prompt: str) -> str:
    if "deepseek" in model.lower():
        return deepseek_chat(model, prompt)

    elif "glm" in model.lower():
        return zhipu_chat(model, prompt)

    elif "claude" in model.lower() or "anthropic" in model.lower():
        # Anthropic Claude format
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        return message.content[0].text

    else:
        # Default to OpenAI format for all other models (gpt-4, o3-mini, o1, etc.)
        response = openai_client.responses.create(
            model=model,
            input=prompt,
        )
        return response.output_text

# === Data Loading ===
def load_and_prepare_data(csv_path: str) -> pd.DataFrame:
    """Load CSV and derive date parts commonly used in charts."""
    df = pd.read_csv(csv_path)
    # Be tolerant if 'date' exists
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["quarter"] = df["date"].dt.quarter
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
    return df

# === Helpers ===
def make_schema_text(df: pd.DataFrame) -> str:
    """Return a human-readable schema from a DataFrame."""
    return "\n".join(f"- {c}: {dt}" for c, dt in df.dtypes.items())

def ensure_execute_python_tags(text: str) -> str:
    """Normalize code to be wrapped in <execute_python>...</execute_python>."""
    text = text.strip()
    # Strip ```python fences if present
    text = re.sub(r"^```(?:python)?\s*|\s*```$", "", text).strip()
    if "<execute_python>" not in text:
        text = f"<execute_python>\n{text}\n</execute_python>"
    return text

def encode_image_b64(path: str) -> tuple[str, str]:
    """Return (media_type, base64_str) for an image file path."""
    mime, _ = mimetypes.guess_type(path)
    media_type = mime or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return media_type, b64


import base64
from IPython.display import HTML, display
import pandas as pd
from typing import Any

def print_html(content: Any, title: str | None = None, is_image: bool = False):
    """
    Pretty-print inside a styled card.
    - If is_image=True and content is a string: treat as image path/URL and render <img>.
    - If content is a pandas DataFrame/Series: render as an HTML table.
    - Otherwise (strings/others): show as code/text in <pre><code>.
    """
    try:
        from html import escape as _escape
    except ImportError:
        _escape = lambda x: x

    def image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    # Render content
    if is_image and isinstance(content, str):
        b64 = image_to_base64(content)
        rendered = f'<img src="data:image/png;base64,{b64}" alt="Image" style="max-width:100%; height:auto; border-radius:8px;">'
    elif isinstance(content, pd.DataFrame):
        rendered = content.to_html(classes="pretty-table", index=False, border=0, escape=False)
    elif isinstance(content, pd.Series):
        rendered = content.to_frame().to_html(classes="pretty-table", border=0, escape=False)
    elif isinstance(content, str):
        rendered = f"<pre><code>{_escape(content)}</code></pre>"
    else:
        rendered = f"<pre><code>{_escape(str(content))}</code></pre>"

    css = """
    <style>
    .pretty-card{
      font-family: ui-sans-serif, system-ui;
      border: 2px solid transparent;
      border-radius: 14px;
      padding: 14px 16px;
      margin: 10px 0;
      background: linear-gradient(#fff, #fff) padding-box,
                  linear-gradient(135deg, #3b82f6, #9333ea) border-box;
      color: #111;
      box-shadow: 0 4px 12px rgba(0,0,0,.08);
    }
    .pretty-title{
      font-weight:700;
      margin-bottom:8px;
      font-size:14px;
      color:#111;
    }
    /* 🔒 Only affects INSIDE the card */
    .pretty-card pre,
    .pretty-card code {
      background: #f3f4f6;
      color: #111;
      padding: 8px;
      border-radius: 8px;
      display: block;
      overflow-x: auto;
      font-size: 13px;
      white-space: pre-wrap;
    }
    .pretty-card img { max-width: 100%; height: auto; border-radius: 8px; }
    .pretty-card table.pretty-table {
      border-collapse: collapse;
      width: 100%;
      font-size: 13px;
      color: #111;
    }
    .pretty-card table.pretty-table th,
    .pretty-card table.pretty-table td {
      border: 1px solid #e5e7eb;
      padding: 6px 8px;
      text-align: left;
    }
    .pretty-card table.pretty-table th { background: #f9fafb; font-weight: 600; }
    </style>
    """

    title_html = f'<div class="pretty-title">{title}</div>' if title else ""
    card = f'<div class="pretty-card">{title_html}{rendered}</div>'
    display(HTML(css + card))

def image_zhipu_call(model_name: str, prompt: str, media_type: str, b64: str) -> str:
    """
    调用 DeepSeek 多模态模型，返回模型生成的文字回复。
    参数说明：
        model_name  DeepSeek 模型名称（多模态模型）
        prompt      文本提示
        media_type  图片 MIME 类型 (image/jpeg、image/png 等）
        b64         已经 base64 编码好的图片二进制数据（不含 data: 前缀）
    """
    data_url = f"data:{media_type};base64,{b64}"
    resp = zhipu_client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    result = (resp.choices[0].message.content or "").strip()
    return result

def image_deepseek_call(model_name: str, prompt: str, media_type: str, b64: str) -> str:
    """
    调用 DeepSeek 多模态模型，返回模型生成的文字回复。
    参数说明：
        model_name  DeepSeek 模型名称（多模态模型）
        prompt      文本提示
        media_type  图片 MIME 类型 (image/jpeg、image/png 等）
        b64         已经 base64 编码好的图片二进制数据（不含 data: 前缀）
    """
    data_url = f"data:{media_type};base64,{b64}"
    resp = deepseek_client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "image": data_url},
                ],
            }
        ],
    )
    content = (resp.choices[0].message.content or "").strip()
    return content


def image_anthropic_call(model_name: str, prompt: str, media_type: str, b64: str) -> str:
    """
    Call Anthropic Claude (messages.create) with text+image and return *all* text blocks concatenated.
    Adds a system message to enforce strict JSON output.
    """
    msg = anthropic_client.messages.create(
        model=model_name,
        max_tokens=2000,
        temperature=0,
        system=(
            "You are a careful assistant. Respond with a single valid JSON object only. "
            "Do not include markdown, code fences, or commentary outside JSON."
        ),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            ],
        }],
    )

    # Anthropic returns a list of content blocks; collect all text
    parts = []
    for block in (msg.content or []):
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def image_openai_call(model_name: str, prompt: str, media_type: str, b64: str) -> str:
    data_url = f"data:{media_type};base64,{b64}"
    resp = openai_client.responses.create(
        model=model_name,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
    )
    content = (resp.output_text or "").strip()
    return content
