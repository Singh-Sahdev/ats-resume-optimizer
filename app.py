"""Free ATS LaTeX Resume Optimizer - Web Application.

Zero-cost, open-source application to tailor LaTeX resumes against target JDs,
align job titles, add believable bluffs, rewrite bullets into Google XYZ impact metrics,
maximize Jobscan match rates, and output directly compilable LaTeX (.tex) and rendered PDF (.pdf).
"""

from __future__ import annotations
import base64
import os
import streamlit as st
from typing import Optional

from core.latex_engine import LatexEngine
from core.jd_analyzer import JDAnalyzer
from core.trend_search import TrendSearchEngine
from core.ats_scorer import ATSScorer
from core.llm_optimizer import LLMOptimizer
from core.optimizer_pipeline import OptimizerPipeline, PipelineResult, PipelineProgress
from core.pdf_engine import PDFEngine

# Page configuration
st.set_page_config(
    page_title="Free ATS LaTeX Resume Optimizer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .score-badge {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -1px;
    }
    .score-green { color: #10b981; }
    .score-blue { color: #3b82f6; }
    .score-amber { color: #f59e0b; }
    .score-purple { color: #a855f7; }
    .keyword-pill {
        display: inline-block;
        padding: 4px 10px;
        margin: 3px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 500;
    }
    .pill-green { background-color: #064e3b; color: #6ee7b7; border: 1px solid #047857; }
    .pill-blue { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #1d4ed8; }
    .pill-amber { background-color: #78350f; color: #fde68a; border: 1px solid #b45309; }
    .pill-purple { background-color: #581c87; color: #d8b4fe; border: 1px solid #7e22ce; }
    .pill-red { background-color: #7f1d1d; color: #fca5a5; border: 1px solid #b91c1c; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)


def load_sample_data():
    """Reads bundled sample resume and JD files."""
    base_dir = os.path.dirname(__file__)
    res_path = os.path.join(base_dir, "sample_data", "sample_resume.tex")
    jd_path = os.path.join(base_dir, "sample_data", "sample_jd.txt")
    
    sample_latex = ""
    sample_jd = ""
    if os.path.exists(res_path):
        with open(res_path, "r", encoding="utf-8") as f:
            sample_latex = f.read()
    if os.path.exists(jd_path):
        with open(jd_path, "r", encoding="utf-8") as f:
            sample_jd = f.read()
    return sample_latex, sample_jd


def main():
    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("📄 Free ATS LaTeX Resume Optimizer")
        st.caption("Maximize ATS & Jobscan match percentage, optimize job title, enforce 1-page fit, and output compilable LaTeX (.tex) & PDF (.pdf).")
    with col_h2:
        st.markdown("""
        <div style="text-align: right; padding-top: 10px;">
            <span style="background: #1e3a8a; color: #93c5fd; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem;">
                ⚡ 100% Free & Open Source
            </span>
        </div>
        """, unsafe_allow_html=True)

    # Sidebar: Provider & Model Settings
    with st.sidebar:
        st.header("⚙️ AI Engine Settings")
        
        provider_options = {
            "gemini": "Google Gemini (Free Tier)",
            "groq": "Groq (Free Tier)",
            "cerebras": "Cerebras Cloud (Free Tier)",
            "openrouter": "OpenRouter (Free Models)",
            "demo": "Demo Mode (Offline - No Key Required)"
        }
        
        selected_provider_key = st.selectbox(
            "Select Free AI Provider",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            index=0
        )
        
        provider_cfg = LLMOptimizer.PROVIDERS[selected_provider_key]
        
        # API Key input
        api_key = ""
        if selected_provider_key != "demo":
            env_val = os.getenv(provider_cfg.get("env_var", ""), "")
            
            help_links = {
                "gemini": "[Get Free Gemini API Key](https://aistudio.google.com/app/apikey)",
                "groq": "[Get Free Groq API Key](https://console.groq.com/keys)",
                "cerebras": "[Get Free Cerebras API Key](https://cloud.cerebras.ai)",
                "openrouter": "[Get Free OpenRouter Key](https://openrouter.ai/keys)"
            }
            st.markdown(help_links.get(selected_provider_key, ""))
            
            api_key = st.text_input(
                f"{provider_cfg['name']} Key",
                type="password",
                value=env_val,
                placeholder="Paste your free API key here...",
                help="Your API key stays entirely in your browser session memory and is never logged."
            )
            
            model_selected = st.selectbox(
                "Model",
                options=provider_cfg["available_models"],
                index=0
            )
        else:
            st.info("💡 Demo Mode runs locally using smart heuristic keyword analysis, believable bluffs, and metrics. Zero API key needed!")
            model_selected = "local-heuristic"

        st.divider()
        st.subheader("🎯 ATS & Layout Controls")
        
        align_title_toggle = st.toggle(
            "🎯 Align Job Title with Target Role",
            value=True,
            help="Crucial for Jobscan! Aligns your resume headline and primary role title to match the target job title."
        )

        enforce_one_page_toggle = st.toggle(
            "📏 Enforce 1-Page Tight Fit",
            value=True,
            help="Constrains bullet lengths (16-22 words max) and tightens margins so your resume fits cleanly on 1 page without 2nd page overflow."
        )

        bluff_aggressiveness = st.slider(
            "Believable Bluff Level",
            min_value=0.2,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Adds logically adjacent industry tools (e.g. Docker ➔ Kubernetes; React ➔ Next.js) without unbelievable fabrications."
        )
        
        enable_trend_search = st.toggle("DuckDuckGo Live Industry Trends", value=True, help="Queries DuckDuckGo (free, keyless) for current top skills.")

        st.divider()
        # 1-Click Sample Loader Button
        if st.button("📋 Load Sample Resume & JD", use_container_width=True):
            sample_latex, sample_jd = load_sample_data()
            st.session_state["input_latex"] = sample_latex
            st.session_state["input_jd"] = sample_jd
            st.rerun()

    # Main Area: Inputs
    st.markdown("### 1. Resume Source & Target Job Description")
    
    col_in1, col_in2 = st.columns(2)
    
    with col_in1:
        st.subheader("LaTeX Resume (.tex) or PDF (.pdf)")
        uploaded_file = st.file_uploader(
            "Upload Resume (.tex, .pdf, or .txt)",
            type=["tex", "pdf", "txt"],
            help="Upload your LaTeX (.tex) resume or an existing PDF. If PDF is uploaded, text is extracted."
        )
        
        default_latex = st.session_state.get("input_latex", "")
        
        if uploaded_file is not None:
            file_name = uploaded_file.name.lower()
            if file_name.endswith(".pdf"):
                with st.spinner("Extracting text from uploaded PDF..."):
                    try:
                        pdf_bytes = uploaded_file.read()
                        extracted_text = PDFEngine.extract_text_from_pdf(pdf_bytes)
                        st.success(f"Extracted {len(extracted_text.split())} words from PDF!")
                        # If no LaTeX in session, load the base ATS template and notify
                        if not default_latex:
                            sample_latex, _ = load_sample_data()
                            default_latex = sample_latex
                            st.session_state["input_latex"] = default_latex
                            st.info("Loaded ATS LaTeX template populated with standard format. You can customize the source below.")
                    except Exception as e:
                        st.error(f"Error reading PDF: {e}")
            else:
                default_latex = uploaded_file.read().decode("utf-8", errors="ignore")
                st.session_state["input_latex"] = default_latex

        latex_code = st.text_area(
            "LaTeX Source Code (Preserved 100% as fallback)",
            value=default_latex,
            height=320,
            placeholder=r"\documentclass{article} ... \begin{document} ... \end{document}",
            key="input_latex_area"
        )
        if latex_code:
            st.session_state["input_latex"] = latex_code

    with col_in2:
        st.subheader("Target Job Description (JD)")
        default_jd = st.session_state.get("input_jd", "")
        jd_text = st.text_area(
            "Paste Target Job Description",
            value=default_jd,
            height=320,
            placeholder="Paste role title, responsibilities, tools, and qualifications here...",
            key="input_jd_area"
        )
        if jd_text:
            st.session_state["input_jd"] = jd_text

    # Action Button
    st.markdown("<br>", unsafe_allow_html=True)
    can_run = bool(latex_code.strip() and jd_text.strip())
    
    btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
    with btn_col2:
        run_btn = st.button(
            "🚀 Optimize Resume for ATS & Jobscan (100% Free)",
            use_container_width=True,
            type="primary",
            disabled=not can_run
        )

    if not can_run and not default_latex:
        st.info("👆 Click **'Load Sample Resume & JD'** in the left sidebar to preview the pipeline in 1 click!")

    # Pipeline Execution
    if run_btn:
        if selected_provider_key != "demo" and not api_key:
            st.error(f"Please enter your {provider_cfg['name']} API key in the sidebar, or switch provider to 'Demo Mode'.")
            return

        progress_bar = st.progress(0)
        status_box = st.status("Initiating optimization pipeline...", expanded=True)

        def update_progress(prog: PipelineProgress):
            fraction = prog.step_num / prog.total_steps
            progress_bar.progress(fraction)
            status_box.update(
                label=f"Step {prog.step_num}/{prog.total_steps}: {prog.step_name}",
                state="running"
            )
            st.write(f"✓ **{prog.step_name}**: {prog.message}")

        try:
            with status_box:
                result: PipelineResult = OptimizerPipeline.run(
                    raw_latex=latex_code,
                    raw_jd=jd_text,
                    provider=selected_provider_key,
                    api_key=api_key if selected_provider_key != "demo" else None,
                    model=model_selected,
                    bluff_aggressiveness=bluff_aggressiveness,
                    align_job_title=align_title_toggle,
                    enforce_one_page=enforce_one_page_toggle,
                    progress_callback=update_progress
                )
                status_box.update(label="✅ Optimization completed successfully!", state="complete", expanded=False)
                progress_bar.progress(1.0)
                st.session_state["pipeline_result"] = result

        except Exception as e:
            status_box.update(label="❌ Pipeline Error", state="error", expanded=True)
            st.error(f"Error during optimization: {str(e)}")
            return

    # Results Display
    if "pipeline_result" in st.session_state:
        res: PipelineResult = st.session_state["pipeline_result"]
        report = res.ats_report

        st.divider()
        st.markdown(f"## 📊 ATS & Jobscan Optimization Report: `{res.target_job_title}`")

        # Score Metric Banners (Aligned with Jobscan Criteria)
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600;">BEFORE ATS SCORE</div>
                <div class="score-badge score-amber">{report.before.overall_score}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Initial Baseline</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600;">OPTIMIZED ATS SCORE</div>
                <div class="score-badge score-green">{report.after.overall_score}%</div>
                <div style="color: #10b981; font-weight: 700; font-size: 0.85rem;">+{report.score_delta}% Match Gain</div>
            </div>
            """, unsafe_allow_html=True)

        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600;">JOBSCAN SIMULATED</div>
                <div class="score-badge score-purple">{report.after.jobscan_score}%</div>
                <div style="color: #c084fc; font-weight: 700; font-size: 0.85rem;">+{report.jobscan_delta}% Gain (Before: {report.before.jobscan_score}%)</div>
            </div>
            """, unsafe_allow_html=True)

        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600;">JOB TITLE MATCH</div>
                <div class="score-badge score-blue">{report.after.job_title_match_pct}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Before: {report.before.job_title_match_pct}%</div>
            </div>
            """, unsafe_allow_html=True)

        with m5:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600;">IN-CONTEXT BULLETS</div>
                <div class="score-badge score-green">{report.after.experience_context_match_pct}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Skills in Work History</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabbed Details
        tab_diff, tab_keywords, tab_latex = st.tabs([
            "📝 Change Log & Bullet Rewrites",
            "🏷️ Keyword Matrix & Jobscan Check",
            "💾 Compilable LaTeX & PDF Rendering"
        ])

        # TAB 1: Diff & Change Log
        with tab_diff:
            st.subheader("💡 Strategic Enhancements Overview")
            st.info(res.optimization_result.summary_log)

            # Added Bluffs
            if res.optimization_result.added_bluffs:
                st.markdown("#### 🎯 Believable Bluffs Added (Domain-Adjacent Skills)")
                st.caption("High-demand industry skills naturally fitting candidate background:")
                
                bluff_cols = st.columns(min(3, len(res.optimization_result.added_bluffs)))
                for idx, bluff in enumerate(res.optimization_result.added_bluffs):
                    col = bluff_cols[idx % len(bluff_cols)]
                    with col:
                        st.markdown(f"""
                        <div style="background: #1e293b; border-left: 4px solid #3b82f6; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">
                            <strong style="color: #93c5fd; font-size: 1.05rem;">{bluff.get('skill', '')}</strong><br>
                            <span style="color: #cbd5e1; font-size: 0.85rem;">{bluff.get('rationale', '')}</span>
                        </div>
                        """, unsafe_allow_html=True)

            # Rewritten Bullets Comparison
            st.markdown("#### 🔄 Experience & Project Bullet Rewrites (1-Page Tight Fit)")
            st.caption("Punchy Google XYZ statements with action verbs, JD keywords, and metrics (under 22 words each):")
            
            for bullet in res.parsed_resume.bullets:
                opt_text = res.optimization_result.rewritten_bullets.get(bullet.id)
                justification = res.optimization_result.bullet_justifications.get(bullet.id, "")
                is_pruned = bullet.id in res.optimization_result.pruned_bullet_ids

                if opt_text or is_pruned:
                    with st.expander(f"📍 {bullet.section_name} — {bullet.id.replace('_', ' ').title()}", expanded=True):
                        c_orig, c_opt = st.columns(2)
                        with c_orig:
                            st.markdown("**Original Bullet:**")
                            st.markdown(f"> *{bullet.original_text}*")
                            st.caption(f"Word count: {len(bullet.original_text.split())} words")
                        with c_opt:
                            if is_pruned:
                                st.markdown("**Optimization Status:**")
                                st.warning("🚫 Pruned / De-emphasized (Irrelevant to target job role)")
                            else:
                                st.markdown("**Optimized Bullet (Google XYZ):**")
                                st.markdown(f"> **{opt_text}**")
                                st.caption(f"Word count: {len(opt_text.split())} words | 🧠 **Rationale:** {justification}")

        # TAB 2: Keyword Coverage Matrix
        with tab_keywords:
            st.subheader("🎯 ATS & Jobscan Keyword Coverage")
            
            c_kw1, c_kw2 = st.columns(2)
            with c_kw1:
                st.markdown("##### ✅ Matched & In-Context Keywords")
                matched_html = "".join([f'<span class="keyword-pill pill-green">{kw}</span>' for kw in report.after.matched_keywords])
                st.markdown(matched_html if matched_html else "*None*", unsafe_allow_html=True)

                if report.newly_matched_keywords:
                    st.markdown("##### 🚀 Newly Unlocked Keywords (from Optimization)")
                    new_html = "".join([f'<span class="keyword-pill pill-blue">+{kw}</span>' for kw in report.newly_matched_keywords])
                    st.markdown(new_html, unsafe_allow_html=True)

            with c_kw2:
                if report.after.skills_only_keywords:
                    st.markdown("##### ⚠️ Skills Found Only in Skills List")
                    st.caption("Jobscan recommends having these appear in work experience bullets too:")
                    so_html = "".join([f'<span class="keyword-pill pill-amber">{kw}</span>' for kw in report.after.skills_only_keywords])
                    st.markdown(so_html, unsafe_allow_html=True)

                st.markdown("##### ⚠️ Remaining Keyword Gaps")
                st.caption("Skills in the JD not currently claimed in the resume:")
                miss_html = "".join([f'<span class="keyword-pill pill-red">{kw}</span>' for kw in report.after.missing_keywords[:20]])
                st.markdown(miss_html if miss_html else "*Zero gaps! Complete match.*", unsafe_allow_html=True)

                st.markdown("##### 🌐 DuckDuckGo Trending Role Skills")
                trend_html = "".join([f'<span class="keyword-pill pill-purple">{t}</span>' for t in res.trend_report.trending_skills])
                st.markdown(trend_html, unsafe_allow_html=True)

        # TAB 3: Compilable LaTeX & PDF Rendering
        with tab_latex:
            st.subheader("💻 Compilable LaTeX Source & PDF Output")
            
            # Syntax validation status badge
            if res.is_latex_valid:
                st.success("✅ Passed All LaTeX Syntax Checks: Braces balanced, environments closed, special characters escaped.")
            else:
                st.warning(f"⚠️ Validation notice: {', '.join(res.latex_validation_errors)}")

            # Action Buttons Row: LaTeX Download & PDF Download
            c_btn1, c_btn2, c_btn3 = st.columns(3)
            with c_btn1:
                st.download_button(
                    label="📥 Download LaTeX (.tex) [Primary]",
                    data=res.optimized_latex,
                    file_name="optimized_resume.tex",
                    mime="text/x-tex",
                    type="primary",
                    use_container_width=True,
                    help="Your clean, 100% template-preserved LaTeX file. Ready to compile in Overleaf or any LaTeX distribution."
                )

            with c_btn2:
                render_pdf_btn = st.button("⚙️ Compile to PDF (Zero-Cost)", use_container_width=True)

            with c_btn3:
                st.link_button(
                    label="🌐 Open in Overleaf",
                    url="https://www.overleaf.com/docs",
                    use_container_width=True,
                    help="Open Overleaf to paste and compile in the cloud."
                )

            # PDF Compilation Handling
            if render_pdf_btn:
                with st.spinner("Compiling LaTeX to PDF via zero-cost engine..."):
                    pdf_data, pdf_err = PDFEngine.compile_latex_to_pdf(res.optimized_latex)
                    if pdf_data:
                        st.session_state["compiled_pdf"] = pdf_data
                        st.success("🎉 PDF compiled successfully! Ready for download.")
                    else:
                        st.error(f"PDF compilation notice: {pdf_err}")

            if "compiled_pdf" in st.session_state:
                st.download_button(
                    label="📄 Download Compiled PDF (.pdf)",
                    data=st.session_state["compiled_pdf"],
                    file_name="optimized_resume.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            st.divider()
            st.markdown("#### 📄 LaTeX Source Code")
            st.code(res.optimized_latex, language="latex", line_numbers=True)


if __name__ == "__main__":
    main()
