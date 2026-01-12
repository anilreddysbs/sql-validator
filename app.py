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
    if 'sqlFile' not in request.files:
        return jsonify({"error":"No file part 'sqlFile'"}), 400

    file = request.files['sqlFile']
    if file.filename == '':
        return jsonify({"error":"No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error":"Only .txt files allowed"}), 400

    content = file.read().decode('utf-8', errors='ignore')

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
