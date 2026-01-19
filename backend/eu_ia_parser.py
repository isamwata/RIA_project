"""
EU Impact Assessment Parser - Semantic + Structural

Extracts structured data from EU Impact Assessment documents using:
- Structural parsing (headings, numbering, annex references)
- Semantic parsing (classifying paragraphs by meaning)

Output: Logically segmented EU IA content aligned to policy analysis concepts.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class EUImpactAssessmentParser:
    """
    Parser for EU Impact Assessment documents.
    Uses both structural and semantic parsing approaches.
    """
    
    # Policy analysis concept categories for semantic classification
    POLICY_CONCEPTS = [
        "problem_definition",
        "objectives",
        "policy_options",
        "baseline",
        "impact_analysis",
        "stakeholder_analysis",
        "cost_benefit",
        "risk_assessment",
        "monitoring_evaluation",
        "subsidiarity",
        "evidence",
        "methodology"
    ]
    
    # Common EU IA structural patterns
    ANNEX_PATTERNS = [
        r'ANNEX\s+[IVX]+[:\s]+([A-Z][^A-Z]+)',
        r'Annex\s+[IVX]+[:\s]+([A-Z][^A-Z]+)',
        r'Annex\s+(\d+)[:\s]+([A-Z][^A-Z]+)'
    ]
    
    SECTION_PATTERNS = [
        r'^\d+\.\s+([A-Z][^\n]+)',  # Numbered sections: "1. Title"
        r'^[A-Z][A-Z\s]+\n',  # ALL CAPS headings
        r'^\d+\.\d+\s+([A-Z][^\n]+)',  # Subsections: "1.1 Title"
    ]
    
    def __init__(self):
        """Initialize the parser."""
        self.text = ""
        self.lines = []
    
    def parse(self, txt_path: str) -> Dict[str, Any]:
        """
        Parse an EU Impact Assessment text file and extract structured data.
        
        Args:
            txt_path: Path to the EU IA text file
        
        Returns:
            Dictionary containing structured EU IA data
        """
        txt_path = Path(txt_path)
        if not txt_path.exists():
            raise FileNotFoundError(f"EU IA text file not found: {txt_path}")
        
        # Read the text file
        self.text = txt_path.read_text(encoding='utf-8')
        self.lines = self.text.splitlines()
        
        # Extract structured data
        result = {
            "metadata": self._extract_metadata(),
            "document_structure": self._extract_document_structure(),
            "annexes": self._extract_annexes(),
            "sections": self._extract_sections(),
            "semantic_segments": self._extract_semantic_segments(),
            "policy_analysis": self._extract_policy_analysis(),
            "source_file": str(txt_path.name),
            "parsed_at": datetime.now().isoformat()
        }
        
        return result
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {
            "document_type": "EU Impact Assessment",
            "swd_reference": None,
            "com_reference": None,
            "date": None,
            "lead_dg": None,
            "policy_domain": None,
            "language": "en"
        }
        
        # Extract SWD reference (e.g., "SWD(2022) 167 final")
        swd_match = re.search(r'SWD\((\d{4})\)\s+(\d+)\s+final', self.text, re.IGNORECASE)
        if swd_match:
            metadata["swd_reference"] = f"SWD({swd_match.group(1)}) {swd_match.group(2)} final"
            metadata["year"] = swd_match.group(1)
        
        # Extract COM reference
        com_match = re.search(r'COM\((\d{4})\)\s+(\d+)\s+final', self.text, re.IGNORECASE)
        if com_match:
            metadata["com_reference"] = f"COM({com_match.group(1)}) {com_match.group(2)} final"
        
        # Extract date
        date_match = re.search(r'Brussels,?\s+(\d{1,2}\.\d{1,2}\.\d{4})', self.text)
        if date_match:
            metadata["date"] = date_match.group(1)
        
        # Extract Lead DG
        dg_match = re.search(r'Lead DG[:\s]+([A-Z]+(?:\s+[A-Z]+)*)', self.text, re.IGNORECASE)
        if dg_match:
            metadata["lead_dg"] = dg_match.group(1).strip()
        
        # Extract policy domain from title or content
        title_match = re.search(r'proposal for.*?Regulation.*?on\s+([^\n{]+)', self.text, re.IGNORECASE | re.DOTALL)
        if title_match:
            title_text = title_match.group(1).strip()
            # Clean up title
            title_text = re.sub(r'\{[^}]+\}', '', title_text).strip()
            metadata["policy_domain"] = title_text[:200]  # Limit length
        
        return metadata
    
    def _extract_document_structure(self) -> Dict[str, Any]:
        """Extract document structure (headings, numbering, hierarchy)."""
        structure = {
            "main_sections": [],
            "subsections": [],
            "heading_hierarchy": []
        }
        
        # Find all numbered sections
        section_pattern = r'^(\d+)\.\s+([A-Z][^\n]+)'
        for line in self.lines:
            match = re.match(section_pattern, line.strip())
            if match:
                structure["main_sections"].append({
                    "number": match.group(1),
                    "title": match.group(2).strip(),
                    "level": 1
                })
        
        # Find subsections (e.g., "1.1 Title")
        subsection_pattern = r'^(\d+)\.(\d+)\s+([A-Z][^\n]+)'
        for line in self.lines:
            match = re.match(subsection_pattern, line.strip())
            if match:
                structure["subsections"].append({
                    "section": match.group(1),
                    "subsection": match.group(2),
                    "title": match.group(3).strip(),
                    "level": 2
                })
        
        return structure
    
    def _extract_annexes(self) -> List[Dict[str, Any]]:
        """Extract all annexes with their content."""
        annexes = []
        
        # Find all annex markers
        annex_patterns = [
            r'ANNEX\s+([IVX]+)[:\s]+([A-Z][^\n]+)',
            r'Annex\s+([IVX]+)[:\s]+([A-Z][^\n]+)',
            r'Annex\s+(\d+)[:\s]+([A-Z][^\n]+)'
        ]
        
        annex_positions = []
        for pattern in annex_patterns:
            for match in re.finditer(pattern, self.text, re.IGNORECASE | re.MULTILINE):
                annex_positions.append({
                    "number": match.group(1),
                    "title": match.group(2).strip(),
                    "position": match.start()
                })
        
        # Sort by position
        annex_positions.sort(key=lambda x: x["position"])
        
        # Extract content for each annex
        for i, annex_info in enumerate(annex_positions):
            start_pos = annex_info["position"]
            end_pos = annex_positions[i + 1]["position"] if i + 1 < len(annex_positions) else len(self.text)
            
            annex_content = self.text[start_pos:end_pos]
            
            # Extract key information from annex
            annex_data = {
                "annex_number": annex_info["number"],
                "annex_title": annex_info["title"],
                "content": annex_content[:5000],  # First 5000 chars
                "content_length": len(annex_content),
                "sections": self._extract_annex_sections(annex_content)
            }
            
            annexes.append(annex_data)
        
        return annexes
    
    def _extract_annex_sections(self, annex_text: str) -> List[Dict[str, Any]]:
        """Extract sections within an annex."""
        sections = []
        
        # Find numbered sections within annex
        section_pattern = r'^(\d+)\.\s+([A-Z][^\n]+)'
        for match in re.finditer(section_pattern, annex_text, re.MULTILINE):
            sections.append({
                "number": match.group(1),
                "title": match.group(2).strip()
            })
        
        return sections
    
    def _extract_sections(self) -> List[Dict[str, Any]]:
        """Extract main document sections with content."""
        sections = []
        
        # Find main sections (numbered 1., 2., etc.)
        section_pattern = r'^(\d+)\.\s+([A-Z][^\n]+)'
        section_matches = list(re.finditer(section_pattern, self.text, re.MULTILINE))
        
        for i, match in enumerate(section_matches):
            section_num = match.group(1)
            section_title = match.group(2).strip()
            start_pos = match.end()
            
            # Find end position (next section or end of text)
            end_pos = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(self.text)
            
            section_content = self.text[start_pos:end_pos]
            
            sections.append({
                "section_number": section_num,
                "title": section_title,
                "content": section_content,
                "content_length": len(section_content),
                "paragraphs": self._split_into_paragraphs(section_content)
            })
        
        return sections
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines or single newline after sentence
        paragraphs = re.split(r'\n\s*\n', text)
        # Clean and filter paragraphs
        cleaned = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
        return cleaned
    
    def _extract_semantic_segments(self) -> List[Dict[str, Any]]:
        """
        Extract semantic segments by classifying paragraphs by meaning.
        Uses keyword-based classification (can be enhanced with LLM).
        """
        segments = []
        
        # Keywords for each policy concept
        concept_keywords = {
            "problem_definition": [
                "problem", "issue", "challenge", "gap", "deficiency", "shortcoming",
                "current situation", "status quo", "baseline situation"
            ],
            "objectives": [
                "objective", "goal", "aim", "purpose", "target", "intention",
                "seeks to", "intended to", "designed to"
            ],
            "policy_options": [
                "option", "alternative", "scenario", "approach", "strategy",
                "option 1", "option 2", "option 3", "baseline option"
            ],
            "baseline": [
                "baseline", "current state", "status quo", "existing situation",
                "without intervention", "do nothing"
            ],
            "impact_analysis": [
                "impact", "effect", "consequence", "outcome", "result",
                "positive impact", "negative impact", "benefit", "cost"
            ],
            "stakeholder_analysis": [
                "stakeholder", "affected", "concerned", "target group",
                "who is affected", "beneficiaries", "users"
            ],
            "cost_benefit": [
                "cost", "benefit", "economic", "financial", "expenditure",
                "savings", "efficiency", "cost-benefit", "CBA"
            ],
            "risk_assessment": [
                "risk", "uncertainty", "threat", "hazard", "vulnerability",
                "mitigation", "precautionary"
            ],
            "monitoring_evaluation": [
                "monitoring", "evaluation", "assessment", "review", "tracking",
                "indicators", "metrics", "KPIs"
            ],
            "subsidiarity": [
                "subsidiarity", "proportionality", "competence", "member state",
                "EU level", "national level"
            ],
            "evidence": [
                "evidence", "data", "study", "research", "analysis", "findings",
                "according to", "based on", "shows that"
            ],
            "methodology": [
                "methodology", "method", "approach", "framework", "model",
                "analytical", "quantitative", "qualitative"
            ]
        }
        
        # Split text into paragraphs
        paragraphs = self._split_into_paragraphs(self.text)
        
        # Classify each paragraph
        for para_idx, paragraph in enumerate(paragraphs):
            para_lower = paragraph.lower()
            
            # Find matching concepts
            matched_concepts = []
            for concept, keywords in concept_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in para_lower:
                        matched_concepts.append(concept)
                        break
            
            # If no match, try to infer from context
            if not matched_concepts:
                # Check for question patterns (often problem definition)
                if re.search(r'\?', paragraph):
                    matched_concepts.append("problem_definition")
                # Check for list patterns (often options or impacts)
                elif re.search(r'^[\d\-\•]', paragraph):
                    matched_concepts.append("policy_options")
            
            # Create segment
            if matched_concepts or len(paragraph) > 100:  # Include substantial paragraphs
                segments.append({
                    "paragraph_index": para_idx,
                    "content": paragraph,
                    "concepts": list(set(matched_concepts)) if matched_concepts else ["general"],
                    "length": len(paragraph),
                    "position": self._find_paragraph_position(paragraph)
                })
        
        return segments
    
    def _find_paragraph_position(self, paragraph: str) -> Dict[str, Any]:
        """Find the position context of a paragraph (which section/annex)."""
        position = {
            "section": None,
            "annex": None,
            "subsection": None
        }
        
        # Find paragraph in text
        para_pos = self.text.find(paragraph[:100])  # Find by first 100 chars
        if para_pos == -1:
            return position
        
        # Check if in an annex
        for annex_match in re.finditer(r'ANNEX\s+([IVX]+|[\d]+)', self.text, re.IGNORECASE):
            if annex_match.start() < para_pos:
                position["annex"] = annex_match.group(1)
        
        # Check if in a numbered section
        section_matches = list(re.finditer(r'^(\d+)\.\s+', self.text, re.MULTILINE))
        for i, match in enumerate(section_matches):
            if match.start() < para_pos:
                if i + 1 < len(section_matches):
                    if section_matches[i + 1].start() > para_pos:
                        position["section"] = match.group(1)
                else:
                    position["section"] = match.group(1)
        
        return position
    
    def _extract_policy_analysis(self) -> Dict[str, Any]:
        """Extract policy analysis elements aligned to EU IA structure."""
        analysis = {
            "problem_definition": [],
            "objectives": [],
            "policy_options": [],
            "baseline": None,
            "impact_assessment": [],
            "stakeholder_analysis": [],
            "cost_benefit_analysis": [],
            "subsidiarity_proportionality": None,
            "monitoring_evaluation": None
        }
        
        # Extract problem definition
        problem_section = self._extract_concept_section("problem_definition")
        if problem_section:
            analysis["problem_definition"] = problem_section
        
        # Extract objectives
        objectives_section = self._extract_concept_section("objectives")
        if objectives_section:
            analysis["objectives"] = objectives_section
        
        # Extract policy options
        options_section = self._extract_concept_section("policy_options")
        if options_section:
            analysis["policy_options"] = options_section
        
        # Extract baseline
        baseline_section = self._extract_concept_section("baseline")
        if baseline_section:
            analysis["baseline"] = "\n\n".join(baseline_section) if isinstance(baseline_section, list) else baseline_section
        
        # Extract impact assessment
        impact_section = self._extract_concept_section("impact_analysis")
        if impact_section:
            analysis["impact_assessment"] = impact_section
        
        # Extract stakeholder analysis
        stakeholder_section = self._extract_concept_section("stakeholder_analysis")
        if stakeholder_section:
            analysis["stakeholder_analysis"] = stakeholder_section
        
        # Extract cost-benefit
        costbenefit_section = self._extract_concept_section("cost_benefit")
        if costbenefit_section:
            analysis["cost_benefit_analysis"] = costbenefit_section
        
        # Extract subsidiarity/proportionality
        subsidiarity_text = self._extract_text_by_keywords(["subsidiarity", "proportionality"])
        if subsidiarity_text:
            analysis["subsidiarity_proportionality"] = subsidiarity_text
        
        # Extract monitoring/evaluation
        monitoring_text = self._extract_text_by_keywords(["monitoring", "evaluation", "indicators"])
        if monitoring_text:
            analysis["monitoring_evaluation"] = monitoring_text
        
        return analysis
    
    def _extract_concept_section(self, concept: str) -> Optional[List[str]]:
        """Extract sections related to a specific policy concept."""
        # Find semantic segments for this concept
        relevant_segments = [
            seg["content"] for seg in self._extract_semantic_segments()
            if concept in seg["concepts"]
        ]
        
        return relevant_segments if relevant_segments else None
    
    def _extract_text_by_keywords(self, keywords: List[str]) -> Optional[str]:
        """Extract text sections containing specific keywords."""
        paragraphs = self._split_into_paragraphs(self.text)
        
        matching_paragraphs = []
        for para in paragraphs:
            para_lower = para.lower()
            if any(keyword.lower() in para_lower for keyword in keywords):
                matching_paragraphs.append(para)
        
        if matching_paragraphs:
            return "\n\n".join(matching_paragraphs[:5])  # Return first 5 matching paragraphs
        
        return None


def parse_eu_ia_file(txt_path: str, output_dir: str = "EU_json") -> str:
    """
    Parse an EU Impact Assessment text file and save structured JSON output.
    
    Args:
        txt_path: Path to the EU IA text file
        output_dir: Directory to save JSON output (default: EU_json)
    
    Returns:
        Path to the created JSON file
    """
    parser = EUImpactAssessmentParser()
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
        print("Usage: python eu_ia_parser.py <input_txt_file> [output_dir]")
        print("Example: python eu_ia_parser.py EU_txt/document.txt EU_json")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "EU_json"
    
    try:
        json_path = parse_eu_ia_file(txt_file, output_dir)
        print(f"✅ Parsed EU IA file: {txt_file}")
        print(f"✅ JSON output saved to: {json_path}")
    except Exception as e:
        print(f"❌ Error parsing EU IA file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
