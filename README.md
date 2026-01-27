# RIA Automation Project

Automated Regulatory Impact Assessment (RIA) system using LLM Council architecture with Meta-Chairman synthesis, bootstrap evaluation contexts, and human-in-the-loop validation.

## Overview

This project modernizes and partially automates the Regulatory Impact Analysis (RIA) workflow used across Belgian federal administrations. It enhances quality, consistency, and analytical depth while reducing manual workload through:

- **LLM Council Architecture**: Multi-model deliberation with 3-stage process (First Opinion, Peer Review, Synthesis)
- **Meta-Chairman Model**: Dedicated synthesis model excluded from deliberation to ensure neutrality
- **Bootstrap Evaluation Contexts**: Reduces bias through varied evaluation criteria, randomized order, and consensus aggregation
- **Human-in-the-Loop (HITL)**: Strategic validation points ensuring accuracy and accountability
- **Knowledge Base Integration**: Vector database and knowledge graph for RIA document management

## Architecture

### LLM Council Process

1. **Stage 1: First Opinions** - All council models generate independent responses
2. **Stage 2: Peer Review** - Bootstrap evaluation with varied criteria and aggregated rankings
3. **Stage 3: Meta-Chairman Synthesis** - Dedicated chairman model produces final response

See [META_CHAIRMAN_FLOW.md](./META_CHAIRMAN_FLOW.md) for detailed process flow.

### Key Features

- **Bootstrap Evaluation**: Multiple iterations with varying criteria reduce pattern recognition bias
- **Meta-Chairman Separation**: Chairman model does not participate in Stages 1 or 2
- **Belgian RIA Framework**: Supports 21 standardized impact categories
- **EU Alignment**: Knowledge graph mapping Belgian categories to EU Impact Assessment framework
- **Document Processing**: PDF and DOCX extraction with OCR support

## Project Structure

```
├── backend/              # FastAPI backend with LLM Council logic
│   ├── config.py        # Model configuration and bootstrap settings
│   ├── council.py       # 3-stage deliberation orchestration
│   └── main.py          # API server
├── frontend/            # React frontend
├── PROJECT_BLUEPRINT.md # Comprehensive system architecture
├── PROJECT_DRAFT.md     # Project understanding and implementation tracks
├── functional_analysis.md # Functional analysis methodology
└── pdf_reader.py        # PDF text extraction and OCR tool
```

## Documentation

- **[PROJECT_BLUEPRINT.md](./PROJECT_BLUEPRINT.md)**: Complete system architecture, requirements, and implementation phases
- **[PROJECT_DRAFT.md](./PROJECT_DRAFT.md)**: Project understanding, HITL philosophy, and implementation strategies
- **[META_CHAIRMAN_FLOW.md](./META_CHAIRMAN_FLOW.md)**: Detailed Meta-Chairman process flow
- **[RIA_STRUCTURE_COMPARISON.md](./RIA_STRUCTURE_COMPARISON.md)**: Belgian vs EU RIA structure analysis
- **[functional_analysis.md](./functional_analysis.md)**: Functional analysis methodology guide

## Setup

### 1. Install Dependencies

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/).

### 3. Configure Models

Edit `backend/config.py` to customize the council and chairman models. The Meta-Chairman must be separate from council models.

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Implementation Tracks

- **Track 1**: LLM-based prompting for direct impact classification
- **Track 1 Phase 2**: EU Impact Assessment as gold standard with graph-based mapping
- **Track 3**: Neural network classification with LLM-driven reporting
- **Track 4**: RIA/SDG dashboard integration and visualization

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown
- **Storage:** JSON files (future: vector database, knowledge graph)
- **Package Management:** uv for Python, npm for JavaScript

## License

This project builds upon the [llm-council](https://github.com/karpathy/llm-council) architecture by Andrej Karpathy.
# Regulatory_Impact_assesement
