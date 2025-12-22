import pytest
from app.services.text_splitter_service import text_splitter_service

def test_split_pdf_text():
    content = "This is a test content for PDF mode."
    result = text_splitter_service.split("pdf", content)
    assert "result" in result
    assert isinstance(result["result"], str)
    assert "This is a test content for PDF mode." in result["result"]

def test_split_table_text():
    content = "| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
    result = text_splitter_service.split("table", content)
    assert "result" in result
    assert isinstance(result["result"], str)
    assert "Header 1" in result["result"]

def test_split_image_text():
    content = "This is a test content for Image mode."
    url = "http://example.com/image.png"
    result = text_splitter_service.split("image", content, preview_url=url)
    assert "result" in result
    assert isinstance(result["result"], str)
    assert url in result["result"]

def test_invalid_mode():
    with pytest.raises(ValueError):
        text_splitter_service.split("invalid_mode", "content")

def test_image_mode_missing_url():
    with pytest.raises(ValueError):
        text_splitter_service.split("image", "content")
