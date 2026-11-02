
"""
DATA_EXTRACTOR_ABSTRACT.py
==========================

Vía EXPERIMENTAL del pipeline, alternativa a `interpretar_abstracts2.py`:
en vez de partir de un abstract cacheado, lee directamente el texto de un
PDF (`pdfs/*.pdf`), aísla las secciones Abstract/Results, y le pide a
Gemini (API cruda, sin `instructor`/Pydantic) que extraiga observaciones.

Estado: menos madura que `interpretar_abstracts2.py`. El JSON de salida
solo trae `doi`, `pmid`, `abstract_source`, `pubmed_abstract` y
`observations` — no completa `Reference`, `Cluster` ni `Data_curator` a
nivel de archivo, así que esas columnas quedarán vacías al compilar con
`compilar_csv.py` (que ya maneja esto sin romperse, vía `defaults.get()`).
"""

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
ncbi_api_key = os.getenv("NCBI_API_KEY")  # opcional: sube el límite de requests/seg a PubMed

if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en .env")

PDF_DIR = Path("pdfs")           # carpeta con los PDFs a analizar
OUTPUT_DIR = Path("resultados")  # carpeta donde se guarda la salida de cada PDF

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# Límite de NCBI: 3 requests/seg sin API key, 10 requests/seg con ella.
PUBMED_DELAY = 0.11 if ncbi_api_key else 0.34

# Patrones de encabezados de sección típicos de un artículo científico.
SECTION_PATTERNS = {
    "abstract": r"abstract",
    "introduction": r"introduction",
    "methods": r"(materials?\s+and\s+methods|methods|experimental\s+procedures)",
    "results": r"results(\s+and\s+discussion)?",
    "discussion": r"discussion",
    "conclusion": r"conclusions?",
    "references": r"(references|literature\s+cited|bibliography|acknowledg(e)?ments?)",
}

# Solo matchea líneas que contienen *únicamente* el encabezado (como suelen
# aparecer los títulos de sección en un PDF), para evitar falsos positivos
# como "estos resultados sugieren..." dentro del cuerpo del texto.
_HEADER_RE = {
    nombre: re.compile(
        rf"(?im)^[ \t]{{0,10}}(?:[ivxlcdm\d]{{1,4}}[\.\)]\s*)?(?:{patron})[ \t]*[:.]?[ \t]*$",
    )
    for nombre, patron in SECTION_PATTERNS.items()
}


def extraer_texto_pdf(ruta: Path) -> str:
    """Extrae todo el texto de un PDF."""
    reader = PdfReader(str(ruta))
    paginas = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(paginas)


def doi_desde_nombre_archivo(ruta_pdf: Path):
    """Reconstruye el DOI a partir del nombre de archivo.

    Los PDFs se descargan con el '/' del DOI reemplazado por '_'
    (ver descargar_abstracts.py), p.ej. '10.1038_s41586-021-04158-y.pdf'
    corresponde al DOI '10.1038/s41586-021-04158-y'.
    """
    match = re.match(r"^(10\.\d{4,9})_(.+)$", ruta_pdf.stem)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def buscar_pmid_por_doi(doi: str):
    """Busca en PubMed el PMID correspondiente a un DOI."""
    params = {"db": "pubmed", "term": f"{doi}[AID]", "retmode": "json"}
    if ncbi_api_key:
        params["api_key"] = ncbi_api_key
    resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
    resp.raise_for_status()
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    return ids[0] if ids else None


def obtener_abstract_pubmed(pmid: str) -> str:
    """Descarga el abstract oficial de PubMed (XML) para un PMID dado."""
    params = {"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "xml"}
    if ncbi_api_key:
        params["api_key"] = ncbi_api_key
    resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=30)
    resp.raise_for_status()
    raiz = ET.fromstring(resp.content)

    partes = []
    for nodo in raiz.iter("AbstractText"):
        etiqueta = nodo.get("Label")
        texto = "".join(nodo.itertext()).strip()
        if not texto:
            continue
        partes.append(f"{etiqueta}: {texto}" if etiqueta else texto)
    return "\n".join(partes).strip()


def abstract_desde_pubmed(doi: str):
    """Devuelve (pmid, abstract) consultando PubMed por DOI, o (None, "") si falla."""
    if not doi:
        return None, ""
    try:
        pmid = buscar_pmid_por_doi(doi)
        time.sleep(PUBMED_DELAY)
        if not pmid:
            print(f"AVISO: no se encontró PMID en PubMed para DOI {doi}")
            return None, ""
        abstract = obtener_abstract_pubmed(pmid)
        time.sleep(PUBMED_DELAY)
        if not abstract:
            print(f"AVISO: PubMed no devolvió abstract para PMID {pmid} (DOI {doi})")
        return pmid, abstract
    except (requests.RequestException, ET.ParseError) as e:
        print(f"AVISO: no se pudo consultar PubMed para DOI {doi}: {e}")
        return None, ""


