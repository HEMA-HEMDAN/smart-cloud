"""End-to-end integration test of the complete experiment lab workflow."""

from __future__ import annotations

import asyncio
import io
import uuid

import pandas as pd
import pytest
from app import app
from app.db.models import RunStatus
from httpx import ASGITransport, AsyncClient


@pytest.mark.integration
async def test_full_experiment_lab_workflow() -> None:
    """
    Test the full user workflow:
    Upload document -> Preview chunks -> Create experiment -> Execute A/B run ->
    Verify measurements, reuse counts, security probe -> Export CSV.
    """
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        # 1. Upload a document
        doc_content = (
            "Organization-Aware Demand-Driven Shared AI Intelligence.\n\n"
            "This research evaluates whether intermediate artifact reuse reduces preparation expenditure "
            "while maintaining answer accuracy and strict cross-consumer authorization isolation."
        )
        files = {"file": ("research_spec.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")}
        upload_resp = await client.post("/api/v1/documents/upload", files=files)
        assert upload_resp.status_code == 201, upload_resp.text
        doc_data = upload_resp.json()
        doc_id = doc_data["id"]
        assert doc_data["content_length_chars"] > 50

        # 2. Preview chunks
        preview_resp = await client.get(f"/api/v1/documents/{doc_id}/preview?chunk_size=150&chunk_overlap=20")
        assert preview_resp.status_code == 200
        preview_data = preview_resp.json()
        assert preview_data["total_chunks"] >= 1
        first_chunk_id = preview_data["chunks"][0]["chunk_id"]

        # 3. Create experiment configuration with 2 consumers, 2 repetitions
        exp_payload = {
            "name": f"test_e2e_lab_{uuid.uuid4().hex[:8]}",
            "description": "Integration test run",
            "provider_config_id": "00000000-0000-0000-0000-000000000000",
            "dataset_name": "research_spec.txt",
            "chunking_config": {"chunk_size": 150, "chunk_overlap": 20},
            "retrieval_config": {"top_k": 3},
            "workload_config": {
                "document_version_id": doc_id,
                "consumer_count": 2,
                "type": "high_reuse",
                "provider": "mock",
                "benchmark_questions": [
                    {
                        "question_id": "q1",
                        "question_text": "What does this research evaluate?",
                        "expected_answer": "intermediate artifact reuse",
                        "expected_chunk_ids": [first_chunk_id],
                    }
                ],
            },
            "random_seed": 42,
            "repetitions": 2,
        }
        create_resp = await client.post("/api/v1/experiments", json=exp_payload)
        assert create_resp.status_code == 201, create_resp.text
        exp_id = create_resp.json()["id"]

        # 4. Launch execution
        start_resp = await client.post(f"/api/v1/experiments/{exp_id}/start")
        assert start_resp.status_code in (200, 201), start_resp.text
        run_id = start_resp.json()["id"]

        # 5. Wait for background execution to complete (mock provider takes ~1 second)
        max_wait = 15
        waited = 0
        run_status = RunStatus.RUNNING
        while waited < max_wait:
            await asyncio.sleep(0.5)
            waited += 0.5
            run_check = await client.get(f"/api/v1/experiments/{exp_id}/runs/{run_id}")
            assert run_check.status_code == 200
            run_status = run_check.json()["status"]
            if run_status in (RunStatus.COMPLETED, RunStatus.FAILED):
                break

        assert run_status == RunStatus.COMPLETED

        # 6. Fetch and verify results summary
        results_resp = await client.get(f"/api/v1/results/{run_id}/results")
        assert results_resp.status_code == 200
        res = results_resp.json()
        assert res["status"] == RunStatus.COMPLETED

        # Total measurements: 2 consumers * 2 repetitions * 1 question * 2 strategies = 8 measurements
        assert res["total_measurements"] == 8

        # Strategy B preparations: 2 repetitions * 2 consumers = 4 events (2 first demands + 2 reuses)
        assert res["reuse_summary"]["reuses"] == 2
        assert res["reuse_summary"]["first_preparations"] == 2
        assert res["reuse_summary"]["reuse_rate"] == 0.5
        assert res["reuse_summary"]["avoided_preparations"] == 2

        # Security probe verification: 0 unauthorized chunk disclosures
        assert res["security_violations"] == 0

        # Quality evaluation verification: ground truth was provided, so recall and correctness are populated
        q_summary = res["quality_summary"]["per_strategy"]
        assert "independent" in q_summary
        assert "shared" in q_summary
        assert q_summary["shared"]["mean_recall_at_k"] is not None

        # 7. Test CSV export
        export_resp = await client.get(f"/api/v1/results/{run_id}/export?format=csv")
        assert export_resp.status_code == 200
        assert "text/csv" in export_resp.headers["content-type"]
        csv_df = pd.read_csv(io.StringIO(export_resp.text))
        assert len(csv_df) == 8
        assert "strategy" in csv_df.columns
        assert "total_duration_ms" in csv_df.columns
