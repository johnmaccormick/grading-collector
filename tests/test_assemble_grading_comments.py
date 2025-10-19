import os
import importlib.util
from pathlib import Path

# Load the module by file path so tests don't depend on sys.path behavior
module_path = Path(__file__).resolve().parents[1] / "assemble_grading_comments.py"
spec = importlib.util.spec_from_file_location("assemble_grading_comments", str(module_path))
agc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agc)

compute_score_totals = agc.compute_score_totals
compute_totals_in_directory = agc.compute_totals_in_directory
REPORT_FILE_NAME = agc.REPORT_FILE_NAME
SUMMARY_FILE_NAME = agc.SUMMARY_FILE_NAME
REPORT_PREAMBLE = agc.REPORT_PREAMBLE


def test_compute_score_totals_parsing():
    comments = [
        "### Grading: 6/10",
        "some text",
        "prefix ### Grading: 4/5 extra",
        "### Grading: 2/2",
    ]
    obt, pos = compute_score_totals(comments)
    assert obt == 12
    assert pos == 17


def test_write_report_non_recursive(tmp_path):
    d = tmp_path / "course_dir"
    d.mkdir()
    a = d / "a.py"
    a.write_text("# comment\n### Grading: 3/5\n### Grading: 1/1\n")
    b = d / "b.py"
    b.write_text("### Grading: 2/2\n")

    # Run non-recursive
    res = compute_totals_in_directory(str(d), recursive=False, report_per_file=True, write_report=True)
    # Should return (obt, pos, per_file_results)
    assert isinstance(res, tuple) and len(res) == 3
    obt, pos, per_file = res
    assert (obt, pos) == (6, 8)

    report_path = d / REPORT_FILE_NAME
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    # Preamble should be present
    assert REPORT_PREAMBLE.strip() in content
    # Per-file totals and grand total should be present
    assert "File: a.py" in content
    assert "Total for a.py: 4 / 6" in content
    assert "Grand total: 6 / 8" in content


def test_write_summary_recursive(tmp_path):
    top = tmp_path / "top"
    (top / "sub1").mkdir(parents=True)
    (top / "sub2" / "subsub").mkdir(parents=True)

    (top / "file_top.py").write_text("### Grading: 1/2\n")
    (top / "sub1" / "f1.py").write_text("### Grading: 2/3\n")
    (top / "sub2" / "f2.py").write_text("### Grading: 3/4\n")
    (top / "sub2" / "subsub" / "f3.py").write_text("### Grading: 4/5\n")

    res = compute_totals_in_directory(str(top), recursive=True, report_per_file=True, write_summary=True)
    # Expect a 3-tuple when report_per_file=True
    assert isinstance(res, tuple) and len(res) == 3
    obtained, possible, per_file = res

    # Totals should include all files
    assert obtained == 10
    assert possible == 14

    summary_path = top / SUMMARY_FILE_NAME
    assert summary_path.exists()
    csv = summary_path.read_text(encoding="utf-8").splitlines()
    assert csv[0].strip() == 'Directory,TotalObtained,TotalPossible'

    # Parse rows into dict
    rows = {}
    for line in csv[1:]:
        if not line.strip():
            continue
        dir_name, tot_obt, tot_pos = line.split(",")
        rows[dir_name] = (int(tot_obt), int(tot_pos))

    top_key = os.path.basename(str(top))
    assert rows[top_key] == (10, 14)
    assert rows[os.path.join('sub1')] == (2, 3)
    assert rows[os.path.join('sub2')] == (7, 9)
    assert rows[os.path.join('sub2', 'subsub')] == (4, 5)
