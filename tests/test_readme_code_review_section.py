"""Tests for the "Code review" section added to README.md.

These tests guard against the README's documentation of the automated PR
review setup drifting out of sync with the actual repository contents: the
config/workflow files it names must exist, the reviewer table must stay well
formed, and the CI checks it advertises must match what `ci.yml` actually
runs.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def code_review_section(readme_text: str) -> str:
    """Extract the body of the '## Code review' section (up to the next '## ')."""
    marker = "## Code review"
    start = readme_text.index(marker)
    rest = readme_text[start + len(marker) :]
    end = rest.index("\n## ")
    return rest[:end]


@pytest.fixture(scope="module")
def table_rows(code_review_section: str) -> list[list[str]]:
    """Parse the markdown table in the Code review section into rows of cells."""
    rows = []
    for line in code_review_section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # Skip the header separator row, e.g. "| --- | --- | --- |"
        if all(set(cell) <= {"-"} for cell in cells):
            continue
        rows.append(cells)
    return rows


def test_code_review_heading_exists(readme_text: str) -> None:
    assert "## Code review" in readme_text


def test_code_review_section_appears_before_license(readme_text: str) -> None:
    assert readme_text.index("## Code review") < readme_text.index("## License")


def test_code_review_section_appears_after_tests(readme_text: str) -> None:
    assert readme_text.index("## Tests") < readme_text.index("## Code review")


def test_table_header_row_present(table_rows: list[list[str]]) -> None:
    assert table_rows[0] == ["Reviewer", "Type", "Config"]


def test_table_has_five_reviewer_rows(table_rows: list[list[str]]) -> None:
    # header row + 5 reviewer rows
    assert len(table_rows) == 6


def test_table_rows_all_have_three_columns(table_rows: list[list[str]]) -> None:
    for row in table_rows:
        assert len(row) == 3, f"expected 3 columns, got {row!r}"


def test_table_rows_have_no_empty_cells(table_rows: list[list[str]]) -> None:
    for row in table_rows:
        for cell in row:
            assert cell, f"unexpected empty cell in row {row!r}"


@pytest.mark.parametrize(
    "reviewer", ["Claude", "CodeRabbit", "Devin", "Sentry", "SonarCloud"]
)
def test_expected_reviewer_listed(table_rows: list[list[str]], reviewer: str) -> None:
    reviewer_names = [row[0] for row in table_rows[1:]]
    assert reviewer in reviewer_names


def test_five_reviewers_claim_matches_table(
    code_review_section: str, table_rows: list[list[str]]
) -> None:
    assert "five automated reviewers" in code_review_section
    assert len(table_rows) - 1 == 5


def _referenced_paths(table_rows: list[list[str]]) -> list[str]:
    """Extract every backtick-quoted, filesystem-looking path from the Config column."""
    paths = []
    for row in table_rows[1:]:
        config_cell = row[2]
        for token in re.findall(r"`([^`]+)`", config_cell):
            # Only keep tokens that look like file paths (contain a dot or slash),
            # excluding env-var-style all-caps tokens like `ANTHROPIC_API_KEY`.
            if token.isupper():
                continue
            if "/" in token or "." in token:
                paths.append(token)
    return paths


def test_referenced_config_paths_extracted() -> None:
    rows = [
        ["Reviewer", "Type", "Config"],
        ["Claude", "GitHub Action", "`.github/workflows/claude-review.yml` (`ANTHROPIC_API_KEY`)"],
        ["SonarCloud", "GitHub Action", "`.github/workflows/sonar.yml` + `sonar-project.properties` (`SONAR_TOKEN`)"],
    ]
    paths = _referenced_paths(rows)
    assert paths == [
        ".github/workflows/claude-review.yml",
        ".github/workflows/sonar.yml",
        "sonar-project.properties",
    ]


def test_referenced_config_files_exist_on_disk(table_rows: list[list[str]]) -> None:
    paths = _referenced_paths(table_rows)
    assert paths, "expected at least one referenced config path in the table"
    for rel_path in paths:
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"README references missing file: {rel_path}"


def test_referenced_workflow_files_are_valid_yaml(table_rows: list[list[str]]) -> None:
    yaml = pytest.importorskip("yaml")
    paths = _referenced_paths(table_rows)
    yaml_paths = [p for p in paths if p.endswith((".yml", ".yaml"))]
    assert yaml_paths, "expected at least one referenced YAML workflow file"
    for rel_path in yaml_paths:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)
        assert "jobs" in parsed


def test_ci_workflow_file_referenced_and_exists(code_review_section: str) -> None:
    assert "`ci.yml`" in code_review_section
    assert (REPO_ROOT / ".github" / "workflows" / "ci.yml").is_file()


def test_ci_claims_match_actual_ci_workflow_jobs(code_review_section: str) -> None:
    """The README claims CI runs 'frontend type-check + build, pytest, and ruff' —
    verify ci.yml actually defines matching job names."""
    ci_yaml = pytest.importorskip("yaml")
    ci_content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    parsed = ci_yaml.safe_load(ci_content)
    job_names = {job.get("name", "") for job in parsed["jobs"].values()}

    assert any("type-check" in name.lower() for name in job_names)
    assert any("pytest" in name.lower() for name in job_names)
    assert any("ruff" in name.lower() for name in job_names)


def test_ci_sentence_present_and_after_table(code_review_section: str) -> None:
    ci_sentence_idx = code_review_section.index(
        "CI (`ci.yml`) must also pass"
    )
    last_table_row_idx = code_review_section.rindex("SonarCloud")
    assert ci_sentence_idx > last_table_row_idx


def test_no_leftover_placeholder_text(code_review_section: str) -> None:
    for placeholder in ("TODO", "TBD", "FIXME", "XXX"):
        assert placeholder not in code_review_section
