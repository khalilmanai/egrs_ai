import logging
from io import BytesIO
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


async def init_browser():
    pass


async def close_browser():
    pass


async def render_pdf(html_content: str, output_path: str):
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode("utf-8")), result)
    if pdf.err:
        raise RuntimeError(f"PDF generation failed: {pdf.err}")
    with open(output_path, "wb") as f:
        f.write(result.getvalue())
    logger.info("PDF generated: %s", output_path)
