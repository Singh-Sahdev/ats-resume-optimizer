"""Unit tests for LaTeX parsing, escaping, validation, reconstruction, and ATS scoring."""

import os
import unittest
from core.latex_engine import LatexEngine, ParsedResume
from core.jd_analyzer import JDAnalyzer
from core.trend_search import TrendSearchEngine
from core.ats_scorer import ATSScorer
from core.optimizer_pipeline import OptimizerPipeline


class TestLatexEngine(unittest.TestCase):
    """Test suite for the core LaTeX Engine and ATS pipeline."""

    @classmethod
    def setUpClass(cls):
        sample_path = os.path.join(
            os.path.dirname(__file__), "..", "sample_data", "sample_resume.tex"
        )
        with open(sample_path, "r", encoding="utf-8") as f:
            cls.sample_latex = f.read()

        jd_path = os.path.join(
            os.path.dirname(__file__), "..", "sample_data", "sample_jd.txt"
        )
        with open(jd_path, "r", encoding="utf-8") as f:
            cls.sample_jd = f.read()

    def test_escape_latex(self):
        """Verifies special character escaping."""
        raw = "Boosted revenue by 25% & reduced latency by $50K under high_load #1"
        escaped = LatexEngine.escape_latex(raw)
        self.assertIn(r"25\%", escaped)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\$50K", escaped)
        self.assertIn(r"high\_load", escaped)
        self.assertIn(r"\#1", escaped)

        # Ensure no double escaping
        double_escaped = LatexEngine.escape_latex(escaped)
        self.assertEqual(escaped, double_escaped)

    def test_parse_latex(self):
        """Verifies parsing extracts sections, bullets, and skills."""
        parsed = LatexEngine.parse_latex(self.sample_latex)
        self.assertGreater(len(parsed.bullets), 0)
        self.assertGreater(len(parsed.skills), 0)
        self.assertIn("Education", parsed.sections_found)
        self.assertIn("Experience", parsed.sections_found)
        self.assertIn("Technical Skills", parsed.sections_found)
        self.assertIn("Python", parsed.plain_text)

    def test_validate_latex(self):
        """Verifies LaTeX syntax validation correctly catches issues."""
        # Valid sample should pass
        is_valid, errors = LatexEngine.validate_latex(self.sample_latex)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

        # Broken braces should fail
        broken_latex = self.sample_latex + "{"
        is_valid_broken, errors_broken = LatexEngine.validate_latex(broken_latex)
        self.assertFalse(is_valid_broken)
        self.assertTrue(any("curly braces" in e for e in errors_broken))

    def test_jd_analyzer(self):
        """Verifies JD analyzer extracts keywords and title."""
        parsed_jd = JDAnalyzer.analyze_jd(self.sample_jd)
        self.assertIn("Senior", parsed_jd.job_title)
        self.assertIn("Python", parsed_jd.keywords.languages)
        self.assertIn("Docker", parsed_jd.keywords.cloud_devops)
        self.assertIn("PostgreSQL", parsed_jd.keywords.databases)
        self.assertIn("Microservices", parsed_jd.keywords.methodologies)

    def test_ats_scorer_and_comparison(self):
        """Verifies ATS evaluation and comparison."""
        parsed_jd = JDAnalyzer.analyze_jd(self.sample_jd)
        before_text = "I developed web apps with Python and MySQL."
        after_text = "Architected scalable microservices with Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL, and Redis, reducing latency by 45%."
        
        report = ATSScorer.compare(before_text, after_text, parsed_jd)
        self.assertGreater(report.after.overall_score, report.before.overall_score)
        self.assertGreater(report.score_delta, 0)
        self.assertIn("Kubernetes", report.newly_matched_keywords)

    def test_full_pipeline_run_offline(self):
        """Tests the complete pipeline in offline demo mode."""
        result = OptimizerPipeline.run(
            raw_latex=self.sample_latex,
            raw_jd=self.sample_jd,
            provider="demo",
            align_job_title=True,
            enforce_one_page=True
        )
        self.assertTrue(result.is_latex_valid, f"Output LaTeX syntax error: {result.latex_validation_errors}")
        self.assertGreater(result.ats_report.after.overall_score, result.ats_report.before.overall_score)
        self.assertGreater(result.ats_report.after.jobscan_score, result.ats_report.before.jobscan_score)
        self.assertIn("Alex Morgan", result.optimized_latex)
        self.assertIn(r"\resumeItem", result.optimized_latex)
        self.assertGreater(len(result.optimization_result.added_bluffs), 0)

    def test_job_title_alignment(self):
        """Verifies target role title is aligned in the reconstructed LaTeX."""
        parsed = LatexEngine.parse_latex(self.sample_latex)
        reconstructed = LatexEngine.reconstruct_latex(
            parsed=parsed,
            rewritten_bullets={},
            skills_updates={},
            target_job_title="Senior Full Stack Software Engineer",
            align_job_title=True
        )
        self.assertIn("Senior Full Stack Software Engineer", reconstructed)

    def test_pdf_engine_import(self):
        """Verifies PDFEngine imports cleanly."""
        from core.pdf_engine import PDFEngine
        self.assertTrue(hasattr(PDFEngine, "extract_text_from_pdf"))
        self.assertTrue(hasattr(PDFEngine, "compile_latex_to_pdf"))


if __name__ == "__main__":
    unittest.main()
