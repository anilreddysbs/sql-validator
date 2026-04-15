import base64
import binascii
import os
import re
from datetime import datetime

from flask import Flask, abort, jsonify, request, send_from_directory, url_for

from pdf_generator.reportlab_pdf import generate_pdf
from validator.validator import validate_sql_text

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
ALLOWED_EXT = {".txt"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.after_request
def apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Upload exceeds the 2 MB limit."}), 413


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXT


def sanitize_filename(name):
    s = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def decode_sql_content(encoded_content):
    try:
        raw_bytes = base64.b64decode(encoded_content, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Failed to decode content: {exc}") from exc

    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Decoded content exceeds the 2 MB limit.")

    return raw_bytes.decode("utf-8", errors="ignore")


@app.route("/validate", methods=["POST"])
def validate_route():
    encoded_content = request.form.get("sql_content_b64")
    if encoded_content:
        try:
            content = decode_sql_content(encoded_content)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    else:
        if "sqlFile" not in request.files:
            return jsonify({"error": "No file part 'sqlFile'"}), 400
        file = request.files["sqlFile"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Only .txt files allowed"}), 400
        content = file.read().decode("utf-8", errors="ignore")

    if not content.strip():
        return jsonify({"error": "File is empty"}), 400

    name = request.form.get("name", "")
    email = request.form.get("email", "")
    team = request.form.get("team", "")
    cr_number = request.form.get("cr_number", "")
    backup_toggle = request.form.get("backup_toggle", "false").lower() == "true"

    results, summary = validate_sql_text(
        content,
        checks_path="config/checks.json",
        backup_toggle=backup_toggle,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_cr = sanitize_filename(cr_number) if cr_number else "REPORT"
    out_filename = f"{clean_cr}_{timestamp}.pdf"
    out_path = os.path.join(OUTPUT_FOLDER, out_filename)

    run_meta = {
        "name": name,
        "email": email,
        "team": team,
        "cr_number": cr_number,
        "generated_at": datetime.utcnow().isoformat(),
    }

    try:
        generate_pdf(run_meta, results, summary, out_path)
    except Exception as exc:
        print(f"ERROR: PDF generation failed: {exc}")
        return jsonify(
            {
                "results": results,
                "summary": summary,
                "pdf_url": None,
                "pdf_error": str(exc),
            }
        )

    pdf_url = url_for("download_file", filename=out_filename)
    return jsonify({"results": results, "summary": summary, "pdf_url": pdf_url})


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    if not filename.lower().endswith(".pdf"):
        abort(404)
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    debug_enabled = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug_enabled, host="0.0.0.0", port=5000)
