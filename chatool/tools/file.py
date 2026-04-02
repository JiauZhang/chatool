import os
from chatchat.tool import tool

@tool(
    name='write_file',
    description='将文本内容写入指定路径的文件（会覆盖已有文件）。',
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件的绝对或相对路径，例如 './output.txt' 或 '/home/user/data.log'"
            },
            "content": {
                "type": "string",
                "description": "要写入文件的文本内容"
            }
        },
        "required": ["file_path", "content"],
    },
)
def write_file(file_path, content):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"成功写入文件：{file_path} (共 {len(content)} 字符)"
    except Exception as e:
        return f"写入文件失败：{str(e)}"
