from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import requests
import io
import os

app = Flask(__name__)

PAGE_ORDER = [
    "etat_civil_1",
    "etat_civil_2",
    "emploi_1",
    "emploi_2",
    "emploi_3",
    "conges",
    "allegement",
    "entree_sortie",
    "prevoyance",
    "salaire",
    "alertes"
]

MAPS = {
    "etat_civil_1": {
        "fields": [
            {"key":"civilite", "type":"text", "x":142, "y":54, "size":16},
            {"key":"nom", "type":"text", "x":245, "y":54, "size":16},
            {"key":"prenoms", "type":"text", "x":140, "y":78, "size":16},

            {"key":"numero_voie", "type":"text", "x":148, "y":129, "size":16},
            {"key":"voie", "type":"text", "x":316, "y":129, "size":16},

            {"key":"distributeur_code_postal", "type":"text", "x":146, "y":172, "size":16},
            {"key":"distributeur_ville", "type":"text", "x":216, "y":172, "size":16},

            {"key":"commune_code_postal", "type":"text", "x":146, "y":198, "size":16},
            {"key":"commune_ville", "type":"text", "x":216, "y":198, "size":16},

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
            {"key":"categorie_normal", "type":"cross", "x":757, "y":239, "size":15}
        ]
    },

    "conges": {
        "fields": []
    },

    "allegement": {
        "fields": []
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
            {"key":"application_smic", "type":"cross", "x":37, "y":337, "size":15}
        ]
    },

    "alertes": {
        "fields": [
            {"key":"date_alerte", "type":"text", "x":31, "y":78, "size":16},
            {"key":"texte_alerte", "type":"text", "x":140, "y":78, "size":16}
        ]
    }
}


def drive_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def download_image(file_id: str) -> Image.Image:
    r = requests.get(drive_download_url(file_id), timeout=60)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def get_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def draw_text(draw, text, x, y, size):
    if text is None or text == "":
        return
    draw.text((x, y), str(text), fill=(0, 0, 0), font=get_font(size))


def draw_cross(draw, x, y, size):
    half = max(4, size // 2)
    draw.line((x - half, y - half, x + half, y + half), fill=(0, 0, 0), width=2)
    draw.line((x + half, y - half, x - half, y + half), fill=(0, 0, 0), width=2)


def render_page(page_name: str, template_id: str, page_data: dict) -> Image.Image:
    img = download_image(template_id)
    draw = ImageDraw.Draw(img)
    fields = MAPS.get(page_name, {}).get("fields", [])

    for field in fields:
        key = field["key"]
        ftype = field["type"]
        x = field["x"]
        y = field["y"]
        size = field.get("size", 16)
        value = page_data.get(key)

        if ftype == "text":
            draw_text(draw, value, x, y, size)
        elif ftype == "cross" and bool(value):
            draw_cross(draw, x, y, size)

    return img


def build_pdf(images):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)

    for img in images:
        w, h = img.size
        c.setPageSize((w, h))

        tmp = io.BytesIO()
        img.save(tmp, format="PNG")
        tmp.seek(0)

        reader = ImageReader(tmp)
        c.drawImage(reader, 0, 0, width=w, height=h)
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def home():
    return jsonify({"ok": True, "service": "generateur-pdf-paie"})


@app.route("/generate", methods=["POST"])
def generate():
    try:
        payload = request.get_json(force=True)
        templates = payload.get("templates", {})
        pages = payload.get("pages", {})

        rendered = []
        for page_name in PAGE_ORDER:
            template_id = templates.get(page_name)
            if not template_id:
                continue
            page_data = pages.get(page_name, {})
            rendered.append(render_page(page_name, template_id, page_data))

        if not rendered:
            return jsonify({"error": "Aucune page rendue"}), 400

        pdf = build_pdf(rendered)
        return send_file(
            pdf,
            mimetype="application/pdf",
            as_attachment=False,
            download_name="dossier_paie.pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
