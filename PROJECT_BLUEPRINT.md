# RIA Project Blueprint: Multi-Proposal Regulatory Impact Assessment System

## Document Information

**Version**: 1.0  
**Date**: 2024  
**Status**: Blueprint / Architecture Document  
**Purpose**: Comprehensive implementation guide for RIA system with LLM Council orchestration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Overview](#project-overview)
3. [Requirements](#requirements)
4. [System Architecture](#system-architecture)
5. [Technology Stack](#technology-stack)
6. [Data Models](#data-models)
7. [Component Specifications](#component-specifications)
8. [Integration Architecture](#integration-architecture)
9. [State Management](#state-management)
10. [Knowledge Base Design](#knowledge-base-design)
11. [Workflow Orchestration](#workflow-orchestration)
12. [Human-in-the-Loop Architecture](#human-in-the-loop-architecture)
13. [API Design](#api-design)
14. [Security & Compliance](#security--compliance)
15. [Performance & Scalability](#performance--scalability)
16. [Implementation Phases](#implementation-phases)
17. [Testing Strategy](#testing-strategy)
18. [Deployment Strategy](#deployment-strategy)

---

## Executive Summary

This document outlines the architecture and implementation blueprint for a **Multi-Proposal Regulatory Impact Assessment (RIA) System** that leverages an LLM Council architecture with Meta-Chairman pattern and Bootstrap Evaluation Contexts to generate comprehensive impact assessments for multiple regulatory proposals.

### Key Features

- **Multi-Proposal Processing**: Handle multiple RIA proposals simultaneously
- **LLM Council Integration**: Use Meta-Chairman architecture with bootstrap evaluation
- **Knowledge Base**: Vector database and knowledge graph for context and similarity
- **State Management**: Track proposal processing through complete lifecycle
- **Automated Report Generation**: Generate structured RIA reports matching government format
- **Orchestration**: Fully orchestrated workflow management

### Business Value

- **Efficiency**: Automated RIA generation reduces manual effort
- **Consistency**: Standardized assessment format across proposals
- **Knowledge Reuse**: Leverage historical RIAs for similar proposals
- **Scalability**: Process multiple proposals in parallel
- **Quality**: LLM Council ensures robust, unbiased assessments

---

## Project Overview

### Problem Statement

Government agencies need to generate Regulatory Impact Assessments (RIAs) for multiple legislative proposals. Each RIA must:

1. Assess impact across 21 predefined themes
2. Evaluate administrative burdens
3. Consider target groups (SMEs, citizens, enterprises)
4. Follow standardized format
5. Be generated efficiently and consistently

### Solution Approach

Build an orchestrated system that:
- Accepts multiple proposal inputs
- Processes each through LLM Council (Meta-Chairman + Bootstrap)
- Generates structured RIA reports
- Maintains knowledge base for future reference
- Tracks state throughout processing lifecycle

### Scope

**In Scope**:
- Multi-proposal ingestion and management
- LLM Council orchestration (3-stage process)
- RIA report generation
- Knowledge base (vector DB + knowledge graph)
- State management and workflow orchestration
- API for proposal submission and retrieval

**Out of Scope** (for initial version):
- Document version control beyond basic versioning
- Advanced analytics and reporting dashboards
- Integration with external government systems
- Complex multi-stage approval workflows

---

## Requirements

### Functional Requirements

#### FR1: Proposal Management
- **FR1.1**: System shall accept proposal creation with metadata (title, description, author, origin)
- **FR1.2**: System shall support multiple proposals simultaneously
- **FR1.3**: System shall track proposal status throughout lifecycle
- **FR1.4**: System shall maintain proposal version history
- **FR1.5**: System shall support proposal relationships (similar, related, dependent)

#### FR2: LLM Council Processing
- **FR2.1**: System shall process proposals through 3-stage LLM Council:
  - Stage 1: First opinions from council models
  - Stage 2: Bootstrap evaluation contexts (5 iterations)
  - Stage 3: Meta-Chairman synthesis
- **FR2.2**: System shall use bootstrap evaluation to reduce bias
- **FR2.3**: System shall aggregate rankings using Borda Count or configured method
- **FR2.4**: System shall store intermediate results from each stage
- **FR2.5**: System shall handle LLM API failures with retry logic

#### FR3: RIA Report Generation
- **FR3.1**: System shall generate RIA reports matching government format
- **FR3.2**: System shall assess all 21 impact themes:
  1. Combating poverty
  2. Equal opportunities and social cohesion
  3. Equality between women and men
  4. Health
  5. Employment
  6. Consumption and production patterns
  7. Economic development
  8. Investments
  9. Research and development
  10. SMEs
  11. Administrative burdens
  12. Energy
  13. Mobility
  14. Food
  15. Climate change
  16. Natural resources
  17. Outdoor and indoor air
  18. Biodiversity
  19. Nuisance
  20. Government
  21. Policy coherence for development
- **FR3.3**: System shall extract impact assessments (positive/negative/no impact) with explanations
- **FR3.4**: System shall generate administrative burden analysis
- **FR3.5**: System shall identify target groups and their involvement
- **FR3.6**: System shall generate reports in multiple formats (PDF, Word, HTML)

#### FR4: Knowledge Base
- **FR4.1**: System shall store proposal embeddings in vector database
- **FR4.2**: System shall support semantic search for similar proposals
- **FR4.3**: System shall maintain knowledge graph of relationships
- **FR4.4**: System shall query knowledge base for context during processing
- **FR4.5**: System shall update knowledge base after proposal completion

#### FR5: State Management
- **FR5.1**: System shall track proposal state through all stages
- **FR5.2**: System shall support state transitions with validation
- **FR5.3**: System shall enable resumption from any stage
- **FR5.4**: System shall maintain state history for audit trail
- **FR5.5**: System shall handle state recovery after failures

#### FR6: Workflow Orchestration
- **FR6.1**: System shall orchestrate multi-stage processing workflows
- **FR6.2**: System shall support parallel processing of multiple proposals
- **FR6.3**: System shall handle workflow failures and retries
- **FR6.4**: System shall support priority-based processing
- **FR6.5**: System shall provide workflow monitoring and logging

#### FR7: Human-in-the-Loop Review
- **FR7.1**: System shall support post-synthesis human review before report generation
- **FR7.2**: System shall support post-report human review before finalization
- **FR7.3**: System shall provide review queue management
- **FR7.4**: System shall support review actions: approve, request revision, reject
- **FR7.5**: System shall enable feedback loop for synthesis regeneration
- **FR7.6**: System shall support optional pre-processing review for high-stakes proposals
- **FR7.7**: System shall track review history and reviewer assignments
- **FR7.8**: System shall support SLA tracking for reviews

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: System shall process single proposal within 10 minutes (typical case)
- **NFR1.2**: System shall support processing 10+ proposals in parallel
- **NFR1.3**: API responses shall be < 2 seconds for status queries
- **NFR1.4**: Report generation shall complete within 30 seconds

#### NFR2: Scalability
- **NFR2.1**: System shall scale horizontally to handle increased load
- **NFR2.2**: System shall support 100+ concurrent proposals
- **NFR2.3**: Knowledge base shall support 10,000+ proposals

#### NFR3: Reliability
- **NFR3.1**: System shall have 99.5% uptime
- **NFR3.2**: System shall handle LLM API failures gracefully
- **NFR3.3**: System shall support automatic retry with exponential backoff
- **NFR3.4**: System shall maintain data consistency

#### NFR4: Security
- **NFR4.1**: System shall authenticate API requests
- **NFR4.2**: System shall encrypt sensitive data at rest
- **NFR4.3**: System shall encrypt data in transit (HTTPS)
- **NFR4.4**: System shall support role-based access control

#### NFR5: Maintainability
- **NFR5.1**: System shall be modular and extensible
- **NFR5.2**: System shall provide comprehensive logging
- **NFR5.3**: System shall support configuration without code changes
- **NFR5.4**: System shall have clear error messages

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  (Web UI, API Clients, Integration Services)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                              │
│  (Authentication, Rate Limiting, Request Routing)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Proposal    │  │  LLM Council │  │   Report      │       │
│  │  Management  │  │  Orchestrator │  │   Generator   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            │                                    │
│  ┌──────────────────────────────────────────────┐             │
│  │      Workflow Orchestrator                   │             │
│  │  (State Management, Task Scheduling)        │             │
│  └──────────────────────────────────────────────┘             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  PostgreSQL  │  │  Vector DB   │  │ Knowledge    │       │
│  │  (Structured)│  │  (Embeddings)│  │ Graph        │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  OpenRouter  │  │  File Storage│  │  Monitoring  │       │
│  │  (LLM APIs)  │  │  (S3/Local)  │  │  (Logging)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### 1. Proposal Management Service

**Responsibilities**:
- CRUD operations for proposals
- Proposal metadata management
- Version control
- Relationship tracking

**Key Operations**:
- `create_proposal(proposal_data)`
- `get_proposal(proposal_id)`
- `update_proposal(proposal_id, updates)`
- `list_proposals(filters, pagination)`
- `get_proposal_relationships(proposal_id)`

#### 2. LLM Council Orchestrator

**Responsibilities**:
- Coordinate 3-stage council process
- Manage bootstrap evaluation contexts
- Handle LLM API interactions
- Store intermediate results

**Key Operations**:
- `process_stage1(proposal_id, user_query)`
- `process_stage2(proposal_id, stage1_results)`
- `process_stage3(proposal_id, stage1_results, stage2_results)`
- `run_full_council(proposal_id, user_query)`

#### 3. Report Generator

**Responsibilities**:
- Extract structured data from synthesis
- Map to RIA format
- Generate formatted reports
- Template management

**Key Operations**:
- `extract_ria_data(synthesis_text)`
- `generate_ria_report(proposal_id, ria_data)`
- `export_report(proposal_id, format)`

#### 4. Knowledge Base Service

**Responsibilities**:
- Vector database operations
- Knowledge graph operations
- Similarity search
- Context retrieval

**Key Operations**:
- `store_proposal_embedding(proposal_id, embedding)`
- `find_similar_proposals(proposal_id, limit)`
- `query_knowledge_graph(query)`
- `update_relationships(proposal_id, relationships)`

#### 5. Workflow Orchestrator

**Responsibilities**:
- Workflow definition and execution
- State management
- Task scheduling
- Error handling and retries

**Key Operations**:
- `start_workflow(proposal_id)`
- `get_workflow_status(proposal_id)`
- `resume_workflow(proposal_id, from_stage)`
- `cancel_workflow(proposal_id)`

#### 6. State Manager

**Responsibilities**:
- State tracking
- State transitions
- State history
- Recovery support

**Key Operations**:
- `update_state(proposal_id, new_state, metadata)`
- `get_state(proposal_id)`
- `get_state_history(proposal_id)`
- `can_transition(from_state, to_state)`

#### 7. Review Management Service

**Responsibilities**:
- Review queue management
- Reviewer assignment
- Review decision tracking
- Revision history
- SLA tracking

**Key Operations**:
- `create_review_queue(proposal_id, review_type)`
- `assign_reviewer(review_id, reviewer_id)`
- `submit_review_decision(review_id, decision, feedback)`
- `get_review_queue(filters)`
- `get_revision_history(proposal_id)`

---

## Technology Stack

### Core Framework

**Language**: Python 3.11+  
**Framework**: FastAPI (for API) or Django (for full-stack)  
**Async Support**: asyncio, aiohttp

**Rationale**:
- Python has excellent LLM integration libraries
- FastAPI provides async support for concurrent processing
- Strong ecosystem for data processing

### Database Layer

#### Primary Database: PostgreSQL 15+

**Purpose**: Structured data storage

**Tables**:
- `proposals` - Proposal metadata
- `proposal_versions` - Version history
- `proposal_relationships` - Relationships between proposals
- `state_transitions` - State management
- `ria_assessments` - Impact assessments
- `administrative_burdens` - Administrative burden data
- `workflow_executions` - Workflow tracking

**Extensions**:
- `pgvector` - Vector similarity search (alternative to separate vector DB)
- `pg_trgm` - Text similarity for fuzzy matching

#### Vector Database: Option A - pgvector (PostgreSQL Extension)

**Advantages**:
- Single database for all data
- ACID transactions
- No separate infrastructure
- Good performance for moderate scale

**Use Case**: If vector DB requirements are moderate (< 1M vectors)

#### Vector Database: Option B - Dedicated Vector DB

**Options**:
- **Pinecone**: Managed, scalable, good performance
- **Weaviate**: Open-source, graph + vector capabilities
- **Qdrant**: Open-source, high performance
- **Chroma**: Lightweight, easy to use

**Use Case**: If vector DB requirements are high (> 1M vectors, high query volume)

**Recommendation**: Start with pgvector, migrate to dedicated if needed

#### Knowledge Graph: Option A - Neo4j

**Advantages**:
- Industry standard for knowledge graphs
- Excellent query language (Cypher)
- Good visualization tools
- Strong performance

**Use Case**: Complex relationship queries, graph analytics

#### Knowledge Graph: Option B - PostgreSQL with Graph Extension

**Advantages**:
- Single database
- ACID transactions
- Lower infrastructure complexity

**Use Case**: Simpler relationship queries, moderate complexity

**Recommendation**: Start with PostgreSQL + custom graph queries, migrate to Neo4j if graph complexity increases

### Workflow Orchestration

#### Option A: Apache Airflow

**Advantages**:
- Mature, battle-tested
- Rich ecosystem
- Good UI for monitoring
- Python-native

**Use Case**: Complex workflows, need for UI, team familiar with Airflow

#### Option B: Temporal

**Advantages**:
- Durable workflows
- Excellent for long-running tasks
- Strong error handling
- Language-agnostic

**Use Case**: Need for durable workflows, complex retry logic

#### Option C: Prefect

**Advantages**:
- Modern, Python-first
- Easy to use
- Good developer experience
- Cloud-native

**Use Case**: Python-focused team, modern stack preference

**Recommendation**: Prefect for modern Python stack, Airflow for enterprise/team familiarity

### Caching & Message Queue

**Redis**:
- Caching (intermediate results, embeddings)
- Session storage
- Rate limiting
- Task queue (if using Celery)

**Celery** (if not using workflow orchestrator):
- Distributed task queue
- Background job processing
- Retry logic

### LLM Integration

**OpenRouter API** (as configured):
- Access to multiple LLM providers
- Unified API interface
- Rate limiting and cost tracking

**Libraries**:
- `openai` - OpenAI-compatible API client
- `httpx` / `aiohttp` - Async HTTP clients

### File Storage

**Options**:
- **AWS S3**: Cloud storage, scalable
- **Azure Blob Storage**: Cloud storage
- **Local Filesystem**: Simple, for development
- **MinIO**: S3-compatible self-hosted

**Recommendation**: S3 for production, local for development

### Document Processing

#### Option A: Google Cloud Document AI (Recommended for Production)

**Advantages**:
- Superior OCR accuracy (Google's ML models)
- Structured data extraction (tables, forms, key-value pairs)
- Layout understanding (sections, headers, paragraphs)
- Custom processor training for RIA-specific documents
- Entity extraction (proposal metadata, impact categories)
- Batch processing capabilities

**Use Cases**:
- Complex PDFs with tables and forms
- Scanned documents
- RIA template forms
- Historical RIA document processing
- EU Impact Assessment documents

**Cost**: ~$1.50 per 1,000 pages (OCR/Form Parser)

**Implementation**: See `DOCUMENT_AI_INTEGRATION.md` for detailed integration guide

#### Option B: PyMuPDF + Tesseract OCR (Current/Fallback)

**Advantages**:
- Open-source, no cloud dependency
- Good for simple text-based PDFs
- No per-page costs
- Works offline

**Limitations**:
- Lower OCR accuracy for complex documents
- Limited structured data extraction
- Manual handling of tables and forms

**Use Cases**:
- Simple text-based PDFs
- Development/testing
- Fallback when Document AI unavailable
- Cost-sensitive scenarios

**Recommendation**: 
- Use Document AI as primary for production
- Keep PyMuPDF/Tesseract as fallback
- Hybrid approach: Document AI for complex docs, PyMuPDF for simple ones

**Libraries**:
- `pymupdf` (fitz) - PDF text extraction
- `pytesseract` - OCR for images
- `google-cloud-documentai` - Document AI integration
- `Pillow` - Image processing

### Monitoring & Logging

**Logging**:
- Python `logging` module
- Structured logging (JSON format)
- Log aggregation: ELK Stack, Loki, or cloud logging

**Monitoring**:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Sentry**: Error tracking

### Development Tools

**Code Quality**:
- `black` - Code formatting
- `ruff` - Linting
- `mypy` - Type checking
- `pytest` - Testing

**API Documentation**:
- FastAPI auto-generated docs (Swagger/OpenAPI)
- Additional documentation with MkDocs or Sphinx

---

## Data Models

### Core Entities

#### Proposal

```python
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "origin": "string",  # treaty, directive, etc.
    "author": {
        "name": "string",
        "email": "string",
        "organization": "string",
        "phone": "string"
    },
    "status": "enum",  # DRAFT, ANALYZING, COMPLETED, etc.
    "created_at": "datetime",
    "updated_at": "datetime",
    "completed_at": "datetime",
    "metadata": {
        "consultations": ["string"],
        "sources": ["string"],
        "tags": ["string"]
    }
}
```

#### RIA Assessment

```python
{
    "id": "uuid",
    "proposal_id": "uuid",
    "theme_id": "int",  # 1-21
    "theme_name": "string",
    "impact_type": "enum",  # POSITIVE, NEGATIVE, NONE
    "explanation": "string",
    "target_groups": ["string"],
    "created_at": "datetime"
}
```

#### Administrative Burden

```python
{
    "id": "uuid",
    "proposal_id": "uuid",
    "target_group": "string",  # enterprises, citizens
    "current_regulation": {
        "formalities": "string",
        "documents": "string",
        "collection_method": "string",
        "periodicity": "string"
    },
    "draft_regulation": {
        "formalities": "string",
        "documents": "string",
        "collection_method": "string",
        "periodicity": "string"
    },
    "mitigation_measures": "string"
}
```

#### State Transition

```python
{
    "id": "uuid",
    "proposal_id": "uuid",
    "from_state": "string",
    "to_state": "string",
    "timestamp": "datetime",
    "metadata": {
        "stage": "string",
        "error": "string",
        "duration": "float"
    }
}
```

#### Workflow Execution

```python
{
    "id": "uuid",
    "proposal_id": "uuid",
    "workflow_type": "string",
    "status": "enum",  # RUNNING, COMPLETED, FAILED
    "started_at": "datetime",
    "completed_at": "datetime",
    "current_stage": "string",
    "stages": [
        {
            "name": "string",
            "status": "enum",
            "started_at": "datetime",
            "completed_at": "datetime",
            "error": "string"
        }
    ]
}
```

### Database Schema (PostgreSQL)

#### Proposals Table

```sql
CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    origin VARCHAR(200),
    author_name VARCHAR(200),
    author_email VARCHAR(200),
    author_organization VARCHAR(200),
    author_phone VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_proposals_status ON proposals(status);
CREATE INDEX idx_proposals_created_at ON proposals(created_at);
```

#### RIA Assessments Table

```sql
CREATE TABLE ria_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(id),
    theme_id INTEGER NOT NULL,
    theme_name VARCHAR(200) NOT NULL,
    impact_type VARCHAR(20) NOT NULL,  -- POSITIVE, NEGATIVE, NONE
    explanation TEXT,
    target_groups TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(proposal_id, theme_id)
);

CREATE INDEX idx_ria_assessments_proposal ON ria_assessments(proposal_id);
CREATE INDEX idx_ria_assessments_theme ON ria_assessments(theme_id);
```

#### State Transitions Table

```sql
CREATE TABLE state_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(id),
    from_state VARCHAR(50),
    to_state VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_state_transitions_proposal ON state_transitions(proposal_id);
CREATE INDEX idx_state_transitions_timestamp ON state_transitions(timestamp);
```

### Vector Database Schema

#### Proposal Embeddings (pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE proposal_embeddings (
    proposal_id UUID PRIMARY KEY REFERENCES proposals(id),
    embedding vector(1536),  -- Adjust based on model
    text_content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_proposal_embeddings_vector ON proposal_embeddings 
USING ivfflat (embedding vector_cosine_ops);
```

### Knowledge Graph Schema (Neo4j)

#### Node Types

- `Proposal` - Proposal nodes
- `Theme` - 21 impact themes
- `Impact` - Impact assessments
- `Organization` - Author organizations
- `TargetGroup` - Target groups (SMEs, citizens, etc.)

#### Relationship Types

- `AFFECTS` - Proposal → Theme
- `HAS_IMPACT` - Proposal → Impact → Theme
- `RELATED_TO` - Proposal → Proposal
- `TARGETS` - Proposal → TargetGroup
- `CONSULTS` - Proposal → Organization

---

## Component Specifications

### 1. Proposal Management Service

#### API Endpoints

```
POST   /api/v1/proposals              - Create proposal
GET    /api/v1/proposals/{id}         - Get proposal
PUT    /api/v1/proposals/{id}         - Update proposal
DELETE /api/v1/proposals/{id}         - Delete proposal
GET    /api/v1/proposals              - List proposals (with filters)
GET    /api/v1/proposals/{id}/history - Get version history
POST   /api/v1/proposals/{id}/relationships - Add relationship
GET    /api/v1/proposals/{id}/similar  - Find similar proposals
```

#### Business Logic

- Validate proposal data before creation
- Generate unique proposal IDs
- Track all state changes
- Maintain version history
- Support soft deletes

### 2. LLM Council Orchestrator

#### Integration Points

- Uses existing `council.py` module
- Configures bootstrap evaluation contexts
- Manages API rate limiting
- Handles retries and errors

#### Processing Flow

```
1. Receive proposal and user query
2. Query knowledge base for similar proposals
3. Prepare context with similar RIAs
4. Stage 1: Generate first opinions (parallel)
5. Stage 2: Bootstrap evaluation (5 iterations, parallel)
6. Stage 3: Meta-Chairman synthesis
7. Store all intermediate results
8. Return final synthesis
```

#### Error Handling

- Retry failed API calls (exponential backoff)
- Store partial results
- Support resumption from any stage
- Log all errors with context

### 3. Report Generator

#### Template System

- RIA template in structured format (YAML/JSON)
- Template sections:
  - Descriptive Sheet (A, B, C, D)
  - 21 Theme Assessments
  - Administrative Burdens
  - Additional sections

#### Data Extraction

- Parse Meta-Chairman synthesis
- Extract impact assessments
- Identify target groups
- Extract administrative burden information
- Map to RIA format

#### Report Formats

- PDF (using reportlab or weasyprint)
- Word (using python-docx)
- HTML (for web viewing)
- JSON (structured data)

### 4. Knowledge Base Service

#### Vector Database Operations

- Generate embeddings using configured model
- Store proposal embeddings
- Similarity search (cosine similarity)
- Update embeddings on proposal update

#### Knowledge Graph Operations

- Create nodes for proposals, themes, impacts
- Create relationships
- Query for related proposals
- Query for theme patterns
- Visualize relationships

#### Context Retrieval

- Find similar proposals before processing
- Retrieve relevant historical RIAs
- Get theme-specific examples
- Provide context to LLM Council

### 5. Workflow Orchestrator

#### Workflow Definition

```python
workflow_stages = [
    {
        "name": "ingest",
        "handler": "ingest_proposal",
        "next_stages": ["preprocess"]
    },
    {
        "name": "preprocess",
        "handler": "preprocess_proposal",
        "next_stages": ["stage1"]
    },
    {
        "name": "stage1",
        "handler": "run_stage1",
        "next_stages": ["stage2"],
        "retry": {"max_retries": 3, "backoff": "exponential"}
    },
    {
        "name": "stage2",
        "handler": "run_stage2",
        "next_stages": ["stage3"],
        "retry": {"max_retries": 3, "backoff": "exponential"}
    },
    {
        "name": "stage3",
        "handler": "run_stage3",
        "next_stages": ["extract"],
        "retry": {"max_retries": 3, "backoff": "exponential"}
    },
    {
        "name": "extract",
        "handler": "extract_ria_data",
        "next_stages": ["generate_report"]
    },
    {
        "name": "generate_report",
        "handler": "generate_ria_report",
        "next_stages": ["update_knowledge"]
    },
    {
        "name": "update_knowledge",
        "handler": "update_knowledge_base",
        "next_stages": ["complete"]
    },
    {
        "name": "complete",
        "handler": "mark_complete",
        "next_stages": []
    }
]
```

#### Task Scheduling

- Priority queue for urgent proposals
- Batch processing for efficiency
- Resource limits (max concurrent proposals)
- Timeout handling

### 6. State Manager

#### State Machine

```
States:
- DRAFT
- PREPROCESSING
- PREPROCESSING_REVIEW_PENDING (optional)
- PREPROCESSING_REVIEW_IN_PROGRESS (optional)
- PREPROCESSING_APPROVED / PREPROCESSING_REVISION_REQUESTED
- STAGE_1_RUNNING
- STAGE_1_COMPLETE
- STAGE_2_RUNNING
- STAGE_2_COMPLETE
- STAGE_3_RUNNING
- STAGE_3_COMPLETE
- SYNTHESIS_REVIEW_PENDING
- SYNTHESIS_REVIEW_IN_PROGRESS
- SYNTHESIS_APPROVED / SYNTHESIS_REVISION_REQUESTED / SYNTHESIS_REJECTED
- EXTRACTING_DATA
- GENERATING_REPORT
- REPORT_REVIEW_PENDING
- REPORT_REVIEW_IN_PROGRESS
- REPORT_APPROVED / REPORT_EDIT_REQUESTED / REPORT_REGENERATION_REQUESTED / REPORT_REJECTED
- UPDATING_KNOWLEDGE
- KNOWLEDGE_REVIEW_PENDING (optional)
- KNOWLEDGE_REVIEW_IN_PROGRESS (optional)
- COMPLETED
- FAILED
- CANCELLED
```

#### State Transitions

- Validate transitions (not all states can transition to all states)
- Store transition history
- Support rollback to previous state
- Handle concurrent state updates

---

## Integration Architecture

### LLM Council Integration

#### Using Existing Code

- Import `council.py` module
- Use `run_full_council()` function
- Configure via `config.py`
- Extend for RIA-specific needs

#### Extensions Needed

- RIA-specific prompt templates
- Context injection from knowledge base
- RIA data extraction from synthesis
- Custom aggregation for RIA themes

### Knowledge Base Integration

#### During Processing

1. **Before Stage 1**:
   - Query vector DB for similar proposals
   - Retrieve relevant historical RIAs
   - Prepare context for council models

2. **After Completion**:
   - Generate proposal embedding
   - Store in vector DB
   - Update knowledge graph
   - Index for future searches

#### Query Patterns

- Similarity search: "Find proposals similar to this one"
- Theme search: "Find proposals affecting theme X"
- Impact search: "Find proposals with positive impact on employment"
- Relationship queries: "Find proposals related to this one"

---

## State Management

### State Storage

#### Database Table

```sql
CREATE TABLE proposal_states (
    proposal_id UUID PRIMARY KEY REFERENCES proposals(id),
    current_state VARCHAR(50) NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);
```

#### State Transitions Table

```sql
CREATE TABLE state_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(id),
    from_state VARCHAR(50),
    to_state VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    triggered_by VARCHAR(100),
    metadata JSONB
);
```

### State Management Logic

#### State Updates

- Atomic state transitions
- Validate transition rules
- Store transition history
- Update timestamps

#### Recovery

- Resume from last successful state
- Retry failed stages
- Handle partial completions
- Clean up on cancellation

---

## Knowledge Base Design

### Vector Database Design

#### Embedding Strategy

- **Proposal Embedding**: Full proposal text (title + description)
- **Theme Embedding**: Theme descriptions + examples
- **Impact Embedding**: Impact assessment explanations

#### Similarity Search

- Use cosine similarity
- Return top-K similar proposals
- Filter by status (only completed proposals)
- Weight by recency

### Knowledge Graph Design

#### Node Properties

**Proposal Nodes**:
- id, title, status, created_at

**Theme Nodes**:
- id, name, description

**Impact Nodes**:
- id, type (positive/negative/none), explanation

#### Relationship Properties

**AFFECTS**:
- strength (based on impact type)
- explanation

**RELATED_TO**:
- similarity_score
- relationship_type (similar, dependent, etc.)

### Query Examples

#### Find Similar Proposals

```cypher
MATCH (p1:Proposal {id: $proposal_id})
MATCH (p2:Proposal)-[:AFFECTS]->(t:Theme)<-[:AFFECTS]-(p1)
WHERE p2.id <> p1.id
RETURN p2, count(t) as common_themes
ORDER BY common_themes DESC
LIMIT 10
```

#### Find Proposals by Theme Impact

```cypher
MATCH (p:Proposal)-[:HAS_IMPACT]->(i:Impact)-[:ON_THEME]->(t:Theme {name: $theme_name})
WHERE i.type = $impact_type
RETURN p, i
ORDER BY p.created_at DESC
```

---

## Workflow Orchestration

### Workflow Engine Setup

#### Using Prefect (Recommended)

```python
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta

@flow(name="process_ria_proposal")
def process_ria_proposal(proposal_id: str):
    # Stage 1
    stage1_result = run_stage1(proposal_id)
    
    # Stage 2
    stage2_result = run_stage2(proposal_id, stage1_result)
    
    # Stage 3
    stage3_result = run_stage3(proposal_id, stage1_result, stage2_result)
    
    # Extract and generate
    ria_data = extract_ria_data(proposal_id, stage3_result)
    generate_report(proposal_id, ria_data)
    
    # Update knowledge base
    update_knowledge_base(proposal_id)
    
    return {"status": "completed"}
```

#### Error Handling

- Automatic retries with exponential backoff
- Failure notifications
- State persistence
- Resume from checkpoint

### Task Scheduling

- Priority-based queue
- Resource limits
- Timeout handling
- Batch processing

---

## Human-in-the-Loop Architecture

### Overview

Human-in-the-loop (HITL) review is essential for ensuring quality, compliance, and accuracy of RIA reports. The system incorporates strategic review points where human judgment adds value while maintaining workflow efficiency.

### Strategic Review Points

#### 1. Post-Synthesis Review (Critical - Essential)

**Location**: After Stage 3 (Meta-Chairman synthesis), before report generation

**Purpose**: Review the core LLM output before formatting into structured report

**Workflow**:
```
Stage 3 Complete (Meta-Chairman synthesis)
    ↓
State: SYNTHESIS_REVIEW_PENDING
    ↓
Human Review Queue
    ↓
State: SYNTHESIS_REVIEW_IN_PROGRESS
    ↓
Human Reviews Synthesis
    ↓
Decision:
  ✅ Approve → State: SYNTHESIS_APPROVED → Continue to Report Generation
  ⚠️ Request Revision → State: SYNTHESIS_REVISION_REQUESTED → Regenerate Stage 3 with feedback
  ❌ Reject → State: SYNTHESIS_REJECTED → Mark for manual review/editing
```

**What Human Sees**:
- Original proposal (title, description, metadata)
- Meta-Chairman synthesis (full text)
- Key highlights/extracted insights
- Confidence indicators
- Similar proposals for context
- Stage 1 and Stage 2 summaries (optional)

**Actions Available**:
- **Approve**: Proceed to report generation
- **Request Revision**: Provide feedback, trigger Stage 3 regeneration
- **Reject**: Flag for manual processing
- **Add Comments**: Annotations for future reference
- **View Context**: See similar proposals, historical RIAs

**Why This Is Critical**:
- Reviews core LLM reasoning before formatting
- Catches reasoning errors early
- Allows feedback to improve synthesis
- Most efficient review point (before report generation)

**Implementation Requirements**:
- Review queue dashboard
- Reviewer assignment system
- Feedback capture mechanism
- Revision request handling
- Notification system

---

#### 2. Post-Report Review (Essential)

**Location**: After RIA report generation, before finalization

**Purpose**: Final quality gate before publication/completion

**Workflow**:
```
Report Generated
    ↓
State: REPORT_REVIEW_PENDING
    ↓
Human Review Queue
    ↓
State: REPORT_REVIEW_IN_PROGRESS
    ↓
Human Reviews Complete RIA Report
    ↓
Decision:
  ✅ Approve → State: REPORT_APPROVED → Finalize and publish
  ⚠️ Request Edits → State: REPORT_EDIT_REQUESTED → Edit report directly
  ⚠️ Request Regeneration → State: REPORT_REGENERATION_REQUESTED → Regenerate from synthesis
  ❌ Reject → State: REPORT_REJECTED → Mark for complete reprocessing
```

**What Human Sees**:
- Complete RIA report in standard format
- All 21 theme assessments with impact types and explanations
- Administrative burden analysis
- Target group information
- Source synthesis (for reference)
- Review history (previous reviews, if any)

**Actions Available**:
- **Approve**: Finalize and mark as completed
- **Edit Report**: Direct manual edits to report
- **Request Regeneration**: Regenerate report with feedback
- **Reject**: Reject and reprocess from beginning
- **Add Annotations**: Comments and notes
- **Export Draft**: Download for offline review

**Why This Is Essential**:
- Final quality gate before publication
- Legal/compliance requirement
- Format compliance check
- Complete picture review
- Ensures all themes are properly assessed

**Implementation Requirements**:
- Report viewing interface
- Inline editing capabilities
- Version comparison (if regenerated)
- Export functionality
- Approval workflow

---

#### 3. Pre-Processing Review (Optional Gate)

**Location**: After proposal creation, before processing starts

**Purpose**: Quality gate for proposal data before LLM processing

**When to Use**:
- High-stakes proposals
- Unusual/complex proposals
- When data quality is uncertain
- First-time users
- Configurable per proposal type

**Workflow**:
```
Proposal Created
    ↓
[Optional] State: PREPROCESSING_REVIEW_PENDING
    ↓
Human Review (if enabled)
    ↓
Decision:
  ✅ Approve → State: PREPROCESSING_APPROVED → Start Processing
  ⚠️ Request Revision → State: PREPROCESSING_REVISION_REQUESTED → Return to creator
  ❌ Reject → State: PREPROCESSING_REJECTED → Archive proposal
```

**What Human Sees**:
- Proposal metadata
- Proposal description
- Author information
- Source documents
- Similar proposals (if any)

**Configuration**:
- Enable/disable per proposal type
- Auto-approve for standard proposals
- Require review for high-stakes proposals

---

#### 4. Knowledge Base Review (Optional)

**Location**: After report completion, before knowledge base update

**Purpose**: Quality assurance for knowledge base entries

**When to Use**:
- Low confidence scores
- Unusual proposals
- Quality assurance sampling (random or targeted)
- First-time proposal types

**Workflow**:
```
Report Completed
    ↓
[Optional] Quality Check
    ↓
Auto-approve (high confidence) OR
Human Review (low confidence/random sample)
    ↓
Decision:
  ✅ Approve → Update Knowledge Base
  ⚠️ Request Changes → Modify before indexing
  ❌ Reject → Skip knowledge base update
```

**Implementation**:
- Confidence scoring system
- Sampling strategy (random, targeted)
- Review interface for embeddings/relationships
- Approval workflow

---

### Recommended HITL Workflow

#### Standard Workflow (Most Proposals)

```
1. Proposal Created
   ↓
2. Auto-Processing Starts
   ↓
3. Stage 1, 2, 3 Complete
   ↓
4. ⚠️ HUMAN REVIEW: Post-Synthesis Review
   - Human reviews Meta-Chairman synthesis
   - Decision: Approve / Request Revision / Reject
   ↓
5. Report Generation
   ↓
6. ⚠️ HUMAN REVIEW: Post-Report Review
   - Human reviews complete RIA report
   - Decision: Approve / Edit / Request Regeneration / Reject
   ↓
7. Report Finalized
   ↓
8. Knowledge Base Updated (auto)
```

#### High-Stakes Workflow (Critical Proposals)

```
1. Proposal Created
   ↓
2. ⚠️ HUMAN REVIEW: Pre-Processing Review (Optional)
   - Human reviews proposal data
   - Decision: Approve / Request Revision
   ↓
3. Processing Starts
   ↓
4. Stage 1, 2, 3 Complete
   ↓
5. ⚠️ HUMAN REVIEW: Post-Synthesis Review
   ↓
6. Report Generation
   ↓
7. ⚠️ HUMAN REVIEW: Post-Report Review
   ↓
8. ⚠️ HUMAN REVIEW: Knowledge Base Review (Optional)
   ↓
9. Report Finalized
```

### Review Queue Management

#### Queue System

**Features**:
- **Queue Dashboard**: View all pending reviews
- **Priority Assignment**: Urgent, normal, low priority
- **Assignment System**: Auto-assign or manual assignment to reviewers
- **SLA Tracking**: Track time in queue, review duration
- **Notification System**: Email/SMS notifications for new reviews
- **Filtering**: Filter by proposal type, priority, reviewer

**Queue States**:
- `PENDING`: Waiting for reviewer assignment
- `ASSIGNED`: Assigned to reviewer, awaiting review
- `IN_REVIEW`: Currently being reviewed
- `COMPLETED`: Review completed
- `OVERDUE`: Past SLA deadline

#### Reviewer Management

**Roles**:
- **Reviewer**: Can review and approve/reject
- **Senior Reviewer**: Can review and override decisions
- **Admin**: Can manage reviewers and queues

**Assignment Rules**:
- Round-robin assignment
- Load balancing (assign to reviewer with fewest pending)
- Skill-based assignment (match proposal type to reviewer expertise)
- Manual assignment override

### Review Interface Design

#### Post-Synthesis Review Interface

**Layout**:
- **Left Panel**: Original proposal (title, description, metadata)
- **Center Panel**: Meta-Chairman synthesis (full text, scrollable)
- **Right Panel**: 
  - Key highlights (extracted insights)
  - Similar proposals (for context)
  - Confidence indicators
  - Review actions

**Features**:
- Side-by-side comparison view
- Highlighting/annotation tools
- Quick actions (approve/reject/request revision)
- Feedback text input (for revision requests)
- Context panel (similar proposals, historical RIAs)
- Confidence indicators
- Export synthesis for offline review

#### Post-Report Review Interface

**Layout**:
- **Main Panel**: Complete RIA report (formatted, scrollable)
- **Sidebar**: 
  - Report sections navigation
  - Source synthesis (collapsible)
  - Review history
  - Review actions

**Features**:
- Report viewing (PDF/HTML format)
- Inline editing (for direct edits)
- Section-by-section review
- Comparison view (if regenerated)
- Export functionality
- Annotation tools
- Approval workflow

### Feedback Loop Implementation

#### Revision Request Flow

**When Human Requests Revision**:

1. **Capture Feedback**:
   - Specific feedback text
   - Areas of concern
   - Suggested improvements
   - Priority level

2. **Feed Back to LLM Council**:
   - Incorporate feedback into Stage 3 prompt
   - Provide context about previous synthesis
   - Request specific improvements

3. **Regenerate Synthesis**:
   - Run Stage 3 again with enhanced prompt
   - Store revision history
   - Track revision iterations

4. **Review Updated Synthesis**:
   - Present new synthesis to reviewer
   - Show changes/differences (if possible)
   - Allow approval or further revision

**Revision Tracking**:
- Track number of revisions
- Store revision history
- Learn from feedback patterns
- Limit maximum revisions (configurable)

### State Machine Updates

#### Review States

Add to existing state machine:

```
States:
- DRAFT
- PREPROCESSING
- PREPROCESSING_REVIEW_PENDING (optional)
- PREPROCESSING_REVIEW_IN_PROGRESS (optional)
- PREPROCESSING_APPROVED / PREPROCESSING_REVISION_REQUESTED
- STAGE_1_RUNNING
- STAGE_1_COMPLETE
- STAGE_2_RUNNING
- STAGE_2_COMPLETE
- STAGE_3_RUNNING
- STAGE_3_COMPLETE
- ⚠️ SYNTHESIS_REVIEW_PENDING
- ⚠️ SYNTHESIS_REVIEW_IN_PROGRESS
- SYNTHESIS_APPROVED / SYNTHESIS_REVISION_REQUESTED / SYNTHESIS_REJECTED
- EXTRACTING_DATA
- GENERATING_REPORT
- ⚠️ REPORT_REVIEW_PENDING
- ⚠️ REPORT_REVIEW_IN_PROGRESS
- REPORT_APPROVED / REPORT_EDIT_REQUESTED / REPORT_REGENERATION_REQUESTED / REPORT_REJECTED
- UPDATING_KNOWLEDGE
- ⚠️ KNOWLEDGE_REVIEW_PENDING (optional)
- ⚠️ KNOWLEDGE_REVIEW_IN_PROGRESS (optional)
- COMPLETED
- FAILED
- CANCELLED
```

#### State Transition Rules

**Valid Transitions**:
- `STAGE_3_COMPLETE` → `SYNTHESIS_REVIEW_PENDING`
- `SYNTHESIS_REVIEW_PENDING` → `SYNTHESIS_REVIEW_IN_PROGRESS`
- `SYNTHESIS_REVIEW_IN_PROGRESS` → `SYNTHESIS_APPROVED` / `SYNTHESIS_REVISION_REQUESTED` / `SYNTHESIS_REJECTED`
- `SYNTHESIS_APPROVED` → `EXTRACTING_DATA`
- `SYNTHESIS_REVISION_REQUESTED` → `STAGE_3_RUNNING` (regenerate)
- `GENERATING_REPORT` → `REPORT_REVIEW_PENDING`
- `REPORT_REVIEW_PENDING` → `REPORT_REVIEW_IN_PROGRESS`
- `REPORT_REVIEW_IN_PROGRESS` → `REPORT_APPROVED` / `REPORT_EDIT_REQUESTED` / `REPORT_REGENERATION_REQUESTED` / `REPORT_REJECTED`
- `REPORT_APPROVED` → `UPDATING_KNOWLEDGE` or `COMPLETED`
- `REPORT_EDIT_REQUESTED` → `REPORT_REVIEW_PENDING` (after edits)
- `REPORT_REGENERATION_REQUESTED` → `GENERATING_REPORT` (regenerate)

### Database Schema for Reviews

#### Review Queue Table

```sql
CREATE TABLE review_queues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(id),
    review_type VARCHAR(50) NOT NULL,  -- SYNTHESIS_REVIEW, REPORT_REVIEW, etc.
    status VARCHAR(50) NOT NULL,  -- PENDING, ASSIGNED, IN_REVIEW, COMPLETED
    priority VARCHAR(20) DEFAULT 'NORMAL',  -- URGENT, NORMAL, LOW
    assigned_to UUID REFERENCES users(id),
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    sla_deadline TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_review_queues_status ON review_queues(status);
CREATE INDEX idx_review_queues_assigned_to ON review_queues(assigned_to);
CREATE INDEX idx_review_queues_sla_deadline ON review_queues(sla_deadline);
```

#### Review Decisions Table

```sql
CREATE TABLE review_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_queue_id UUID REFERENCES review_queues(id),
    proposal_id UUID REFERENCES proposals(id),
    reviewer_id UUID REFERENCES users(id),
    decision VARCHAR(50) NOT NULL,  -- APPROVED, REVISION_REQUESTED, REJECTED, EDITED
    feedback TEXT,
    comments TEXT,
    reviewed_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_review_decisions_proposal ON review_decisions(proposal_id);
CREATE INDEX idx_review_decisions_reviewer ON review_decisions(reviewer_id);
```

#### Revision History Table

```sql
CREATE TABLE revision_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(id),
    revision_number INTEGER NOT NULL,
    review_decision_id UUID REFERENCES review_decisions(id),
    feedback TEXT,
    synthesis_before TEXT,
    synthesis_after TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(proposal_id, revision_number)
);

CREATE INDEX idx_revision_history_proposal ON revision_history(proposal_id);
```

### API Endpoints for Reviews

#### Review Queue

```
GET    /api/v1/reviews/queue                    - Get review queue
GET    /api/v1/reviews/queue/{id}              - Get review queue item
POST   /api/v1/reviews/queue/{id}/assign       - Assign reviewer
POST   /api/v1/reviews/queue/{id}/start        - Start review
POST   /api/v1/reviews/queue/{id}/complete     - Complete review
GET    /api/v1/reviews/my-queue                - Get my assigned reviews
```

#### Review Decisions

```
POST   /api/v1/reviews/{id}/approve            - Approve review
POST   /api/v1/reviews/{id}/request-revision    - Request revision
POST   /api/v1/reviews/{id}/reject             - Reject review
POST   /api/v1/reviews/{id}/edit                - Edit report
GET    /api/v1/reviews/{id}/history             - Get revision history
```

#### Review Statistics

```
GET    /api/v1/reviews/stats                    - Get review statistics
GET    /api/v1/reviews/stats/sla                - Get SLA statistics
GET    /api/v1/reviews/stats/reviewer           - Get reviewer statistics
```

### Quality Metrics

#### Review Metrics to Track

- **Review Approval Rate**: % of reviews approved vs. revision requested
- **Revision Request Frequency**: How often revisions are requested
- **Time in Review**: Average time from assignment to completion
- **SLA Compliance**: % of reviews completed within SLA
- **Common Rejection Reasons**: Patterns in rejection feedback
- **Reviewer Feedback Patterns**: Learn from feedback to improve synthesis
- **Revision Iterations**: Average number of revisions per proposal

#### Quality Indicators

- **Synthesis Quality Score**: Based on approval rate, revision requests
- **Report Quality Score**: Based on approval rate, edit requests
- **Reviewer Satisfaction**: Feedback from reviewers
- **Time to Completion**: End-to-end time including reviews

### Implementation Considerations

#### Notification System

- **Email Notifications**: 
  - New review assigned
  - Review deadline approaching
  - Review completed
  - Revision requested
  
- **In-App Notifications**:
  - Real-time updates
  - Review queue changes
  - Status updates

#### SLA Management

- **SLA Configuration**: 
  - Default SLA: 24 hours for synthesis review, 48 hours for report review
  - Configurable per proposal type
  - Priority-based SLA (urgent: 4 hours, normal: 24 hours, low: 72 hours)

- **SLA Tracking**:
  - Calculate deadline on assignment
  - Track time remaining
  - Alert on approaching deadline
  - Escalate overdue reviews

#### Integration with Workflow Orchestrator

- **Workflow Pause**: Pause workflow at review points
- **Resume on Approval**: Resume workflow when approved
- **Revision Handling**: Handle revision requests in workflow
- **State Synchronization**: Keep workflow state and review state synchronized

### Benefits of This Architecture

#### Efficiency
- Two essential review points (not too many)
- Automated processing between reviews
- Parallel review queues
- Efficient feedback loop

#### Quality Assurance
- Reviews core LLM output (synthesis)
- Reviews final formatted output (report)
- Catches issues at right stages
- Human judgment where it matters most

#### Flexibility
- Optional pre-processing review for high-stakes cases
- Can request revisions with feedback
- Can edit reports directly if needed
- Configurable review requirements

#### Compliance
- Human oversight before publication
- Audit trail of all reviews
- Legal requirement satisfied
- Quality assurance documented

#### User Experience
- Clear workflow
- Reasonable review burden
- Fast turnaround for standard cases
- Good reviewer experience

---

## API Design

### REST API Endpoints

#### Proposals

```
POST   /api/v1/proposals
GET    /api/v1/proposals
GET    /api/v1/proposals/{id}
PUT    /api/v1/proposals/{id}
DELETE /api/v1/proposals/{id}
GET    /api/v1/proposals/{id}/status
POST   /api/v1/proposals/{id}/process
POST   /api/v1/proposals/{id}/cancel
```

#### Reports

```
GET    /api/v1/proposals/{id}/report
GET    /api/v1/proposals/{id}/report/{format}
POST   /api/v1/proposals/{id}/report/regenerate
```

#### Reviews (Human-in-the-Loop)

```
GET    /api/v1/reviews/queue
GET    /api/v1/reviews/queue/{id}
POST   /api/v1/reviews/queue/{id}/assign
POST   /api/v1/reviews/queue/{id}/start
POST   /api/v1/reviews/{id}/approve
POST   /api/v1/reviews/{id}/request-revision
POST   /api/v1/reviews/{id}/reject
POST   /api/v1/reviews/{id}/edit
GET    /api/v1/reviews/{id}/history
GET    /api/v1/reviews/my-queue
GET    /api/v1/reviews/stats
```

#### Knowledge Base

```
GET    /api/v1/proposals/{id}/similar
GET    /api/v1/knowledge/themes/{theme_id}/proposals
GET    /api/v1/knowledge/graph/visualize
```

### API Response Format

```json
{
    "success": true,
    "data": {},
    "metadata": {
        "timestamp": "2024-01-01T00:00:00Z",
        "request_id": "uuid"
    }
}
```

### Error Response Format

```json
{
    "success": false,
    "error": {
        "code": "PROPOSAL_NOT_FOUND",
        "message": "Proposal with ID {id} not found",
        "details": {}
    },
    "metadata": {
        "timestamp": "2024-01-01T00:00:00Z",
        "request_id": "uuid"
    }
}
```

---

## Security & Compliance

### Authentication & Authorization

- API key authentication
- JWT tokens for user sessions
- Role-based access control (RBAC)
- Proposal-level permissions

### Data Protection

- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Secure API keys and credentials
- Regular security audits

### Compliance

- GDPR compliance (if handling EU data)
- Data retention policies
- Audit logging
- Access logging

---

## Performance & Scalability

### Caching Strategy

- Cache proposal embeddings
- Cache similar proposal queries
- Cache completed RIA reports
- Use Redis for caching

### Database Optimization

- Indexes on frequently queried fields
- Partitioning for large tables
- Connection pooling
- Query optimization

### Horizontal Scaling

- Stateless API servers
- Load balancing
- Distributed task processing
- Shared database and cache

### Resource Management

- Limit concurrent LLM API calls
- Queue management for proposals
- Rate limiting
- Cost tracking

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-4)

**Goals**:
- Set up infrastructure
- Basic proposal management
- Single-proposal processing
- Simple report generation

**Deliverables**:
- Database schema
- Basic API
- Proposal CRUD
- LLM Council integration
- Basic report generation

### Phase 2: Knowledge Base (Weeks 5-8)

**Goals**:
- Vector database integration
- Knowledge graph setup
- Similarity search
- Context retrieval

**Deliverables**:
- Vector DB setup
- Embedding generation
- Similarity search API
- Knowledge graph queries

### Phase 3: Orchestration (Weeks 9-12)

**Goals**:
- Workflow orchestrator
- State management
- Multi-proposal processing
- Error handling

**Deliverables**:
- Workflow engine
- State management system
- Parallel processing
- Retry logic
- Human-in-the-loop review system

### Phase 4: Enhancement (Weeks 13-16)

**Goals**:
- Performance optimization
- Advanced features
- Monitoring
- Documentation

**Deliverables**:
- Performance improvements
- Monitoring dashboard
- Comprehensive documentation
- Testing suite

---

## Testing Strategy

### Unit Tests

- Test individual components
- Mock external dependencies
- Test error handling
- Test edge cases

### Integration Tests

- Test component interactions
- Test database operations
- Test LLM API integration
- Test workflow execution

### End-to-End Tests

- Test complete proposal processing
- Test report generation
- Test knowledge base updates
- Test error recovery

### Performance Tests

- Load testing
- Stress testing
- Scalability testing
- Cost analysis

---

## Deployment Strategy

### Development Environment

- Local development setup
- Docker Compose for services
- Mock external services
- Development database

### Staging Environment

- Production-like setup
- Real external services
- Test data
- Performance testing

### Production Environment

- High availability
- Monitoring and alerting
- Backup and recovery
- Disaster recovery plan

### Deployment Process

- CI/CD pipeline
- Automated testing
- Staged deployments
- Rollback procedures

---

## Monitoring & Observability

### Metrics

- Proposal processing time
- API response times
- Error rates
- LLM API costs
- System resource usage

### Logging

- Structured logging (JSON)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Request/response logging
- Error stack traces

### Alerting

- Failed proposals
- High error rates
- System downtime
- Cost thresholds

---

## Documentation Requirements

### Technical Documentation

- API documentation
- Database schema documentation
- Architecture diagrams
- Deployment guides

### User Documentation

- User guide
- API usage examples
- Report format guide
- Troubleshooting guide

### Developer Documentation

- Code comments
- Development setup guide
- Contributing guidelines
- Testing guide

---

## Success Criteria

### Functional

- ✅ Process multiple proposals simultaneously
- ✅ Generate accurate RIA reports
- ✅ Maintain knowledge base
- ✅ Handle errors gracefully
- ✅ Support human review workflow
- ✅ Enable feedback loop for improvements

### Performance

- ✅ Process proposal within 10 minutes
- ✅ Support 10+ concurrent proposals
- ✅ API response < 2 seconds

### Quality

- ✅ 99.5% uptime
- ✅ Accurate impact assessments
- ✅ Consistent report format
- ✅ Reliable knowledge base queries

---

## Risk Mitigation

### Technical Risks

- **LLM API Failures**: Retry logic, fallback mechanisms
- **Database Failures**: Replication, backups
- **Performance Issues**: Caching, optimization, scaling

### Business Risks

- **Inaccurate Assessments**: Human review process, validation
- **Cost Overruns**: Cost tracking, budget limits
- **Compliance Issues**: Regular audits, compliance checks

---

## Conclusion

This blueprint provides a comprehensive guide for implementing the RIA system. The architecture is designed to be:

- **Scalable**: Handle growth in proposal volume
- **Reliable**: Robust error handling and recovery
- **Maintainable**: Modular, well-documented
- **Extensible**: Easy to add features

The integration with the existing LLM Council system ensures consistency and leverages the Meta-Chairman architecture with bootstrap evaluation contexts for high-quality assessments.

---

## Appendix

### A. RIA Theme Definitions

[Detailed definitions of all 21 themes]

### B. API Examples

[Complete API request/response examples]

### C. Database Migration Scripts

[SQL migration scripts]

### D. Configuration Examples

[Configuration file examples]

### E. Glossary

[Terminology definitions]

---

**Document End**
