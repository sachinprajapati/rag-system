import asyncio

from src.services.generation import _answer_exact_structured_lookup, generate_response
from src.services.retrieval import (
    _exact_structured_record_matches,
    aggregate_structured_records,
    average_structured_field,
    count_structured_records,
)
from src.utils.document_router import route_and_chunk_document


def test_csv_is_chunked_as_individual_records(tmp_path):
    csv_file = tmp_path / "market_area_Dedection.csv"
    csv_file.write_text(
        "tower,flat,owner,flat_size,Deduction\n"
        "17,1101,Needs The Super Market,5400,13500\n"
        "17,1115,Vijay Sales,0,0\n"
    )

    file_type, chunks, _ = route_and_chunk_document(csv_file)

    assert file_type == "csv"
    assert len(chunks) == 2
    assert chunks[0]["chunking_strategy"] == "csv_rows"
    assert chunks[0]["row_data"] == {
        "tower": "17", "flat": "1101", "owner": "Needs The Super Market",
        "flat_size": "5400", "deduction": "13500",
    }
    assert "1115" not in chunks[0]["text"]


def test_exact_tower_and_flat_match_and_answer(monkeypatch):
    record = {
        "chunking_strategy": "csv_rows",
        "tenant_id": "default",
        "row_data": {"tower": "17", "flat": "1101", "deduction": "13500"},
        "text": "tower: 17\nflat: 1101\nDeduction: 13500",
        "file_name": "market_area_Dedection.csv",
    }

    class Manager:
        documents = [record]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())
    matches = _exact_structured_record_matches("what is the deduction tower 17 and flat 1101?", "default")

    assert matches == [{
        "rank": 1,
        "score": 1.0,
        "search_method": "exact_structured_record",
        "exact_match_fields": ["tower", "flat"],
        **record,
    }]
    assert _answer_exact_structured_lookup("what is the deduction tower 17 and flat 1101?", matches) == (
        "The deduction for tower 17, flat 1101 is 13500."
    )


def test_deduction_query_does_not_select_flat_size():
    document = {
        "search_method": "exact_structured_record",
        "exact_match_fields": ["tower", "flat"],
        "row_data": {
            "tower": "17", "flat": "1101", "flat_size": "5400", "deduction": "13500",
        },
    }

    answer = _answer_exact_structured_lookup(
        "what is the deduction amount of tower 17 and flat 1101?", [document]
    )

    assert answer == "The deduction for tower 17, flat 1101 is 13500."


def test_exact_csv_matching_uses_any_uploaded_schema(monkeypatch):
    record = {
        "chunking_strategy": "csv_rows",
        "tenant_id": "default",
        "row_data": {"building": "North", "unit": "A102", "maintenance_cost": "900"},
    }

    class Manager:
        documents = [record]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())
    matches = _exact_structured_record_matches(
        "what is the maintenance cost for building North and unit A102?", "default"
    )

    assert matches[0]["exact_match_fields"] == ["building", "unit"]


def test_count_query_counts_all_matching_csv_rows_not_top_k(monkeypatch):
    records = [
        {
            "tenant_id": "default",
            "file_name": "market_area_Dedection.csv",
            "row_data": {"tower": "17", "flat": str(flat)},
        }
        for flat in range(1, 52)
    ] + [{
        "tenant_id": "default",
        "file_name": "market_area_Dedection.csv",
        "row_data": {"tower": "18", "flat": "1"},
    }]

    class Manager:
        documents = records

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    count = count_structured_records("how many records are there of tower 17?", "default")
    result = asyncio.run(generate_response("how many records are there of tower 17?", top_k=5, tenant_id="default"))

    assert count["count"] == 51
    assert result["answer"] == "There are 51 records matching tower 17."
    assert len(result["retrieved_documents"]) == 5


