import os
import csv
import textwrap
import importlib.util
from pathlib import Path

# Load the module by file path so tests don't depend on sys.path behavior
module_path = Path(__file__).resolve().parents[1] / "assemble_grading_comments.py"
spec = importlib.util.spec_from_file_location("assemble_grading_comments", str(module_path))
agc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agc)


def test_compute_score_totals_basic():
    comments = [
        "### Grading: 3/5",
        "Some note",
        "### Grading: 2/2",
        "### Grading: 1/5 ### Grading: 2/2",
    ]
    obt, poss = agc.compute_score_totals(comments)
    assert obt == 8
    assert poss == 14


def test_compute_totals_in_directory_non_recursive(tmp_path):
    # Create two python files with grading comments
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text(textwrap.dedent("""
        # starter
        ### Grading: 4/5
        ### Grading: 1/1
    """))
    b.write_text(textwrap.dedent("""
        # another
        ### Grading: 2/2
    """))

    # Run the directory totals with report writing enabled
    result = agc.compute_totals_in_directory(str(tmp_path), recursive=False, report_per_file=True, write_report=True)
    # result should be (obt, poss, per_file_results)
    assert isinstance(result, tuple) and len(result) == 3
    obt = result[0]
    poss = result[1]
    per_file = result[2]
    assert obt == 7
    assert poss == 8
    # per_file should have two entries
    assert len(per_file) == 2

    # Check that a report file was created and contains the REPORT_PREAMBLE and grand total
    report_path = tmp_path / agc.REPORT_FILE_NAME
    assert report_path.exists()
    content = report_path.read_text(encoding='utf-8')
    assert agc.REPORT_PREAMBLE.strip().splitlines()[0] in content
    assert "Grand total: 7 / 8" in content


def test_recursive_summary_csv(tmp_path):
    # Create nested directories and files
    top = tmp_path / "topdir"
    sub = top / "sub"
    subsub = sub / "subsub"
    subsub.mkdir(parents=True)
    (top / "t.py").write_text("### Grading: 1/2\n")
    (sub / "s.py").write_text("### Grading: 2/3\n")
    (subsub / "ss.py").write_text("### Grading: 3/4\n")

    # Run recursive summary generation
    agc.compute_totals_in_directory(str(top), recursive=True, report_per_file=False, write_report=False, write_summary=True)

    summary_path = top / agc.SUMMARY_FILE_NAME
    assert summary_path.exists()

    # Read CSV and map rel->(obt, poss)
    rows = {}
    with summary_path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows[r['Directory']] = (int(r['TotalObtained']), int(r['TotalPossible']))

    # Build expected keys relative to top
    topname = os.path.basename(str(top))
    assert topname in rows
    # Determine expected totals
    assert rows[topname] == (6, 9)
    assert rows['sub'] == (5, 7)
    # sub/subsub path may be represented as 'sub\\subsub' or 'sub/subsub' depending on OS
    # construct rel for sub/subsub
    rel_subsub = os.path.join('sub', 'subsub')
    if rel_subsub in rows:
        assert rows[rel_subsub] == (3, 4)
    else:
        # on some systems rel may be 'sub\\subsub' already normalized by csv writing
        alt = 'sub' + os.sep + 'subsub'
        assert rows.get(alt, (None, None)) == (3, 4)
