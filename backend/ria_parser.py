"""
Belgian RIA Parser - Template-based extraction

Extracts structured data from Belgian Regulatory Impact Assessment documents
following the standardized 21-theme format.

Output: Structured JSON with metadata, 21 impact themes, and administrative burdens.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class BelgianRIAParser:
    """
    Parser for Belgian Federal RIA documents.
    Extracts structured information from standardized RIA forms.
    """
    
    @staticmethod
    def _safe_strip(text: Optional[str]) -> Optional[str]:
        """Safely strip text, returning None if input is None."""
        return text.strip() if text else None
    
    # 21 Impact Themes (in order)
    IMPACT_THEMES = [
        "Lutte contre la pauvreté",
        "Égalité des chances et cohésion sociale",
        "Égalité des femmes et les hommes",
        "Santé",
        "Emploi",
        "Consommation et production",
        "Développement économique",
        "Investissements",
        "Recherche et développement",
        "PME",
        "Charges administratives",
        "Énergie",
        "Mobilité",
        "Alimentation",
        "Changement climatique",
        "Ressources naturelles",
        "Air extérieur et intérieur",
        "Biodiversité",
        "Nuisances",
        "Gouvernement",
        "Cohérence des politiques pour le développement"
    ]
    
    # Alternative theme names/variations
    THEME_VARIANTS = {
        1: ["pauvreté", "poverty"],
        2: ["égalité des chances", "cohesion sociale", "equal opportunities"],
        3: ["égalité des femmes", "égalité hommes femmes", "gender equality"],
        4: ["santé", "health"],
        5: ["emploi", "employment"],
        6: ["consommation", "production", "consumption"],
        7: ["développement économique", "economic development"],
        8: ["investissements", "investments"],
        9: ["recherche", "développement", "research", "development"],
        10: ["PME", "SME", "petites et moyennes entreprises"],
        11: ["charges administratives", "administrative burdens", "burdens"],
        12: ["énergie", "energy"],
        13: ["mobilité", "mobility"],
        14: ["alimentation", "food"],
        15: ["changement climatique", "climate change"],
        16: ["ressources naturelles", "natural resources"],
        17: ["air extérieur", "air intérieur", "outdoor air", "indoor air"],
        18: ["biodiversité", "biodiversity"],
        19: ["nuisances", "nuisance"],
        20: ["gouvernement", "government"],
        21: ["cohérence", "développement", "policy coherence", "development"]
    }
    
    def __init__(self):
        """Initialize the parser."""
        self.text = ""
        self.lines = []
    
    def parse(self, txt_path: str) -> Dict[str, Any]:
        """
        Parse a Belgian RIA text file and extract structured data.
        
        Args:
            txt_path: Path to the RIA text file
        
        Returns:
            Dictionary containing structured RIA data
        """
        txt_path = Path(txt_path)
        if not txt_path.exists():
            raise FileNotFoundError(f"RIA text file not found: {txt_path}")
        
        # Read the text file
        self.text = txt_path.read_text(encoding='utf-8')
        self.lines = self.text.splitlines()
        
        # Extract structured data
        result = {
            "metadata": self._extract_metadata(),
            "descriptive_sheet": self._extract_descriptive_sheet(),
            "impact_themes": self._extract_impact_themes(),
            "administrative_burdens": self._extract_administrative_burdens(),
            "source_file": str(txt_path.name),
            "parsed_at": datetime.now().isoformat()
        }
        
        return result
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {
            "document_id": None,
            "date": None,
            "language": "fr"  # Default to French
        }
        
        # Extract document ID (e.g., "2014A03330.002")
        doc_id_pattern = r'(\d{4}[A-Z]\d{5}\.\d{3})'
        doc_id_match = re.search(doc_id_pattern, self.text)
        if doc_id_match:
            metadata["document_id"] = doc_id_match.group(1)
        
        # Extract date (look for date patterns)
        date_patterns = [
            r'(\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'CMR AIR du (\d{2}-\d{2}-\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                metadata["date"] = match.group(1)
                break
        
        return metadata
    
    def _extract_descriptive_sheet(self) -> Dict[str, Any]:
        """Extract descriptive sheet sections (A, B, C, D, E)."""
        descriptive = {
            "A_Author": self._extract_section_a(),
            "B_Project": self._extract_section_b(),
            "C_Consultation": self._extract_section_c(),
            "D_Sources": self._extract_section_d(),
            "E_Date": self._extract_section_e()
        }
        return descriptive
    
    def _extract_section_a(self) -> Dict[str, Any]:
        """Extract Section A: Author information."""
        section_a = {
            "competent_government_member": None,
            "policy_cell_contact": {},
            "administration": None,
            "administration_contact": {}
        }
        
        # Find Section A
        section_start = self._find_section_start("A\\. Auteur", "B\\. Projet")
        if section_start == -1:
            return section_a
        
        section_text = self._get_section_text(section_start, "B\\. Projet")
        
        # Extract government member name (usually after "Membre du Gouvernement")
        member_match = re.search(r'Membre du Gouvernement[^>]*>\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', section_text)
        if member_match and member_match.group(1):
            section_a["competent_government_member"] = member_match.group(1).strip()
        
        # Extract policy cell contact (name, email, phone)
        policy_pattern = r'Contact cellule stratégique[^>]*>\s*([^,]+),\s*([^\s,]+@[^\s,]+),\s*([\d\s\.\+\-]+)'
        policy_match = re.search(policy_pattern, section_text, re.IGNORECASE)
        if policy_match and all(policy_match.group(i) for i in range(1, 4)):
            section_a["policy_cell_contact"] = {
                "name": policy_match.group(1).strip() if policy_match.group(1) else "",
                "email": policy_match.group(2).strip() if policy_match.group(2) else "",
                "phone": policy_match.group(3).strip() if policy_match.group(3) else ""
            }
        
        # Extract administration
        admin_match = re.search(r'Administration[^>]*>\s*([^\n]+)', section_text)
        if admin_match and admin_match.group(1):
            section_a["administration"] = admin_match.group(1).strip()
        
        # Extract administration contact
        admin_contact_pattern = r'Contact administration[^>]*>\s*([^,]+),\s*([^\s,]+@[^\s,]+),\s*([\d\s\.\+\-]+)'
        admin_contact_match = re.search(admin_contact_pattern, section_text, re.IGNORECASE)
        if admin_contact_match and all(admin_contact_match.group(i) for i in range(1, 4)):
            section_a["administration_contact"] = {
                "name": admin_contact_match.group(1).strip() if admin_contact_match.group(1) else "",
                "email": admin_contact_match.group(2).strip() if admin_contact_match.group(2) else "",
                "phone": admin_contact_match.group(3).strip() if admin_contact_match.group(3) else ""
            }
        
        return section_a
    
    def _extract_section_b(self) -> Dict[str, Any]:
        """Extract Section B: Project information."""
        section_b = {
            "regulation_title": None,
            "description": None,
            "origin": None,
            "implementation_goals": None,
            "previous_impact_analyses": None
        }
        
        section_start = self._find_section_start("B\\. Projet", "C\\. Consultations")
        if section_start == -1:
            return section_b
        
        section_text = self._get_section_text(section_start, "C\\. Consultations")
        
        # Extract regulation title
        title_match = re.search(r'Titre de la réglementation:\s*([^\n]+)', section_text, re.IGNORECASE)
        if title_match and title_match.group(1):
            section_b["regulation_title"] = title_match.group(1).strip()
        
        # Extract description (text after "Description succincte")
        desc_match = re.search(r'Description succincte[^\n]*\n(.*?)(?=Analyses d\'impact|$)', section_text, re.DOTALL | re.IGNORECASE)
        if desc_match:
            description = desc_match.group(1).strip()
            # Try to extract origin and goals from description
            section_b["description"] = description
            
            # Look for origin indicators
            origin_keywords = ["traités", "directive", "accord de coopération", "actualité", "loi du"]
            for keyword in origin_keywords:
                if keyword.lower() in description.lower():
                    section_b["origin"] = keyword
                    break
        
        # Extract previous impact analyses
        prev_match = re.search(r'Analyses d\'impact déjà réalisées[^>]*>\s*☐\s*Oui\s*/\s*X\s*Non|☒\s*Oui\s*/\s*☐\s*Non', section_text)
        if prev_match:
            section_b["previous_impact_analyses"] = "Oui" if "☒" in prev_match.group(0) or "X" in prev_match.group(0) else "Non"
        
        return section_b
    
    def _extract_section_c(self) -> Dict[str, Any]:
        """Extract Section C: Consultation information."""
        section_c = {
            "consultations": None
        }
        
        section_start = self._find_section_start("C\\. Consultations", "D\\. Sources")
        if section_start == -1:
            return section_c
        
        section_text = self._get_section_text(section_start, "D\\. Sources")
        
        # Extract consultation text
        consult_match = re.search(r'Consultations[^:]*:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]\.|$)', section_text, re.MULTILINE)
        if consult_match and consult_match.group(1):
            section_c["consultations"] = self._safe_strip(consult_match.group(1))
        
        return section_c
    
    def _extract_section_d(self) -> Dict[str, Any]:
        """Extract Section D: Sources."""
        section_d = {
            "sources": None
        }
        
        section_start = self._find_section_start("D\\. Sources", "E\\. Date")
        if section_start == -1:
            return section_d
        
        section_text = self._get_section_text(section_start, "E\\. Date")
        
        # Extract sources text
        sources_match = re.search(r'Sources[^:]*:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]\.|$)', section_text, re.MULTILINE)
        if sources_match and sources_match.group(1):
            section_d["sources"] = self._safe_strip(sources_match.group(1))
        
        return section_d
    
    def _extract_section_e(self) -> Dict[str, Any]:
        """Extract Section E: Date of finalization."""
        section_e = {
            "finalization_date": None,
            "cmr_reference": None
        }
        
        section_start = self._find_section_start("E\\. Date", "21 thèmes|Quel est l'impact")
        if section_start == -1:
            return section_e
        
        section_text = self._get_section_text(section_start, "21 thèmes|Quel est l'impact")
        
        # Extract CMR reference
        cmr_match = re.search(r'CMR AIR du\s+([^\n]+)', section_text)
        if cmr_match and cmr_match.group(1):
            section_e["cmr_reference"] = self._safe_strip(cmr_match.group(1))
        
        # Extract date
        date_match = re.search(r'(\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})', section_text, re.IGNORECASE)
        if date_match and date_match.group(1):
            section_e["finalization_date"] = self._safe_strip(date_match.group(1))
        
        return section_e
    
    def _extract_impact_themes(self) -> List[Dict[str, Any]]:
        """Extract all 21 impact theme assessments."""
        themes = []
        
        # Find the start of impact themes section
        themes_start = self._find_section_start("21 thèmes|Quel est l'impact", None)
        if themes_start == -1:
            return themes
        
        # Extract each theme
        for theme_num, theme_name in enumerate(self.IMPACT_THEMES, 1):
            theme_data = self._extract_theme(theme_num, theme_name)
            themes.append(theme_data)
        
        return themes
    
    def _extract_theme(self, theme_num: int, theme_name: str) -> Dict[str, Any]:
        """Extract data for a specific impact theme."""
        theme_data = {
            "theme_number": theme_num,
            "theme_name": theme_name,
            "impact_type": None,  # "positive", "negative", "none"
            "explanation": None,
            "special_fields": {}
        }
        
        # Find theme section (look for theme number in brackets or theme name)
        theme_patterns = [
            rf'\[{theme_num}\]',  # [1], [2], etc.
            re.escape(theme_name),
            rf'{theme_num}\.?\s+{re.escape(theme_name)}'
        ]
        
        theme_start = -1
        for pattern in theme_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                theme_start = match.start()
                break
        
        if theme_start == -1:
            return theme_data
        
        # Get text for this theme (until next theme or end)
        next_theme_pattern = rf'\[{theme_num + 1}\]|{re.escape(self.IMPACT_THEMES[theme_num] if theme_num < 21 else "")}'
        theme_text = self._get_section_text_by_position(theme_start, next_theme_pattern)
        
        # Extract impact type (checkboxes)
        if re.search(r'☒\s*Impact positif|X\s*Impact positif|Impact positif\s*☒', theme_text, re.IGNORECASE):
            theme_data["impact_type"] = "positive"
        elif re.search(r'☒\s*Impact négatif|X\s*Impact négatif|Impact négatif\s*☒', theme_text, re.IGNORECASE):
            theme_data["impact_type"] = "negative"
        elif re.search(r'☒\s*Pas d\'impact|X\s*Pas d\'impact|Pas d\'impact\s*☒|Pas d\'impact\s*X', theme_text, re.IGNORECASE):
            theme_data["impact_type"] = "none"
        
        # Extract explanation
        explanation_patterns = [
            r'Expliquez[^\n]*\n(.*?)(?=\n\s*(?:Click here|→|\[|\d+\.|$))',
            r'↓Expliquez[^\n]*\n(.*?)(?=\n\s*(?:Click here|→|\[|\d+\.|$))',
            r'expliquer[^\n]*\n(.*?)(?=\n\s*(?:Click here|→|\[|\d+\.|$))'
        ]
        
        for pattern in explanation_patterns:
            match = re.search(pattern, theme_text, re.DOTALL | re.IGNORECASE)
            if match and match.group(1):
                explanation = self._safe_strip(match.group(1))
                if explanation:
                    # Clean up explanation
                    explanation = re.sub(r'Click here to enter text\.?', '', explanation, flags=re.IGNORECASE)
                    explanation = self._safe_strip(explanation)
                    if explanation and len(explanation) > 5:  # Valid explanation
                        theme_data["explanation"] = explanation
                        break
        
        # Extract special fields for specific themes
        if theme_num == 3:  # Gender equality
            theme_data["special_fields"] = self._extract_gender_equality_fields(theme_text)
        elif theme_num == 10:  # SMEs
            theme_data["special_fields"] = self._extract_sme_fields(theme_text)
        elif theme_num == 11:  # Administrative burdens
            # Administrative burdens handled separately
            pass
        elif theme_num == 21:  # Policy coherence for development
            theme_data["special_fields"] = self._extract_development_fields(theme_text)
        
        return theme_data
    
    def _extract_gender_equality_fields(self, theme_text: str) -> Dict[str, Any]:
        """Extract special fields for gender equality theme."""
        fields = {}
        
        # Extract person composition question
        persons_match = re.search(r'Quelles personnes sont concernées[^?]*\?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\d+\.|→)', theme_text, re.DOTALL | re.IGNORECASE)
        if persons_match and persons_match.group(1):
            fields["persons_concerned"] = self._safe_strip(persons_match.group(1))
        
        # Extract differences question
        differences_match = re.search(r'différences entre la situation[^?]*\?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\d+\.|→)', theme_text, re.DOTALL | re.IGNORECASE)
        if differences_match and differences_match.group(1):
            fields["gender_differences"] = self._safe_strip(differences_match.group(1))
        
        # Extract problematic differences
        problematic_match = re.search(r'différences problématiques[^?]*\?\s*\[O/N\]\s*>\s*([^\n]+)', theme_text, re.IGNORECASE)
        if problematic_match and problematic_match.group(1):
            fields["problematic_differences"] = self._safe_strip(problematic_match.group(1))
        
        # Extract measures
        measures_match = re.search(r'mesures sont prises[^?]*\?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\[|\n\s*\d+\.|$)', theme_text, re.DOTALL | re.IGNORECASE)
        if measures_match and measures_match.group(1):
            fields["mitigation_measures"] = self._safe_strip(measures_match.group(1))
        
        return fields
    
    def _extract_sme_fields(self, theme_text: str) -> Dict[str, Any]:
        """Extract special fields for SME theme."""
        fields = {}
        
        # Extract enterprise involvement
        enterprises_match = re.search(r'entreprises[^?]*\?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\d+\.|→)', theme_text, re.DOTALL | re.IGNORECASE)
        if enterprises_match and enterprises_match.group(1):
            fields["enterprises_involved"] = self._safe_strip(enterprises_match.group(1))
        
        # Extract SME percentage
        sme_pct_match = re.search(r'%\s*PME[^:]*:\s*([^\n]+)', theme_text, re.IGNORECASE)
        if sme_pct_match and sme_pct_match.group(1):
            fields["sme_percentage"] = self._safe_strip(sme_pct_match.group(1))
        
        # Extract impact on SMEs
        impact_match = re.search(r'impact.*?PME[^?]*\?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\[|\n\s*\d+\.|$)', theme_text, re.DOTALL | re.IGNORECASE)
        if impact_match and impact_match.group(1):
            fields["sme_impact"] = self._safe_strip(impact_match.group(1))
        
        return fields
    
    def _extract_development_fields(self, theme_text: str) -> Dict[str, Any]:
        """Extract special fields for policy coherence for development theme."""
        fields = {}
        
        # Extract impact on developing countries
        impact_match = re.search(r'impact.*?pays en développement[^?]*\?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\[|\n\s*\d+\.|$)', theme_text, re.DOTALL | re.IGNORECASE)
        if impact_match and impact_match.group(1):
            fields["development_impact"] = self._safe_strip(impact_match.group(1))
        
        return fields
    
    def _extract_administrative_burdens(self) -> Dict[str, Any]:
        """Extract detailed administrative burdens information (Theme 11)."""
        burdens = {
            "target_groups": {},
            "formalities": {},
            "documents_required": {},
            "collection_methods": {},
            "periodicity": {},
            "mitigation_measures": None
        }
        
        # Find administrative burdens section (usually part of Theme 11)
        burdens_start = self._find_section_start("Charges administratives|Administrative burdens", None)
        if burdens_start == -1:
            return burdens
        
        # Get administrative burdens text
        burdens_text = self._get_section_text_by_position(burdens_start, r'\[12\]|Énergie')
        
        # Extract target groups
        target_match = re.search(r'groupes cibles|target groups[^:]*:\s*([^\n]+)', burdens_text, re.IGNORECASE)
        if target_match and target_match.group(1):
            burdens["target_groups"]["description"] = self._safe_strip(target_match.group(1))
        
        # Extract formalities (current vs draft)
        formalities_match = re.search(r'Formalités[^:]*:\s*Régulation actuelle[^\n]*\n(.*?)\nRégulation projetée[^\n]*\n(.*?)(?=\n\s*\d+\.|$)', burdens_text, re.DOTALL | re.IGNORECASE)
        if formalities_match and formalities_match.group(1) and formalities_match.group(2):
            burdens["formalities"] = {
                "current": self._safe_strip(formalities_match.group(1)),
                "draft": self._safe_strip(formalities_match.group(2))
            }
        
        # Extract documents required
        docs_match = re.search(r'documents[^:]*:\s*Régulation actuelle[^\n]*\n(.*?)\nRégulation projetée[^\n]*\n(.*?)(?=\n\s*\d+\.|$)', burdens_text, re.DOTALL | re.IGNORECASE)
        if docs_match and docs_match.group(1) and docs_match.group(2):
            burdens["documents_required"] = {
                "current": self._safe_strip(docs_match.group(1)),
                "draft": self._safe_strip(docs_match.group(2))
            }
        
        # Extract collection methods
        collection_match = re.search(r'collecte|collection[^:]*:\s*Régulation actuelle[^\n]*\n(.*?)\nRégulation projetée[^\n]*\n(.*?)(?=\n\s*\d+\.|$)', burdens_text, re.DOTALL | re.IGNORECASE)
        if collection_match and collection_match.group(1) and collection_match.group(2):
            burdens["collection_methods"] = {
                "current": self._safe_strip(collection_match.group(1)),
                "draft": self._safe_strip(collection_match.group(2))
            }
        
        # Extract periodicity
        periodicity_match = re.search(r'périodicité|periodicity[^:]*:\s*Régulation actuelle[^\n]*\n(.*?)\nRégulation projetée[^\n]*\n(.*?)(?=\n\s*\d+\.|$)', burdens_text, re.DOTALL | re.IGNORECASE)
        if periodicity_match and periodicity_match.group(1) and periodicity_match.group(2):
            burdens["periodicity"] = {
                "current": self._safe_strip(periodicity_match.group(1)),
                "draft": self._safe_strip(periodicity_match.group(2))
            }
        
        # Extract mitigation measures
        mitigation_match = re.search(r'mesures.*?alléger|mitigation[^:]*:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*\[|\n\s*\d+\.|$)', burdens_text, re.DOTALL | re.IGNORECASE)
        if mitigation_match and mitigation_match.group(1):
            burdens["mitigation_measures"] = self._safe_strip(mitigation_match.group(1))
        
        return burdens
    
    def _find_section_start(self, start_pattern: str, end_pattern: Optional[str]) -> int:
        """Find the start position of a section."""
        match = re.search(start_pattern, self.text, re.IGNORECASE)
        if match:
            return match.start()
        return -1
    
    def _get_section_text(self, start_pos: int, end_pattern: Optional[str]) -> str:
        """Get text for a section between start position and end pattern."""
        if start_pos == -1:
            return ""
        
        if end_pattern:
            end_match = re.search(end_pattern, self.text[start_pos:], re.IGNORECASE)
            if end_match:
                return self.text[start_pos:start_pos + end_match.start()]
        
        return self.text[start_pos:]
    
    def _get_section_text_by_position(self, start_pos: int, end_pattern: Optional[str]) -> str:
        """Get text for a section starting at a specific position."""
        if start_pos == -1:
            return ""
        
        if end_pattern:
            end_match = re.search(end_pattern, self.text[start_pos:], re.IGNORECASE)
            if end_match:
                return self.text[start_pos:start_pos + end_match.start()]
        
        # Default to next 2000 characters or end of text
        return self.text[start_pos:start_pos + 2000]


def parse_ria_file(txt_path: str, output_dir: str = "RIA_json") -> str:
    """
    Parse a Belgian RIA text file and save structured JSON output.
    
    Args:
        txt_path: Path to the RIA text file
        output_dir: Directory to save JSON output (default: RIA_json)
    
    Returns:
        Path to the created JSON file
    """
    parser = BelgianRIAParser()
    result = parser.parse(txt_path)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate output filename
    txt_file = Path(txt_path)
    json_filename = txt_file.stem + ".json"
    json_path = output_path / json_filename
    
    # Save JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return str(json_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ria_parser.py <input_txt_file> [output_dir]")
        print("Example: python ria_parser.py RIA_txt/document.txt RIA_json")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "RIA_json"
    
    try:
        json_path = parse_ria_file(txt_file, output_dir)
        print(f"✅ Parsed RIA file: {txt_file}")
        print(f"✅ JSON output saved to: {json_path}")
    except Exception as e:
        print(f"❌ Error parsing RIA file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
