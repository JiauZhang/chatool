import os
from itertools import islice
from chatchat.tool import tool


@tool(
    name='write_file',
    description='Write text content to a file. Creates parent directories automatically. Overwrites existing file.',
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file, e.g. './output.txt' or '/home/user/data.log'"
            },
            "content": {
                "type": "string",
                "description": "Text content to write to the file"
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
        return f"File written: {file_path} ({len(content)} chars)"
    except Exception as e:
        return f"Error writing file: {e}"


@tool(
    name='read_file',
    description='Read file content from disk. Supports line range with offset and limit for large files.',
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding (default: utf-8)"
            },
            "offset": {
                "type": "integer",
                "description": "Starting line number (0-indexed, default: 0)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read (omit to read entire file)"
            }
        },
        "required": ["file_path"],
    },
)
def read_file(file_path, encoding='utf-8', offset=0, limit=None):
    try:
        if not os.path.exists(file_path):
            return f"Error: file not found: {file_path}"
        if not os.path.isfile(file_path):
            return f"Error: not a file: {file_path}"

        with open(file_path, 'r', encoding=encoding) as f:
            stop = None if limit is None else offset + limit
            content = ''.join(islice(f, offset, stop))

        return content
    except Exception as e:
        return f"Error reading file: {e}"