def limpiar_bloque_json(texto: str) -> str:
    """Quita el cercado ```json ... ``` que a veces agrega el modelo."""
    texto = texto.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", texto, re.DOTALL)
    return match.group(1) if match else texto


def encontrar_encabezados(texto: str):
    """Devuelve [(inicio, fin, nombre_sección), ...] ordenado por posición."""
    encabezados = []
    for nombre, patron in _HEADER_RE.items():
        match = patron.search(texto)
        if match:
            encabezados.append((match.start(), match.end(), nombre))
    encabezados.sort(key=lambda x: x[0])
    return encabezados


def extraer_abstract_y_resultados(texto: str):
    """Aísla el texto del Abstract y de la sección de Results."""
    encabezados = encontrar_encabezados(texto)

    def seccion(nombre):
        for i, (_, fin_encabezado, n) in enumerate(encabezados):
            if n == nombre:
                fin = encabezados[i + 1][0] if i + 1 < len(encabezados) else len(texto)
                return texto[fin_encabezado:fin].strip()
        return ""

    abstract = seccion("abstract")
    resultados = seccion("results")

    # Si no se detectó un encabezado "Abstract", se usa el inicio del
    # documento (hasta el primer encabezado encontrado) como respaldo.
    if not abstract:
        fin = encabezados[0][0] if encabezados else min(len(texto), 3000)
        abstract = texto[:fin].strip()

    return abstract, resultados


def construir_prompt(nombre_archivo: str, texto_relevante: str) -> str:
    return f"""
Extract developmental milestone observations from the scientific record below.
The record below contains only the Abstract and Results sections of the article "{nombre_archivo}".

Return only valid JSON, with this structure:
{{
  "observations": [
    {{
      "species": "string",
      "parameter": "string",
      "age_min": number or null,
      "age_max": number or null,
      "age_unit": "string or null",
      "source_text": "string"
    }}
  ]
}}

Rules:
- Create a separate observation for each species and distinct age estimate.
- Preserve the original age values and units.
- ED means embryonic day.
- GW means gestational week.
- Do not convert ages or infer missing values.
- Do not merge different estimates for the same species.
- The parameter is any developmental milestone explicitly described (e.g. marker expression onset, growth peak, cell generation window, differentiation stage).
- Include only observations explicitly supported by the record.

Scientific record:
{texto_relevante}
"""


def main():
    client = genai.Client(api_key=api_key)

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"No se encontraron PDFs en la carpeta '{PDF_DIR}'")

    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"PDFs encontrados: {len(pdfs)}")

    for ruta_pdf in pdfs:
        print(f"\n--- Procesando: {ruta_pdf.name} ---")
        try:
            texto = extraer_texto_pdf(ruta_pdf)
        except Exception as e:
            print(f"ERROR al leer {ruta_pdf.name}: {e}")
            continue

        if not texto.strip():
            print(f"OMITIDO: {ruta_pdf.name} no tiene texto extraíble (¿PDF escaneado o vacío?)")
            continue

        abstract_pdf, resultados = extraer_abstract_y_resultados(texto)

        # Se prioriza el abstract oficial de PubMed (más confiable que el
        # extraído del PDF); si no se encuentra, se cae al abstract del PDF.
        doi = doi_desde_nombre_archivo(ruta_pdf)
        pmid, abstract_pubmed = abstract_desde_pubmed(doi)
        if abstract_pubmed:
            abstract = abstract_pubmed
            fuente_abstract = "pubmed"
        else:
            abstract = abstract_pdf
            fuente_abstract = "pdf"

        if not abstract and not resultados:
            print(f"OMITIDO: no se detectaron secciones de Abstract ni Results en {ruta_pdf.name}")
            continue
        if not resultados:
            print(f"AVISO: no se detectó la sección de Results en {ruta_pdf.name}; se usa solo el Abstract")

        texto_relevante = f"ABSTRACT:\n{abstract}\n\nRESULTS:\n{resultados}".strip()

        prompt = construir_prompt(ruta_pdf.name, texto_relevante)

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
            )
        except Exception as e:
            print(f"ERROR al consultar Gemini para {ruta_pdf.name}: {e}")
            continue

        print(response.text)

        try:
            datos = json.loads(limpiar_bloque_json(response.text))
        except json.JSONDecodeError:
            print(f"AVISO: la respuesta de Gemini para {ruta_pdf.name} no es JSON válido; se guarda sin parsear")
            datos = {"observations": [], "raw_response": response.text}

        # Metadatos para trazabilidad/auditoría de la fuente del abstract.
        datos["doi"] = doi
        datos["pmid"] = pmid
        datos["abstract_source"] = fuente_abstract
        datos["pubmed_abstract"] = abstract_pubmed

        salida = OUTPUT_DIR / (ruta_pdf.stem + ".json")
        salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Guardado: {salida}")


if __name__ == "__main__":
    main()
