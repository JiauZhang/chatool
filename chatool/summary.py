import os, fitz
from chatchat.tencent import Chat

system_instruction = '''
### 角色设定
- 你是一位专业的 AI 研究员

### 目标设定
- 你需要精炼的总结所给的论文内容
- 第一段精炼总结此论文要解决的问题，如果论文作者或者团队较为知名，也需把此信息增加到此段落内
- 第二段精炼总结此论文解决问题的方法
- 第三段精炼总结此论文方法所带来的效果
- 对于论文中的一些特有英文单词，你需要保持原样不要翻译成中文
- 你的输出只能使用纯文本格式，禁止使用 markdown 格式
'''
prompt = '''
总结如下论文内容：
{content}
'''
history = [
    {
        "role": "system",
        "content": system_instruction,
    },
]
chat = Chat(model='hunyuan-lite', history=history, client_kwargs={'timeout': None})

def extract_pdf_text(pdf_path, start_page=0, end_page=None):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"文件不存在: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        if end_page is None or end_page >= total_pages:
            end_page = total_pages - 1

        if start_page < 0 or start_page > end_page:
            raise ValueError(f"无效的页码范围: 开始页 {start_page}, 结束页 {end_page}")

        text = ""
        for page_num in range(start_page, end_page + 1):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text += '\n' + page_text
        doc.close()

        return text
    except Exception as e:
        raise Exception(f"提取PDF文本时出错: {str(e)}")

content = extract_pdf_text(r'D:\code\automation\arxiv-papers\2025-09-15\06-146.pdf')
print(f'content size: {len(content)}')
r = chat.chat(prompt.format(content=content))
print(r)
