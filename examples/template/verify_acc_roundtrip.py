"""
Round-trip verification of the generated ACC project.

For every schema version, each generated ARXML file is read back with the
library reader and written out again. The re-serialized XML is compared
line-by-line against the file on disk; any difference is a round-trip gap of
the reader or the writer and is reported (not hidden).
"""

import difflib
import glob
import os
import sys
from acc_system import generator
import autosar.xml


def compare(file_path: str, schema_version: int) -> list[str]:
    """
    Reads a file, writes it back and returns the unified diff (empty when identical)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        expected = file.read()
    reader = autosar.xml.Reader(warn_on_unprocessed_element=False)
    document = reader.read_file(file_path)
    writer = autosar.xml.Writer()
    actual = writer.write_str(document, skip_root_attr=False)
    if actual == expected:
        return []
    unsupported = sorted(reader.observed_unsupported_elements)
    if unsupported:
        print(f"  Elements not supported by the reader: {', '.join(unsupported)}")
    return list(difflib.unified_diff(expected.splitlines(),
                                     actual.splitlines(),
                                     fromfile=f"{os.path.basename(file_path)} (generated)",
                                     tofile=f"{os.path.basename(file_path)} (read back, schema {schema_version})",
                                     lineterm=""))


def main() -> int:
    """Main"""
    error_count = 0
    for schema_version in generator.SCHEMA_VERSIONS:
        document_root = generator.schema_dir(schema_version)
        file_paths = sorted(glob.glob(os.path.join(document_root, "*.arxml")))
        if not file_paths:
            print(f"No generated ARXML found in {document_root}, run generate_acc_xml.py first")
            return 1
        for file_path in file_paths:
            diff = compare(file_path, schema_version)
            if diff:
                error_count += 1
                print(f"ROUND-TRIP GAP in {file_path}:")
                print('\n'.join(diff[:40]))
            else:
                print(f"OK  schema {schema_version}: {os.path.basename(file_path)}")
    if error_count:
        print(f"{error_count} file(s) did not round-trip")
        return 1
    print("All files round-tripped without differences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
