from datetime import datetime, timezone
from pathlib import Path

from docx import Document

from messari_tg_bot.src.docx_renderer import ContentPayload, DocxRenderer


def test_docx_renderer_writes_file(tmp_path: Path) -> None:
    renderer = DocxRenderer(output_dir=tmp_path)
    payload = ContentPayload(
        item_id="id-1",
        slug="slug-1",
        title="Sample Title",
        url="https://example.com",
        publish_date=datetime.now(timezone.utc),
        item_type="research",
        translated_content="Первый абзац\nВторой абзац",
    )

    output_path = renderer.render(payload)
    assert output_path.exists()

    doc = Document(output_path)
    assert any("Sample Title" in para.text for para in doc.paragraphs)
