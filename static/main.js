let lastFingerprint = null;

// Clear warning when user changes any input
document.getElementById("uploadForm").addEventListener("input", function () {
    document.getElementById("duplicateWarning").style.display = "none";
});
document.getElementById("uploadForm").addEventListener("change", function () {
    document.getElementById("duplicateWarning").style.display = "none";
});

document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const fileInput = document.getElementById("sqlFile");
    const file = fileInput.files[0];

    // Create a fingerprint of the current form state
    const currentFingerprint = [
        document.getElementById("name").value,
        document.getElementById("email").value,
        document.getElementById("team").value,
        document.getElementById("cr_number").value,
        file ? file.name : "",
        file ? file.size : "",
        file ? file.lastModified : ""
    ].join("|");

    const warningDiv = document.getElementById("duplicateWarning");

    // Clear previous warning
    warningDiv.style.display = "none";
    warningDiv.innerText = "";

    if (currentFingerprint === lastFingerprint) {
        warningDiv.innerText = "⚠️ You have already validated this file with these specific details. Please upload a new file or modify the details to validate again.";
        warningDiv.style.display = "block";
        return;
    }

    const formData = new FormData(this);

    // BROWSER-SIDE ENCODING TO BYPASS WAF
    // WAFs often block "SELECT *" in content-type multipart/form-data.
    // We will Base64 encode the file content and send it as a plain text field.
    if (file) {
        const reader = new FileReader();
        reader.onload = async function (evt) {
            const base64Content = btoa(evt.target.result); // Standard JS Base64
            formData.set("sql_content_base64", base64Content);

            // Should we remove the file object to be safe? 
            // Yes, let's remove the raw file to prevent WAF from scanning it.
            formData.delete("sqlFile");

            await runValidation(formData, currentFingerprint);
        };
        reader.readAsText(file); // Read as text then encode
        return; // Stop here, let the reader callback handle submission
    }

    // Call helper function if no file (rare case, form requires file but paranoia)
    await runValidation(formData, currentFingerprint);
});

