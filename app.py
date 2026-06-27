import os
import tempfile
import requests
from flask import Flask, request, jsonify
from docling.document_converter import DocumentConverter

app = Flask(__name__)

# Initialize converter once at startup
converter = DocumentConverter()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "docling"})

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()

    required = ['job_id', 'niche', 'source', 'pdf_url']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    pdf_url = data['pdf_url']

    # Download PDF
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch PDF: {str(e)}"}), 500

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    # Extract with Docling
    try:
        result = converter.convert(tmp_path)
        markdown_output = result.document.export_to_markdown()

        # Extract tables
        tables = []
        for table in result.document.tables:
            try:
                rows = [[cell.text for cell in row.cells] for row in table.data.grid]
                tables.append({
                    "page": table.prov[0].page_no if table.prov else None,
                    "rows": rows
                })
            except Exception:
                pass

    except Exception as e:
        os.unlink(tmp_path)
        return jsonify({"error": f"Docling extraction failed: {str(e)}"}), 500

    os.unlink(tmp_path)

    return jsonify({
        "job_id": data['job_id'],
        "status": "success",
        "niche": data['niche'],
        "source": data['source'],
        "source_url": pdf_url,
        "title": data.get('title', ''),
        "published_date": data.get('published_date', ''),
        "markdown": markdown_output,
        "tables": tables,
        "extraction_engine": "docling"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
