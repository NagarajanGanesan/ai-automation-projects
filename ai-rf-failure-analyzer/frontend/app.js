/* Frontend logic for the AI Robot Framework Failure Analyzer.
 * Plain ES modules-free JavaScript so it can be served as a static file with
 * no build step. Talks to the FastAPI backend under /api.
 */
(function () {
  "use strict";

  const API = "/api";
  let currentResultId = null;

  const $ = (id) => document.getElementById(id);

  // ---- helpers ------------------------------------------------------------
  async function request(path, options) {
    const res = await fetch(API + path, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = (data && data.error && data.error.message) || res.statusText;
      throw new Error(msg);
    }
    return data;
  }

  function setStatus(el, message, kind) {
    el.textContent = message || "";
    el.className = "status" + (kind ? " " + kind : "");
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function statCard(label, value) {
    return (
      '<div class="stat"><div class="value">' +
      escapeHtml(value) +
      '</div><div class="label">' +
      escapeHtml(label) +
      "</div></div>"
    );
  }

  function insightItem(title, meta) {
    return (
      '<li><div class="title">' +
      escapeHtml(title) +
      '</div><div class="meta">' +
      escapeHtml(meta) +
      "</div></li>"
    );
  }

  // ---- rendering ----------------------------------------------------------
  function renderSummary(parsed) {
    const passRate = Math.round((parsed.pass_rate || 0) * 1000) / 10;
    $("stats-grid").innerHTML =
      statCard("Total", parsed.total_tests) +
      statCard("Passed", parsed.passed) +
      statCard("Failed", parsed.failed) +
      statCard("Skipped", parsed.skipped) +
      statCard("Pass rate", passRate + "%") +
      statCard("Duration", (parsed.total_duration_seconds || 0) + "s");

    const total = Math.max(parsed.total_tests || 0, 1);
    $("pass-bar").style.width = (100 * (parsed.passed || 0)) / total + "%";
    $("fail-bar").style.width = (100 * (parsed.failed || 0)) / total + "%";
    $("skip-bar").style.width = (100 * (parsed.skipped || 0)) / total + "%";

    const tbody = $("failed-table").querySelector("tbody");
    tbody.innerHTML =
      (parsed.failed_tests || [])
        .map(
          (t) =>
            "<tr><td>" +
            escapeHtml(t.suite) +
            "</td><td>" +
            escapeHtml(t.name) +
            "</td><td>" +
            escapeHtml(t.failing_keyword || "—") +
            "</td><td>" +
            escapeHtml(t.message || "") +
            "</td></tr>"
        )
        .join("") ||
      '<tr><td colspan="4">No failed tests 🎉</td></tr>';
  }

  function renderAnalysis(analysis) {
    const risk = (analysis.overall_risk || "medium").toLowerCase();
    const badge = $("risk-badge");
    badge.textContent = risk + " risk";
    badge.className = "badge " + risk;
    $("exec-summary").textContent = analysis.executive_summary || "";

    $("root-causes").innerHTML =
      (analysis.root_causes || [])
        .map((c) =>
          insightItem(
            c.title,
            c.explanation +
              (c.affected_tests && c.affected_tests.length
                ? " • Tests: " + c.affected_tests.join(", ")
                : "")
          )
        )
        .join("") || "<li>No root causes identified.</li>";

    $("flaky-patterns").innerHTML =
      (analysis.flaky_patterns || [])
        .map((p) => insightItem(p.description, p.evidence))
        .join("") || "<li>No flaky patterns detected.</li>";

    $("risk-areas").innerHTML =
      (analysis.risk_areas || [])
        .map((r) =>
          insightItem(r.area + " [" + r.severity + "]", r.reason)
        )
        .join("") || "<li>No elevated risk areas.</li>";

    $("recommendations").innerHTML =
      (analysis.recommendations || [])
        .map((r) =>
          insightItem(r.title + " [" + r.priority + "]", r.detail)
        )
        .join("") || "<li>No recommendations.</li>";

    $("analysis").classList.remove("hidden");
  }

  // ---- actions ------------------------------------------------------------
  async function handleUpload(event) {
    event.preventDefault();
    const input = $("file-input");
    if (!input.files.length) {
      setStatus($("upload-status"), "Please choose a file first.", "error");
      return;
    }
    const form = new FormData();
    form.append("file", input.files[0]);

    $("upload-btn").disabled = true;
    setStatus($("upload-status"), "Uploading and parsing…");
    try {
      const data = await request("/upload", { method: "POST", body: form });
      currentResultId = data.result_id;
      renderSummary(data.parsed);
      $("results").classList.remove("hidden");
      $("analysis").classList.add("hidden");
      setStatus($("analyze-status"), "");
      setStatus($("upload-status"), "Parsed successfully.", "success");
    } catch (err) {
      setStatus($("upload-status"), err.message, "error");
    } finally {
      $("upload-btn").disabled = false;
    }
  }

  async function handleAnalyze() {
    if (!currentResultId) return;
    $("analyze-btn").disabled = true;
    setStatus($("analyze-status"), "Analyzing… this can take a moment.");
    try {
      const data = await request("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result_id: currentResultId }),
      });
      renderAnalysis(data.analysis);
      const tag = data.analysis.generated_by_ai ? "AI" : "rule-based";
      setStatus($("analyze-status"), "Analysis complete (" + tag + ").", "success");
    } catch (err) {
      setStatus($("analyze-status"), err.message, "error");
    } finally {
      $("analyze-btn").disabled = false;
    }
  }

  async function loadHealth() {
    try {
      const data = await request("/health", {});
      $("ai-status").textContent =
        "v" +
        data.version +
        " • AI provider: " +
        (data.ai_enabled ? "Claude (live)" : "rule-based fallback");
    } catch (err) {
      $("ai-status").textContent = "backend unavailable";
    }
  }

  // ---- wiring -------------------------------------------------------------
  function init() {
    $("upload-form").addEventListener("submit", handleUpload);
    $("analyze-btn").addEventListener("click", handleAnalyze);

    const input = $("file-input");
    const drop = document.querySelector(".file-drop");
    input.addEventListener("change", () => {
      $("file-label").textContent = input.files.length
        ? input.files[0].name
        : "Choose output.xml (or drag & drop)";
    });
    ["dragover", "dragenter"].forEach((evt) =>
      drop.addEventListener(evt, (e) => {
        e.preventDefault();
        drop.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((evt) =>
      drop.addEventListener(evt, (e) => {
        e.preventDefault();
        drop.classList.remove("dragover");
      })
    );
    drop.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event("change"));
      }
    });

    loadHealth();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
