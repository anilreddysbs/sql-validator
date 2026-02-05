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

@app.route('/validate', methods=['POST'])
def validate_route():
    content = ""
    # Check if a file is uploaded
    if 'sqlFile' in request.files and request.files['sqlFile'].filename != '':
        f = request.files['sqlFile']
        # Read raw bytes
        raw_data = f.read()
        try:
           # Try to see if it's base64 encoded (WAF bypass)
           # The frontend might send it as a file with base64 content
           # Or, if we change frontend to send 'sql_text_base64' field...
           # Actually, standard file upload is binary. 
           # If WAF blocks the CONTENT of the file, we must encode it on CLIENT side before form append.
           # But file input is read-only in JS. We can't modify the File object content easily.
           # Better approach: Read file in JS, base64 encode it, and send as a text field 'sql_content_base64'.
           pass
        except:
           pass
        content = raw_data.decode('utf-8', errors='ignore')
    
    # Check if alternative base64 field exists (WAF Bypass)
    if 'sql_content_base64' in request.form:
        import base64
        try:
            content = base64.b64decode(request.form['sql_content_base64']).decode('utf-8', errors='ignore')
        except Exception as e:
            return jsonify({"error": f"Base64 decode failed: {str(e)}"}), 400
    
    if not content.strip():
        return jsonify({"error": "File is empty or no content provided"}), 400

    if not content.strip():
        return jsonify({"error": "File is empty"}), 400

    # parse form fields
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    team = request.form.get('team', '')
    cr_number = request.form.get('cr_number', '')
    # run validator (Static Only)
    results, summary = validate_sql_text(
        content,
        checks_path="config/checks.json",
        skip_ai=True
    )

    # -----------------------------
    # 🔥 CUSTOM FILENAME FORMAT
    # <CR>_<YYYYMMDD>_<HHMMSS>.pdf
    # -----------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{cr_number}_{timestamp}.pdf"
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
    generate_pdf(run_meta, results, summary, out_path)

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

@app.route('/analyze_ai', methods=['POST'])
def analyze_ai_route():
    content = ""
    if 'sql_content_base64' in request.form:
        import base64
        try:
            content = base64.b64decode(request.form['sql_content_base64']).decode('utf-8', errors='ignore')
        except Exception as e:
            return jsonify({"error": f"Base64 decode failed: {str(e)}"}), 400
    elif 'sqlFile' in request.files:
         f = request.files['sqlFile']
         content = f.read().decode('utf-8', errors='ignore')
    
    if not content.strip():
        return jsonify({"error": "File is empty"}), 400

    # Run FULL validation (AI Enabled)
    results, summary = validate_sql_text(
        content,
        checks_path="config/checks.json",
        skip_ai=False
    )

    # -----------------------------
    # 🔥 RE-GENERATE PDF (WITH AI)
    # -----------------------------
    # Get metadata again (request.form is available from the same FormData)
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    team = request.form.get('team', '')
    cr_number = request.form.get('cr_number', '')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Add _AI suffix to distinguish
    out_filename = f"{cr_number}_{timestamp}_AI.pdf"
    out_path = os.path.join(OUTPUT_FOLDER, out_filename)

    run_meta = {
        "name": name,
        "email": email,
        "team": team,
        "cr_number": cr_number,
        "generated_at": datetime.utcnow().isoformat()
    }

    generate_pdf(run_meta, results, summary, out_path)
    pdf_url = url_for('download_file', filename=out_filename)

    return jsonify({
        "results": results, 
        "summary": summary,
        "pdf_url": pdf_url
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
