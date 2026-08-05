#!/usr/bin/env python3
"""
batch_convert_gemini.py — Convertit en masse un dossier d'entrants (SVG, PPTX, PDF,
DOCX, images, XLSX, HTML, CSV, JSON, XML, ZIP, audio, etc.) en fichiers Markdown.

Variante de batch_convert.py (skill `entrants-to-markdown`) : la phase de lecture
des fichiers visuels (SVG, PNG, JPG, GIF, WEBP, BMP, TIFF, schémas, captures...)
est déléguée à l'API Gemini au lieu de l'outil de vision de Claude, pour rester
scalable sur de gros dossiers sans consommer le contexte de la conversation.

Si l'API Gemini n'est pas configurée, échoue sur un fichier donné, ou est
désactivée via --skip-gemini, ce fichier retombe dans la liste `vision_needed`
du rapport, exactement comme dans le skill d'origine, pour un traitement manuel
par Claude.

Usage:
    python batch_convert_gemini.py --input <dossier_entrant> [--output <dossier_sortie>]
                                    [--combined] [--only-combined]
                                    [--model gemini-2.5-flash] [--delay 4.5]
                                    [--api-key <clé>] [--skip-gemini]

Dépendances : pip install markitdown tqdm google-genai
Clé API : export GEMINI_API_KEY=... (ou GOOGLE_API_KEY), voir https://aistudio.google.com/apikey
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    from tqdm import tqdm
except ImportError:
    print("Erreur : le paquet 'tqdm' est requis. Installe-le avec :")
    print("    pip install tqdm")
    sys.exit(1)

try:
    from markitdown import MarkItDown
except ImportError:
    print("Erreur : le paquet 'markitdown' est requis. Installe-le avec :")
    print("    pip install markitdown")
    sys.exit(1)

# Extensions gérées automatiquement par markitdown
AUTO_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    ".html", ".htm", ".csv", ".json", ".xml", ".txt", ".zip",
    ".mp3", ".wav", ".epub", ".msg",
}

# Extensions "image raster" envoyées à Gemini en pièce jointe multimodale
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
}

# SVG traité à part : envoyé à Gemini comme XML brut (pas de rendu image)
SVG_EXTENSION = ".svg"

VISION_EXTENSIONS = set(IMAGE_MIME_TYPES) | {SVG_EXTENSION}

# Extensions binaires propriétaires illisibles hors-ligne : nécessitent un MCP dédié
API_NEEDED_EXTENSIONS = {
    ".fig",  # Figma — nécessite le MCP Figma ou un lien de partage
}

IMAGE_PROMPT = (
    "Décris ce fichier image de façon fidèle et structurée en Markdown, pour "
    "quelqu'un qui ne peut pas le voir. Retranscris tout texte lisible, décris "
    "la structure si c'est un schéma/diagramme/interface, mentionne les couleurs "
    "et éléments graphiques importants. Réponds uniquement avec le contenu Markdown, "
    "sans phrase d'introduction."
)

SVG_PROMPT_TEMPLATE = (
    "Voici le code XML brut d'un fichier SVG. Analyse sa structure (formes, texte "
    "contenu dans des balises <text>, couleurs, mise en page) et rédige une "
    "description Markdown fidèle. Retranscris tout texte lisible. Réponds "
    "uniquement avec le contenu Markdown, sans phrase d'introduction.\n\n"
    "```xml\n{svg_content}\n```"
)


def find_input_files(input_dir: Path):
    return sorted(p for p in input_dir.rglob("*") if p.is_file())


def convert_file(md_engine: "MarkItDown", filepath: Path) -> str:
    """Convertit un fichier via markitdown et renvoie le contenu markdown."""
    result = md_engine.convert(str(filepath))
    return result.text_content


def build_gemini_client(api_key: str):
    from google import genai
    return genai.Client(api_key=api_key)


def describe_image_with_gemini(client, model: str, filepath: Path, mime_type: str) -> str:
    from google.genai import types
    data = filepath.read_bytes()
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=data, mime_type=mime_type),
            IMAGE_PROMPT,
        ],
    )
    return response.text


def describe_svg_with_gemini(client, model: str, filepath: Path) -> str:
    svg_content = filepath.read_text(encoding="utf-8", errors="replace")
    prompt = SVG_PROMPT_TEMPLATE.format(svg_content=svg_content)
    response = client.models.generate_content(model=model, contents=prompt)
    description = response.text or ""
    return f"{description.strip()}\n\n## Code SVG brut\n\n```xml\n{svg_content}\n```\n"


def main():
    parser = argparse.ArgumentParser(description="Conversion batch d'entrants vers Markdown (visuels via Gemini)")
    parser.add_argument("--input", required=True, help="Dossier contenant les fichiers à convertir")
    parser.add_argument("--output", default=None, help="Dossier de sortie (défaut: <input>/markdown_output)")
    parser.add_argument("--combined", action="store_true", help="Produit AUSSI un fichier combiné (en plus des .md individuels)")
    parser.add_argument("--only-combined", action="store_true", help="Ne produit QUE le fichier combiné (pas de .md individuels)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Modèle Gemini multimodal à utiliser (défaut: gemini-2.5-flash)")
    parser.add_argument("--delay", type=float, default=4.5, help="Pause en secondes entre deux appels Gemini (défaut: 4.5)")
    parser.add_argument("--api-key", default=None, help="Clé API Gemini (défaut: variable d'env GEMINI_API_KEY ou GOOGLE_API_KEY)")
    parser.add_argument("--skip-gemini", action="store_true", help="Désactive Gemini : tous les visuels remontent dans vision_needed")
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    if not input_dir.is_dir():
        print(f"Erreur : dossier introuvable : {input_dir}")
        sys.exit(1)

    output_dir = Path(args.output).expanduser().resolve() if args.output else input_dir / "markdown_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    files = find_input_files(input_dir)
    files = [f for f in files if output_dir not in f.parents]

    if not files:
        print(f"Aucun fichier trouvé dans {input_dir}")
        sys.exit(0)

    # --- Client Gemini (optionnel) ---
    gemini_client = None
    if not args.skip_gemini:
        import os
        api_key = args.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("⚠️  Pas de clé API Gemini trouvée (GEMINI_API_KEY / GOOGLE_API_KEY / --api-key).")
            print("    Les fichiers visuels seront listés pour traitement manuel par Claude.\n")
        else:
            try:
                gemini_client = build_gemini_client(api_key)
            except ImportError:
                print("⚠️  Le paquet 'google-genai' n'est pas installé (pip install google-genai).")
                print("    Les fichiers visuels seront listés pour traitement manuel par Claude.\n")
            except Exception as e:
                print(f"⚠️  Impossible d'initialiser le client Gemini ({e}).")
                print("    Les fichiers visuels seront listés pour traitement manuel par Claude.\n")

    md_engine = MarkItDown()

    converted = []
    vision_needed = []
    vision_processed = []
    api_needed = []
    errors = []

    auto_files = [f for f in files if f.suffix.lower() in AUTO_EXTENSIONS]
    vision_files = [f for f in files if f.suffix.lower() in VISION_EXTENSIONS]
    api_files = [f for f in files if f.suffix.lower() in API_NEEDED_EXTENSIONS]
    api_needed = [str(f.relative_to(input_dir)) for f in api_files]

    print(f"Conversion de {len(files)} fichier(s) depuis {input_dir}\n")

    # --- Phase 1 : conversion automatique (markitdown) ---
    for filepath in tqdm(auto_files, desc="Conversion automatique", unit="fichier"):
        try:
            text = convert_file(md_engine, filepath)
            rel = filepath.relative_to(input_dir)

            if not args.only_combined:
                out_path = output_dir / rel.with_suffix(".md")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(
                    f"# {filepath.name}\n\n{text.strip()}\n", encoding="utf-8"
                )

            converted.append({"file": str(rel), "chars": len(text)})

        except Exception as e:
            errors.append({"file": str(filepath.relative_to(input_dir)), "error": str(e)})

    # --- Phase 2 : description des visuels (Gemini, avec fallback) ---
    for filepath in tqdm(vision_files, desc="Description visuelle (Gemini)", unit="fichier"):
        rel = filepath.relative_to(input_dir)
        ext = filepath.suffix.lower()

        if gemini_client is None:
            vision_needed.append(str(rel))
            continue

        try:
            if ext == SVG_EXTENSION:
                description = describe_svg_with_gemini(gemini_client, args.model, filepath)
            else:
                description = describe_image_with_gemini(gemini_client, args.model, filepath, IMAGE_MIME_TYPES[ext])

            if not args.only_combined:
                out_path = output_dir / rel.with_suffix(".md")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(
                    f"# {filepath.name}\n\n{description.strip()}\n", encoding="utf-8"
                )

            vision_processed.append({"file": str(rel), "model": args.model})
            time.sleep(args.delay)

        except Exception as e:
            errors.append({"file": str(rel), "error": f"Gemini: {e}"})
            vision_needed.append(str(rel))

    # --- Fichier combiné (si demandé) ---
    if args.combined or args.only_combined:
        combined_path = output_dir / "combined.md"
        with combined_path.open("w", encoding="utf-8") as out:
            out.write(f"# Conversion combinée — {input_dir.name}\n\n")
            out.write(f"_Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n---\n\n")
            for filepath in files:
                ext = filepath.suffix.lower()
                if ext in API_NEEDED_EXTENSIONS:
                    continue
                if ext in VISION_EXTENSIONS and str(filepath.relative_to(input_dir)) in vision_needed:
                    continue
                rel = filepath.relative_to(input_dir)
                md_path = output_dir / rel.with_suffix(".md")
                if md_path.exists():
                    out.write(md_path.read_text(encoding="utf-8"))
                    out.write("\n\n---\n\n")

    # --- Rapport pour la suite (fallback vision + .fig, traités par Claude) ---
    report_path = output_dir / "_conversion_report.json"
    report = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "generated_at": datetime.now().isoformat(),
        "gemini_model": args.model if gemini_client is not None else None,
        "converted": converted,
        "vision_processed": vision_processed,
        "vision_needed": vision_needed,
        "api_needed": api_needed,
        "errors": errors,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ {len(converted)} fichier(s) converti(s) automatiquement → {output_dir}")
    if vision_processed:
        print(f"✨ {len(vision_processed)} visuel(s) décrit(s) automatiquement par Gemini ({args.model})")
    if vision_needed:
        print(f"👁️  {len(vision_needed)} visuel(s) à traiter manuellement par Claude (voir _conversion_report.json) :")
        for f in vision_needed:
            print(f"   - {f}")
    if api_needed:
        print(f"🔗 {len(api_needed)} fichier(s) nécessitant une API/MCP dédié (ex: Figma) :")
        for f in api_needed:
            print(f"   - {f}")
    if errors:
        print(f"⚠️  {len(errors)} erreur(s) :")
        for e in errors:
            print(f"   - {e['file']}: {e['error']}")


if __name__ == "__main__":
    main()