def test_count_query_respects_tenant_boundaries(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "tenant-a", "row_data": {"tower": "17"}},
            {"tenant_id": "tenant-b", "row_data": {"tower": "17"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    assert count_structured_records("count of records for tower 17", "tenant-a")["count"] == 1


def test_count_query_intersects_multiple_filters(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "default", "row_data": {"tower": "17", "flat": "1101"}},
            {"tenant_id": "default", "row_data": {"tower": "17", "flat": "1102"}},
            {"tenant_id": "default", "row_data": {"tower": "18", "flat": "1101"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    result = count_structured_records("how many records for tower 17 and flat 1101?", "default")

    assert result["count"] == 1


def test_count_query_applies_numeric_deduction_filter(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "default", "row_data": {"tower": "17", "deduction": "0"}},
            {"tenant_id": "default", "row_data": {"tower": "17", "deduction": "1999"}},
            {"tenant_id": "default", "row_data": {"tower": "17", "deduction": "2000"}},
            {"tenant_id": "default", "row_data": {"tower": "17", "deduction": "2500"}},
            {"tenant_id": "default", "row_data": {"tower": "18", "deduction": "1000"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    query = "count the records of tower 17 where Deduction is less then 2000"
    count = count_structured_records(query, "default")
    result = asyncio.run(generate_response(query, tenant_id="default"))

    assert count["count"] == 2
    assert result["answer"] == (
        "There are 2 records matching tower 17 and deduction less than 2000."
    )


def test_count_query_filters_rows_with_a_missing_named_field(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "default", "row_data": {"name": "Asha", "phone_number": "9876543210"}},
            {"tenant_id": "default", "row_data": {"name": "Bilal", "phone_number": ""}},
            {"tenant_id": "default", "row_data": {"name": "Chen", "phone_number": "N/A"}},
            {"tenant_id": "default", "row_data": {"name": "Divya", "phone_number": "null"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    query = "give me count of records where phone number is missing"
    count = count_structured_records(query, "default")
    result = asyncio.run(generate_response(query, tenant_id="default"))

    assert count["count"] == 3
    assert count["filter_descriptions"] == ["phone number is missing"]
    assert result["answer"] == "There are 3 records matching phone number is missing."


def test_count_query_reports_zero_when_no_named_values_are_missing(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "default", "row_data": {"phone_number": "9876543210"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    query = "count records where phone number is missing"
    assert count_structured_records(query, "default")["count"] == 0
    result = asyncio.run(generate_response(query, tenant_id="default"))
    assert result["answer"] == "There are 0 records matching phone number is missing."


def test_count_grouping_uses_the_requested_schema_field(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "default", "row_data": {"flat_size": "5400", "deduction": "100"}},
            {"tenant_id": "default", "row_data": {"flat_size": "0", "deduction": "200"}},
            {"tenant_id": "default", "row_data": {"flat_size": "5400", "deduction": "300"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    query = "give me count of flat_size grouping"
    aggregate = aggregate_structured_records(query, "default")
    result = asyncio.run(generate_response(query, tenant_id="default"))

    assert [(group["key"], group["value"]) for group in aggregate["groups"]] == [("0", 1), ("5400", 2)]
    assert result["answer"] == "Counts are grouped by flat size in the table below."
    assert result["table"] == {
        "title": "Count by Flat Size",
        "columns": ["Flat Size", "Count"],
        "rows": [["0", "1"], ["5400", "2"]],
    }


def test_sum_grouped_by_field(monkeypatch):
    class Manager:
        documents = [
            {"tenant_id": "default", "row_data": {"tower": "17", "deduction": "100"}},
            {"tenant_id": "default", "row_data": {"tower": "17", "deduction": "200"}},
            {"tenant_id": "default", "row_data": {"tower": "18", "deduction": "50"}},
        ]

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    result = asyncio.run(generate_response("sum deduction by tower", tenant_id="default"))

    assert result["answer"] == "The sum is grouped by tower in the table below."


def test_average_query_uses_all_matching_rows_not_top_k(monkeypatch):
    records = [
        {
            "tenant_id": "default",
            "file_name": "market_area_Dedection.csv",
            "row_data": {"tower": "17", "deduction": str(value)},
        }
        for value in range(1, 52)
    ] + [{
        "tenant_id": "default",
        "file_name": "market_area_Dedection.csv",
        "row_data": {"tower": "18", "deduction": "1000"},
    }]

    class Manager:
        documents = records

    monkeypatch.setattr("src.services.retrieval.get_faiss_manager", lambda: Manager())

    aggregate = average_structured_field("average deduction value of tower 17", "default")
    result = asyncio.run(generate_response("average deduction value of tower 17", top_k=5, tenant_id="default"))

    assert aggregate["average"] == 26
    assert aggregate["record_count"] == 51
    assert result["answer"] == "The average deduction is 26, calculated from 51 matching records."
    assert len(result["retrieved_documents"]) == 5
