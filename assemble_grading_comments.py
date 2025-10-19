import re

GRADING_MARKER = '### Grading:'

REPORT_FILE_NAME = 'grading_report.txt'

def extract_grading_comments_from_file(file_name):
    """
    Extract grading comments from a specified file.

    This function reads a file containing grading comments and extracts
    the relevant information for further processing.

    Returns:
        list: A list of grading comments extracted from the file.
    """
    grading_comments = []

    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                line_text = line.strip()
                if line_text:
                    if GRADING_MARKER in line_text:
                        # Extract the comment after the grading marker, but including the marker itself
                        extracted = line_text[line_text.index(
                            GRADING_MARKER):].strip()
                        grading_comments.append(extracted)
    except FileNotFoundError:
        print(f"The file '{file_name}' was not found.")
    except OSError as e:
        print(f"An I/O error occurred while reading '{file_name}': {e}")

    return grading_comments


def compute_score_totals(grading_comments):
    """
    Compute total obtained and total possible scores from grading comments.

    Args:
        grading_comments (list[str]): list of comment strings (each usually
            starting with the GRADING_MARKER).

    Returns:
        tuple: (total_obtained, total_possible) as integers. If no matches are
            found both values are 0.

    Notes:
        This function looks for occurrences of the pattern
        "<GRADING_MARKER> <obtained>/<possible>" inside each comment. It
        supports multiple matches in a single comment (all are summed).
    """
    total_obtained = 0
    total_possible = 0

    # Build a regex that requires the GRADING_MARKER before the score pair.
    # We use a non-capturing group for repeated scanning; findall returns the
    # captured groups (obtained, possible).
    pattern = re.compile(re.escape(GRADING_MARKER) + r"\s*(\d+)\s*/\s*(\d+)")

    for c in grading_comments:
        # Find all (obtained, possible) pairs that directly follow the marker
        matches = pattern.findall(c)
        for obtained_str, possible_str in matches:
            try:
                obt = int(obtained_str)
                pos = int(possible_str)
            except ValueError:
                # skip values that aren't integers
                continue
            total_obtained += obt
            total_possible += pos

    return total_obtained, total_possible


def compute_totals_in_directory(directory_path, recursive=False, report_per_file=False, write_report=False):
    """
    Scan Python files in `directory_path` and compute summed scores.

    Args:
        directory_path (str): path to directory to scan for .py files.
        recursive (bool): if True, walk subdirectories recursively. Default False.

    Returns:
        tuple: (total_obtained, total_possible) summed across all .py files found.
    """
    import os

    total_obtained = 0
    total_possible = 0

    if recursive:
        walker = os.walk(directory_path)
    else:
        # single directory listing
        try:
            entries = [(directory_path, [], [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))])]
            walker = entries
        except OSError as e:
            print(f"Could not list directory '{directory_path}': {e}")
            return 0, 0

    # Store per-file tuples: (comments_list, (obtained, possible))
    per_file_results = {}

    for root, _dirs, files in walker:
        for name in files:
            if name.endswith('.py'):
                path = os.path.join(root, name)
                try:
                    file_comments = extract_grading_comments_from_file(path)
                except OSError as e:
                    # If a single file fails to read/parse, continue with others
                    print(f"Skipping '{path}' due to I/O error: {e}")
                    continue
                obt, pos = compute_score_totals(file_comments)
                total_obtained += obt
                total_possible += pos
                if report_per_file or write_report:
                    per_file_results[path] = (file_comments, (obt, pos))

    # If requested, write a report file into the directory_path (non-recursive)
    # or into each directory encountered when recursive.
    if write_report:
        # Determine which directories to write reports for. If recursive, write
        # for every directory that had any .py files processed. Otherwise only
        # write for the provided directory_path.
        dirs_to_report = set()
        if recursive:
            for filepath in per_file_results:
                dirs_to_report.add(os.path.dirname(filepath))
        else:
            dirs_to_report.add(directory_path)

        for d in sorted(dirs_to_report):
            report_path = os.path.join(d, REPORT_FILE_NAME)
            try:
                with open(report_path, 'w', encoding='utf-8') as rpt:
                    rpt.write(f"Grading report for directory: {os.path.basename(d)}\n")
                    rpt.write("\n")
                    grand_obt = 0
                    grand_pos = 0
                    # Collect files in this directory in a stable order
                    files_in_dir = [p for p in sorted(per_file_results) if os.path.dirname(p) == d]
                    for p in files_in_dir:
                        comments_list, (fobt, fpos) = per_file_results[p]
                        rpt.write(f"File: {os.path.basename(p)}\n")
                        for c in comments_list:
                            rpt.write(c + "\n")
                        rpt.write(f"Total for {os.path.basename(p)}: {fobt} / {fpos}\n")
                        rpt.write("\n")
                        grand_obt += fobt
                        grand_pos += fpos
                    rpt.write(f"Grand total: {grand_obt} / {grand_pos}\n")
            except OSError as e:
                print(f"Could not write report to '{report_path}': {e}")

    if report_per_file:
        return total_obtained, total_possible, per_file_results
    return total_obtained, total_possible


def single_file_demo():
    """
    Demonstrate grading comment extraction and score computation on a single file.
    """
    comments = extract_grading_comments_from_file(r"C:\Users\jmac\claude\assemble-grading-comments\Elian Vera_1276956_assignsubmission_file\circles_graded.py")
    for comment in comments:
        print(comment)
    # Demonstrate the new score-summing function
    obtained, possible = compute_score_totals(comments)
    print(f"Total obtained: {obtained} / Total possible: {possible}")


def directory_demo(directory_path, recursive=False, report_per_file=False, write_report=False):
    """
    Demonstrate scanning a directory of .py files and computing totals.

    If report_per_file is True, the demo will also print per-file totals.
    """
    if report_per_file:
        result = compute_totals_in_directory(
            directory_path, recursive=recursive, report_per_file=True, write_report=write_report
        )
        if isinstance(result, tuple) and len(result) == 3:
            obtained = result[0]
            possible = result[1]
            per_file = result[2]
        else:
            # Fallback if implementation changes unexpectedly
            obtained = result[0]
            possible = result[1]
            per_file = {}
        print(f"Directory totals for '{directory_path}' (recursive={recursive}): {obtained} / {possible}")
        print("Per-file breakdown:")
        for path, (obt, pos) in sorted(per_file.items()):
            print(f"  {path}: {obt} / {pos}")
    else:
        if write_report:
            obtained, possible = compute_totals_in_directory(
                directory_path, recursive=recursive, report_per_file=False, write_report=True
            )
        else:
            obtained, possible = compute_totals_in_directory(
                directory_path, recursive=recursive, report_per_file=False, write_report=False
            )
        print(f"Directory totals for '{directory_path}' (recursive={recursive}): {obtained} / {possible}")

if __name__ == "__main__":
    # Run the single-file demo
    single_file_demo()

    # Example directory demos: change the paths to folders you want to scan.
    # Set report_per_file=True to enable per-file debugging output.
    # Example: enable per-file printing but don't write report files
    # directory_demo(r"C:\Users\jmac\claude\assemble-grading-comments\Dylan Elder_1276949_assignsubmission_file", recursive=False, report_per_file=True, write_report=False)
    # Example: enable per-file printing and write report files to each directory
    # directory_demo(r"C:\Users\jmac\claude\assemble-grading-comments\Elian Vera_1276956_assignsubmission_file", recursive=False, report_per_file=True, write_report=True)
    

    directory_demo(r"C:\Users\jmac\claude\assemble-grading-comments", recursive=True, report_per_file=True, write_report=True)
