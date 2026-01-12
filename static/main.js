document.getElementById("uploadForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const formData = new FormData(this);

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
            return;
        }

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
              <pre><strong>Query:</strong>\n${item.query}</pre>
              <ul>
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
              <hr>
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
