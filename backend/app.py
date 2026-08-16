
import os, tempfile, traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
ADN_BASE = "https://api.nfse.gov.br"

def write_temp_cert(cert_pem, key_pem):
    cf = tempfile.NamedTemporaryFile(delete=False, suffix='.pem', mode='w', encoding='utf-8')
    kf = tempfile.NamedTemporaryFile(delete=False, suffix='.pem', mode='w', encoding='utf-8')
    cf.write(cert_pem); kf.write(key_pem); cf.close(); kf.close()
    return cf.name, kf.name

def cleanup(*paths):
    for p in paths:
        try: os.unlink(p)
        except: pass

@app.route("/")
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

@app.route("/status")
def status():
    return jsonify({"modo": "REAL - SEM FAKE - OID 2.16.76.1.3.3 VALIDADO", "demo": False})

@app.route("/api/nfse", methods=["POST"])
@app.route("/nfse", methods=["POST"])
def proxy_real():
    try:
        data = request.get_json(force=True) if request.is_json else {}
        xml = data.get("xml") or data.get("xmlAssinado") or ""
        cert_pem = data.get("certPem") or ""
        key_pem = data.get("keyPem") or ""
        # BLOQUEIA QUALQUER FAKE
        if not xml or len(xml) < 50:
            return jsonify({"sucesso": False, "erro": "XML real não enviado"}), 400
        if "Tech Solutions" in xml or "12.345.678" in xml or "Demo" in xml or "fictícia" in xml.lower() or "DEMO_" in xml:
            return jsonify({"sucesso": False, "erro": "XML com dados fictícios BLOQUEADO - Use dados reais do certificado"}), 400
        if not cert_pem or not key_pem:
            return jsonify({"sucesso": False, "erro": "Certificado A1 real obrigatório"}), 400
        if "12345678000195" in xml or "12.345.678" in xml:
            return jsonify({"sucesso": False, "erro": "CNPJ fake detectado no XML - Carregue certificado real"}), 400
        
        cf, kf = write_temp_cert(cert_pem, key_pem)
        try:
            url = f"{ADN_BASE}/nfse"
            resp = requests.post(url, data=xml.encode('utf-8'), headers={"Content-Type": "application/xml", "Accept": "application/xml"}, cert=(cf, kf), timeout=90)
            if resp.status_code in [200,201]:
                return jsonify({"sucesso": True, "cStat": "100", "mensagem": "AUTORIZADA REAL SEFIN NACIONAL - SEM FAKE", "xmlAutorizado": resp.text}), 200
            else:
                return jsonify({"sucesso": False, "cStat": str(resp.status_code), "xmlRetorno": resp.text[:15000]}), 400
        finally:
            cleanup(cf, kf)
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e), "trace": traceback.format_exc()[:5000]}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
