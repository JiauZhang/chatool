import os, fitz, argparse
from chatchat.client import Client

parser = argparse.ArgumentParser()
parser.add_argument('--provider', type=str, default='tencent')
parser.add_argument('--model', type=str, default='hunyuan-lite')
parser.add_argument('--pdf', type=str, required=True)
args = parser.parse_args()

instruction = '''
# 角色设定
- 你是一位专业的 AI 研究员
- 你首先需要从整体上精炼的总结论文内容，如果论文作者或者团队较为知名，也需把此信息增加到此段落内
- 精炼总结此论文要解决的问题是什么，即论文的研究背景
- 精炼总结此论文解决问题的方法，即论文的研究方法
- 精炼总结此论文方法所带来的效果，即实验数据和结果分析
- 对于论文中的一些特有英文单词，你需要保持原样不要翻译成中文
  - transformer

# 专有名词
- object detection：目标检测
'''
client = Client(
    provider=args.provider, model=args.model,
    instruction=instruction, http_options={'timeout': None},
)

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

content = extract_pdf_text(args.pdf)
print(f'content size: {len(content)}')
message = '''
总结如下论文内容：
{content}
'''.format(content=content)

for chunk in client.chat(message, generation_options={'stream': True}):
    print(chunk, end='')
print('')
