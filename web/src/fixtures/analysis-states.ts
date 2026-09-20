// web/src/fixtures/analysis-states.ts
export const FIXTURES = {
    empty: { state: "empty" },
    valid_pdf: { state: "input_ready", fileType: "pdf", name: "resume.pdf" },
    valid_text: { state: "input_ready", fileType: "text", length: 1500 },
    invalid_type: { state: "error", code: "invalid_type", message: "Only PDF and text files are supported." },
    oversize_file: { state: "error", code: "payload_too_large", message: "File exceeds 5MB limit." },
    empty_text: { state: "error", code: "empty_text", message: "Input text cannot be empty." },
    analyzing: { state: "analyzing", progress: 50 },
    success: {
        state: "complete",
        schema_version: "2.0",
        analysis_id: "test-001",
        created_at: "2026-09-20T10:00:00Z",
        status: "complete",
        input_mode: "pdf",
        model: { id: "ensemble-v1", calibrated: true },
        policy_version: "1.0",
        score: 0.1,
        score_kind: "calibrated_probability",
        decision: "no_signals_detected",
        reason_codes: [],
        coverage: { pages_total: 1, pages_analyzed: 1, limitations: [] },
        modules: {
            a: { status: "ok", score: 0.1, reason: null, findings: [] },
            b: { status: "ok", score: 0.0, reason: null, findings: [] },
            c: { status: "ok", score: 0.1, reason: null, findings: [] }
        },
        findings: [],
        timings_ms: { total: 120 }
    },
    review_recommended: {
        state: "complete",
        schema_version: "2.0",
        analysis_id: "test-002",
        created_at: "2026-09-20T10:00:00Z",
        status: "complete",
        input_mode: "pdf",
        model: { id: "ensemble-v1", calibrated: true },
        policy_version: "1.0",
        decision: "review_recommended",
        reason_codes: ["invisible_text"],
        coverage: { pages_total: 1, pages_analyzed: 1, limitations: [] },
        score: 0.95,
        score_kind: "calibrated_probability",
        modules: {
            a: { status: "ok", score: 0.9, reason: null, findings: [] },
            b: { status: "ok", score: 1.0, reason: null, findings: [] },
            c: { status: "ok", score: 0.9, reason: null, findings: [] }
        },
        findings: [
            { id: "f1", detector: "b", category: "invisible_text", severity: "high", explanation: "Hidden text detected" }
        ],
        timings_ms: { total: 150 }
    },
    partial: { state: "partial", decision: "review_recommended", coverage: { pages_analyzed: 1, pages_total: 5 } },
    unsupported: { state: "unscorable", decision: "insufficient_evidence", reason_codes: ["image_only_pdf"] },
    server_unavailable: { state: "error", code: "server_unavailable", message: "Service is temporarily unreachable." },
    timeout: { state: "error", code: "timeout", message: "Analysis took too long." },
    cancelled: { state: "cancelled" },
    export_ready: { state: "complete", exportable: true },
    no_findings: { state: "complete", decision: "no_signals_detected", findings: [] },
    long_findings: { state: "complete", decision: "review_recommended", findings: Array(50).fill({ id: "f", severity: "low" }) },
    lab_unavailable: { state: "lab_unavailable", message: "Lab environment is offline." }
};
