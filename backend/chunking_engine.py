"""
Multi-Level Chunking Engine - Stage 2

Breaks documents into multiple complementary chunk types:
- Category Chunks: High-level policy categories
- Analysis Chunks: Core reasoning units
- Evidence Chunks: Fine-grained factual material
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Chunk:
    """Represents a single chunk with metadata."""
    chunk_id: str
    chunk_type: str  # "category", "analysis", "evidence"
    content: str
    metadata: Dict[str, Any]
    source_document: str
    position: Dict[str, Any]  # section, page, theme_number, etc.


class PolicyCategoryMapper:
    """Maps document content to high-level policy categories."""
    
    # High-level policy categories
    POLICY_CATEGORIES = [
        "Environment",
        "Digital",
        "Competition",
        "Health",
        "Fundamental Rights",
        "Employment",
        "Economic Development",
        "Social Cohesion",
        "Energy",
        "Transport",
        "Agriculture",
        "Education",
        "Research & Innovation",
        "Public Administration",
        "International Relations"
    ]
    
    # Mapping from Belgian 21 themes to policy categories
    BELGIAN_THEME_TO_CATEGORY = {
        # Theme 1: Lutte contre la pauvreté
        1: ["Social Cohesion", "Fundamental Rights"],
        # Theme 2: Égalité des chances et cohésion sociale
        2: ["Social Cohesion", "Fundamental Rights"],
        # Theme 3: Égalité des femmes et les hommes
        3: ["Fundamental Rights", "Social Cohesion"],
        # Theme 4: Santé
        4: ["Health"],
        # Theme 5: Emploi
        5: ["Employment", "Economic Development"],
        # Theme 6: Consommation et production
        6: ["Economic Development", "Environment"],
        # Theme 7: Développement économique
        7: ["Economic Development"],
        # Theme 8: Investissements
        8: ["Economic Development"],
        # Theme 9: Recherche et développement
        9: ["Research & Innovation", "Economic Development"],
        # Theme 10: PME
        10: ["Economic Development", "Competition"],
        # Theme 11: Charges administratives
        11: ["Public Administration", "Economic Development"],
        # Theme 12: Énergie
        12: ["Energy", "Environment"],
        # Theme 13: Mobilité
        13: ["Transport", "Environment"],
        # Theme 14: Alimentation
        14: ["Health", "Agriculture"],
        # Theme 15: Changement climatique
        15: ["Environment", "Energy"],
        # Theme 16: Ressources naturelles
        16: ["Environment"],
        # Theme 17: Air extérieur et intérieur
        17: ["Environment", "Health"],
        # Theme 18: Biodiversité
        18: ["Environment"],
        # Theme 19: Nuisances
        19: ["Environment", "Health"],
        # Theme 20: Gouvernement
        20: ["Public Administration"],
        # Theme 21: Cohérence des politiques pour le développement
        21: ["International Relations", "Economic Development"]
    }
    
    # Keywords for EU policy domain mapping
    EU_DOMAIN_KEYWORDS = {
        "Environment": ["environment", "biodiversity", "climate", "nature", "ecosystem", "pollution", "emission"],
        "Digital": ["digital", "cyber", "data", "ai", "algorithm", "platform", "online", "internet"],
        "Competition": ["competition", "market", "antitrust", "merger", "cartel", "dominance"],
        "Health": ["health", "medical", "pharmaceutical", "disease", "treatment", "patient"],
        "Fundamental Rights": ["rights", "discrimination", "equality", "freedom", "privacy", "dignity"],
        "Employment": ["employment", "labour", "worker", "job", "unemployment", "workplace"],
        "Economic Development": ["economic", "growth", "trade", "market", "business", "sme"],
        "Energy": ["energy", "renewable", "electricity", "power", "fuel", "carbon"],
        "Transport": ["transport", "mobility", "vehicle", "road", "rail", "aviation"],
        "Agriculture": ["agriculture", "farming", "food", "rural", "crop", "livestock"],
        "Research & Innovation": ["research", "innovation", "technology", "development", "science"],
        "Public Administration": ["administration", "governance", "public service", "regulation"],
        "International Relations": ["international", "trade", "development", "cooperation", "global"]
    }
    
    @classmethod
    def map_belgian_theme(cls, theme_number: int) -> List[str]:
        """Map Belgian theme number to policy categories."""
        return cls.BELGIAN_THEME_TO_CATEGORY.get(theme_number, ["General"])
    
    @classmethod
    def map_eu_domain(cls, policy_domain: str) -> List[str]:
        """Map EU policy domain to policy categories."""
        if not policy_domain:
            return ["General"]
        
        domain_lower = policy_domain.lower()
        matched_categories = []
        
        for category, keywords in cls.EU_DOMAIN_KEYWORDS.items():
            if any(keyword in domain_lower for keyword in keywords):
                matched_categories.append(category)
        
        return matched_categories if matched_categories else ["General"]


class ChunkingEngine:
    """Multi-level chunking engine for RIA and EU IA documents."""
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        """
        Initialize chunking engine.
        
        Args:
            max_chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.category_mapper = PolicyCategoryMapper()
    
    def process_document(self, json_path: str) -> List[Chunk]:
        """
        Process a parsed document and create chunks.
        
        Args:
            json_path: Path to JSON file from Stage 1
        
        Returns:
            List of chunks
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            doc_data = json.load(f)
        
        # Determine document type
        if "impact_themes" in doc_data:
            return self._process_belgian_ria(doc_data, json_path.name)
        elif "semantic_segments" in doc_data:
            return self._process_eu_ia(doc_data, json_path.name)
        else:
            raise ValueError(f"Unknown document type: {json_path.name}")
    
    def _process_belgian_ria(self, doc_data: Dict[str, Any], source_file: str) -> List[Chunk]:
        """Process Belgian RIA document."""
        chunks = []
        metadata = doc_data.get("metadata", {})
        
        # Extract base metadata
        base_metadata = {
            "jurisdiction": "Belgian",
            "document_type": "RIA",
            "document_id": metadata.get("document_id"),
            "date": metadata.get("date"),
            "language": metadata.get("language", "fr"),
            "year": self._extract_year(metadata.get("date"))
        }
        
        # 1. Category Chunks
        categories = self._extract_categories_belgian(doc_data)
        for category in categories:
            chunk = Chunk(
                chunk_id=f"{source_file}_category_{category}",
                chunk_type="category",
                content=f"Policy Category: {category}\nDocument: {source_file}\nJurisdiction: Belgian Federal",
                metadata={**base_metadata, "category": category},
                source_document=source_file,
                position={"type": "category", "category": category}
            )
            chunks.append(chunk)
        
        # 2. Analysis Chunks (from impact themes)
        impact_themes = doc_data.get("impact_themes", [])
        for theme in impact_themes:
            if theme.get("impact_type") and theme.get("impact_type") != "none":
                # Create analysis chunk for each theme with impact
                analysis_content = self._build_analysis_content_belgian(theme, doc_data)
                
                # Get categories for this theme
                theme_categories = self.category_mapper.map_belgian_theme(theme.get("theme_number", 0))
                
                chunk = Chunk(
                    chunk_id=f"{source_file}_analysis_theme_{theme.get('theme_number')}",
                    chunk_type="analysis",
                    content=analysis_content,
                    metadata={
                        **base_metadata,
                        "analysis_type": "impact_assessment",
                        "theme_number": theme.get("theme_number"),
                        "theme_name": theme.get("theme_name"),
                        "impact_type": theme.get("impact_type"),
                        "categories": theme_categories
                    },
                    source_document=source_file,
                    position={
                        "type": "theme",
                        "theme_number": theme.get("theme_number"),
                        "section": "impact_themes"
                    }
                )
                chunks.append(chunk)
        
        # 3. Evidence Chunks (from administrative burdens, special fields)
        evidence_chunks = self._extract_evidence_belgian(doc_data, source_file, base_metadata)
        chunks.extend(evidence_chunks)
        
        return chunks
    
    def _process_eu_ia(self, doc_data: Dict[str, Any], source_file: str) -> List[Chunk]:
        """Process EU Impact Assessment document."""
        chunks = []
        metadata = doc_data.get("metadata", {})
        
        # Extract base metadata
        base_metadata = {
            "jurisdiction": "EU",
            "document_type": "Impact Assessment",
            "swd_reference": metadata.get("swd_reference"),
            "com_reference": metadata.get("com_reference"),
            "lead_dg": metadata.get("lead_dg"),
            "policy_domain": metadata.get("policy_domain"),
            "date": metadata.get("date"),
            "language": metadata.get("language", "en"),
            "year": metadata.get("year")
        }
        
        # Map policy domain to categories
        categories = self.category_mapper.map_eu_domain(metadata.get("policy_domain", ""))
        
        # 1. Category Chunks
        for category in categories:
            chunk = Chunk(
                chunk_id=f"{source_file}_category_{category}",
                chunk_type="category",
                content=f"Policy Category: {category}\nDocument: {source_file}\nPolicy Domain: {metadata.get('policy_domain', 'N/A')}\nJurisdiction: EU",
                metadata={**base_metadata, "category": category},
                source_document=source_file,
                position={"type": "category", "category": category}
            )
            chunks.append(chunk)
        
        # 2. Analysis Chunks (from policy_analysis and semantic_segments)
        policy_analysis = doc_data.get("policy_analysis", {})
        
        # Problem definition chunks
        if policy_analysis.get("problem_definition"):
            for i, problem_text in enumerate(policy_analysis["problem_definition"]):
                chunk = Chunk(
                    chunk_id=f"{source_file}_analysis_problem_{i}",
                    chunk_type="analysis",
                    content=f"Problem Definition:\n\n{problem_text}",
                    metadata={
                        **base_metadata,
                        "analysis_type": "problem_definition",
                        "categories": categories
                    },
                    source_document=source_file,
                    position={"type": "analysis", "section": "problem_definition", "index": i}
                )
                chunks.append(chunk)
        
        # Policy options chunks
        if policy_analysis.get("policy_options"):
            for i, option_text in enumerate(policy_analysis["policy_options"]):
                chunk = Chunk(
                    chunk_id=f"{source_file}_analysis_option_{i}",
                    chunk_type="analysis",
                    content=f"Policy Option:\n\n{option_text}",
                    metadata={
                        **base_metadata,
                        "analysis_type": "policy_option",
                        "categories": categories
                    },
                    source_document=source_file,
                    position={"type": "analysis", "section": "policy_options", "index": i}
                )
                chunks.append(chunk)
        
        # Impact assessment chunks
        if policy_analysis.get("impact_assessment"):
            for i, impact_text in enumerate(policy_analysis["impact_assessment"]):
                chunk = Chunk(
                    chunk_id=f"{source_file}_analysis_impact_{i}",
                    chunk_type="analysis",
                    content=f"Impact Analysis:\n\n{impact_text}",
                    metadata={
                        **base_metadata,
                        "analysis_type": "impact_assessment",
                        "categories": categories
                    },
                    source_document=source_file,
                    position={"type": "analysis", "section": "impact_assessment", "index": i}
                )
                chunks.append(chunk)
        
        # Baseline chunks
        if policy_analysis.get("baseline"):
            baseline_text = policy_analysis["baseline"]
            if isinstance(baseline_text, list):
                baseline_text = "\n\n".join(baseline_text)
            
            chunk = Chunk(
                chunk_id=f"{source_file}_analysis_baseline",
                chunk_type="analysis",
                content=f"Baseline Scenario:\n\n{baseline_text}",
                metadata={
                    **base_metadata,
                    "analysis_type": "baseline",
                    "categories": categories
                },
                source_document=source_file,
                position={"type": "analysis", "section": "baseline"}
            )
            chunks.append(chunk)
        
        # 3. Evidence Chunks (from annexes, citations, statistics)
        evidence_chunks = self._extract_evidence_eu(doc_data, source_file, base_metadata)
        chunks.extend(evidence_chunks)
        
        return chunks
    
    def _extract_categories_belgian(self, doc_data: Dict[str, Any]) -> List[str]:
        """Extract unique categories from Belgian RIA."""
        categories = set()
        impact_themes = doc_data.get("impact_themes", [])
        
        for theme in impact_themes:
            theme_num = theme.get("theme_number", 0)
            theme_categories = self.category_mapper.map_belgian_theme(theme_num)
            categories.update(theme_categories)
        
        return sorted(list(categories))
    
    def _build_analysis_content_belgian(self, theme: Dict[str, Any], doc_data: Dict[str, Any]) -> str:
        """Build analysis content for Belgian RIA theme."""
        content_parts = [
            f"Theme {theme.get('theme_number')}: {theme.get('theme_name')}",
            f"Impact Type: {theme.get('impact_type', 'N/A')}",
            ""
        ]
        
        if theme.get("explanation"):
            content_parts.append("Explanation:")
            content_parts.append(theme["explanation"])
        
        # Add special fields if present
        special_fields = theme.get("special_fields", {})
        if special_fields:
            content_parts.append("")
            content_parts.append("Additional Information:")
            for key, value in special_fields.items():
                if value:
                    content_parts.append(f"{key}: {value}")
        
        return "\n".join(content_parts)
    
    def _extract_evidence_belgian(self, doc_data: Dict[str, Any], source_file: str, base_metadata: Dict[str, Any]) -> List[Chunk]:
        """Extract evidence chunks from Belgian RIA."""
        chunks = []
        
        # Administrative burdens
        admin_burdens = doc_data.get("administrative_burdens", {})
        if admin_burdens:
            # Extract formalities
            if admin_burdens.get("formalities"):
                formalities = admin_burdens["formalities"]
                content = f"Administrative Burdens - Formalities:\n\nCurrent: {formalities.get('current', 'N/A')}\n\nDraft: {formalities.get('draft', 'N/A')}"
                
                chunk = Chunk(
                    chunk_id=f"{source_file}_evidence_formalities",
                    chunk_type="evidence",
                    content=content,
                    metadata={
                        **base_metadata,
                        "evidence_type": "administrative_burdens",
                        "subtype": "formalities"
                    },
                    source_document=source_file,
                    position={"type": "evidence", "section": "administrative_burdens", "subtype": "formalities"}
                )
                chunks.append(chunk)
            
            # Extract mitigation measures
            if admin_burdens.get("mitigation_measures"):
                chunk = Chunk(
                    chunk_id=f"{source_file}_evidence_mitigation",
                    chunk_type="evidence",
                    content=f"Mitigation Measures:\n\n{admin_burdens['mitigation_measures']}",
                    metadata={
                        **base_metadata,
                        "evidence_type": "administrative_burdens",
                        "subtype": "mitigation_measures"
                    },
                    source_document=source_file,
                    position={"type": "evidence", "section": "administrative_burdens", "subtype": "mitigation"}
                )
                chunks.append(chunk)
        
        # Sources
        sources = doc_data.get("descriptive_sheet", {}).get("D_Sources", {}).get("sources")
        if sources and sources != "Néant":
            chunk = Chunk(
                chunk_id=f"{source_file}_evidence_sources",
                chunk_type="evidence",
                content=f"Sources:\n\n{sources}",
                metadata={
                    **base_metadata,
                    "evidence_type": "sources"
                },
                source_document=source_file,
                position={"type": "evidence", "section": "sources"}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_evidence_eu(self, doc_data: Dict[str, Any], source_file: str, base_metadata: Dict[str, Any]) -> List[Chunk]:
        """Extract evidence chunks from EU IA."""
        chunks = []
        
        # Annexes
        annexes = doc_data.get("annexes", [])
        for i, annex in enumerate(annexes[:10]):  # Limit to first 10 annexes
            annex_content = annex.get("content", "")
            if len(annex_content) > 100:  # Only include substantial annexes
                # Split large annexes into smaller chunks
                annex_chunks = self._split_text(annex_content, f"{source_file}_evidence_annex_{annex.get('annex_number')}")
                
                for j, chunk_content in enumerate(annex_chunks):
                    chunk = Chunk(
                        chunk_id=f"{source_file}_evidence_annex_{annex.get('annex_number')}_{j}",
                        chunk_type="evidence",
                        content=f"Annex {annex.get('annex_number')}: {annex.get('annex_title', '')}\n\n{chunk_content}",
                        metadata={
                            **base_metadata,
                            "evidence_type": "annex",
                            "annex_number": annex.get("annex_number"),
                            "annex_title": annex.get("annex_title")
                        },
                        source_document=source_file,
                        position={
                            "type": "evidence",
                            "section": "annex",
                            "annex_number": annex.get("annex_number"),
                            "chunk_index": j
                        }
                    )
                    chunks.append(chunk)
        
        # Extract citations and statistics from semantic segments
        semantic_segments = doc_data.get("semantic_segments", [])
        for segment in semantic_segments:
            content = segment.get("content", "")
            
            # Check if segment contains evidence (statistics, citations)
            if self._is_evidence_segment(content):
                chunk = Chunk(
                    chunk_id=f"{source_file}_evidence_segment_{segment.get('paragraph_index')}",
                    chunk_type="evidence",
                    content=content,
                    metadata={
                        **base_metadata,
                        "evidence_type": "statistical_citation",
                        "concepts": segment.get("concepts", [])
                    },
                    source_document=source_file,
                    position={
                        "type": "evidence",
                        "section": "semantic_segment",
                        "paragraph_index": segment.get("paragraph_index"),
                        "position": segment.get("position", {})
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _is_evidence_segment(self, text: str) -> bool:
        """Check if text segment contains evidence (statistics, citations)."""
        # Patterns for evidence
        evidence_patterns = [
            r'\d+%',  # Percentages
            r'\d+\.\d+',  # Decimal numbers
            r'\([A-Z][a-z]+\s+et\s+al\.',  # Citations
            r'\([A-Z][a-z]+\s+\d{4}\)',  # Year citations
            r'https?://',  # URLs
            r'Table\s+\d+',  # Table references
            r'Figure\s+\d+',  # Figure references
            r'Annex\s+[IVX]+',  # Annex references
        ]
        
        text_lower = text.lower()
        for pattern in evidence_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for statistical keywords
        stats_keywords = ["percent", "percentage", "statistic", "data", "study", "research", "finding"]
        if any(keyword in text_lower for keyword in stats_keywords):
            return True
        
        return False
    
    def _split_text(self, text: str, base_id: str) -> List[str]:
        """Split large text into chunks with overlap."""
        if len(text) <= self.max_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.max_chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for paragraph break
                    para_end = text.rfind('\n\n', start, end)
                    if para_end > start:
                        end = para_end + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _extract_year(self, date_str: Optional[str]) -> Optional[str]:
        """Extract year from date string."""
        if not date_str:
            return None
        
        # Try to find 4-digit year
        year_match = re.search(r'\d{4}', date_str)
        if year_match:
            return year_match.group(0)
        
        return None


def chunk_document(json_path: str, output_dir: str = "chunks") -> str:
    """
    Process a document and save chunks to JSON.
    
    Args:
        json_path: Path to JSON file from Stage 1
        output_dir: Directory to save chunk files
    
    Returns:
        Path to saved chunks file
    """
    engine = ChunkingEngine()
    chunks = engine.process_document(json_path)
    
    # Convert chunks to dict format
    chunks_data = {
        "source_document": Path(json_path).name,
        "chunk_count": len(chunks),
        "chunks": [asdict(chunk) for chunk in chunks],
        "created_at": datetime.now().isoformat()
    }
    
    # Save to output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    source_name = Path(json_path).stem
    output_file = output_path / f"{source_name}_chunks.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    return str(output_file)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python chunking_engine.py <input_json_file> [output_dir]")
        print("Example: python chunking_engine.py RIA_json/document.json chunks")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "chunks"
    
    try:
        output_path = chunk_document(json_file, output_dir)
        print(f"✅ Processed document: {json_file}")
        print(f"✅ Chunks saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
