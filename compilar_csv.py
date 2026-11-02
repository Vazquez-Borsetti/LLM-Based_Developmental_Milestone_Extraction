"""
compilar_csv.py
================

Etapa 3 del pipeline: lee todos los `resultados/*.json` producidos por
`interpretar_abstracts.py` y arma un único CSV con el esquema del dataset
maestro + una columna extra `Model` al final:

    Species, Parameter, DAF, Reference, Obs, Quote, DOI, link,
    Cluster, Data_curator, GA(H+14), Model

Las primeras 11 columnas son el esquema original del dataset maestro
(sin tocar). La columna `Model` (al final) registra qué modelo de Gemini
produjo cada fila, para poder comparar corridas con distintos modelos.
Como los JSON no traen un campo `model` propio, se usa `Data_curator`
como proxy (p. ej. "gemini-3.8-flash-instructor"); si en el futuro un
JSON sí trae `model` explícito, ese valor tiene prioridad.

Es un script separado de `interpretar_abstracts.py` para poder iterar
sobre el formato de salida sin volver a llamar a Gemini (que cuesta
plata y tiempo).

NOTA: las columnas `DAF` y `GA(H+14)` se dejan **vacías** por ahora.
La conversión desde `age_min`/`age_max`/`age_unit` (que sí están en
los JSON) la hace un script aparte (a escribir) que post-procesa el
CSV o los JSON. Mientras tanto, este script solo vuelca lo que sí hay.

Uso:
    python compilar_csv.py
    # o indicando otra carpeta / archivo de salida:
    python compilar_csv.py --input resultados --output resultados/dataset.csv
"""

import argparse
import csv
import glob
import json

# Columnas del CSV: las primeras 11 son el esquema original del dataset
# maestro (sin tocar). La última (`Model`) es extra y registra qué modelo
# de Gemini produjo cada fila, para comparar modelos a posteriori.
COLUMNAS_CSV = [
    "Species",
    "Parameter",
    "DAF",
    "Reference",
    "Obs",
    "Quote",
    "DOI",
    "link",
    "Cluster",
    "Data_curator",
    "GA(H+14)",
    "Model",
]


def normalizar_doi(doi: str) -> str:
    """Si el DOI no viene como URL, lo prefija con https://doi.org/."""
    if not doi:
        return ""
    doi = doi.strip()
    if doi.startswith("http://") or doi.startswith("https://"):
        return doi
    if doi.lower().startswith("doi:"):
        doi = doi[4:].strip()
    return f"https://doi.org/{doi}"


def observacion_a_fila(obs: dict, defaults: dict) -> dict:
    """Mapea una observación del JSON a una fila del CSV maestro.

    DAF y GA(H+14) quedan vacíos: la conversión desde age_min/age_max/
    age_unit la hace un script aparte (a escribir).

    Las observaciones individuales (producidas por `interpretar_abstracts2.py`)
    solo traen `species`, `parameter`, `age_min/max/unit` y `source_text`; el
    resto de los campos (`Reference`, `Cluster`, `Data_curator`) viven a nivel
    de archivo y se completan siempre desde `defaults`.

    `Model` no es un campo propio del JSON: se completa desde `model` si
    existiera (corridas futuras) y si no, cae al valor de `Data_curator`
    (que hoy ya registra qué modelo de Gemini se usó, p. ej.
    "gemini-3.8-flash-instructor").
    """
    species = obs.get("species", "") or ""
    return {
        "Species": species,
        "Parameter": obs.get("parameter", "") or "",
        "DAF": "",
        "Reference": obs.get("reference") or defaults.get("reference", ""),
        "Obs": obs.get("obs", "") or "",
        "Quote": obs.get("source_text", "") or "",
        "DOI": normalizar_doi(obs.get("doi") or defaults.get("doi", "")),
        "link": "",
        "Cluster": obs.get("cluster") or defaults.get("cluster", ""),
        "Data_curator": obs.get("data_curator") or defaults.get("data_curator", ""),
        "GA(H+14)": "",
        "Model": obs.get("model") or defaults.get("model", ""),
    }


def compilar(input_dir: str, output_csv: str) -> int:
    """Lee todos los *.json de input_dir y escribe output_csv.

    No valida las carpetas de antemano: si `input_dir` no existe o está
    vacía, el aviso "No se encontraron JSONs en ..." ya lo indica; si la
    carpeta de `output_csv` no existe, `open()` levanta su propio
    `FileNotFoundError`, que ya es suficientemente indicativo.

    Devuelve la cantidad de filas escritas.
    """
    archivos = sorted(glob.glob(f"{input_dir}/*.json"))
    if not archivos:
        raise ValueError(f"No se encontraron JSONs en {input_dir}")

    filas = []
    for ruta in archivos:
        nombre = ruta.replace("\\", "/").rsplit("/", 1)[-1]

        # Por las dudas, no intentar leer el CSV de salida si vive acá.
        if nombre == output_csv.replace("\\", "/").rsplit("/", 1)[-1]:
            continue

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except json.JSONDecodeError:
            print(f"AVISO: {nombre} no es JSON válido; se ignora")
            continue

        observations = datos.get("observations", [])
        if not isinstance(observations, list):
            observations = []

        defaults = {
            "reference": datos.get("Reference", ""),
            "doi": datos.get("doi", ""),
            "cluster": datos.get("Cluster", ""),
            "data_curator": datos.get("Data_curator", ""),
            "model": datos.get("model", "") or datos.get("Data_curator", ""),
        }

        for obs in observations:
            filas.append(observacion_a_fila(obs, defaults))

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
        writer.writeheader()
        writer.writerows(filas)

    print(f"CSV maestro escrito: {output_csv}  ({len(filas)} filas, {len(archivos)} archivos procesados)")
    return len(filas)


def main():
    parser = argparse.ArgumentParser(description="Compila resultados/*.json a un CSV maestro.")
    parser.add_argument("--input", default="resultados",
                        help="Carpeta con los *.json de salida (default: resultados)")
    parser.add_argument("--output", default="resultados/dataset.csv",
                        help="Ruta del CSV de salida (default: resultados/dataset.csv)")
    args = parser.parse_args()

    compilar(args.input, args.output)


if __name__ == "__main__":
    main()
