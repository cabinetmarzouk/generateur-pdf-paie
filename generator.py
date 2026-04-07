from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import requests
import io
import os
import textwrap

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
            {"key":"indice_emploi", "type":"text", "x":242, "y":258, "size":16},
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
            {"key":"cdd_motif", "type":"text", "x":332, "y":76, "size":16},
            {"key":"categorie_normal", "type":"cross", "x":757, "y":239, "size":15},
            {"key":"ref_contrat_note", "type":"multiline_text", "x":145, "y":470, "size":14, "max_width":260, "line_spacing":4}
        ]
    },

    "conges": {
        "fields": [
            {"key":"note_conges", "type":"multiline_text", "x":162, "y":62, "size":13, "max_width":220, "line_spacing":3}
        ]
    },

    "allegement": {
        "fields": [
            {"key":"note_allegement", "type":"multiline_text", "x":168, "y":206, "size":13, "max_width":240, "line_spacing":3}
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


def draw_multiline_text(draw, text, x, y, size, max_width=250, line_spacing=4):
    if text is None or text == "":
        return

    font = get_font(size)
    words = str(text).split()
    if not words:
        return

    lines = []
    current = words[0]

    for word in words[1:]:
        test_line = current + " " + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = word

    lines.append(current)

    current_y = y
    for line in lines:
        draw.text((x, current_y), line, fill=(0, 0, 0), font=font)
        current_y += size + line_spacing


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
        elif ftype == "multiline_text":
            draw_multiline_text(
                draw,
                value,
                x,
                y,
                size,
                field.get("max_width", 250),
                field.get("line_spacing", 4)
            )
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


def normalize_text(value):
    return str(value or "").strip()


def normalize_lower(value):
    return normalize_text(value).lower()


def normalize_upper(value):
    return normalize_text(value).upper()


def to_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def decimal_string(value):
    try:
        return f"{float(value):.2f}".replace(".", ",")
    except Exception:
        return ""


def heures_mensuelles(heures_hebdo):
    return round(to_float(heures_hebdo) * 4.3333333, 2)


def split_adresse(adresse):
    txt = normalize_text(adresse)
    if not txt:
        return {"numero_voie": "", "voie": ""}

    parts = txt.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return {"numero_voie": parts[0], "voie": parts[1]}
    return {"numero_voie": "", "voie": txt}


def detect_categorie(page_data):
    categorie = normalize_lower(page_data.get("categorie_salarie") or page_data.get("categorie") or "")
    emploi = normalize_lower(page_data.get("emploi_exerce") or page_data.get("emploi") or "")

    if "cadre" in categorie or "cadre" in emploi or "gérant" in emploi or "gerant" in emploi:
        return "cadre"
    if "etam" in categorie or "etam" in emploi:
        return "etam"
    return "ouvrier"


def is_batiment(page_data):
    convention = normalize_lower(page_data.get("convention_collective") or "")
    ape = normalize_text(page_data.get("ape") or "")
    return (
        ape.startswith("41")
        or ape.startswith("43")
        or "btp" in convention
        or "bâtiment" in convention
        or "batiment" in convention
        or "1596" in convention
        or "1597" in convention
    )


def compute_code_insee_emploi(page_data):
    categorie = detect_categorie(page_data)

    if is_batiment(page_data):
        if categorie == "cadre":
            return "220"
        if categorie == "etam":
            return "241"
        return "243"

    if categorie == "cadre":
        return "221"
    return "240"


def compute_indice_emploi(page_data):
    categorie = detect_categorie(page_data)
    if categorie == "cadre":
        return "2"
    if categorie == "etam":
        return "1"
    return "0"


def compute_pourcentage_activite(page_data):
    heures_hebdo = to_float(page_data.get("heures"))
    heures_mois = heures_mensuelles(heures_hebdo)
    base = 151.67

    if heures_mois >= base or heures_mois <= 0:
        return ""

    pct = round((heures_mois / base) * 100, 2)
    return decimal_string(pct)


def enrich_page_data(page_name, page_data):
    data = dict(page_data or {})

    if page_name == "etat_civil_1":
        adresse = split_adresse(data.get("adresseSal") or data.get("adresse") or "")
        cp = normalize_text(data.get("codePostal") or data.get("code_postal") or "")
        ville = normalize_upper(data.get("ville") or data.get("commune") or "")

        data["numero_voie"] = data.get("numero_voie") or adresse["numero_voie"]
        data["voie"] = data.get("voie") or adresse["voie"]

        data["distributeur_code_postal"] = data.get("distributeur_code_postal") or cp
        data["distributeur_ville"] = data.get("distributeur_ville") or ville
        data["commune_code_postal"] = data.get("commune_code_postal") or cp
        data["commune_ville"] = data.get("commune_ville") or ville

    elif page_name == "emploi_1":
        if not normalize_text(data.get("code_insee_emploi")):
            data["code_insee_emploi"] = compute_code_insee_emploi(data)

        if not normalize_text(data.get("indice_emploi")):
            data["indice_emploi"] = compute_indice_emploi(data)

        if not normalize_text(data.get("pourcentage_activite")):
            data["pourcentage_activite"] = compute_pourcentage_activite(data)

    elif page_name == "emploi_3":
        contrat = normalize_upper(data.get("contrat"))
        if contrat == "CDD":
            data["cdd_motif"] = "31"
        else:
            data["cdd_motif"] = ""

        if not normalize_text(data.get("ref_contrat_note")):
            data["ref_contrat_note"] = "Si SALARIE DEJA EMBAUCHE DANS LE PASSE VOIR EDDY3"

    elif page_name == "conges":
        if not normalize_text(data.get("note_conges")):
            data["note_conges"] = "non si gérant ou président"

    elif page_name == "allegement":
        if not normalize_text(data.get("note_allegement")):
            data["note_allegement"] = "non si gérant ou président"

    elif page_name == "entree_sortie":
        contrat = normalize_upper(data.get("contrat"))
        if contrat == "CDD":
            data["motif_sortie"] = "31"

    elif page_name == "salaire":
        heures_hebdo = to_float(data.get("heures"))
        heures_mois = heures_mensuelles(heures_hebdo)
        base = 151.67
        surplus = round(max(0, heures_mois - base), 2)

        if heures_mois > base:
            data["heures_par_periode"] = decimal_string(base)
            data["heures_a_majorer"] = decimal_string(surplus)
        else:
            if not normalize_text(data.get("heures_par_periode")):
                data["heures_par_periode"] = decimal_string(heures_mois)
            if not normalize_text(data.get("heures_a_majorer")):
                data["heures_a_majorer"] = ""

    return data


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
            page_data = enrich_page_data(page_name, page_data)
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
