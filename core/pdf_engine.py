"""PDF Ingestion and Zero-Cost LaTeX-to-PDF Compilation Engine."""

from __future__ import annotations
import io
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
from typing import Optional, Tuple
import httpx
import pypdf

logger = logging.getLogger(__name__)


class PDFEngine:
    """Handles PDF text extraction and free zero-cost LaTeX-to-PDF compilation."""

    @classmethod
    def extract_text_from_pdf(cls, pdf_bytes: bytes) -> str:
        """Extracts plain text content from an uploaded PDF file."""
        if not pdf_bytes:
            return ""
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text_pages = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_pages.append(page_text.strip())
            return "\n\n".join(text_pages)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Could not read PDF file: {str(e)}")

    @classmethod
    def compile_latex_to_pdf(cls, latex_code: str, timeout_sec: float = 35.0) -> Tuple[Optional[bytes], Optional[str]]:
        """Compiles LaTeX code to PDF using zero-cost methods.

        Strategy:
        1. Check if local pdflatex or tectonic is installed on the host/container.
        2. If not local, use the free, open-source latexonline.cc compiler API.
        3. Returns (pdf_bytes, None) on success or (None, error_message) on failure.
        """
        if not latex_code or not latex_code.strip():
            return None, "LaTeX code is empty."

        # Strategy 1: Local pdflatex or tectonic compiler (if available)
        local_compiler = shutil.which("pdflatex") or shutil.which("tectonic")
        if local_compiler:
            try:
                pdf_bytes, err = cls._compile_locally(latex_code, local_compiler)
                if pdf_bytes:
                    return pdf_bytes, None
            except Exception as e:
                logger.warning(f"Local compiler failed: {e}. Falling back to online compiler.")

        # Strategy 2: Free Public latexonline.cc API via multipart POST
        try:
            # Package the LaTeX source into an in-memory tar.gz archive
            # This completely avoids the '414 Request-URI Too Large' error caused by GET queries
            tar_buf = io.BytesIO()
            with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
                data = latex_code.encode("utf-8")
                ti = tarfile.TarInfo(name="main.tex")
                ti.size = len(data)
                tar.addfile(ti, io.BytesIO(data))
            tar_bytes = tar_buf.getvalue()

            files = {"file": ("project.tar.gz", tar_bytes, "application/gzip")}
            url = "https://latexonline.cc/data?target=main.tex"
            
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(url, files=files)
                if resp.status_code == 200 and (
                    resp.headers.get("content-type", "").startswith("application/pdf")
                    or (len(resp.content) > 1000 and resp.content[:4] == b"%PDF")
                ):
                    return resp.content, None
                else:
                    err_msg = resp.text[:300] if resp.text else f"HTTP {resp.status_code}"
                    return None, f"Compiler service error: {err_msg}"
        except httpx.TimeoutException:
            return None, "PDF compilation timed out (public compiler was busy). You can still download the .tex file directly."
        except Exception as e:
            return None, f"Network error during PDF compilation: {str(e)}"

    @classmethod
    def _compile_locally(cls, latex_code: str, compiler_cmd: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Compiles LaTeX using local CLI compiler inside a temporary sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "resume.tex")
            pdf_file = os.path.join(tmpdir, "resume.pdf")

            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_code)

            cmd = [compiler_cmd, "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)

            if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
                with open(pdf_file, "rb") as pf:
                    return pf.read(), None
            return None, proc.stdout.decode("utf-8", errors="ignore")[:400]
