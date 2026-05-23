from pathlib import Path
from chatool.tools.file import write_file, read_file


class TestWriteFile:
    def test_write_content(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        result = write_file(file_path=str(path), content="hello world")
        assert path.read_text() == "hello world"
        assert result == f"File written: {path} (11 chars)"

    def test_creates_parent_directories(self, tmp_path: Path):
        path = tmp_path / "a" / "b" / "test.txt"
        result = write_file(file_path=str(path), content="nested")
        assert path.read_text() == "nested"
        assert "Error" not in result

    def test_overwrites_existing_file(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("old content")
        write_file(file_path=str(path), content="new content")
        assert path.read_text() == "new content"

    def test_empty_content(self, tmp_path: Path):
        path = tmp_path / "empty.txt"
        result = write_file(file_path=str(path), content="")
        assert path.read_text() == ""
        assert result == f"File written: {path} (0 chars)"


class TestReadFile:
    def test_read_full_file(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("line 1\nline 2\nline 3\n")
        assert read_file(file_path=str(path)) == "line 1\nline 2\nline 3\n"

    def test_read_with_offset(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("a\nb\nc\nd\ne\n")
        assert read_file(file_path=str(path), offset=2) == "c\nd\ne\n"

    def test_read_with_limit(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("a\nb\nc\nd\ne\n")
        assert read_file(file_path=str(path), limit=3) == "a\nb\nc\n"

    def test_read_with_offset_and_limit(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("a\nb\nc\nd\ne\n")
        assert read_file(file_path=str(path), offset=1, limit=2) == "b\nc\n"

    def test_read_file_not_found(self):
        result = read_file(file_path="/tmp/_nonexistent_file_xyz.txt")
        assert "Error" in result

    def test_read_directory_instead_of_file(self, tmp_path: Path):
        result = read_file(file_path=str(tmp_path))
        assert "Error" in result

    def test_read_beyond_file(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("a\nb\nc\n")
        assert read_file(file_path=str(path), offset=10) == ""
