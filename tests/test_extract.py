import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from extract import EXPECTED_COLUMNS, check_structure, extract_data  # noqa: E402


def _sample_df():
    return pd.DataFrame(
        [["489434", "85048", "ITEM", 12, "2009-12-01 07:45:00", 6.95, 13085.0, "United Kingdom"]],
        columns=EXPECTED_COLUMNS,
    )


def test_check_structure_ok():
    info = check_structure(_sample_df())
    assert info["rows"] == 1


def test_check_structure_missing_column():
    with pytest.raises(ValueError):
        check_structure(_sample_df().drop(columns=["Price"]))


def test_extract_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_data(path=tmp_path / "tidak_ada.csv", output_path=tmp_path / "out.pkl")


def test_extract_roundtrip(tmp_path):
    csv = tmp_path / "retail.csv"
    _sample_df().to_csv(csv, index=False)
    out = extract_data(path=csv, output_path=tmp_path / "out.pkl")
    assert len(pd.read_pickle(out)) == 1


def test_extract_empty_file(tmp_path):
    csv = tmp_path / "kosong.csv"
    csv.write_text("")
    with pytest.raises(ValueError, match="kosong"):
        extract_data(path=csv, output_path=tmp_path / "out.pkl")


def test_extract_wrong_columns(tmp_path):
    csv = tmp_path / "salah.csv"
    csv.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(ValueError, match="Kolom hilang"):
        extract_data(path=csv, output_path=tmp_path / "out.pkl")


def test_extract_latin1_file(tmp_path):
    csv = tmp_path / "latin1.csv"
    df = _sample_df()
    df.loc[0, "Description"] = "CAF\xc9 MUG"
    df.to_csv(csv, index=False, encoding="latin1")
    out = extract_data(path=csv, output_path=tmp_path / "out.pkl")
    assert len(pd.read_pickle(out)) == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
