import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
import instructor
from pydantic import BaseModel, Field

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en .env")

ABSTRACTS_DIR = Path("abstracts")
OUTPUT_DIR = Path("resultados")
LIMITE_ANALISIS = 10
MODEL_NAME = "gemini-3.8-flash"  # O el modelo compatible que estés usando


# ==========================================
# 1. Definición del Esquema con Pydantic
# ==========================================
class DevelopmentalObservation(BaseModel):
    species: str = Field(description="Species name, e.g., Human, Mouse, Macaque")
    parameter: str = Field(description="Clear biological parameter or developmental milestone, e.g., GE volume peak, cell proliferation")
    age_min: Optional[float] = Field(description="Minimum age value, or null if not specified")
    age_max: Optional[float] = Field(description="Maximum age value, or null if not specified")
    age_unit: Optional[str] = Field(description="Age unit, e.g., gw, ed, postnatal days, or null")
    source_text: str = Field(description="Exact quote from the abstract supporting this observation")


class AbstractExtraction(BaseModel):
    observations: List[DevelopmentalObservation] = Field(description="List of extracted developmental observations")


def cargar_abstract_cacheado(ruta_json: Path):
    """Lee abstracts/{stem}.json y devuelve el diccionario completo si es de pubmed, o None."""
    try:
        datos = json.loads(ruta_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"AVISO: cache de abstract corrupto en {ruta_json}; se ignora")
        return None

    if datos.get("source") != "pubmed":
        return None
        
    return datos


def main():
    # Inicialización limpia y única del cliente con instructor para Google Gemini
    client = instructor.from_provider(
        f"google/{MODEL_NAME}",
        api_key=api_key
    )

    caches = sorted(ABSTRACTS_DIR.glob("*.json"))
    if not caches:
        raise ValueError(f"No se encontraron abstracts en la carpeta '{ABSTRACTS_DIR}'")

    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Abstracts encontrados: {len(caches)}")

    if LIMITE_ANALISIS:
        print(f"Límite activo: se analizarán como máximo {LIMITE_ANALISIS} abstracts")

    analizados = 0

    for ruta_json in caches:
        if LIMITE_ANALISIS is not None and analizados >= LIMITE_ANALISIS:
            print(f"\nLímite de {LIMITE_ANALISIS} análisis alcanzado; se detiene el procesamiento.")
            break

        print(f"\n--- Procesando: {ruta_json.name} ---")

        datos = cargar_abstract_cacheado(ruta_json)
        if not datos or not datos.get("abstract"):
            print(f"OMITIDO: {ruta_json.name} no tiene abstract de PubMed (source != 'pubmed' o vacío)")
            continue

        doi = datos.get("doi")
        pmid = datos.get("pmid")
        abstract = datos.get("abstract", "")
        autores = datos.get("autores", [])
        anio = datos.get("anio")
        titulo = datos.get("titulo", "")

        analizados += 1

        prompt = f"""
Extract developmental milestone observations from the scientific record below.
The record below is the Abstract of the article "{ruta_json.stem}".

Rules:
- Create a separate observation for each species, cell type, or distinct age estimate.
- Preserve the original age values and units as stated in the text.
- ED means embryonic day.
- GW means gestational week.
- Do not convert ages or infer missing values.
- Do not merge different estimates for the same species.
- The parameter is any developmental milestone explicitly described (e.g. marker expression onset, growth peak, cell generation window, differentiation stage).
-- **CRITICAL: The parameter must be a concise, specific categorical label (3 to 6 words) that MUST include the relevant cell type, anatomical structure, or specific marker when mentioned in the text.**
  - Good examples: "tyrosine hydroxylase detection onset", "catecholaminergic neuron final mitosis", "cortical plate neurogenesis onset".
  - Bad examples: "final mitosis completion" (too vague, missing cell/region), "analysis of histological organization..." (too long/methodological).
- Do NOT extract the study's general sampling window or tissue collection range.
- Include only observations explicitly supported by the record.

Scientific record:
{abstract}
"""

        try:
            # Instructor con el proveedor de Google usa .create() directamente
            response: AbstractExtraction = client.create(
                model=MODEL_NAME,
                response_model=AbstractExtraction,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except Exception as e:
            print(f"ERROR al consultar Gemini con Instructor para {ruta_json.name}: {e}")
            continue

        # Construir la referencia bibliográfica automáticamente
        referencia = ""
        if autores:
            primer_autor = autores[0].split()[0]
            referencia = f"{primer_autor} et al., {anio}" if len(autores) > 1 else f"{primer_autor}, {anio}"

        # Ensamblar el diccionario final corregido
        datos_salida = {
            "doi": doi,
            "pmid": pmid,
            "titulo": titulo,
            "Reference": referencia,
            "link": f"https://doi.org/{doi}" if doi else "",
            "Cluster": "Brain",
            "Data_curator": f"{MODEL_NAME}-instructor",
            "abstract_source": "pubmed",
            "pubmed_abstract": abstract,
            "observations": [obs.model_dump() for obs in response.observations]
        }

        salida = OUTPUT_DIR / (ruta_json.stem + ".json")
        salida.write_text(json.dumps(datos_salida, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Guardado completo con Instructor: {salida}")


if __name__ == "__main__":
    main()