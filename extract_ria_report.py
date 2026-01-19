#!/usr/bin/env python3
"""
Extract RIA report from JSON result and save as text file.
"""

import json
from pathlib import Path

def extract_report(json_file: str = "test_langgraph_result.json", output_file: str = "ria_report.txt"):
    """Extract RIA report from JSON and save as text."""
    
    # Load the result file
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    report_text = []
    report_text.append('=' * 80)
    report_text.append('BELGIAN REGULATORY IMPACT ASSESSMENT (RIA) REPORT')
    report_text.append('Generated using EU-style detailed analysis')
    report_text.append('=' * 80)
    report_text.append('')
    
    # Proposal
    proposal = data.get('proposal', '')
    if proposal:
        report_text.append('PROPOSAL:')
        report_text.append('-' * 80)
        report_text.append(proposal)
        report_text.append('')
        report_text.append('')
    
    # Metadata
    metadata = data.get('final_report', {}).get('metadata', {})
    if metadata:
        report_text.append('METADATA:')
        report_text.append('-' * 80)
        report_text.append(f'  Generated at: {metadata.get("generated_at", "Unknown")}')
        report_text.append(f'  Model: {metadata.get("model", "Unknown")}')
        report_text.append(f'  Retrieval Strategy: {metadata.get("retrieval_strategy", "Unknown")}')
        report_text.append(f'  Chunks Used: {metadata.get("chunks_used", 0)}')
        report_text.append('')
        report_text.append('')
    
    # Final report
    final_report = data.get('final_report', {})
    
    # Note: We only show structured sections, not the full raw content
    # The structured sections contain the organized assessment
    
    # Sections
    sections = final_report.get('sections', {})
    if sections:
        report_text.append('=' * 80)
        report_text.append('STRUCTURED SECTIONS')
        report_text.append('=' * 80)
        report_text.append('')
        
        # Separate sections by priority
        background_section = sections.get('Background and Problem Definition', '')
        impact_themes_section = sections.get('21 Belgian Impact Themes Assessment', '') or sections.get('21 Impact Themes Assessment', '')
        other_sections = {k: v for k, v in sections.items() if k not in ['Background and Problem Definition', '21 Belgian Impact Themes Assessment', '21 Impact Themes Assessment']}
        
        # Print Background/Problem Definition FIRST (most important)
        if background_section:
            report_text.append('=' * 80)
            report_text.append('BACKGROUND AND PROBLEM DEFINITION')
            report_text.append('=' * 80)
            report_text.append('')
            report_text.append(background_section)
            report_text.append('')
            report_text.append('')
        
        # Print other sections (Executive Summary, Proposal Overview, etc.)
        for section_name, section_content in other_sections.items():
            if section_content:
                report_text.append(section_name.upper())
                report_text.append('-' * 80)
                report_text.append(section_content)
                report_text.append('')
                report_text.append('')
        
        # Print 21 Belgian Impact Themes Assessment prominently
        if impact_themes_section:
            report_text.append('=' * 80)
            report_text.append('21 BELGIAN IMPACT THEMES ASSESSMENT')
            report_text.append('(Standard Belgian RIA Structure with EU-style Analysis)')
            report_text.append('=' * 80)
            report_text.append('')
            report_text.append(impact_themes_section)
            report_text.append('')
            report_text.append('')
    
    # Note: Retrieved context is used internally to inform the assessment but not shown in final report
    # Citations in the assessment content should reference the documents that were used
    
    # Sources
    sources = final_report.get('sources', [])
    if sources:
        report_text.append('=' * 80)
        report_text.append('SOURCES')
        report_text.append('=' * 80)
        report_text.append('')
        for i, source in enumerate(sources, 1):
            report_text.append(f'{i}. {source.get("document", "Unknown")}')
            report_text.append(f'   Jurisdiction: {source.get("jurisdiction", "Unknown")}')
            report_text.append(f'   Category: {source.get("category", "Unknown")}')
            report_text.append(f'   Year: {source.get("year", "Unknown")}')
            report_text.append('')
    
    # Write to file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_text))
    
    file_size = output_path.stat().st_size
    print(f'✅ RIA Report saved to: {output_file}')
    print(f'   File size: {file_size:,} bytes')
    print(f'   Sections: {len([s for s in sections.values() if s])}/{len(sections)}')
    print(f'   Sources: {len(sources)}')

if __name__ == "__main__":
    import sys
    json_file = sys.argv[1] if len(sys.argv) > 1 else "test_langgraph_result.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "ria_report.txt"
    extract_report(json_file, output_file)
