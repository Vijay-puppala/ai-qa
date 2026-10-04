"""Finding unimplemented skeletons from the repository alone (FR-028, SC-015).

Also covers SC-016: a generated skeleton must be syntactically valid and
collectable. A generated file with a syntax error breaks collection for the
**entire** suite, not just its own tests.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from ai_qa.generate import scaffold
from ai_qa.generate.brief import build
from ai_qa.generate.listing import find_skeletons
from ai_qa.generate.sentinel import SKELETON_SENTINEL, skip_reason
from ai_qa.jira.models import JiraIssue


def _write(tmp_path, body: str):
    (tmp_path / "ui").mkdir(exist_ok=True)
    path = tmp_path / "ui" / "test_sample.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_finds_skeletons_and_ignores_implemented_tests(tmp_path) -> None:
    _write(
        tmp_path,
        '''
        import pytest
        from ai_qa.generate.sentinel import SKELETON_SENTINEL, skip_reason

        pytestmark = [pytest.mark.ui, pytest.mark.ticket("TC-345")]

        def test_not_done_fstring():
            pytest.skip(f"{SKELETON_SENTINEL}: body not implemented")

        def test_not_done_helper():
            pytest.skip(skip_reason())

        def test_done():
            assert 1 == 1
        ''',
    )

    found = find_skeletons(tmp_path)

    assert {s.test_name for s in found} == {"test_not_done_fstring", "test_not_done_helper"}
    assert all(s.ticket == "TC-345" for s in found)


def test_a_broken_file_does_not_crash_the_scan(tmp_path) -> None:
    _write(tmp_path, "def test_broken(:\n    pass\n")
    assert find_skeletons(tmp_path) == []


def test_scan_needs_no_test_run_and_no_network(tmp_path) -> None:
    """Skips are evaluated at run time, so --collect-only would find nothing."""
    _write(
        tmp_path,
        '''
        import pytest
        from ai_qa.generate.sentinel import skip_reason
        pytestmark = pytest.mark.ticket("TC-9")
        def test_x():
            pytest.skip(skip_reason())
        ''',
    )
    assert len(find_skeletons(tmp_path)) == 1


def test_a_generated_skeleton_is_collectable(tmp_path) -> None:
    """SC-016: zero collection errors, or the whole suite stops collecting."""
    issue = JiraIssue(
        key="TC-345",
        project_key="TC",
        summary="Checkout rejects an expired card",
        description="An expired card must be refused.",
        raw={},
    )
    rendered = scaffold.render(build(issue))
    body = rendered + textwrap.dedent(
        '''

        def test_expired_card_is_rejected():
            """Checkout refuses an expired card and shows why."""
            pytest.skip(skip_reason())
        '''
    )
    target = tmp_path / "test_generated.py"
    target.write_text(body, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", str(target),
         "-o", "addopts=", "-o", "markers=ui: ui\nticket(key): ticket"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert result.returncode == 0, f"generated file failed to collect:\n{result.stdout}\n{result.stderr}"
    assert "1 test" in result.stdout or "test_expired_card_is_rejected" in result.stdout


def test_sentinel_is_a_single_shared_constant() -> None:
    """Three features import it; a copied literal drifts and breaks two."""
    assert SKELETON_SENTINEL == "ai-qa:unimplemented"
    assert SKELETON_SENTINEL in skip_reason()
