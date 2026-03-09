"""Repo Doctor — Streamlit web GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from repo_doctor.context import build_context
from repo_doctor.engine import RuleEngine
from repo_doctor.models import Severity


def main() -> None:
    st.set_page_config(page_title="Repo Doctor", page_icon="🩺", layout="wide")
    st.title("🩺 Repo Doctor")
    st.caption("Turn any repository into an open-source-ready, professional repo.")

    # --- Sidebar ---
    with st.sidebar:
        repo_path = st.text_input("Repository path", value=".", help="Absolute or relative path")
        strict = st.checkbox("Strict mode", help="Treat warnings as errors")
        col1, col2 = st.columns(2)
        scan_clicked = col1.button("Scan", type="primary", use_container_width=True)
        fix_clicked = col2.button("Fix (dry run)", use_container_width=True)

    path = Path(repo_path).resolve()

    if not path.is_dir():
        if scan_clicked or fix_clicked:
            st.error(f"Not a valid directory: `{path}`")
        return

    if not scan_clicked and not fix_clicked:
        st.info("Enter a repository path and click **Scan** to get started.")
        return

    # --- Run scan ---
    ctx = build_context(path)
    engine = RuleEngine()
    report = engine.scan(ctx)

    # --- Score ---
    grade_colors = {"A": "green", "B": "blue", "C": "orange", "D": "red"}
    color = grade_colors.get(report.grade.value, "gray")

    col_score, col_grade, col_stack = st.columns(3)
    col_score.metric("Score", f"{report.score} / 100")
    col_grade.metric("Grade", report.grade.value)
    col_stack.metric("Stack", report.stack)

    # --- Results table ---
    st.subheader("Results")
    rows = []
    for r in report.results:
        icon = "✅" if r.passed else {"error": "❌", "warn": "⚠️", "info": "ℹ️"}.get(r.severity.value, "—")
        rows.append({
            "Status": icon,
            "Rule": r.name,
            "Severity": r.severity.value.upper(),
            "Details": "" if r.passed else r.rationale,
            "Auto-fix": "Yes" if r.auto_fixable else "",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- Fix preview ---
    if fix_clicked:
        plan = engine.build_change_plan(ctx, report)
        if not plan.changes:
            st.success("Nothing to fix — repository looks good!")
        else:
            st.subheader("Proposed changes (dry run)")
            for change in plan.changes:
                with st.expander(f"{change.operation.value.upper()} {change.file_path} — {change.description}"):
                    st.code(change.content, language="text")

    # --- Strict check ---
    if strict:
        has_issues = any(
            not r.passed and r.severity in (Severity.WARN, Severity.ERROR)
            for r in report.results
        )
        if has_issues:
            st.error("Strict mode: warnings or errors found.")


if __name__ == "__main__":
    main()
