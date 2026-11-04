import pytest

from opl_mcp import queries


def names(results):
    return [r["name"] for r in results]


class TestSearchLifters:
    def test_matches_every_disambiguated_lifter(self, con):
        results = queries.search_lifters(con, "john smith")
        assert sorted(names(results)) == ["John Smith #1", "John Smith #2"]

    def test_reports_base_name_and_meet_count(self, con):
        [result] = queries.search_lifters(con, "smith #1")
        assert result["base_name"] == "John Smith"
        assert result["meets"] == 2
        assert result["best_total_kg"] == 625.0
        assert result["last_meet"] == "2023-06-03"

    def test_suffix_token_matches_exact_number(self, con):
        assert names(queries.search_lifters(con, "John #2")) == ["John Smith #2"]

    def test_words_match_in_any_order(self, con):
        assert names(queries.search_lifters(con, "doe JANE")) == ["Jane Doe"]

    def test_wildcards_are_literal(self, con):
        assert queries.search_lifters(con, "%") == []
        assert queries.search_lifters(con, "_") == []

    def test_blank_query_returns_nothing(self, con):
        assert queries.search_lifters(con, "   ") == []

    def test_limit(self, con):
        assert len(queries.search_lifters(con, "o", limit=2)) == 2


class TestLifterHistory:
    def test_meets_in_date_order_with_attempts(self, con):
        history = queries.lifter_history(con, "john smith #1")
        assert history["found"] is True
        assert history["name"] == "John Smith #1"
        first, second = history["meets"]
        assert first["date"] == "2022-03-12"
        assert second["date"] == "2023-06-03"
        assert first["squat"] == {
            "attempts": [200.0, 210.0, -215.0],
            "best": 210.0,
            "fourth": None,
        }
        assert first["total_kg"] == 615.0
        assert first["tested"] is True
        assert first["weight_class_kg"] == "93"

    def test_disqualified_meet(self, con):
        [meet] = queries.lifter_history(con, "Erik Lund")["meets"]
        assert meet["place"] == "DQ"
        assert meet["total_kg"] is None
        assert meet["squat"] == {
            "attempts": [-180.0, -180.0, -180.0],
            "best": -180.0,
            "fourth": None,
        }
        assert meet["bench"] == {"attempts": [None, None, None], "best": None, "fourth": None}

    def test_unknown_name_suggests_candidates(self, con):
        history = queries.lifter_history(con, "John Smith")
        assert history["found"] is False
        assert sorted(names(history["candidates"])) == ["John Smith #1", "John Smith #2"]

    def test_fourth_attempt_is_kept_apart_from_the_three(self, con):
        [meet] = queries.lifter_history(con, "Tom Press")["meets"]
        assert meet["bench"] == {
            "attempts": [170.0, 175.0, 180.0],
            "best": 180.0,
            "fourth": 182.5,
        }

    def test_exact_name_wins_over_case_variant(self, con):
        history = queries.lifter_history(con, "Erik lund")
        assert history["name"] == "Erik lund"
        assert [m["event"] for m in history["meets"]] == ["D"]

    def test_case_insensitive_match_when_unique(self, con):
        assert queries.lifter_history(con, "JANE DOE")["name"] == "Jane Doe"

    def test_ambiguous_case_variants_list_both(self, con):
        history = queries.lifter_history(con, "ERIK LUND")
        assert history["found"] is False
        assert sorted(names(history["candidates"])) == ["Erik Lund", "Erik lund"]

    def test_wrong_suffix_still_suggests_candidates(self, con):
        history = queries.lifter_history(con, "Jane Doe #1")
        assert history["found"] is False
        assert names(history["candidates"]) == ["Jane Doe"]


class TestPercentileForTotal:
    def test_uses_each_lifters_best_total(self, con):
        result = queries.percentile_for_total(con, 377.5, sex="F", equipment="Raw")
        assert result["lifters"] == 3
        assert result["percentile"] == pytest.approx(50.0)

    def test_tested_filter(self, con):
        result = queries.percentile_for_total(con, 377.5, sex="F", tested=True)
        assert result["lifters"] == 2
        assert result["percentile"] == pytest.approx(25.0)

    def test_untested_filter(self, con):
        result = queries.percentile_for_total(con, 300, sex="F", tested=False)
        assert result["lifters"] == 1
        assert result["percentile"] == pytest.approx(100.0)

    def test_weight_class_and_event_filters(self, con):
        result = queries.percentile_for_total(con, 620, sex="M", weight_class="93")
        assert result["lifters"] == 1
        assert result["percentile"] == pytest.approx(0.0)
        bench = queries.percentile_for_total(con, 200, sex="M", event="B")
        assert bench["lifters"] == 1
        assert bench["percentile"] == pytest.approx(100.0)

    def test_reports_cohort_quantiles(self, con):
        result = queries.percentile_for_total(con, 377.5, sex="F")
        assert result["cohort_totals_kg"]["median"] == 377.5
        assert result["cohort_totals_kg"]["max"] == 400.0

    def test_empty_cohort(self, con):
        result = queries.percentile_for_total(con, 500, sex="Mx")
        assert result["lifters"] == 0
        assert result["percentile"] is None


class TestCompareLifters:
    def test_summarises_each_lifter(self, con):
        result = queries.compare_lifters(con, ["jane doe", "Anna Berg"])
        jane, anna = result["lifters"]
        assert jane["name"] == "Jane Doe"
        assert jane["meets"] == 2
        assert jane["best_squat_kg"] == 137.5
        assert jane["best_total_kg"] == 377.5
        assert jane["latest_bodyweight_kg"] == 62.8
        assert anna["best_dots"] == 450.2
        assert result["not_found"] == []

    def test_reports_unknown_names(self, con):
        result = queries.compare_lifters(con, ["Jane Doe", "Nobody Here"])
        assert names(result["lifters"]) == ["Jane Doe"]
        assert result["not_found"] == ["Nobody Here"]

    def test_equipment_filter(self, con):
        result = queries.compare_lifters(con, ["John Smith #1", "John Smith #2"], equipment="Raw")
        assert names(result["lifters"]) == ["John Smith #1"]
        assert result["not_found"] == ["John Smith #2"]

    def test_case_variants_stay_separate(self, con):
        result = queries.compare_lifters(con, ["Erik Lund", "Erik lund"])
        lund, lund_masters = result["lifters"]
        assert (lund["name"], lund["best_total_kg"]) == ("Erik Lund", None)
        assert (lund_masters["name"], lund_masters["best_total_kg"]) == ("Erik lund", 210.0)

    def test_case_insensitive_match_returns_stored_name(self, con):
        result = queries.compare_lifters(con, ["jane doe", "ERIK LUND"])
        assert names(result["lifters"]) == ["Jane Doe"]
        assert result["not_found"] == ["ERIK LUND"]
