# -*- coding: utf-8 -*-
"""
descargar_pdfs.py
==================

Etapa 1 (alternativa) del pipeline: descarga PDFs de acceso abierto desde
una columna de DOIs, usando OpenAlex (API gratuita, sin email ni registro).

pip install pandas requests openpyxl   (openpyxl solo si el archivo es .xlsx)
"""

import os

import pandas as pd
import requests

SALIDA_DIR = "pdfs"  # carpeta donde se guardan los PDFs descargados


def doi_a_stem(doi):
    invalid_chars = '<>:"\\|?*'
    return "".join(
        f"%{ord(char):02X}" if char in invalid_chars else "_" if char == "/" else char
        for char in doi
    )


df = pd.read_csv("data/dataset_mrh_0.9.csv")          # o: pd.read_excel("articulos.xlsx")
df = df.sample(frac=0.2, random_state=42)  # mezclar filas (opcional)
print("Total de filas:", len(df))

os.makedirs(SALIDA_DIR, exist_ok=True)

ok, fallidos = [], []

for doi in df["DOI"]:
    doi = str(doi).strip().lower().replace("https://doi.org/", "")

    if not doi.startswith("10."):
        print(f"OMITIDO: DOI inválido: '{doi}'")
        fallidos.append((doi, "DOI inválido"))
        continue

    try:
        # 1) Buscar el PDF de acceso abierto en OpenAlex
        meta = requests.get(
            f"https://api.openalex.org/works/https://doi.org/{doi}", timeout=30
        )
        meta.raise_for_status()                       # DOI inexistente -> error
        pdf_url = (meta.json().get("best_oa_location") or {}).get("pdf_url")
        if not pdf_url:
            print(f"OMITIDO: sin PDF de acceso abierto para: {doi}")
            fallidos.append((doi, "sin PDF de acceso abierto"))
            continue

        # 2) Descargar el PDF en la carpeta de salida
        pdf = requests.get(pdf_url, timeout=60)
        pdf.raise_for_status()                        # descarga fallida -> error

        nombre = os.path.join(SALIDA_DIR, doi_a_stem(doi) + ".pdf")
        with open(nombre, "wb") as f:
            f.write(pdf.content)
        print("OK", nombre)
        ok.append(doi)
    except requests.RequestException as e:
        print(f"ERROR al procesar {doi}: {e}")
        fallidos.append((doi, str(e)))

print(f"\nTerminado. Descargados: {len(ok)} / Fallidos: {len(fallidos)}")
if fallidos:
    print("DOIs fallidos:")
    for doi, motivo in fallidos:
        print(f"  - {doi}: {motivo}")