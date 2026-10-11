"""DuckDuckGo Keyless Trend Search Module for Real-Time Role Skills & Tooling Trends."""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class TrendReport:
    """Contains trending industry skills and search insights for a target role."""
    job_title: str
    query_used: str
    trending_skills: List[str] = field(default_factory=list)
    top_snippets: List[str] = field(default_factory=list)


class TrendSearchEngine:
    """Performs zero-cost, keyless DuckDuckGo searches to find current industry skill trends."""

    # Fallback curated trending skills by general domain
    DOMAIN_TRENDS = {
        "full stack": ["Next.js 14", "TypeScript", "Tailwind CSS", "GraphQL", "Docker", "PostgreSQL", "CI/CD", "Redis", "REST APIs"],
        "frontend": ["React 19", "Next.js", "TypeScript", "Tailwind CSS", "State Management", "Vite", "Web Vitals", "Jest"],
        "backend": ["FastAPI", "Go", "Distributed Systems", "Kafka", "PostgreSQL", "Docker", "Kubernetes", "Redis", "gRPC"],
        "machine learning": ["PyTorch", "LLMs", "RAG", "LangChain", "Vector Databases", "MLflow", "Transformers", "CUDA", "FastAPI"],
        "data engineer": ["Apache Spark", "Airflow", "dbt", "Snowflake", "Kafka", "PostgreSQL", "Docker", "Databricks", "Data Modeling"],
        "devops": ["Kubernetes", "Terraform", "GitHub Actions", "Docker", "AWS", "Helm", "Prometheus", "Grafana", "ArgoCD"],
        "cloud": ["AWS", "Terraform", "Kubernetes", "Microservices", "Serverless", "Docker", "CI/CD", "IAM", "CloudWatch"],
    }

    @classmethod
    def search_role_trends(cls, job_title: str, max_results: int = 5) -> TrendReport:
        """Searches DuckDuckGo for top trending skills for the specified job title."""
        query = f"{job_title} top skills trending tools 2025 2026"
        snippets: List[str] = []
        trending_skills: List[str] = []

        try:
            # Try ddgs first
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            except ImportError:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))

            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                snippet = f"{title}: {body}"
                snippets.append(snippet)

            # Extract trending keywords from snippets
            trending_skills = cls._extract_keywords_from_snippets(snippets)

        except Exception as e:
            logger.warning(f"DuckDuckGo search encountered an error: {e}. Falling back to domain heuristics.")
            snippets.append(f"Live search fallback activated for role '{job_title}'.")

        # If search returned few keywords, supplement with curated domain trends
        if len(trending_skills) < 5:
            jt_lower = job_title.lower()
            for domain_key, skills in cls.DOMAIN_TRENDS.items():
                if domain_key in jt_lower:
                    for s in skills:
                        if s not in trending_skills:
                            trending_skills.append(s)
            
            # Default fallback if no match
            if not trending_skills:
                trending_skills = ["Docker", "Kubernetes", "CI/CD", "PostgreSQL", "Redis", "REST APIs", "Git", "System Design"]

        return TrendReport(
            job_title=job_title,
            query_used=query,
            trending_skills=trending_skills[:10],
            top_snippets=snippets[:3]
        )

    @classmethod
    def _extract_keywords_from_snippets(cls, snippets: List[str]) -> List[str]:
        """Extracts recognizable modern tech stack terms from search snippets."""
        text = " ".join(snippets).lower()
        candidates = [
            "docker", "kubernetes", "typescript", "react", "next.js", "fastapi", "golang", "go",
            "python", "aws", "gcp", "azure", "terraform", "graphql", "kafka", "redis", "postgresql",
            "ci/cd", "github actions", "microservices", "rag", "llm", "langchain", "pytorch",
            "tailwind css", "mongodb", "rest apis", "distributed systems", "airflow", "snowflake"
        ]
        found = []
        for c in candidates:
            if c in text:
                found.append(c.title() if c not in ["aws", "gcp", "ci/cd", "rag", "llm"] else c.upper())
        return found
