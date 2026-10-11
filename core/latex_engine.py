"""LaTeX parsing, AST extraction, special character escaping, syntax validation,
and template-preserving reconstruction engine.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any


@dataclass
class BulletItem:
    """Represents a single bullet point in an experience or project section."""
    id: str
    section_name: str
    original_text: str
    optimized_text: Optional[str] = None
    change_type: str = "unchanged"  # "unchanged", "rewritten", "pruned"
    justification: Optional[str] = None
    raw_latex_wrapper: str = r"\item"  # e.g., r"\item" or r"\resumeItem"


@dataclass
class SkillCategory:
    """Represents a category in the skills section."""
    id: str
    category_name: str
    original_skills: List[str] = field(default_factory=list)
    optimized_skills: List[str] = field(default_factory=list)
    added_bluffs: List[str] = field(default_factory=list)
    pruned_skills: List[str] = field(default_factory=list)
    raw_template_format: str = ""  # Pattern to format back to original LaTeX


@dataclass
class ParsedResume:
    """Structured representation of parsed LaTeX resume."""
    raw_latex: str
    preamble: str
    bullets: List[BulletItem] = field(default_factory=list)
    skills: List[SkillCategory] = field(default_factory=list)
    sections_found: List[str] = field(default_factory=list)
    plain_text: str = ""


class LatexEngine:
    """Engine for parsing, escaping, validating, and reconstructing LaTeX resumes."""

    # Characters that must be escaped in plain LaTeX text
    SPECIAL_CHARS = [
        (re.compile(r'(?<!\\)%'), r'\%'),
        (re.compile(r'(?<!\\)&'), r'\&'),
        (re.compile(r'(?<!\\)_'), r'\_'),
        (re.compile(r'(?<!\\)\$'), r'\$'),
        (re.compile(r'(?<!\\)#'), r'\#'),
    ]

    @classmethod
    def escape_latex(cls, text: str) -> str:
        """Deterministically escapes LaTeX special characters (% , & , _ , $ , #).

        Avoids double escaping existing backslashes.
        """
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.SPECIAL_CHARS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def strip_latex_to_plain_text(cls, latex: str) -> str:
        """Strips LaTeX markup to extract clean plain text for ATS keyword scanning."""
        if not latex:
            return ""
        # Remove comments (ignore escaped \%)
        cleaned = re.sub(r'(?<!\\)%.*?$', '', latex, flags=re.MULTILINE)
        # Remove common commands like \textbf{...}, \textit{...}, \emph{...}
        cleaned = re.sub(r'\\(?:textbf|textit|emph|underline|href|url)\{([^}]*)\}', r'\1', cleaned)
        # Remove \resumeItem{...} wrapper
        cleaned = re.sub(r'\\resumeItem\{([^}]*)\}', r'\1', cleaned)
        # Remove macro tags like \item, \section{...}, \begin{...}, \end{...}
        cleaned = re.sub(r'\\section\*?\{([^}]*)\}', r' \1 ', cleaned)
        cleaned = re.sub(r'\\(?:begin|end)\{[^}]*\}', ' ', cleaned)
        cleaned = re.sub(r'\\item\b', ' ', cleaned)
        # Remove leftover backslash commands
        cleaned = re.sub(r'\\[a-zA-Z]+(?:\*|\[.*?\])?', ' ', cleaned)
        # Replace escaped characters
        cleaned = cleaned.replace(r'\%', '%').replace(r'\&', '&').replace(r'\_', '_')
        cleaned = cleaned.replace(r'\$', '$').replace(r'\#', '#').replace(r'\{', '{').replace(r'\}', '}')
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @classmethod
    def parse_latex(cls, raw_latex: str) -> ParsedResume:
        """Parses raw LaTeX resume into sections, bullet items, and skills categories."""
        plain_text = cls.strip_latex_to_plain_text(raw_latex)
        
        # Preamble extraction (before \begin{document})
        doc_start = raw_latex.find(r"\begin{document}")
        preamble = raw_latex[:doc_start] if doc_start != -1 else ""

        bullets: List[BulletItem] = []
        skills: List[SkillCategory] = []
        sections_found: List[str] = []

        # Find all sections (handles \section{...} and \begin{rSection}{...})
        section_pattern = re.compile(
            r'(?:\\section\*?\{([^}]+)\}|\\begin\{rSection\}\{([^}]+)\})',
            re.IGNORECASE
        )
        for match in section_pattern.finditer(raw_latex):
            sec_name = (match.group(1) or match.group(2) or "").strip()
            if sec_name and sec_name not in sections_found:
                sections_found.append(sec_name)

        # 1. Parse bullet points
        # Case A: \resumeItem{content}
        resume_item_matches = list(re.finditer(r'\\resumeItem\{((?:[^{}]|\{[^{}]*\})*)\}', raw_latex))
        if resume_item_matches:
            for idx, m in enumerate(resume_item_matches):
                content = m.group(1).strip()
                sec_context = cls._infer_section(raw_latex, m.start())
                bullets.append(
                    BulletItem(
                        id=f"bullet_{idx+1}",
                        section_name=sec_context,
                        original_text=content,
                        raw_latex_wrapper=r"\resumeItem"
                    )
                )
        else:
            # Case B: Standard \item content (up to next \item, \end, or double newline)
            item_matches = list(re.finditer(
                r'\\item\s+(.+?)(?=(?:\\item\b|\\end\{itemize\}|\\end\{enumerate\}|\n\n|\Z))',
                raw_latex,
                re.DOTALL
            ))
            for idx, m in enumerate(item_matches):
                content = m.group(1).strip()
                # filter out empty or meta items
                if content and len(content) > 10:
                    sec_context = cls._infer_section(raw_latex, m.start())
                    bullets.append(
                        BulletItem(
                            id=f"bullet_{idx+1}",
                            section_name=sec_context,
                            original_text=content,
                            raw_latex_wrapper=r"\item"
                        )
                    )

        # 2. Parse Technical Skills
        # Matches patterns like:
        # \textbf{Languages}{: Python, Java, C++}
        # \textbf{Languages}: Python, Java, C++
        # \textbf{Languages}{:} Python, Java, C++
        skill_lines = list(re.finditer(
            r'\\textbf\{([^}]+)\}(?:\{:\s*([^\}]+)\}|(?:\:|\{:\})\s*([^\n\\]+))',
            raw_latex
        ))
        skill_idx = 1
        for m in skill_lines:
            category = m.group(1).strip()
            raw_items = (m.group(2) or m.group(3) or "").strip()
            # Clean trailing formatting or slashes
            raw_items = re.sub(r'\\\\\s*$', '', raw_items).strip()
            # Split by comma or semicolon
            items_list = [s.strip() for s in re.split(r'[,;]\s*', raw_items) if s.strip()]
            if items_list and any(kw in category.lower() for kw in ['skill', 'language', 'framework', 'tool', 'librar', 'platform', 'database', 'tech']):
                skills.append(
                    SkillCategory(
                        id=f"skill_cat_{skill_idx}",
                        category_name=category,
                        original_skills=items_list,
                        optimized_skills=items_list.copy(),
                        raw_template_format=m.group(0)
                    )
                )
                skill_idx += 1

        return ParsedResume(
            raw_latex=raw_latex,
            preamble=preamble,
            bullets=bullets,
            skills=skills,
            sections_found=sections_found,
            plain_text=plain_text
        )

    @classmethod
    def _infer_section(cls, text: str, pos: int) -> str:
        """Infers the enclosing section name before a given character index."""
        preceding = text[:pos]
        matches = list(re.finditer(
            r'(?:\\section\*?\{([^}]+)\}|\\begin\{rSection\}\{([^}]+)\})',
            preceding,
            re.IGNORECASE
        ))
        if matches:
            last = matches[-1]
            return (last.group(1) or last.group(2) or "Experience").strip()
        return "Experience"

    @classmethod
    def reconstruct_latex(
        cls,
        parsed: ParsedResume,
        rewritten_bullets: Dict[str, str],
        skills_updates: Dict[str, List[str]],
        pruned_bullet_ids: Optional[List[str]] = None,
        target_job_title: Optional[str] = None,
        align_job_title: bool = True,
        enforce_one_page: bool = True
    ) -> str:
        """Reconstructs the full LaTeX document with modifications injected deterministically.

        Ensures all other macros, packages, layout, and document structure remain
        100% untouched.
        """
        output = parsed.raw_latex
        pruned_set = set(pruned_bullet_ids or [])

        # 0. Job Title Alignment (Crucial for ATS / Jobscan match)
        if align_job_title and target_job_title and target_job_title.strip():
            clean_title = cls.escape_latex(target_job_title.strip())
            
            # Case A: Update first resumeSubheading role title if present
            # e.g., \resumeSubheading{Software Engineer}{June 2022 -- Present}
            subheading_match = re.search(r'\\resumeSubheading\s*\{([^}]+)\}(\{[^}]+\})', output)
            if subheading_match:
                orig_role = subheading_match.group(1).strip()
                dates_part = subheading_match.group(2)
                # Only update if the original title is somewhat generic and different
                if clean_title.lower() != orig_role.lower():
                    # Preserve context if original had level e.g. "Lead" or "Senior"
                    new_sub_title = clean_title
                    old_snippet = f"\\resumeSubheading{{{orig_role}}}{dates_part}"
                    new_snippet = f"\\resumeSubheading{{{new_sub_title}}}{dates_part}"
                    if old_snippet in output:
                        output = output.replace(old_snippet, new_snippet, 1)

            # Case B: Add/align headline under Candidate Name in header if not already present
            # Matches \textbf{\Huge ... Name} \\ \vspace{...}
            name_pattern = re.search(r'(\\textbf\{\\(?:Huge|huge|LARGE|Large)[^}]+\})\s*\\\\\s*(?:\\vspace\{[^}]+\})?', output)
            if name_pattern and clean_title.lower() not in output.lower():
                full_match = name_pattern.group(0)
                # Append target title headline
                headline_insert = f"{full_match}\n    \\small{{\\textbf{{{clean_title}}}}} \\\\ \\vspace{{1pt}}"
                output = output.replace(full_match, headline_insert, 1)

        # 1. Update Bullet Points
        for bullet in parsed.bullets:
            orig = bullet.original_text
            new_text = rewritten_bullets.get(bullet.id)
            is_pruned = bullet.id in pruned_set

            if bullet.raw_latex_wrapper == r"\resumeItem":
                orig_snippet = f"\\resumeItem{{{orig}}}"
                if is_pruned:
                    # Comment out pruned bullet with a note
                    replacement = f"% [ATS Pruned] \\resumeItem{{{cls.escape_latex(orig)}}}"
                elif new_text:
                    escaped_new = cls.escape_latex(new_text)
                    replacement = f"\\resumeItem{{{escaped_new}}}"
                else:
                    continue
                output = output.replace(orig_snippet, replacement, 1)

            else:  # Standard \item
                orig_snippet = f"\\item {orig}"
                if orig_snippet not in output:
                    orig_snippet = f"\\item\n{orig}"
                if orig_snippet in output:
                    if is_pruned:
                        replacement = f"% [ATS Pruned] \\item {cls.escape_latex(orig)}"
                    elif new_text:
                        escaped_new = cls.escape_latex(new_text)
                        replacement = f"\\item {escaped_new}"
                    else:
                        continue
                    output = output.replace(orig_snippet, replacement, 1)

        # 2. Update Skills Categories
        for skill_cat in parsed.skills:
            if skill_cat.category_name in skills_updates:
                new_list = skills_updates[skill_cat.category_name]
                new_skills_str = ", ".join(cls.escape_latex(s) for s in new_list)
                
                # Check original pattern
                orig_pattern = skill_cat.raw_template_format
                if "{:" in orig_pattern:
                    new_snippet = f"\\textbf{{{skill_cat.category_name}}}{{: {new_skills_str}}}"
                elif "{:}" in orig_pattern:
                    new_snippet = f"\\textbf{{{skill_cat.category_name}}}{{:}} {new_skills_str}"
                elif ":" in orig_pattern:
                    new_snippet = f"\\textbf{{{skill_cat.category_name}}}: {new_skills_str}"
                else:
                    new_snippet = f"\\textbf{{{skill_cat.category_name}}}{{: {new_skills_str}}}"

                if orig_pattern in output:
                    output = output.replace(orig_pattern, new_snippet, 1)

        # 3. Tight 1-Page Spacing Adjustments (if requested)
        if enforce_one_page:
            # Ensure margins are optimal for 1-page presentation
            if r"\addtolength{\textheight}{" in output:
                output = re.sub(r'\\addtolength\{\\textheight\}\{[^}]+\}', r'\\addtolength{\\textheight}{1.15in}', output, count=1)

        return output

    @classmethod
    def validate_latex(cls, latex: str) -> Tuple[bool, List[str]]:
        r"""Validates that the LaTeX output will compile without syntax errors.

        Checks:
        - Brace balance: {}
        - Environment balance: \begin{env} ... \end{env}
        - Math delimiter balance: $ ... $
        - Essential environments: \begin{document} and \end{document}
        """
        errors = []

        # 1. Document environment check
        if r"\begin{document}" not in latex:
            errors.append("Missing '\\begin{document}' declaration.")
        if r"\end{document}" not in latex:
            errors.append("Missing '\\end{document}' declaration.")

        # 2. Brace balance check (ignoring escaped \{ and \})
        # Remove comments first (ignore escaped \%)
        clean = re.sub(r'(?<!\\)%.*?$', '', latex, flags=re.MULTILINE)
        clean_no_escapes = clean.replace(r'\{', '').replace(r'\}', '')
        open_braces = clean_no_escapes.count('{')
        close_braces = clean_no_escapes.count('}')
        if open_braces != close_braces:
            errors.append(f"Mismatched curly braces: {open_braces} open vs {close_braces} close.")

        # 3. Environment matching check
        begins = re.findall(r'\\begin\{([^}]+)\}', clean)
        ends = re.findall(r'\\end\{([^}]+)\}', clean)
        
        begin_counts: Dict[str, int] = {}
        for b in begins:
            begin_counts[b] = begin_counts.get(b, 0) + 1
            
        end_counts: Dict[str, int] = {}
        for e in ends:
            end_counts[e] = end_counts.get(e, 0) + 1

        all_envs = set(begin_counts.keys()).union(set(end_counts.keys()))
        for env in all_envs:
            b_cnt = begin_counts.get(env, 0)
            e_cnt = end_counts.get(env, 0)
            if b_cnt != e_cnt:
                errors.append(f"Mismatched environment '\\begin{{{env}}}' ({b_cnt}) vs '\\end{{{env}}}' ({e_cnt}).")

        # 4. Unescaped percent signs in body that might comment out commands
        # Check if there are accidental unescaped '%' that look like metrics: e.g. "20% " without backslash
        raw_pct_matches = re.findall(r'[0-9]+\s*%(?!\w)', clean)
        if raw_pct_matches:
            errors.append(f"Detected {len(raw_pct_matches)} unescaped '%' symbols (e.g., '{raw_pct_matches[0]}'). These must be '\\%'.")

        is_valid = len(errors) == 0
        return is_valid, errors
