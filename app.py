# app.py
import os
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory, url_for
from validator.validator import validate_sql_text
from pdf_generator.reportlab_pdf import generate_pdf
from datetime import datetime
import uuid

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
ALLOWED_EXT = {'.txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='static')

@app.route('/')
def index():
    # serves static/index.html
    return send_from_directory('static', 'index.html')

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXT

def sanitize_filename(name):
    """Sanitize string for safe filename usage."""
    import re
    # Replace non-alphanumeric (except . and _) with underscores
    s = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    # Avoid double underscores
    s = re.sub(r'_+', '_', s)
    return s.strip('_')

@app.route('/validate', methods=['POST'])
def validate_route():
    # 🔥 WAF BYPASS: Decode Base64 content
    encoded_content = request.form.get('sql_content_b64')
    if encoded_content:
        import base64
        try:
            content = base64.b64decode(encoded_content).decode('utf-8', errors='ignore')
        except Exception as e:
            return jsonify({"error": f"Failed to decode content: {str(e)}"}), 400
    else:
        # Fallback to file upload if B64 is missing
        if 'sqlFile' not in request.files:
            return jsonify({"error":"No file part 'sqlFile'"}), 400
        file = request.files['sqlFile']
        if file.filename == '':
            return jsonify({"error":"No selected file"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error":"Only .txt files allowed"}), 400
        content = file.read().decode('utf-8', errors='ignore')

    if not content.strip():
        return jsonify({"error": "File is empty"}), 400

    # parse form fields
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    team = request.form.get('team', '')
    cr_number = request.form.get('cr_number', '')
    backup_toggle = request.form.get('backup_toggle', 'false').lower() == 'true'

    # run validator
    results, summary = validate_sql_text(
        content,
        checks_path="config/checks.json",
        backup_toggle=backup_toggle
    )

    # -----------------------------
    # 🔥 CUSTOM FILENAME FORMAT
    # <CR>_<YYYYMMDD>_<HHMMSS>.pdf
    # -----------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_cr = sanitize_filename(cr_number) if cr_number else "REPORT"
    out_filename = f"{clean_cr}_{timestamp}.pdf"
    out_path = os.path.join(OUTPUT_FOLDER, out_filename)

    # metadata for PDF header
    run_meta = {
        "name": name,
        "email": email,
        "team": team,
        "cr_number": cr_number,
        "generated_at": datetime.utcnow().isoformat()
    }

    # generate PDF
    try:
        generate_pdf(run_meta, results, summary, out_path)
    except Exception as e:
        print(f"ERROR: PDF generation failed: {str(e)}")
        # We still return results, but without pdf_url
        return jsonify({
            "results": results,
            "summary": summary,
            "pdf_url": None,
            "pdf_error": str(e)
        })

    # return downloadable URL
    pdf_url = url_for('download_file', filename=out_filename)

    return jsonify({
        "results": results,
        "summary": summary,
        "pdf_url": pdf_url
    })

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(path):
        return "Not found", 404
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
