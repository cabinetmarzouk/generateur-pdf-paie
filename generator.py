
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import requests
import io
import os

app = Flask(__name__)

PAGE_ORDER = [
    "etat_civil_1", "etat_civil_2", "emploi_1", "emploi_2", "emploi_3",
    "conges", "allegement", "entree_sortie", "prevoyance", "salaire", "alertes"
]

MAPS = {
    "etat_civil_1": {
        "fields": [
            {"key":"civilite", "type":"text", "x":142, "y":54, "size":16},
            {"key":"nom", "type":"text", "x":245, "y":54, "size":16},
            {"key":"prenoms", "type":"text", "x":140, "y":78, "size":16},
            {"key":"numero_voie", "type":"text", "x":148, "y":129, "size":16},
            {"key":"voie", "type":"text", "x":316, "y":129, "size":16},
            # Ajustement : Code postal et Ville (Distributeur et Commune)
            {"key":"distributeur_code_postal", "type":"text", "x":30, "y":172, "size":16},
            {"key":"distributeur_ville", "type":"text", "x":146, "y":172, "size":16},
            {"key":"commune_code_postal", "type":"text", "x":30, "y":198, "size":16},
            {"key":"commune_ville", "type":"text", "x":146, "y":198, "size":16},
            {"key":"date_naissance", "type":"text", "x":158, "y":306, "size":16},
            {"key":"secu", "type":"text", "x":158, "y":331, "size":16},
            {"key":"commune_naissance", "type":"text", "x":288, "y":349, "size":16},
            {"key":"sexe_homme", "type":"cross", "x":83, "y":505, "size":15},
            {"key":"sexe_femme", "type":"cross", "x":83, "y":530, "size":15}
        ]
    },
    "etat_civil_2": {
        "fields": [
            {"key":"prudhomme_college_salarie", "type":"cross", "x":246, "y":330, "size":15},
            {"key":"prudhomme_lieu_commune", "type":"cross", "x":367, "y":456, "size":15}
        ]
    },
    "emploi_1": {
        "fields": [
            {"key":"emploi_exerce", "type":"text", "x":242, "y":48, "size":16},
            {"key":"code_insee_emploi", "type":"text", "x":242, "y":205, "size":16},
            # Le "0" est maintenant placé dans la case Indice (bas de page)
            {"key":"indice_emploi", "type":"text", "x":145, "y":678, "size":16},
            {"key":"pourcentage_activite", "type":"text", "x":242, "y":431, "size":16}
        ]
    },
    "emploi_2": {
        "fields": [
            {"key":"temps_complet", "type":"cross", "x":195, "y":111, "size":15},
            {"key":"temps_partiel", "type":"cross", "x":326, "y":111, "size":15},
            {"key":"date_anciennete", "type":"text", "x":271, "y":228, "size":16}
        ]
    },
    "emploi_3": {
        "fields": [
            {"key":"contrat_cdi", "type":"cross", "x":142, "y":64, "size":15},
            {"key":"contrat_cdd", "type":"cross", "x":142, "y":89, "size":15},
            {"key":"cdd_motif", "type":"text", "x":327, "y":166, "size":15},
            {"key":"categorie_normal", "type":"cross", "x":757, "y":239, "size":15},
            {
                "key":"ref_contrat_note",
                "type":"boxed_text",
                "x":280, "y":500, "w":450, "h":50, "size":14,
                "text":"Si déjà embauché dans le passé voir EDDY"
            }
        ]
    },
    "conges": {
        "fields": [
            {"key":"note_conges", "type":"boxed_text", "x":160, "y":45, "w":250, "h":36, "size":12, "text":"non si gérant ou président"}
        ]
    },
    "allegement": {
        "fields": [
            {"key":"note_allegement", "type":"boxed_text", "x":172, "y":350, "w":250, "h":36, "size":12, "text":"non si gérant ou président"}
        ]
    },
    "entree_sortie": {
        "fields": [
            {"key":"date_entree", "type":"text", "x":34, "y":78, "size":16},
            {"key":"date_sortie", "type":"text", "x":494, "y":78, "size":16},
            {"key":"motif_sortie", "type":"text", "x":828, "y":78, "size":16}
        ]
    },
    "prevoyance": {
        "fields": [
            {"key":"date_premiere_entree", "type":"text", "x":503, "y":83, "size":16}
        ]
    },
    "salaire": {
        "fields": [
            {"key":"periodicite_mois", "type":"cross", "x":672, "y":112, "size":15},
            {"key":"salaire_mensuel", "type":"text", "x":233, "y":223, "size":16},
            {"key":"heures_par_periode", "type":"text", "x":419, "y":223, "size":16},
            {"key":"heures_a_majorer", "type":"text", "x":409, "y":258, "size":16},
            {"key":"total_salaire", "type":"text", "x":165, "y":286, "size":16},
            {"key":"application_smic", "type":"cross", "x":37, "y":337, "size":15},
            {"key":"note_forfaitaire", "type":"boxed_text", "x":140, "y":78, "w":400, "h":38, "size":16, "text":"mettre forfaitaire si gérants ou présidents"}
        ]
    },
    "alertes": {
        "fields": [
            {"key":"date_alerte", "type":"text", "x":31, "y":78, "size":16},
            {"key":"texte_alerte", "type":"text", "x":140, "y":78, "size":16}
        ]
    }
}

