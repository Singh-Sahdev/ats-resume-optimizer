"""Job Description Parser & Keyword Extraction Engine."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set


@dataclass
class JobKeywords:
    """Categorized keywords extracted from a Job Description."""
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    cloud_devops: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    methodologies: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    other_keywords: List[str] = field(default_factory=list)

    @property
    def all_keywords(self) -> List[str]:
        """Returns flattened list of all unique keywords."""
        combined = (
            self.languages
            + self.frameworks
            + self.cloud_devops
            + self.databases
            + self.methodologies
            + self.soft_skills
            + self.other_keywords
        )
        seen = set()
        res = []
        for k in combined:
            k_clean = k.strip()
            if k_clean and k_clean.lower() not in seen:
                seen.add(k_clean.lower())
                res.append(k_clean)
        return res


@dataclass
class ParsedJobDescription:
    """Structured representation of target job description."""
    raw_text: str
    job_title: str
    company_name: str
    keywords: JobKeywords
    keyword_frequencies: Dict[str, int] = field(default_factory=dict)
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)


class JDAnalyzer:
    """Analyzer for Job Descriptions to extract titles, skills, and ATS keywords."""

    # Comprehensive dictionaries of industry keywords
    KNOWN_LANGUAGES = [
        "python", "javascript", "typescript", "golang", "go", "java", "c++", "c#", "c",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "bash", "shell",
        "html", "css", "dart", "perl", "elixir", "matlab"
    ]

    KNOWN_FRAMEWORKS = [
        "react", "react.js", "next.js", "vue", "vue.js", "angular", "node.js", "nodejs",
        "express", "express.js", "fastapi", "flask", "django", "spring", "spring boot",
        "nest.js", "nestjs", "pytorch", "tensorflow", "keras", "scikit-learn", "pandas",
        "numpy", "graphql", "tailwind", "tailwind css", "bootstrap", "asp.net", ".net core"
    ]

    KNOWN_CLOUD_DEVOPS = [
        "aws", "amazon web services", "gcp", "google cloud", "azure", "docker", "kubernetes",
        "k8s", "terraform", "ansible", "helm", "ci/cd", "github actions", "gitlab ci",
        "jenkins", "prometheus", "grafana", "datadog", "argocd", "linux", "cloudformation",
        "nginx", "serverless", "lambda"
    ]

    KNOWN_DATABASES = [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
        "rabbitmq", "cassandra", "dynamodb", "sqlite", "snowflake", "bigquery", "clickhouse",
        "neo4j", "supabase", "firebase"
    ]

    KNOWN_METHODOLOGIES = [
        "microservices", "microservices architecture", "rest api", "restful api", "restful apis",
        "rest apis", "distributed systems", "system design", "agile", "scrum", "kanban",
        "test-driven development", "tdd", "event-driven", "event-driven architecture",
        "object-oriented programming", "oop", "clean architecture", "domain-driven design", "ddd",
        "design patterns", "etl", "data pipelines", "unit testing", "integration testing",
        "high availability", "code reviews", "cloud infrastructure", "relational databases"
    ]

    KNOWN_SOFT_SKILLS = [
        "mentorship", "cross-functional", "cross-functional collaboration", "leadership",
        "collaboration", "communication", "problem solving", "critical thinking", "ownership",
        "adaptability", "team player", "stakeholder management", "project management"
    ]

    # Critical multi-word phrases that ATS & Jobscan heavily weight
    HIGH_IMPACT_PHRASES = [
        "RESTful APIs", "Microservices Architecture", "Distributed Systems", "CI/CD Pipelines",
        "Relational Databases", "Unit Testing", "High Availability", "Code Reviews",
        "System Design", "Cloud Infrastructure", "Agile Workflows", "Cross-Functional Collaboration",
        "Event-Driven Architecture", "Database Optimization", "Data Pipelines"
    ]

    @classmethod
    def extract_job_title(cls, text: str) -> str:
        """Extracts target job title from JD text."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "Software Engineer"
        
        # Check first 5 lines for common title patterns
        title_patterns = [
            r'^(?:Job Title|Role|Position|Title)\s*[:\-]\s*(.+)$',
            r'^(.+?(?:Engineer|Developer|Architect|Scientist|Specialist|Manager|Lead|DevOps|Analyst|Consultant).*)$'
        ]
        
        for line in lines[:5]:
            for pat in title_patterns:
                m = re.match(pat, line, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    if 3 < len(candidate) < 60:
                        return candidate

        return lines[0][:50] if len(lines[0]) < 60 else "Software Engineer"

    @classmethod
    def analyze_jd(cls, raw_jd: str) -> ParsedJobDescription:
        """Parses JD into categorized keywords and frequency distribution."""
        job_title = cls.extract_job_title(raw_jd)
        jd_lower = " " + raw_jd.lower() + " "
        
        # Word frequency map
        freq_map: Dict[str, int] = {}

        def find_matches(keyword_list: List[str]) -> List[str]:
            found = []
            for kw in keyword_list:
                # Use regex word boundaries
                pattern = r'(?<![a-zA-Z0-9_\-\.])' + re.escape(kw) + r'(?![a-zA-Z0-9_\-\.])'
                matches = list(re.finditer(pattern, jd_lower))
                if matches:
                    count = len(matches)
                    proper_name = cls._format_name(kw)
                    found.append(proper_name)
                    freq_map[proper_name] = count
            return found

        languages = find_matches(cls.KNOWN_LANGUAGES)
        frameworks = find_matches(cls.KNOWN_FRAMEWORKS)
        cloud_devops = find_matches(cls.KNOWN_CLOUD_DEVOPS)
        databases = find_matches(cls.KNOWN_DATABASES)
        methodologies = find_matches(cls.KNOWN_METHODOLOGIES)
        soft_skills = find_matches(cls.KNOWN_SOFT_SKILLS)

        # Multi-word high impact phrase detection
        for phrase in cls.HIGH_IMPACT_PHRASES:
            pat = r'(?<![a-zA-Z0-9_\-\.])' + re.escape(phrase.lower()) + r'(?![a-zA-Z0-9_\-\.])'
            matches = list(re.finditer(pat, jd_lower))
            if matches and phrase not in methodologies:
                methodologies.append(phrase)
                freq_map[phrase] = len(matches)

        # Extract capitalized acronyms / tools (e.g., CI/CD, SDK, ETL, ML, AI, LLM)
        acronyms = set(re.findall(r'\b[A-Z]{2,6}\b', raw_jd))
        known_acronyms = {"API", "REST", "SDK", "ETL", "CI", "CD", "LLM", "NLP", "ML", "AI", "SaaS", "PaaS", "AWS", "GCP"}
        valid_acronyms = [a for a in acronyms if a in known_acronyms and a not in languages and a not in cloud_devops]

        keywords = JobKeywords(
            languages=languages,
            frameworks=frameworks,
            cloud_devops=cloud_devops,
            databases=databases,
            methodologies=methodologies,
            soft_skills=soft_skills,
            other_keywords=valid_acronyms
        )

        return ParsedJobDescription(
            raw_text=raw_jd,
            job_title=job_title,
            company_name="Target Company",
            keywords=keywords,
            keyword_frequencies=freq_map,
            required_skills=keywords.all_keywords[:15],
            preferred_skills=keywords.all_keywords[15:25]
        )

    @staticmethod
    def _format_name(name: str) -> str:
        """Capitalizes acronyms and proper names cleanly."""
        mapping = {
            "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
            "golang": "Go", "go": "Go", "java": "Java", "c++": "C++", "c#": "C#", "c": "C",
            "rust": "Rust", "ruby": "Ruby", "php": "PHP", "swift": "Swift", "kotlin": "Kotlin",
            "scala": "Scala", "sql": "SQL", "react": "React", "react.js": "React.js",
            "next.js": "Next.js", "vue": "Vue.js", "vue.js": "Vue.js", "angular": "Angular",
            "node.js": "Node.js", "nodejs": "Node.js", "fastapi": "FastAPI", "flask": "Flask",
            "django": "Django", "spring": "Spring", "spring boot": "Spring Boot",
            "pytorch": "PyTorch", "tensorflow": "TensorFlow", "scikit-learn": "Scikit-Learn",
            "aws": "AWS", "gcp": "GCP", "azure": "Azure", "docker": "Docker", "kubernetes": "Kubernetes",
            "k8s": "Kubernetes", "terraform": "Terraform", "ci/cd": "CI/CD", "github actions": "GitHub Actions",
            "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mongodb": "MongoDB", "redis": "Redis",
            "elasticsearch": "Elasticsearch", "kafka": "Kafka", "microservices": "Microservices",
            "rest api": "RESTful APIs", "restful apis": "RESTful APIs", "distributed systems": "Distributed Systems"
        }
        return mapping.get(name.lower(), name.title())
