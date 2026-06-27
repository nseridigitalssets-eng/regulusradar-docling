import os
import tempfile
import requests
from flask import Flask, request, jsonify
import pypdfium2 as pdfium

app = Flask(__name__)

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

    # Extract text with pypdfium2
    try:
        pdf = pdfium.PdfDocument(tmp_path)
        pages_text = []
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            pages_text.append(textpage.get_text_range())
        markdown_output = "\n\n".join(pages_text)
        page_count = len(pdf)
        pdf.close()
    except Exception as e:
        os.unlink(tmp_path)
        return jsonify({"error": f"PDF extraction failed: {str(e)}"}), 500

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
        "page_count": page_count,
        "tables": [],
        "extraction_engine": "pypdfium2"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
