import json, sys

CONTRACT = "contracts/origin_mesh.py"
A = "https://news.example.org/original-report"
B = "https://wire.example.net/syndicated-report"
C = "https://lab.example.com/independent-measurement"
TEXT_A = "The city transport office published a primary count of 128 electric buses entering service in April. The report identifies fleet records and depot logs as its direct evidence."
TEXT_B = "According to the city transport office report, 128 electric buses entered service in April. This article repeats the fleet figure from that original report."
TEXT_C = "Our independent depot survey counted 126 electric buses in active service during April. Inspectors used separate charging records and physical observations."


def result(forged=False):
    return {"sources": [
        {"index": 0, "source_id": "city-report", "relation": "ORIGINAL", "root_id": "city-report", "evidence_quote": "published a primary count of 128 electric buses entering service in April", "root_quote": "published a primary count of 128 electric buses entering service in April", "explanation": "This page presents the office records as its direct evidence."},
        {"index": 1, "source_id": "wire-copy", "relation": "DERIVED", "root_id": "city-report", "evidence_quote": "This article repeats the fleet figure from that original report", "root_quote": "published a primary count of 128 electric buses entering service in April", "explanation": "The wire explicitly attributes and repeats the city report."},
        {"index": 2, "source_id": "lab-survey", "relation": "ORIGINAL", "root_id": "lab-survey", "evidence_quote": "Our independent depot survey counted 126 electric buses", "root_quote": "Our independent depot survey counted 126 electric buses", "explanation": "The lab describes separate records and physical observations."},
    ]}


def create(contract, study_id="bus-count-roots"):
    study = contract.create_study(study_id, "Electric bus source roots", "At least two independently gathered sources support the reported electric bus deployment.", 2)
    contract.add_source(study, "city-report", "City transport report", A)
    contract.add_source(study, "wire-copy", "Regional wire article", B)
    contract.add_source(study, "lab-survey", "Independent depot survey", C)
    contract.seal_sources(study)
    return study


def consensus(contract, monkeypatch, comparator=None):
    module = sys.modules[contract.__class__.__module__]
    monkeypatch.setattr(module.gl.eq_principle, "strict_eq", lambda fn: fn())
    monkeypatch.setattr(module.gl.eq_principle, "prompt_comparative", comparator or (lambda fn, *_args, **_kwargs: fn()))


def mocks(vm, payload=None):
    vm.mock_web(A, {"method": "GET", "status": 200, "body": TEXT_A})
    vm.mock_web(B, {"method": "GET", "status": 200, "body": TEXT_B})
    vm.mock_web(C, {"method": "GET", "status": 200, "body": TEXT_C})
    vm.mock_llm("ORIGINMESH_PRODUCER", json.dumps(json.dumps(payload or result())))


def test_contract_loads(direct_deploy):
    assert direct_deploy(CONTRACT) is not None


def test_rejects_duplicate_ids_documents_and_unsafe_urls(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    contract.create_study("source-study", "Source study", "Determine whether the evidence has independent reporting roots.", 2)
    with direct_vm.expect_revert("already exists"):
        contract.create_study("source-study", "Source study", "Determine whether the evidence has independent reporting roots.", 2)
    with direct_vm.expect_revert("public HTTPS"):
        contract.add_source("source-study", "unsafe-source", "Unsafe source", "http://localhost/report")
    contract.add_source("source-study", "first-source", "First source", A)
    with direct_vm.expect_revert("Duplicate source document"):
        contract.add_source("source-study", "same-document", "Same document", A)


def test_owner_controls_draft_but_audit_and_finalization_are_permissionless(direct_vm, direct_deploy, direct_alice, monkeypatch):
    contract = direct_deploy(CONTRACT); direct_vm.sender = direct_alice; study = create(contract)
    direct_vm.sender = "0x3333333333333333333333333333333333333333"
    consensus(contract, monkeypatch); mocks(direct_vm)
    audit = contract.audit(study); direct_vm.clear_mocks()
    assert audit["outcome"] == "INDEPENDENT" and audit["independent_roots"] == 2
    final = contract.finalize(study)
    assert final["status"] == "FINAL" and len(final["final_receipt"]["receipt_sha256"]) == 64
    with direct_vm.expect_revert("Only an audited study"):
        contract.finalize(study)


def test_audit_binds_every_quote_root_and_receipt(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); study = create(contract); consensus(contract, monkeypatch); mocks(direct_vm)
    audit = contract.audit(study)
    assert audit["root_groups"] == [{"root_id": "city-report", "members": ["city-report", "wire-copy"]}, {"root_id": "lab-survey", "members": ["lab-survey"]}]
    assert len(audit["receipts"]) == 3 and all(len(item["sha256"]) == 64 for item in audit["receipts"])


def test_forged_quote_and_non_original_root_fail_closed(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); study = create(contract); consensus(contract, monkeypatch)
    forged = result(); forged["sources"][1]["evidence_quote"] = "A fabricated quotation absent from the page"
    mocks(direct_vm, forged)
    with direct_vm.expect_revert("Evidence quote"):
        contract.audit(study)

    direct_vm.clear_mocks()
    study2 = study
    bad_root = result(); bad_root["sources"][0]["relation"] = "DERIVED"; bad_root["sources"][0]["root_id"] = "lab-survey"; bad_root["sources"][0]["root_quote"] = "Our independent depot survey counted 126 electric buses"; bad_root["sources"][1]["root_id"] = "city-report"
    consensus(contract, monkeypatch); mocks(direct_vm, bad_root)
    with direct_vm.expect_revert("original root"):
        contract.audit(study2)


def test_validator_disagreement_and_unreadable_source_do_not_write_state(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); study = create(contract)
    def disagree(fn, *_args, **_kwargs):
        fn(); raise RuntimeError("validator disagreement")
    consensus(contract, monkeypatch, disagree); mocks(direct_vm)
    try:
        contract.audit(study)
        assert False, "unexpected audit success"
    except RuntimeError as error:
        assert "disagreement" in str(error)
    assert contract.get_study(study)["status"] == "READY"

    direct_vm.clear_mocks()
    study2 = create(contract, "bus-count-roots-two"); consensus(contract, monkeypatch)
    direct_vm.mock_web(A, {"method": "GET", "status": 200, "body": "too short"})
    direct_vm.mock_web(B, {"method": "GET", "status": 200, "body": TEXT_B})
    direct_vm.mock_web(C, {"method": "GET", "status": 200, "body": TEXT_C})
    with direct_vm.expect_revert("unavailable or unreadable"):
        contract.audit(study2)
