"""
descargar_abstracts.py
======================

Etapa 1 del pipeline: descarga el abstract oficial de PubMed para cada DOI.

Toma los DOIs desde un CSV/Excel (columna "DOI" por defecto), los normaliza
igual que el script de descarga de PDFs (strip + lowercase + quitar el
prefijo https://doi.org/) y consulta PubMed para obtener el abstract oficial.

El resultado se guarda en `abstracts/{doi_safe}.json` con la forma:
    {
      "doi": "...",
      "pmid": "..." o null,
      "titulo": "..." o "",
      "autores": ["Apellido Nombre", ...],
      "anio": 2020 o null,
      "abstract": "..." o "",
      "source": "pubmed" | "not_found"
    }

El nombre del JSON usa el DOI con '/' reemplazado por '_' (mismo formato que
los PDFs descargados por el otro script), para que interpretar_pdfs.py e
interpretar_abstracts.py puedan encontrar el cache por stem.

Requisitos:
    pip install requests python-dotenv pandas openpyxl
    Variables de entorno (en .env):
        NCBI_API_KEY   (opcional, sube el límite a 10 req/seg)
"""

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

ncbi_api_key = os.getenv("NCBI_API_KEY")  # opcional: 3 req/seg sin key, 10 con ella

df = pd.read_csv("data/dataset_mrh_0.9.csv")          # o: pd.read_excel("articulos.xlsx")
df = df.sample(frac=0.1, random_state=42)  # mezclar filas (opcional)
print("Total de filas:", len(df))

ABSTRACTS_DIR = Path("abstracts")        # carpeta donde se cachean los abstracts

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_DELAY = 0.11 if ncbi_api_key else 0.34


def normalizar_doi(valor):
    """Normaliza un DOI igual que el script de descarga de PDFs.

    strip + lowercase + quitar prefijo 'https://doi.org/'.
    Devuelve None si está vacío, es NaN, o no comienza con '10.'.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    doi = str(valor).strip().lower().replace("https://doi.org/", "")
    if not doi.startswith("10."):
        return None
    return doi


def doi_a_stem(doi: str) -> str:
    """Convierte un DOI a un nombre de archivo compatible con Windows."""
    invalid_chars = '<>:"\\|?*'
    return "".join(
        f"%{ord(char):02X}" if char in invalid_chars else "_" if char == "/" else char
        for char in doi
    )


def buscar_pmid_por_doi(doi: str):
    """Busca en PubMed el PMID correspondiente a un DOI."""
    params = {"db": "pubmed", "term": f"{doi}[AID]", "retmode": "json"}
    if ncbi_api_key:
        params["api_key"] = ncbi_api_key
    resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
    resp.raise_for_status()
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    return ids[0] if ids else None


def obtener_metadatos_pubmed(pmid: str) -> dict:
    """Descarga desde PubMed (XML) el abstract, título, autores y año para un PMID dado."""
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
    abstract = "\n".join(partes).strip()

    titulo_nodo = raiz.find(".//Article/ArticleTitle")
    titulo = "".join(titulo_nodo.itertext()).strip() if titulo_nodo is not None else ""

    autores = []
    for autor_nodo in raiz.iter("Author"):
        apellido = autor_nodo.findtext("LastName", "")
        nombre = autor_nodo.findtext("ForeName") or autor_nodo.findtext("Initials", "")
        if apellido:
            autores.append(f"{apellido} {nombre}".strip())
        else:
            colectivo = autor_nodo.findtext("CollectiveName", "")
            if colectivo:
                autores.append(colectivo)

    anio = None
    pub_date = raiz.find(".//Article/Journal/JournalIssue/PubDate")
    if pub_date is not None:
        anio_texto = pub_date.findtext("Year")
        if not anio_texto:
            match = re.search(r"\d{4}", pub_date.findtext("MedlineDate", ""))
            anio_texto = match.group(0) if match else None
        if anio_texto:
            try:
                anio = int(anio_texto)
            except ValueError:
                anio = None

    return {"abstract": abstract, "titulo": titulo, "autores": autores, "anio": anio}


def descargar_abstract_para(doi: str):
    """Consulta PubMed por DOI y devuelve (pmid, metadatos) o (None, {}) si falla.

    `metadatos` tiene la forma {"abstract", "titulo", "autores", "anio"}.
    """
    try:
        pmid = buscar_pmid_por_doi(doi)
        time.sleep(PUBMED_DELAY)
        if not pmid:
            print(f"AVISO: no se encontró PMID en PubMed para DOI {doi}")
            return None, {}
        metadatos = obtener_metadatos_pubmed(pmid)
        time.sleep(PUBMED_DELAY)
        if not metadatos["abstract"]:
            print(f"AVISO: PubMed no devolvió abstract para PMID {pmid} (DOI {doi})")
        return pmid, metadatos
    except (requests.RequestException, ET.ParseError) as e:
        print(f"AVISO: no se pudo consultar PubMed para DOI {doi}: {e}")
        return None, {}





def main(df):
    
    ABSTRACTS_DIR.mkdir(exist_ok=True)
    #print(f"DOIs en '{INPUT_FILE}' (columna '{DOI_COLUMN}'): {len(df)}")

    ok = []
    sin_abstract = []
    invalidos = []
    ya_cacheados = 0

    for valor in df["DOI"]:
        doi = normalizar_doi(valor)
        if not doi:
            print(f"OMITIDO: DOI inválido: '{valor}'")
            invalidos.append((str(valor), "DOI inválido"))
            continue

        stem = doi_a_stem(doi)
        salida = ABSTRACTS_DIR / (stem + ".json")

        # Re-ejecución segura: si ya existe el cache, se saltea.
        if salida.exists():
            ya_cacheados += 1
            print(f"SKIP (ya cacheado): {salida.name}")
            ok.append(doi)
            continue

        print(f"\n--- Procesando: {doi} ---")
        pmid, metadatos = descargar_abstract_para(doi)
        abstract = metadatos.get("abstract", "")
        fuente = "pubmed" if abstract else "not_found"

        datos = {
            "doi": doi,
            "pmid": pmid,
            "titulo": metadatos.get("titulo", ""),
            "autores": metadatos.get("autores", []),
            "anio": metadatos.get("anio"),
            "abstract": abstract,
            "source": fuente,
        }
        salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        if abstract:
            ok.append(doi)
            print(f"OK: {salida.name}")
        else:
            sin_abstract.append((doi, "sin PMID o sin abstract en PubMed"))
            print(f"SIN ABSTRACT: {salida.name}")

    print(f"\n=== Resumen ===")
    print(f"  Con abstract:    {len(ok)}")
    print(f"  Sin abstract:    {len(sin_abstract)}")
    print(f"  DOI inválido:    {len(invalidos)}")
    print(f"  Ya cacheados:    {ya_cacheados}")

    if sin_abstract:
        print("\nDOIs sin abstract en PubMed:")
        for doi, motivo in sin_abstract:
            print(f"  - {doi}: {motivo}")
    if invalidos:
        print("\nDOIs inválidos:")
        for doi, motivo in invalidos:
            print(f"  - {doi}: {motivo}")


if __name__ == "__main__":
    main(df)