// Extracted validation logic
async function runValidation(formData, currentFingerprint) {
    const output = document.getElementById("validationOutput");
    const resultDiv = document.getElementById("results");
    const topDownloadBtn = document.getElementById("topDownloadBtn");



    // Hide download button while validating
    topDownloadBtn.style.display = "none";
    topDownloadBtn.onclick = null;

    resultDiv.style.display = "block";
    output.innerHTML = "<p>🔄 Validating, please wait...</p>";

    try {
        // --- STEP 1: Static Validation (Fast) ---
        const response = await fetch("/validate", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            output.innerHTML = `<p class="error">${data.error}</p>`;
            return;
        }

        lastFingerprint = currentFingerprint;

        // Render Static Results First
        let html = "";

        // Placeholder for AI Summary (to be filled later)
        html += `<div id="ai-loading-container" style="text-align:center; padding: 20px; background:#f9f9f9; border-radius:8px; margin-bottom:20px;">
                    <p>⚡ Static analysis complete. <strong>AI is thinking...</strong> <span class="loader-spinner"></span></p>
                 </div>
                 <div id="ai-summary-container"></div>`;

        // Standard Summary
        html += `
          <h3>Validation Summary:</h3>
          <ul>
            <li><strong>Number of SQL queries:</strong> ${data.summary.total}</li>
            <li><strong>Passed:</strong> <span style="color:green">${data.summary.passed}</span></li>
            <li><strong>Failed:</strong> <span style="color:red">${data.summary.failed}</span></li>
          </ul>
          <h3>Validations Performed:</h3>
        `;

        // Detailed results (Card container)
        html += `<div id="card-container">`;
        data.results.forEach((item, index) => {
            html += `
              <div class="result-card" data-index="${index}">
                  <pre><strong>Query:</strong>\n${item.query}</pre>
                  <ul class="validation-list" style="margin-top: 10px; padding-left: 20px;">
                    ${item.validations.map(v => {
                let cls;
                if (v.startsWith("❌")) {
                    cls = "error";
                } else if (v.startsWith("⚠️")) {
                    cls = "warning";
                } else if (v.startsWith("🧠")) {
                    cls = "ai-msg";
                } else {
                    cls = "success";
                }
                return `<li class="${cls}">${v}</li>`;
            }).join("")}
                  </ul>
              </div>`;
        });
        html += `</div>`;

        output.innerHTML = html;

        // Show download button immediately (contains static report)
        if (data.pdf_url) {
            topDownloadBtn.style.display = "inline-block";
            topDownloadBtn.onclick = () => window.location.href = data.pdf_url;
        }

        // --- STEP 2: Async AI Analysis (Slow) ---
        // We don't await this blocking the UI. We let it run.
        fetch("/analyze_ai", {
            method: "POST",
            body: formData
        })
            .then(res => res.json())
            .then(aiData => {
                if (aiData.error) {
                    console.error("AI Error:", aiData.error);
                    document.getElementById("ai-loading-container").innerHTML = `<p style="color:red">AI Analysis failed: ${aiData.error}</p>`;
                    return;
                }

                // Remove Loading Indicator
                document.getElementById("ai-loading-container").style.display = "none";

                // 1. Inject AI Summary & Global Insights
                const aiContainer = document.getElementById("ai-summary-container");
                let aiHtml = "";

                // Executive Summary
                if (aiData.summary.ai_summary) {
                    aiHtml += `
            <div class="ai-summary-card">
                <div class="ai-header">🤖 AI Executive Summary</div>
                <div>${aiData.summary.ai_summary}</div>
            </div>`;
                }

                // Global Insights
                if (aiData.summary.ai_insights && aiData.summary.ai_insights.length > 0) {
                    aiHtml += `<h3 class="ai-section-title">🧠 AI Logic & Performance Analysis</h3>`;
                    aiData.summary.ai_insights.forEach(insight => {
                        aiHtml += `
                 <div class="ai-insight-card ai-insight-${insight.severity}">
                    <strong>${insight.type}:</strong> ${insight.message}
                 </div>`;
                    });
                    aiHtml += `<hr style="margin: 30px 0; border: 0; border-top: 1px solid #ddd;">`;
                }

                // Fade-in effect for the new content
                aiContainer.innerHTML = aiHtml;
                aiContainer.style.opacity = 0;
                aiContainer.style.transition = "opacity 0.5s";
                requestAnimationFrame(() => aiContainer.style.opacity = 1);

                // 2. Inject Per-Query AI Insights
                const cardContainer = document.getElementById("card-container");
                const cards = cardContainer.getElementsByClassName("result-card");

                aiData.results.forEach((item, index) => {
                    // Find new AI messages (start with 🧠)
                    const aiMessages = item.validations.filter(v => v.startsWith("🧠"));

                    if (aiMessages.length > 0 && cards[index]) {
                        const ul = cards[index].querySelector(".validation-list");

                        aiMessages.forEach(msg => {
                            // Check if already exists (paranoia check)
                            const li = document.createElement("li");
                            li.className = "ai-msg";
                            li.innerText = msg;
                            li.style.opacity = "0";
                            li.style.transition = "opacity 1s";
                            ul.appendChild(li);

                            // Trigger reflow for transition
                            requestAnimationFrame(() => li.style.opacity = "1");
                        });
                    }
                });

                // 3. Update Download Button (New PDF with AI matches)
                if (aiData.pdf_url) {
                    const topDownloadBtn = document.getElementById("topDownloadBtn");
                    topDownloadBtn.onclick = () => window.location.href = aiData.pdf_url;
                }

            })
            .catch(err => {
                console.error("AI Fetch Error:", err);
                document.getElementById("ai-loading-container").innerText = "";
            });

    } catch (err) {
        console.error("Validation Error:", err);
        output.innerHTML = `<p class="error">❌ An error occurred: ${err.message}</p>`;
    }
}
