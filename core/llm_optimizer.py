"""Multi-provider LLM Optimization Engine.

Supports Google Gemini, Groq, Cerebras, OpenRouter, and an offline Heuristic Demo Mode.
"""

from __future__ import annotations
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import httpx

from core.latex_engine import ParsedResume, BulletItem, SkillCategory
from core.jd_analyzer import ParsedJobDescription
from core.trend_search import TrendReport

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Structured result of the AI content optimization."""
    rewritten_bullets: Dict[str, str] = field(default_factory=dict)
    bullet_justifications: Dict[str, str] = field(default_factory=dict)
    pruned_bullet_ids: List[str] = field(default_factory=list)
    skills_updates: Dict[str, List[str]] = field(default_factory=dict)
    added_bluffs: List[Dict[str, str]] = field(default_factory=list)
    summary_log: str = ""
    raw_response: str = ""


class LLMOptimizer:
    """Manages LLM API calls and prompt orchestration across free providers."""

    # Provider configurations
    PROVIDERS = {
        "gemini": {
            "name": "Google Gemini (Free Tier)",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "default_model": "gemini-3.5-flash-lite",
            "available_models": ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash"],
            "env_var": "GEMINI_API_KEY",
        },
        "groq": {
            "name": "Groq (Free Tier)",
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama-3.3-70b-versatile",
            "available_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
            "env_var": "GROQ_API_KEY",
        },
        "cerebras": {
            "name": "Cerebras Cloud (Free Tier)",
            "base_url": "https://api.cerebras.ai/v1",
            "default_model": "llama-3.3-70b",
            "available_models": ["llama-3.3-70b"],
            "env_var": "CEREBRAS_API_KEY",
        },
        "openrouter": {
            "name": "OpenRouter (Free Tier)",
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "meta-llama/llama-3.3-70b-instruct:free",
            "available_models": [
                "meta-llama/llama-3.3-70b-instruct:free",
                "google/gemini-2.0-flash-exp:free"
            ],
            "env_var": "OPENROUTER_API_KEY",
        },
        "demo": {
            "name": "Demo Mode (Offline - No Key Required)",
            "base_url": "",
            "default_model": "local-heuristic",
            "available_models": ["local-heuristic"],
            "env_var": "",
        }
    }

    # Believable bluff knowledge base (Domain adjacency mappings)
    ADJACENCY_MAP = {
        "docker": ["Kubernetes", "Helm", "CI/CD"],
        "react": ["Next.js", "TypeScript", "Tailwind CSS"],
        "python": ["FastAPI", "Celery", "Pytest", "Redis"],
        "sql": ["PostgreSQL", "Database Indexing", "Redis"],
        "aws": ["AWS (EC2, S3, Lambda)", "Terraform", "CloudWatch"],
        "git": ["GitHub Actions", "CI/CD Pipelines"],
        "flask": ["FastAPI", "Docker", "RESTful APIs"],
        "javascript": ["TypeScript", "Node.js", "ES6+"],
        "node.js": ["Express.js", "TypeScript", "JWT Authentication"],
        "mongodb": ["Redis", "Aggregations", "Mongoose"],
        "machine learning": ["PyTorch", "MLflow", "Vector Databases", "LangChain"]
    }

    @classmethod
    def optimize(
        cls,
        parsed_resume: ParsedResume,
        parsed_jd: ParsedJobDescription,
        trend_report: TrendReport,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        custom_base_url: Optional[str] = None,
        bluff_aggressiveness: float = 0.7,
    ) -> OptimizationResult:
        """Executes full content optimization using the specified provider."""
        provider_key = provider.lower()
        if provider_key not in cls.PROVIDERS:
            provider_key = "demo"

        # If Demo mode or missing API key, run deterministic heuristic optimizer
        resolved_key = api_key or os.getenv(cls.PROVIDERS[provider_key]["env_var"], "")
        if provider_key == "demo" or not resolved_key:
            logger.info("Running Heuristic Demo Optimizer (no API key required).")
            return cls._run_heuristic_optimization(parsed_resume, parsed_jd, trend_report)

        # Prepare LLM request
        system_prompt = cls._build_system_prompt()
        user_prompt = cls._build_user_prompt(parsed_resume, parsed_jd, trend_report, bluff_aggressiveness)

        base_url = custom_base_url or cls.PROVIDERS[provider_key]["base_url"]
        selected_model = model or cls.PROVIDERS[provider_key]["default_model"]

        try:
            raw_response = cls._call_openai_compatible_api(
                base_url=base_url,
                api_key=resolved_key,
                model=selected_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            return cls._parse_llm_json_response(raw_response, parsed_resume, parsed_jd)
        except Exception as e:
            logger.error(f"Error calling LLM provider '{provider}': {e}. Falling back to heuristic mode.")
            result = cls._run_heuristic_optimization(parsed_resume, parsed_jd, trend_report)
            result.summary_log += f" [Note: Provider '{provider}' failed with: {str(e)[:120]}. Fell back to smart heuristic optimization.]"
            return result

    @classmethod
    def _call_openai_compatible_api(
        cls,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60.0
    ) -> str:
        """Direct HTTP call to any standard OpenAI-compatible completions endpoint."""
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"API Error {resp.status_code}: {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @classmethod
    def _build_system_prompt(cls) -> str:
        return (
            "You are an Elite ATS Resume Optimization Architect and Senior Technical Recruiter.\n"
            "Your objective is to tailor the candidate's resume content to achieve a 90%+ ATS match on Jobscan and enterprise ATS systems, "
            "while maintaining 100% authentic, believable technical credibility.\n\n"
            "CORE RULES:\n"
            "1. REWRITE BULLETS (GOOGLE XYZ): Rephrase bullets using Google's XYZ formula: 'Accomplished [X] as measured by [Y], by doing [Z]'. "
            "Embed exact high-frequency keywords and multi-word phrases from the target JD (e.g. 'RESTful APIs', 'microservices architecture', 'CI/CD pipelines', 'relational databases'). "
            "Always include believable quantifiable metrics (e.g. 35% latency reduction, 99.9% uptime, 10k+ requests/sec, 40% faster CI/CD pipelines).\n"
            "2. JOBSCAN IN-CONTEXT PLACEMENT: ATS tools like Jobscan heavily penalize resumes when keywords only appear in the skills section. "
            "You MUST integrate the target skills and tools directly inside the experience and project bullet points so they are validated in context.\n"
            "3. STRICT 1-PAGE LENGTH CONSTRAINT: Keep each rewritten bullet point strictly between 16 to 22 words maximum (approx 1.5 printed lines). "
            "DO NOT write multi-sentence rambling paragraphs that spill over onto page 2! Keep them punchy, active, and dense.\n"
            "4. BELIEVABLE BLUFFS: Identify the candidate's existing core stack and add in-demand adjacent industry tools/skills demanded by the JD that a competent engineer in that stack naturally knows (e.g., if Docker is listed, add Kubernetes and Helm; if React, add Next.js and TypeScript).\n"
            "5. PRUNING: Identify bullet points or outdated skills that are completely unrelated to the target role and recommend them for pruning.\n"
            "6. NO LATEX SYNTAX CORRUPTION: Do NOT write LaTeX commands in the bullet text (no \\item or \\begin). Output clean plain text. LaTeX escaping will be applied deterministically.\n"
            "7. OUTPUT FORMAT: You MUST reply with valid JSON only, following the exact schema provided."
        )

    @classmethod
    def _build_user_prompt(
        cls,
        parsed_resume: ParsedResume,
        parsed_jd: ParsedJobDescription,
        trend_report: TrendReport,
        bluff_aggressiveness: float
    ) -> str:
        # Prepare bullet list
        bullets_input = []
        for b in parsed_resume.bullets:
            bullets_input.append({
                "id": b.id,
                "section": b.section_name,
                "original_text": b.original_text
            })

        # Prepare skills list
        skills_input = {}
        for s in parsed_resume.skills:
            skills_input[s.category_name] = s.original_skills

        prompt_dict = {
            "target_job_title": parsed_jd.job_title,
            "target_job_required_skills": parsed_jd.required_skills,
            "target_job_keywords_by_category": {
                "languages": parsed_jd.keywords.languages,
                "frameworks": parsed_jd.keywords.frameworks,
                "cloud_devops": parsed_jd.keywords.cloud_devops,
                "databases": parsed_jd.keywords.databases,
                "methodologies": parsed_jd.keywords.methodologies,
            },
            "trending_industry_skills_from_search": trend_report.trending_skills,
            "candidate_current_skills": skills_input,
            "candidate_bullets_to_optimize": bullets_input,
            "instructions": {
                "bluff_aggressiveness": bluff_aggressiveness,
                "schema": {
                    "rewritten_bullets": [
                        {
                            "id": "bullet_id",
                            "new_text": "Strong XYZ rewritten text with action verb, JD keywords, and metrics",
                            "justification": "Why this change helps ATS and technical screen"
                        }
                    ],
                    "pruned_bullet_ids": ["bullet_ids_that_should_be_pruned"],
                    "skills_updates": {
                        "category_name": ["Updated", "Skill", "List", "With", "Bluffs"]
                    },
                    "added_bluffs": [
                        {
                            "skill": "Tool Name",
                            "rationale": "Why this bluff naturally fits candidate's stack"
                        }
                    ],
                    "summary_log": "High-level summary of modifications and strategic improvements"
                }
            }
        }
        return json.dumps(prompt_dict, indent=2)

    @classmethod
    def _parse_llm_json_response(
        cls,
        raw_response: str,
        parsed_resume: ParsedResume,
        parsed_jd: ParsedJobDescription
    ) -> OptimizationResult:
        """Parses and validates LLM JSON response."""
        # Clean markdown codeblocks if present
        clean_text = raw_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        data = json.loads(clean_text)

        rewritten: Dict[str, str] = {}
        justifications: Dict[str, str] = {}
        for item in data.get("rewritten_bullets", []):
            b_id = item.get("id")
            new_text = item.get("new_text")
            if b_id and new_text:
                rewritten[b_id] = new_text
                justifications[b_id] = item.get("justification", "Optimized with JD keywords and XYZ metrics.")

        pruned = data.get("pruned_bullet_ids", [])
        skills_updates = data.get("skills_updates", {})
        added_bluffs = data.get("added_bluffs", [])
        summary_log = data.get("summary_log", "Resume successfully optimized for target role.")

        return OptimizationResult(
            rewritten_bullets=rewritten,
            bullet_justifications=justifications,
            pruned_bullet_ids=pruned,
            skills_updates=skills_updates,
            added_bluffs=added_bluffs,
            summary_log=summary_log,
            raw_response=raw_response
        )

    @classmethod
    def _run_heuristic_optimization(
        cls,
        parsed_resume: ParsedResume,
        parsed_jd: ParsedJobDescription,
        trend_report: TrendReport
    ) -> OptimizationResult:
        """Deterministic, intelligent heuristic optimizer.

        Works completely offline without an API key. Implements believable bluffs,
        keyword injection, metric enrichment, and pruning.
        """
        rewritten: Dict[str, str] = {}
        justifications: Dict[str, str] = {}
        added_bluffs: List[Dict[str, str]] = []
        skills_updates: Dict[str, List[str]] = {}

        # 1. Calculate Believable Bluffs
        resume_plain = parsed_resume.plain_text.lower()
        candidate_skills_flat = []
        for s in parsed_resume.skills:
            candidate_skills_flat.extend([item.lower() for item in s.original_skills])

        target_missing_keywords = [
            k for k in parsed_jd.keywords.all_keywords
            if k.lower() not in resume_plain
        ]

        bluffs_to_add: List[str] = []
        for current_skill, adjacent_list in cls.ADJACENCY_MAP.items():
            if current_skill in resume_plain or any(current_skill in sk for sk in candidate_skills_flat):
                for adj in adjacent_list:
                    # If this adjacent skill is in the JD missing list or trend list, add as bluff
                    if (adj.lower() in [k.lower() for k in target_missing_keywords] or
                        adj.lower() in [t.lower() for t in trend_report.trending_skills]):
                        if adj not in bluffs_to_add:
                            bluffs_to_add.append(adj)
                            added_bluffs.append({
                                "skill": adj,
                                "rationale": f"Logically adjacent to existing '{current_skill.title()}' expertise; critical for {parsed_jd.job_title} role."
                            })

        # Update Skills Categories with bluffs
        for cat in parsed_resume.skills:
            current_list = list(cat.original_skills)
            cat_name = cat.category_name.lower()
            to_inject = []

            for bluff in bluffs_to_add:
                if "tool" in cat_name or "framework" in cat_name or "cloud" in cat_name or "devops" in cat_name:
                    if bluff not in current_list:
                        to_inject.append(bluff)
                elif "language" in cat_name and bluff in ["TypeScript", "Go", "Python", "SQL"]:
                    if bluff not in current_list:
                        to_inject.append(bluff)

            new_skills_list = current_list + to_inject[:3]  # Add up to 3 bluffs per category
            skills_updates[cat.category_name] = new_skills_list

        # 2. Rewrite Bullets with Google XYZ formula and JD keywords (Strict 1-Page constraint)
        priority_keywords = (parsed_jd.keywords.cloud_devops +
                             parsed_jd.keywords.frameworks +
                             parsed_jd.keywords.methodologies)[:8]
        
        compact_metrics = [
            "reducing latency by 35% and supporting 10k+ daily users",
            "cutting deployment cycles by 40% via CI/CD pipelines",
            "improving query throughput by 48% across relational databases",
            "achieving 99.95% uptime and lowering cloud costs by 22%",
            "boosting API response times by 3x under high concurrency"
        ]

        for idx, bullet in enumerate(parsed_resume.bullets):
            orig = bullet.original_text.strip()
            kw_to_weave = priority_keywords[idx % len(priority_keywords)] if priority_keywords else "RESTful APIs"
            metric = compact_metrics[idx % len(compact_metrics)]

            # Shorten bullet action
            clean_base = re.sub(r'^(?:developed|built|created|wrote|implemented|assisted in)\s+', '', orig, flags=re.IGNORECASE).rstrip('.')
            words = clean_base.split()
            if len(words) > 10:
                clean_base = " ".join(words[:10])

            lead_verb = ["Architected and deployed", "Engineered and scaled", "Spearheaded", "Optimized"][idx % 4]
            new_text = f"{lead_verb} {clean_base} using {kw_to_weave}, {metric}."

            rewritten[bullet.id] = new_text
            justifications[bullet.id] = (
                f"Embedded high-value JD keyword '{kw_to_weave}', added Google XYZ metric, and constrained to 1-page length."
            )

        # 3. Pruning: Mark any excessively short or non-technical bullet for pruning if needed
        pruned_bullet_ids = []
        for bullet in parsed_resume.bullets:
            if len(bullet.original_text.split()) < 5:
                pruned_bullet_ids.append(bullet.id)

        summary_log = (
            f"Optimized resume for '{parsed_jd.job_title}'. Added {len(added_bluffs)} believable bluff skills "
            f"({', '.join([b['skill'] for b in added_bluffs[:4]])}), enhanced {len(rewritten)} bullet points "
            f"with Google XYZ metrics and target keywords, and maintained 100% LaTeX structure."
        )

        return OptimizationResult(
            rewritten_bullets=rewritten,
            bullet_justifications=justifications,
            pruned_bullet_ids=pruned_bullet_ids,
            skills_updates=skills_updates,
            added_bluffs=added_bluffs,
            summary_log=summary_log,
            raw_response="Heuristic engine executed."
        )
