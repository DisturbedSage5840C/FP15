"""Step 14A: the widened leader table (src/leader_ladder.py, src/leader_master.py, src/leader_master_report.py).

Invented names, companies, domains and numbers only: no real data. The ladder is: (1) exact name key, (2) the
existing loose name rule, (3) company name, then domain, accepted only when exactly one firm row is meant.
"""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import pytest

from src.eda_common import EdaSettings
from src.id_matching import Entity, make_entity
from src.id_sources import (
    SOURCE_COMPANY,
    SOURCE_ROSTER,
    SOURCE_SHEETS,
    SOURCE_SUMMARIES,
    company_entities,
)
from src.leader_ladder import (
    AMBIGUOUS,
    COMPANY_NAME,
    DOMAIN,
    NAME_EXACT,
    NAME_LOOSE,
    NONE,
    domain_label,
)
from src.leader_master import FIRM_COLUMNS, PERSON_COLUMNS, build_master, run
from src.leader_master_report import render_report
from src.name_key import name_key

SETTINGS = EdaSettings(min_posts=15, disclosure_min=5, model_min=20, size_bands=4)
KEY_COLUMNS = ("Person_Name", "CompanyName", "DomainName")
FRAME_COLUMNS = [*KEY_COLUMNS, *PERSON_COLUMNS, *FIRM_COLUMNS]


def fake_id(key: str) -> str:
    return "L" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


