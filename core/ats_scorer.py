"""ATS Scoring and Keyword Gap Analysis Engine."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from core.jd_analyzer import ParsedJobDescription


@dataclass
class ATSScoreBreakdown:
    """Detailed score breakdown across critical ATS evaluation dimensions."""
    overall_score: int  # 0 to 100
    jobscan_score: int  # Simulated Jobscan match score
    job_title_match_pct: int
    hard_skills_match_pct: int
    tools_cloud_match_pct: int
    methodology_match_pct: int
    experience_context_match_pct: int  # Keywords present inside experience/projects bullets
    impact_metrics_score: int
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    skills_only_keywords: List[str] = field(default_factory=list)  # In skills section but missing in bullets
    quantifiable_metrics_count: int = 0
    action_verbs_count: int = 0


@dataclass
class ATSComparisonReport:
    """Comprehensive comparison report showing Before vs After optimization results."""
    before: ATSScoreBreakdown
    after: ATSScoreBreakdown
    score_delta: int
    jobscan_delta: int
    newly_matched_keywords: List[str] = field(default_factory=list)
    remaining_gaps: List[str] = field(default_factory=list)


class ATSScorer:
    """Evaluates resume content against target Job Description to generate ATS score."""

    ACTION_VERBS = [
        "accelerated", "achieved", "architected", "automated", "built", "centralized",
        "configured", "delivered", "deployed", "designed", "developed", "engineered",
        "enhanced", "established", "executed", "generated", "implemented", "improved",
        "increased", "integrated", "launched", "led", "managed", "maximized", "migrated",
        "optimized", "orchestrated", "overhauled", "reduced", "refactored", "resolved",
        "scaled", "spearheaded", "standardized", "streamlined", "transformed", "upgraded"
    ]

    METRIC_PATTERN = re.compile(
        r'(?:\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?[kmbKMB]?|\d+(?:x|X)|\b\d{1,3}(?:,\d{3})+\b|\b\d+\s*(?:ms|sec|seconds|users|clients|nodes|servers|gb|tb|pb|queries|rps|tps|req/s)\b)',
        re.IGNORECASE
    )

    @classmethod
    def evaluate(
        cls,
        resume_plain_text: str,
        parsed_jd: ParsedJobDescription,
        experience_bullet_text: Optional[str] = None
    ) -> ATSScoreBreakdown:
        """Evaluates plain resume text against JD keywords and Jobscan formulas."""
        resume_lower = " " + resume_plain_text.lower() + " "
        exp_lower = " " + (experience_bullet_text or resume_plain_text).lower() + " "

        def match_list(keywords: List[str]) -> Tuple[List[str], List[str], List[str]]:
            matched = []
            missing = []
            skills_only = []
            for kw in keywords:
                pat = r'(?<![a-zA-Z0-9_\-\.])' + re.escape(kw.lower()) + r'(?![a-zA-Z0-9_\-\.])'
                in_resume = bool(re.search(pat, resume_lower))
                in_exp = bool(re.search(pat, exp_lower))
                if in_resume:
                    matched.append(kw)
                    if not in_exp:
                        skills_only.append(kw)
                else:
                    missing.append(kw)
            return matched, missing, skills_only

        # 1. Job Title Match (Crucial for Jobscan!)
        title_lower = parsed_jd.job_title.lower()
        title_words = [w for w in title_lower.split() if w not in ["senior", "lead", "junior", "staff", "principal", "ii", "iii", "the", "a", "an"]]
        title_matched_words = sum(1 for w in title_words if re.search(r'\b' + re.escape(w) + r'\b', resume_lower))
        title_match_pct = int((title_matched_words / len(title_words)) * 100) if title_words else 90

        # Category matches
        lang_fw = parsed_jd.keywords.languages + parsed_jd.keywords.frameworks
        tools_db = parsed_jd.keywords.cloud_devops + parsed_jd.keywords.databases
        methods = parsed_jd.keywords.methodologies

        m_lang, miss_lang, so_lang = match_list(lang_fw)
        m_tools, miss_tools, so_tools = match_list(tools_db)
        m_methods, miss_methods, so_methods = match_list(methods)

        # Percentages
        pct_lang = int((len(m_lang) / len(lang_fw) * 100)) if lang_fw else 80
        pct_tools = int((len(m_tools) / len(tools_db) * 100)) if tools_db else 75
        pct_methods = int((len(m_methods) / len(methods) * 100)) if methods else 75

        # In-context placement percentage (Skills in bullets vs skills only in list)
        total_matched = len(m_lang) + len(m_tools) + len(m_methods)
        skills_only_total = len(so_lang) + len(so_tools) + len(so_methods)
        in_context_total = total_matched - skills_only_total
        context_pct = int((in_context_total / max(1, total_matched)) * 100)

        # Metric detection
        metrics_found = len(cls.METRIC_PATTERN.findall(resume_plain_text))
        metric_score = min(100, int((metrics_found / 5) * 100))

        # Action verb detection
        action_verb_count = 0
        for v in cls.ACTION_VERBS:
            if re.search(r'\b' + re.escape(v) + r'\b', resume_lower):
                action_verb_count += 1
        verb_score = min(100, int((action_verb_count / 7) * 100))

        impact_score = int((metric_score * 0.6) + (verb_score * 0.4))

        # Jobscan-Simulated Score formula:
        # Jobscan heavily weighs:
        # 25% Job Title Match
        # 30% Hard Skills Match
        # 20% Context Placement (in work experience, not just skills section)
        # 15% Methodologies / Phrases
        # 10% Measurable Results & Formatting
        jobscan_sim = int(
            (title_match_pct * 0.25) +
            (pct_lang * 0.20) +
            (pct_tools * 0.15) +
            (context_pct * 0.20) +
            (pct_methods * 0.10) +
            (impact_score * 0.10)
        )
        jobscan_sim = max(15, min(98, jobscan_sim))

        # Overall composite score
        overall = int(
            (pct_lang * 0.30) +
            (pct_tools * 0.25) +
            (pct_methods * 0.20) +
            (impact_score * 0.15) +
            (title_match_pct * 0.10)
        )
        overall = max(15, min(99, overall))

        all_matched = sorted(list(set(m_lang + m_tools + m_methods)))
        all_missing = sorted(list(set(miss_lang + miss_tools + miss_methods)))
        all_skills_only = sorted(list(set(so_lang + so_tools + so_methods)))

        return ATSScoreBreakdown(
            overall_score=overall,
            jobscan_score=jobscan_sim,
            job_title_match_pct=title_match_pct,
            hard_skills_match_pct=pct_lang,
            tools_cloud_match_pct=pct_tools,
            methodology_match_pct=pct_methods,
            experience_context_match_pct=context_pct,
            impact_metrics_score=impact_score,
            matched_keywords=all_matched,
            missing_keywords=all_missing,
            skills_only_keywords=all_skills_only,
            quantifiable_metrics_count=metrics_found,
            action_verbs_count=action_verb_count
        )

    @classmethod
    def compare(
        cls,
        before_text: str,
        after_text: str,
        parsed_jd: ParsedJobDescription,
        before_bullets: Optional[str] = None,
        after_bullets: Optional[str] = None
    ) -> ATSComparisonReport:
        """Compares resume state before and after optimization."""
        before_eval = cls.evaluate(before_text, parsed_jd, before_bullets)
        after_eval = cls.evaluate(after_text, parsed_jd, after_bullets)

        before_set = set(k.lower() for k in before_eval.matched_keywords)
        newly_matched = [k for k in after_eval.matched_keywords if k.lower() not in before_set]

        return ATSComparisonReport(
            before=before_eval,
            after=after_eval,
            score_delta=after_eval.overall_score - before_eval.overall_score,
            jobscan_delta=after_eval.jobscan_score - before_eval.jobscan_score,
            newly_matched_keywords=newly_matched,
            remaining_gaps=after_eval.missing_keywords
        )
