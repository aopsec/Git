import tempfile
from pathlib import Path

from bbwebscan.wordlist_builder import build_supplement, extract_path_words


def test_extract_path_words_simple() -> None:
    """extract_path_words() extracts words from simple paths."""
    urls = [
        "https://example.com/api/users",
        "https://example.com/admin/dashboard",
    ]
    words = extract_path_words(urls)

    assert "api" in words
    assert "users" in words
    assert "admin" in words
    assert "dashboard" in words


def test_extract_path_words_with_delimiters() -> None:
    """extract_path_words() splits on /,-,_,."""
    urls = [
        "https://example.com/my-api/user_data",
        "https://example.com/config.json",
    ]
    words = extract_path_words(urls)

    # "my" is filtered (< 3 chars), "api" is kept from "my-api"
    assert "api" in words
    assert "user" in words
    assert "data" in words
    assert "config" in words


def test_extract_path_words_min_length() -> None:
    """extract_path_words() filters words < 3 chars."""
    urls = [
        "https://example.com/api/a/my/data",
    ]
    words = extract_path_words(urls)

    assert "api" in words
    assert "data" in words
    assert "my" not in words  # 2 chars, filtered
    assert "a" not in words   # 1 char, filtered


def test_extract_path_words_alpha_only() -> None:
    """extract_path_words() filters non-alpha characters."""
    urls = [
        "https://example.com/api123/test",
    ]
    words = extract_path_words(urls)

    assert "test" in words
    assert "api" not in words  # Contains numbers
    assert "api123" not in words


def test_extract_path_words_deduplicates() -> None:
    """extract_path_words() deduplicates extracted words."""
    urls = [
        "https://example.com/api/users",
        "https://example.com/api/posts",
    ]
    words = extract_path_words(urls)

    # api should appear only once in the list
    assert words.count("api") == 1


def test_extract_path_words_empty_urls() -> None:
    """extract_path_words() handles empty URL list."""
    words = extract_path_words([])
    assert words == []


def test_extract_path_words_invalid_urls() -> None:
    """extract_path_words() handles invalid/malformed URLs gracefully."""
    urls = [
        "not-a-url",
        "://missing-protocol",
        "https://example.com/api",
    ]
    words = extract_path_words(urls)

    # Should still extract from valid URL
    assert "api" in words


def test_build_supplement_creates_file() -> None:
    """build_supplement() writes merged wordlist to output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_file = Path(tmpdir) / "base.txt"
        output_file = Path(tmpdir) / "supplement.txt"

        # Create base wordlist
        base_file.write_text("existing\nwords\n")

        words = ["new", "extracted", "words"]
        result = build_supplement(words, base_file, output_file)

        assert output_file.exists()
        assert result == output_file

        content = output_file.read_text()
        assert "existing" in content
        assert "new" in content
        assert "extracted" in content


def test_build_supplement_deduplicates() -> None:
    """build_supplement() deduplicates between base and new words."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_file = Path(tmpdir) / "base.txt"
        output_file = Path(tmpdir) / "supplement.txt"

        # Create base with some words
        base_file.write_text("admin\napi\nusers\n")

        # Some words overlap
        words = ["api", "admin", "posts"]
        build_supplement(words, base_file, output_file)

        content = output_file.read_text()
        lines = [line for line in content.strip().split('\n') if line]

        # "admin" and "api" appear once (deduped), plus "posts" and "users"
        assert lines.count("admin") == 1
        assert lines.count("api") == 1
        assert "posts" in content
        assert "users" in content


def test_build_supplement_sorts_output() -> None:
    """build_supplement() outputs words in sorted order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_file = Path(tmpdir) / "base.txt"
        output_file = Path(tmpdir) / "supplement.txt"

        base_file.write_text("zebra\napple\n")
        words = ["monkey", "banana"]
        build_supplement(words, base_file, output_file)

        content = output_file.read_text()
        lines = [line for line in content.strip().split('\n') if line]

        # Should be sorted
        assert lines == sorted(lines)


def test_build_supplement_nonexistent_base() -> None:
    """build_supplement() handles nonexistent base wordlist gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_file = Path(tmpdir) / "nonexistent.txt"
        output_file = Path(tmpdir) / "supplement.txt"

        words = ["word1", "word2"]
        build_supplement(words, base_file, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "word1" in content
        assert "word2" in content
