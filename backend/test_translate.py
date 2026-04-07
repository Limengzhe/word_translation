import asyncio, time
from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(
        api_key="sk-e6264213b3b840dda1bfa09dfa6be2b5",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    html = '<p><strong>北京数据先行区服务有限公司</strong></p><p><strong>人员登记表</strong></p><p>填表时间：2026年3月16日</p><table><tr><td>姓名</td><td>性别</td><td>男</td></tr></table>'
    system = (
        "你是一位专业翻译员。请将以下zh文本翻译成en。\n"
        "要求：\n- 只输出译文，不加解释或额外内容\n- 保持原文的语义和语气\n"
        "这是一段 HTML 文档，请：\n"
        "- 完整保留所有 HTML 标签及其属性，不得增删或修改标签\n"
        "- 只翻译标签之间的文字内容，不翻译属性值\n"
        "- 直接输出完整翻译后的 HTML，不加任何解释"
    )

    t0 = time.time()
    print(f"[START] Sending translate_once request...")
    resp = await client.chat.completions.create(
        model="qwen-plus",
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": html},
        ],
    )
    elapsed = time.time() - t0
    print(f"[DONE] {elapsed:.1f}s")
    print(resp.choices[0].message.content)

asyncio.run(test())
