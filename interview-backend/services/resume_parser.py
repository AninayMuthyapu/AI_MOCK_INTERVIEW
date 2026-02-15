"""Resume text extraction service."""
from PyPDF2 import PdfReader
import docx


class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(file_path):
        text = ""
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text

    @staticmethod
    def extract_text_from_docx(file_path):
        doc = docx.Document(file_path)
        text = [paragraph.text for paragraph in doc.paragraphs]
        return "\n".join(text)
