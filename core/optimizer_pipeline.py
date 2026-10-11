"""Orchestrator Pipeline for the Free ATS LaTeX Resume Optimizer."""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable

from core.latex_engine import LatexEngine, ParsedResume
from core.jd_analyzer import JDAnalyzer, ParsedJobDescription
from core.trend_search import TrendSearchEngine, TrendReport
from core.ats_scorer import ATSScorer, ATSComparisonReport, ATSScoreBreakdown
from core.llm_optimizer import LLMOptimizer, OptimizationResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineProgress:
    """Carries progress messages for UI streaming."""
    step_num: int
    total_steps: int
    step_name: str
    message: str


@dataclass
class PipelineResult:
    """Comprehensive output bundle returned upon optimization pipeline completion."""
    original_latex: str
    optimized_latex: str
    is_latex_valid: bool
    latex_validation_errors: List[str]
    parsed_resume: ParsedResume
    parsed_jd: ParsedJobDescription
    trend_report: TrendReport
    optimization_result: OptimizationResult
    ats_report: ATSComparisonReport
    target_job_title: str = ""


class OptimizerPipeline:
    """End-to-End Orchestrator for the ATS Resume Optimization Pipeline."""

    @classmethod
    def run(
        cls,
        raw_latex: str,
        raw_jd: str,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        bluff_aggressiveness: float = 0.7,
        target_job_title: Optional[str] = None,
        align_job_title: bool = True,
        enforce_one_page: bool = True,
        progress_callback: Optional[Callable[[PipelineProgress], None]] = None
    ) -> PipelineResult:
        """Executes the entire optimization sequence."""

        def report(step: int, name: str, msg: str):
            if progress_callback:
                progress_callback(PipelineProgress(step, 6, name, msg))

        # 1. Parse LaTeX Resume
        report(1, "Parsing LaTeX", "Extracting sections, bullets, and technical skills...")
        parsed_resume = LatexEngine.parse_latex(raw_latex)

        # 2. Parse Job Description
        report(2, "Analyzing Job Description", "Extracting target keywords, frameworks, and requirements...")
        parsed_jd = JDAnalyzer.analyze_jd(raw_jd)
        effective_title = (target_job_title or parsed_jd.job_title).strip()

        # 3. DuckDuckGo Industry Trend Search
        report(3, "Trend Intelligence", f"Querying live DuckDuckGo skill trends for '{effective_title}'...")
        trend_report = TrendSearchEngine.search_role_trends(effective_title)

        # 4. Content Optimization (AI Engine)
        report(4, "AI Content Optimization", f"Synthesizing believable bluffs, XYZ metrics, and pruning with {provider.title()}...")
        opt_result = LLMOptimizer.optimize(
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            trend_report=trend_report,
            provider=provider,
            api_key=api_key,
            model=model,
            bluff_aggressiveness=bluff_aggressiveness
        )

        # 5. LaTeX Reconstruction & Escaping
        report(5, "Reconstructing LaTeX", "Deterministically patching LaTeX template, aligning title, and escaping characters...")
        optimized_latex = LatexEngine.reconstruct_latex(
            parsed=parsed_resume,
            rewritten_bullets=opt_result.rewritten_bullets,
            skills_updates=opt_result.skills_updates,
            pruned_bullet_ids=opt_result.pruned_bullet_ids,
            target_job_title=effective_title if align_job_title else None,
            align_job_title=align_job_title,
            enforce_one_page=enforce_one_page
        )

        # Validate Syntax
        is_valid, validation_errors = LatexEngine.validate_latex(optimized_latex)

        # 6. ATS & Jobscan Scoring & Comparison
        report(6, "Calculating ATS & Jobscan Scores", "Comparing keyword density, title match, and in-context placement...")
        optimized_plain = LatexEngine.strip_latex_to_plain_text(optimized_latex)
        
        # Collect bullet texts for in-context analysis
        orig_bullet_text = " ".join([b.original_text for b in parsed_resume.bullets])
        opt_bullet_text = " ".join([opt_result.rewritten_bullets.get(b.id, b.original_text) for b in parsed_resume.bullets])

        ats_report = ATSScorer.compare(
            before_text=parsed_resume.plain_text,
            after_text=optimized_plain,
            parsed_jd=parsed_jd,
            before_bullets=orig_bullet_text,
            after_bullets=opt_bullet_text
        )

        return PipelineResult(
            original_latex=raw_latex,
            optimized_latex=optimized_latex,
            is_latex_valid=is_valid,
            latex_validation_errors=validation_errors,
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            trend_report=trend_report,
            optimization_result=opt_result,
            ats_report=ats_report,
            target_job_title=effective_title
        )