def drive_download_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def download_image(file_id):
    r = requests.get(drive_download_url(file_id), timeout=60)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def get_font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

def draw_text(draw, text, x, y, size):
    if text: draw.text((x, y), str(text), fill=(0, 0, 0), font=get_font(size))

def draw_cross(draw, x, y, size):
    h = max(4, size // 2)
    draw.line((x-h, y-h, x+h, y+h), fill=(0,0,0), width=2)
    draw.line((x+h, y-h, x-h, y+h), fill=(0,0,0), width=2)

def draw_boxed_text(draw, text, x, y, w, h, size):
    draw.rectangle([x, y, x + w, y + h], fill="white", outline="black", width=1)
    draw.text((x + 6, y + 8), str(text), fill=(0, 0, 0), font=get_font(size))

def enrich_page_data(page_name, page_data):
    d = dict(page_data or {})
    if page_name == "emploi_3":
        if str(d.get("contrat", "")).upper() == "CDD":
            d["cdd_motif"] = "31"
    return d

def render_page(page_name, template_id, page_data):
    img = download_image(template_id)
    draw = ImageDraw.Draw(img)
    for f in MAPS.get(page_name, {}).get("fields", []):
        val = page_data.get(f["key"])
        if f["type"] == "text": draw_text(draw, val, f["x"], f["y"], f.get("size", 16))
        elif f["type"] == "cross" and val: draw_cross(draw, f["x"], f["y"], f.get("size", 15))
        elif f["type"] == "boxed_text": draw_boxed_text(draw, val or f.get("text"), f["x"], f["y"], f["w"], f["h"], f.get("size", 12))
    return img

@app.route("/generate", methods=["POST"])
def generate():
    try:
        payload = request.get_json(force=True)
        templates, pages = payload.get("templates", {}), payload.get("pages", {})
        rendered = []
        for name in PAGE_ORDER:
            tid = templates.get(name)
            if tid: rendered.append(render_page(name, tid, enrich_page_data(name, pages.get(name, {}))))
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        for img in rendered:
            w, h = img.size
            c.setPageSize((w, h))
            tmp = io.BytesIO()
            img.save(tmp, format="PNG")
            c.drawImage(ImageReader(tmp), 0, 0, width=w, height=h)
            c.showPage()
        c.save()
        buffer.seek(0)
        return send_file(buffer, mimetype="application/pdf", download_name="dossier_paie.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
