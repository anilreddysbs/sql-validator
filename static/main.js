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

    // ... code continues ...


    const resultDiv = document.getElementById("results");
    const output = document.getElementById("validationOutput");
    const topDownloadBtn = document.getElementById("topDownloadBtn");

    // Hide download button while validating
    topDownloadBtn.style.display = "none";
    topDownloadBtn.onclick = null;

    resultDiv.style.display = "block";
    output.innerHTML = "<p>🔄 Validating, please wait...</p>";

    try {
        const response = await fetch("/validate", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            output.innerHTML = `<p class="error">${data.error}</p>`;
            // Do not update fingerprint on error, so they can try again if it was a transient error (though usually logic error)
            // Actually, if it's a validation error (like empty file), we might want to let them retry?
            // But if the server says "error", it implies invalid request. 
            // Better to NOT update fingerprint on error, so they can click again if needed (e.g. server glitch).
            return;
        }

        // Update fingerprint only on successful validation response
        lastFingerprint = currentFingerprint;

        // Summary
        output.innerHTML = `
          <h3>Validation Summary:</h3>
          <ul>
            <li><strong>Number of SQL queries:</strong> ${data.summary.total}</li>
            <li><strong>Passed:</strong> <span style="color:green">${data.summary.passed}</span></li>
            <li><strong>Failed:</strong> <span style="color:red">${data.summary.failed}</span></li>
          </ul>
          <h3>Validations Performed:</h3>
        `;

        // Detailed results
        data.results.forEach(item => {
            output.innerHTML += `
              <div class="result-card">
                  <pre><strong>Query:</strong>\n${item.query}</pre>
                  <ul style="margin-top: 10px; padding-left: 20px;">
                    ${item.validations.map(v => {
                let cls;
                if (v.startsWith("❌")) {
                    cls = "error";
                } else if (v.startsWith("⚠️")) {
                    cls = "warning";
                } else {
                    cls = "success";
                }
                return `<li class="${cls}">${v}</li>`;
            }).join("")}
                  </ul>
              </div>
            `;
        });

        // Enable PDF download button
        if (data.pdf_url) {
            topDownloadBtn.style.display = "inline-block";
            topDownloadBtn.onclick = () => window.open(data.pdf_url, "_blank");
        }

    } catch (err) {
        output.innerHTML = `<p class="error">❌ An error occurred.</p>`;
    }
});
