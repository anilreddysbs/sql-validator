let lastFingerprint = null;

function validationClass(message) {
    if (message.startsWith("FAIL") || message.startsWith("❌") || message.startsWith("âŒ")) {
        return "error";
    }
    if (message.startsWith("⚠️") || message.startsWith("âš ï¸")) {
        return "warning";
    }
    return "success";
}

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
    warningDiv.style.display = "none";
    warningDiv.innerText = "";

    if (currentFingerprint === lastFingerprint) {
        warningDiv.innerText = "You have already validated this file with these details. Upload a new file or change the details to validate again.";
        warningDiv.style.display = "block";
        return;
    }

    const formData = new FormData(this);

    if (file) {
        try {
            const base64Content = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    const bytes = new Uint8Array(reader.result);
                    let binary = "";
                    for (let i = 0; i < bytes.byteLength; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    resolve(btoa(binary));
                };
                reader.onerror = reject;
                reader.readAsArrayBuffer(file);
            });
            formData.append("sql_content_b64", base64Content);
            formData.delete("sqlFile");
        } catch (err) {
            console.error("Base64 encoding failed:", err);
        }
    }

    const resultDiv = document.getElementById("results");
    const output = document.getElementById("validationOutput");
    const topDownloadBtn = document.getElementById("topDownloadBtn");

    topDownloadBtn.style.display = "none";
    topDownloadBtn.onclick = null;

    resultDiv.style.display = "block";
    output.innerHTML = "<p>Validating, please wait...</p>";

    try {
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

        output.innerHTML = `
          <h3>Validation Summary:</h3>
          <ul>
            <li><strong>Number of SQL queries:</strong> ${data.summary.total}</li>
            <li><strong>Passed:</strong> <span style="color:green">${data.summary.passed}</span></li>
            <li><strong>Failed:</strong> <span style="color:red">${data.summary.failed}</span></li>
          </ul>
        `;

        if (data.summary.global_validations && data.summary.global_validations.length) {
            output.innerHTML += `
              <h3>File-Level Rules:</h3>
              <ul style="margin-top: 10px; padding-left: 20px;">
                ${data.summary.global_validations.map(msg => (
                    `<li class="${validationClass(msg)}">${msg}</li>`
                )).join("")}
              </ul>
            `;
        }

        if (data.summary.warnings && data.summary.warnings.length) {
            output.innerHTML += `
              <h3>Warnings:</h3>
              <ul style="margin-top: 10px; padding-left: 20px;">
                ${data.summary.warnings.map(item => (
                    `<li class="warning">Query ${item.query_index}: ${item.message}</li>`
                )).join("")}
              </ul>
            `;
        }

        output.innerHTML += "<h3>Validations Performed:</h3>";

        data.results.forEach(item => {
            output.innerHTML += `
              <div class="result-card">
                  <pre><strong>Query:</strong>\n${item.query}</pre>
                  <ul style="margin-top: 10px; padding-left: 20px;">
                    ${item.validations.map(v => (
                        `<li class="${validationClass(v)}">${v}</li>`
                    )).join("")}
                  </ul>
              </div>
            `;
        });

        if (data.pdf_url) {
            topDownloadBtn.style.display = "inline-block";
            topDownloadBtn.onclick = () => {
                window.open(data.pdf_url, "_blank");
            };
        } else if (data.pdf_error) {
            output.innerHTML += `<p class="error">Results validated, but PDF generation failed: ${data.pdf_error}</p>`;
        }
    } catch (err) {
        output.innerHTML = '<p class="error">An error occurred.</p>';
    }
});