def company_frame(rows: Sequence[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame([{c: row.get(c, "") for c in FRAME_COLUMNS} for row in rows], columns=FRAME_COLUMNS)


def entities(source: str, people: Sequence[tuple[str, str]]) -> tuple[Entity, ...]:
    made = (make_entity(source, f"{source}:{i}", name, firm) for i, (name, firm) in enumerate(people, start=1))
    return tuple(entity for entity in made if entity is not None)


def master(
    company: pd.DataFrame,
    sheets: Sequence[tuple[str, str]] = (),
    roster: Sequence[tuple[str, str]] = (),
    summaries: Sequence[tuple[str, str]] = (),
    posts: dict[str, int] | None = None,
) -> pd.DataFrame:
    sources = {
        SOURCE_SHEETS: entities(SOURCE_SHEETS, sheets),
        SOURCE_ROSTER: entities(SOURCE_ROSTER, roster),
        SOURCE_SUMMARIES: entities(SOURCE_SUMMARIES, summaries),
        SOURCE_COMPANY: company_entities(company),
    }
    return build_master(sources, company, posts or {}, fake_id).frame


def row_of(frame: pd.DataFrame, person: str) -> pd.Series:
    found = frame[frame["leader_id"] == fake_id(name_key(person))]
    assert len(found) == 1, f"expected one row for the invented leader, found {len(found)}"
    return found.iloc[0]


ACME = {"Person_Name": "Olive Branch", "CompanyName": "Acme Robotics", "DomainName": "acmerobotics.com",
        "Gender": "1", "Current_Title": "CEO", "TotalEmployeeCount": "120"}
OTHER = {"Person_Name": "Quinn Reed", "CompanyName": "Borealis Foods", "DomainName": "borealis.in",
         "Gender": "0", "Current_Title": "Founder", "TotalEmployeeCount": "40"}


# --- ladder step 1: exact name key --------------------------------------------------------------------------------


def test_exact_name_key_is_matched_first_and_copies_person_and_firm_columns() -> None:
    frame = master(company_frame([ACME, OTHER]), sheets=[("Branch Olive", "Something Else")])

    row = row_of(frame, "Olive Branch")

    assert row["match_method"] == NAME_EXACT
    assert row["Gender"] == "1" and row["TotalEmployeeCount"] == "120"
    assert row["columns_scope"] == "person_and_firm"
    assert row["in_posts"] and row["in_company"]


def test_a_company_name_that_would_also_match_does_not_beat_the_name_step() -> None:
    other = {**OTHER, "CompanyName": "Acme Robotics"}
    frame = master(company_frame([ACME, other]), sheets=[("Quinn Reed", "Acme Robotics")])

    assert row_of(frame, "Quinn Reed")["match_method"] == NAME_EXACT


# --- ladder step 2: the existing loose rule, unchanged ------------------------------------------------------------


def test_loose_name_rule_matches_a_name_that_contains_the_other_name() -> None:
    frame = master(company_frame([ACME, OTHER]), sheets=[("Olive Mae Branch", "")])

    row = row_of(frame, "Olive Mae Branch")

    assert row["match_method"] == NAME_LOOSE
    assert row["Gender"] == "1"
    assert not row["in_company"]


# --- ladder step 3: company name, then domain ---------------------------------------------------------------------


def test_company_name_match_carries_firm_columns_but_not_the_other_persons_columns() -> None:
    frame = master(company_frame([ACME, OTHER]), roster=[("Zed Quill", "Acme Robotics")])

    row = row_of(frame, "Zed Quill")

    assert row["match_method"] == COMPANY_NAME
    assert row["TotalEmployeeCount"] == "120"
    assert row["Gender"] == "" and row["Current_Title"] == ""
    assert row["columns_scope"] == "firm_only"
    assert not row["in_company"]


def test_domain_match_is_tried_after_the_company_name_and_needs_one_firm_row() -> None:
    firm = {**ACME, "CompanyName": "A Wholly Different Legal Name", "DomainName": "https://www.acmerobotics.co.in/"}
    frame = master(company_frame([firm, OTHER]), roster=[("Zed Quill", "Acme Robotics")])

    row = row_of(frame, "Zed Quill")

    assert row["match_method"] == DOMAIN
    assert row["TotalEmployeeCount"] == "120"
    assert row["Gender"] == ""


def test_domain_match_compares_the_company_name_with_its_words_sorted_like_the_name_key() -> None:
    firm = {**ACME, "CompanyName": "Legal Name Pvt", "DomainName": "acmerobotics.com"}
    frame = master(company_frame([firm, OTHER]), roster=[("Zed Quill", "Robotics Acme")])

    assert row_of(frame, "Zed Quill")["match_method"] == DOMAIN


def test_domain_label_strips_scheme_www_path_and_the_country_suffix() -> None:
    assert domain_label("https://www.acmerobotics.co.in/about") == "acmerobotics"
    assert domain_label("Acme.COM") == "acme"
    assert domain_label("mail.acme.org") == "acme"
    assert domain_label("") == ""
    assert domain_label("-") == ""
    assert domain_label(".") == ""


# --- ambiguity is never resolved ----------------------------------------------------------------------------------


def test_a_company_shared_by_two_firm_rows_leaves_the_leader_ambiguous() -> None:
    twin = {**OTHER, "CompanyName": "Acme Robotics", "DomainName": "twin.com"}
    frame = master(company_frame([ACME, twin]), roster=[("Zed Quill", "Acme Robotics")])

    row = row_of(frame, "Zed Quill")

    assert row["match_method"] == AMBIGUOUS
    assert row["n_candidates"] == 2
    assert row["columns_scope"] == "none"
    assert row["TotalEmployeeCount"] == ""
    assert row["firm_row_claims"] == 0


def test_two_loose_name_candidates_stay_ambiguous_when_the_company_step_finds_nothing() -> None:
    first = {**ACME, "Person_Name": "Ravi Sharma", "CompanyName": "Alpha Works", "DomainName": "alpha.in"}
    second = {**OTHER, "Person_Name": "Ravi Kumar Sharma", "CompanyName": "Beta Works", "DomainName": "beta.in"}
    frame = master(company_frame([first, second]), sheets=[("Ravi Kumar Sharma Singh", "")])

    assert row_of(frame, "Ravi Kumar Sharma Singh")["match_method"] == AMBIGUOUS


def test_a_leader_with_no_company_and_no_name_match_is_none() -> None:
    frame = master(company_frame([ACME, OTHER]), sheets=[("Zed Quill", "")])

    row = row_of(frame, "Zed Quill")

    assert row["match_method"] == NONE
    assert row["columns_scope"] == "none"


# --- a firm row claimed twice is recorded -------------------------------------------------------------------------


def test_a_firm_row_reached_by_several_leaders_is_recorded_for_each_of_them() -> None:
    frame = master(
        company_frame([ACME, OTHER]),
        sheets=[("Zed Quill", "Acme Robotics")],
        roster=[("Yara Moss", "Acme Robotics")],
    )

    claims = {name: row_of(frame, name)["firm_row_claims"] for name in ("Zed Quill", "Yara Moss", "Olive Branch")}

    assert claims == {"Zed Quill": 3, "Yara Moss": 3, "Olive Branch": 3}
    assert row_of(frame, "Quinn Reed")["firm_row_claims"] == 1


def test_a_leader_without_a_firm_row_has_zero_claims() -> None:
    frame = master(company_frame([ACME]), sheets=[("Zed Quill", "")])

    assert row_of(frame, "Zed Quill")["firm_row_claims"] == 0


# --- leaders without posts stay; blanks never match blanks --------------------------------------------------------


def test_a_leader_with_no_posts_is_kept_with_zero_cells_and_post_counts_are_attached() -> None:
    frame = master(
        company_frame([ACME, OTHER]),
        sheets=[("Olive Branch", "")],
        roster=[("Zed Quill", "")],
        posts={name_key("Olive Branch"): 17},
    )

    assert row_of(frame, "Zed Quill")["raw_post_cells"] == 0
    assert not row_of(frame, "Zed Quill")["in_posts"]
    assert row_of(frame, "Olive Branch")["raw_post_cells"] == 17
    assert row_of(frame, "Quinn Reed")["raw_post_cells"] == 0
    assert len(frame) == 3


def test_blank_company_never_matches_a_blank_firm_name_or_a_blank_domain() -> None:
    nameless = {**OTHER, "Person_Name": "Pat Lowe", "CompanyName": "", "DomainName": ""}
    dotted = {**OTHER, "Person_Name": "Sam Hart", "CompanyName": ".", "DomainName": "-"}
    frame = master(company_frame([nameless, dotted]), sheets=[("Zed Quill", ""), ("Yara Moss", ".")])

    assert row_of(frame, "Zed Quill")["match_method"] == NONE
    assert row_of(frame, "Yara Moss")["match_method"] == NONE
    assert not row_of(frame, "Pat Lowe")["has_domain"]
    assert not row_of(frame, "Pat Lowe")["has_company_name"]
    assert not row_of(frame, "Sam Hart")["has_company_name"]
    assert not row_of(frame, "Sam Hart")["has_domain"]


def test_the_dot_and_dash_markers_are_blank_in_the_carried_columns() -> None:
    marked = {**ACME, "Gender": ".", "TotalEmployeeCount": "-"}
    frame = master(company_frame([marked]))

    row = row_of(frame, "Olive Branch")
    assert row["Gender"] == "" and row["TotalEmployeeCount"] == ""


# --- keys shared inside one source are retained without guessing --------------------------------------------------


def test_a_name_key_held_twice_inside_company_data_is_kept_as_separate_flagged_rows() -> None:
    twin_a = {**OTHER, "Person_Name": "Sam Hart"}
    twin_b = {**OTHER, "Person_Name": "Hart Sam", "CompanyName": "Gamma Co"}
    company = company_frame([ACME, twin_a, twin_b])
    sources = {
        SOURCE_SHEETS: (),
        SOURCE_ROSTER: (),
        SOURCE_SUMMARIES: (),
        SOURCE_COMPANY: company_entities(company),
    }

    result = build_master(sources, company, {}, fake_id)

    shared = result.frame[result.frame["company_key_shared"]]
    assert result.excluded_ambiguous_keys == 0
    assert len(result.frame) == 3
    assert len(shared) == 2
    assert shared["leader_id"].is_unique
    assert shared["in_company"].all()


# --- the output holds no names, links or keys ---------------------------------------------------------------------


def test_the_output_has_ids_flags_counts_and_whitelisted_columns_only() -> None:
    company = company_frame([ACME, OTHER])
    frame = master(company, sheets=[("Olive Branch", "Acme Robotics")], roster=[("Zed Quill", "Acme Robotics")])

    text = frame.to_csv(index=False).lower()

    for banned in (*KEY_COLUMNS, "LinkedIn_Profile_Link", "Website"):
        assert banned not in frame.columns
    for forbidden in ("olive", "branch", "quinn", "reed", "zed", "quill", "acme", "borealis", "acmerobotics"):
        assert forbidden not in text
    assert frame["leader_id"].is_unique


def test_universe_is_the_union_of_the_four_sources() -> None:
    frame = master(
        company_frame([ACME]),
        sheets=[("Sheet Only", "")],
        roster=[("Roster Only", "")],
        summaries=[("Summary Only", "")],
    )

    assert len(frame) == 4
    assert int(frame["in_summaries"].sum()) == 1


def test_a_missing_company_data_column_is_refused_not_ignored() -> None:
    company = company_frame([ACME]).drop(columns=[PERSON_COLUMNS[0]])
    sources = {SOURCE_SHEETS: (), SOURCE_ROSTER: (), SOURCE_SUMMARIES: (), SOURCE_COMPANY: company_entities(company)}

    with pytest.raises(ValueError, match="missing"):
        build_master(sources, company, {}, fake_id)


# --- report -------------------------------------------------------------------------------------------------------


def test_report_is_counts_only_hides_small_cells_and_shows_the_fifteen_post_column() -> None:
    people = [{**OTHER, "Person_Name": f"Person Num{i:02d}", "CompanyName": f"Firm {i:02d}",
               "DomainName": f"firm{i:02d}.in"} for i in range(30)]
    posts = {name_key(f"Person Num{i:02d}"): 20 for i in range(12)}
    frame = master(
        company_frame(people),
        sheets=[(f"Person Num{i:02d}", "") for i in range(12)] + [("Lone Sheet", "")],
        posts=posts,
    )

    report = render_report(frame, excluded_ambiguous_keys=2, settings=SETTINGS)

    assert "<5" in report
    assert "15+" in report
    assert "Lone Sheet" not in report and "Person Num" not in report
    assert "personality" not in report.lower()
    assert "relayed" in report.lower()


# --- run(): files in, the git-ignored table and the report out ----------------------------------------------------


def _write_inputs(root: Path) -> None:
    interim = root / "interim"
    interim.mkdir()
    pd.DataFrame(
        [{"leader": "Olive Branch", "company": "Acme Robotics", "workbook": "wb.xlsx", "sheet_idx": "0",
          "text_kind": "raw"}] * 3
        + [{"leader": "Zed Quill", "company": "Acme Robotics", "workbook": "wb.xlsx", "sheet_idx": "1",
            "text_kind": "raw"}]
    ).to_csv(interim / "harmonised_posts.csv", index=False)
    pd.DataFrame({"person_name": ["Yara Moss"], "company": [""]}).to_csv(interim / "roster.csv", index=False)
    company_frame([ACME, OTHER]).to_csv(interim / "company_data.csv", index=False)
    raw = root / "raw"
    raw.mkdir()
    (raw / "MANIFEST.sha256").write_text("", encoding="utf-8")
    (root / "thresholds.yaml").write_text(
        "min_posts_per_leader: 15\neda_disclosure_min_leaders: 5\neda_model_min_leaders: 20\neda_size_bands: 4\n",
        encoding="utf-8",
    )


def _paths(root: Path) -> dict[str, Path]:
    return {
        "raw_dir": root / "raw",
        "interim_dir": root / "interim",
        "out_path": root / "interim" / "leader_master.csv",
        "report_path": root / "reports" / "leader_master.md",
        "thresholds_path": root / "thresholds.yaml",
    }


def test_run_writes_the_table_and_a_counts_only_report(tmp_path: Path) -> None:
    _write_inputs(tmp_path)

    code = run(**_paths(tmp_path), id_of=fake_id)

    table = pd.read_csv(tmp_path / "interim" / "leader_master.csv", dtype=str, keep_default_na=False)
    report = (tmp_path / "reports" / "leader_master.md").read_text(encoding="utf-8")
    assert code == 0
    assert len(table) == 4
    assert table.loc[table["leader_id"] == fake_id(name_key("Yara Moss")), "raw_post_cells"].iloc[0] == "0"
    assert "Olive" not in report and "Acme" not in report


def test_run_fails_without_writing_when_company_data_is_missing(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    (tmp_path / "interim" / "company_data.csv").unlink()

    code = run(**_paths(tmp_path), id_of=fake_id)

    assert code == 1
    assert not (tmp_path / "interim" / "leader_master.csv").exists()
    assert not (tmp_path / "reports" / "leader_master.md").exists()


def test_run_fails_clearly_when_the_id_key_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FP15_ID_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    _write_inputs(tmp_path)

    code = run(**_paths(tmp_path))

    assert code == 1
    assert not (tmp_path / "interim" / "leader_master.csv").exists()
