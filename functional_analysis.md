# Functional Analysis Methodology for RIA Automation Project

## Overview

This document provides a comprehensive methodology for conducting the functional analysis phase of the RIA Automation & Human‑in‑the‑Loop Impact Classification Project. The functional analysis will map the current RIA workflow, identify bottlenecks, and define functional requirements for the automated system.

---

## 1. Current State Analysis (As-Is)

### A. Workflow Mapping

**Activities:**

1. **Document the current RIA process end-to-end**
   - Start: Proposal submission/initiation
   - End: Final RIA report approval/publication
   - Map all steps, decision points, handoffs

2. **Identify all actors and roles**
   - Who creates proposals?
   - Who performs impact analysis?
   - Who reviews/approves?
   - Who uses the final RIA?

3. **Document current tools and systems**
   - What software/tools are used?
   - What templates/forms exist?
   - What databases/repositories are accessed?
   - What communication channels are used?

4. **Capture time and effort**
   - How long does each step take?
   - How many people are involved?
   - What are the bottlenecks?
   - Where is most time spent?

**Deliverable**: Current state workflow diagram and process documentation

---

### B. Pain Points and Bottlenecks

**Questions to explore:**
- What takes the longest time?
- Where do errors/mistakes commonly occur?
- What is repetitive or manual?
- Where is information lost or duplicated?
- What causes delays?
- What is frustrating for users?
- Where is quality inconsistent?

**Methods:**
- Interviews with RIA creators/reviewers
- Observation sessions (watch them work)
- Survey/questionnaire
- Analysis of historical RIAs (time stamps, versions)

**Deliverable**: Pain points matrix with severity and frequency

---

### C. Data and Information Flow

**Map:**
- What information is needed to create an RIA?
- Where does it come from?
- How is it collected?
- How is it stored?
- How is it shared?
- What information is lost or not captured?

**Focus areas:**
- Proposal documents
- Historical RIAs
- Policy documents
- Consultation responses
- Evidence sources
- Administrative burden data

**Deliverable**: Information flow diagram and data inventory

---

## 2. Stakeholder Engagement

### A. Identify All Stakeholders

**Internal:**
- RIA creators/analysts
- Reviewers/validators
- Policy makers
- IT support
- Management/decision makers

**External:**
- Impact Analysis Committee (IAC)
- AI4Belgium
- Network of impact evaluators (via Wouter Eerdekens)
- BOSA representatives
- End users of RIA reports

### B. Stakeholder Interviews

**Structure interviews around:**
1. **Current process** (how do you do it now?)
2. **Pain points** (what's difficult/frustrating?)
3. **Requirements** (what do you need?)
4. **Success criteria** (what would make this successful?)
5. **Concerns** (what are you worried about?)

**Key questions:**
- How do you currently assess each of the 21 impact categories?
- How do you determine positive/negative/no impact?
- What information do you need to make these assessments?
- How do you handle administrative burdens analysis?
- What would an ideal system look like?
- What must the system do vs. what would be nice to have?

**Deliverable**: Stakeholder requirements matrix

---

## 3. Requirements Gathering

### A. Functional Requirements

**Organize by functional area:**

#### 1. Proposal Management
- Create/edit proposals
- Store proposal metadata
- Version control
- Proposal relationships

#### 2. Impact Classification
- Classify each of 21 impact categories
- Determine impact type (positive/negative/no impact)
- Generate explanations
- Handle special cases (gender, SMEs, administrative burdens)

#### 3. Administrative Burdens Analysis
- Compare current vs. draft regulation
- Identify formalities and obligations
- Document collection methods
- Assess mitigation measures

#### 4. Knowledge Base
- Store historical RIAs
- Similarity search
- Context retrieval
- EU-Belgium category mapping

#### 5. Human Review
- Review queue management
- Reviewer assignment
- Feedback capture
- Approval workflow

#### 6. Report Generation
- Generate RIA report in standard format
- Export to different formats (PDF, Word)
- Template management

#### 7. Workflow Orchestration
- Process multiple proposals
- Track state/progress
- Handle errors and retries
- Notifications

**Deliverable**: Functional requirements specification (FRD)

---

### B. Non-Functional Requirements

**Performance:**
- Processing time per proposal
- Concurrent proposal handling
- API response times
- System availability

**Quality:**
- Accuracy of impact classifications
- Consistency across RIAs
- Completeness of assessments

**Usability:**
- User interface requirements
- Ease of use
- Training needs

**Security:**
- Data protection
- Access control
- Audit logging

**Compliance:**
- GDPR requirements
- Government standards
- Administrative procedures

**Deliverable**: Non-functional requirements specification

---

## 4. Gap Analysis

### A. Current vs. Future State

**Compare:**
- Current manual process vs. automated system
- Current capabilities vs. required capabilities
- Current pain points vs. proposed solutions

**Identify:**
- What can be automated?
- What must remain manual?
- What needs human oversight?
- What are the gaps to fill?

**Deliverable**: Gap analysis document

---

## 5. Use Cases and Scenarios

### A. Primary Use Cases

#### 1. Create New RIA
- **Actor**: RIA analyst
- **Trigger**: New proposal submitted
- **Flow**: System processes → Human reviews → Report generated
- **Success**: Complete RIA report in standard format

#### 2. Review Impact Classification
- **Actor**: Human reviewer
- **Trigger**: System generates impact classifications
- **Flow**: Review synthesis → Approve/Request revision → Finalize
- **Success**: Validated impact classifications

#### 3. Generate RIA Report
- **Actor**: System + Human reviewer
- **Trigger**: Impact classifications approved
- **Flow**: Extract data → Format report → Review → Finalize
- **Success**: Complete RIA report

#### 4. Find Similar RIAs
- **Actor**: RIA analyst
- **Trigger**: Need context for new proposal
- **Flow**: Search knowledge base → Retrieve similar RIAs → Use as context
- **Success**: Relevant historical RIAs found

**Deliverable**: Use case specifications

---

### B. Edge Cases and Error Scenarios

**Consider:**
- What if LLM fails?
- What if human reviewer rejects?
- What if proposal is incomplete?
- What if knowledge base has no similar RIAs?
- What if multiple reviewers disagree?

**Deliverable**: Error handling and edge case documentation

---

## 6. Data Requirements

### A. Input Data

**What data is needed:**
- Proposal text/description
- Author information
- Consultation information
- Source documents
- Historical RIAs (for knowledge base)
- EU Impact Assessments (for mapping)

**Data quality requirements:**
- Completeness
- Accuracy
- Format standards
- Update frequency

**Deliverable**: Data requirements specification

---

### B. Output Data

**What data is produced:**
- Impact classifications (21 categories)
- Explanations
- Administrative burden analysis
- Final RIA report
- Review decisions
- Feedback data

**Output format requirements:**
- Report format (PDF, Word, HTML)
- Data structure (JSON, database)
- Metadata requirements

**Deliverable**: Output specification

---

## 7. Integration Points

### A. External Systems

**Identify:**
- What systems need to integrate?
- What data needs to be exchanged?
- What APIs exist?
- What standards must be followed?

**Consider:**
- Government databases
- Policy document repositories
- Consultation platforms
- Reporting systems

**Deliverable**: Integration requirements

---

## 8. Success Metrics and KPIs

### A. Define Success Criteria

**Quantitative:**
- Time to generate RIA (current vs. automated)
- Accuracy of classifications
- Consistency across RIAs
- Human review approval rate
- System uptime/availability

**Qualitative:**
- User satisfaction
- Quality of assessments
- Ease of use
- Transparency

**Deliverable**: Success metrics definition

---

## 9. Documentation Structure for V1

### Recommended Structure:

```
Functional Analysis V1
├── Executive Summary
├── Current State Analysis
│   ├── Workflow Mapping
│   ├── Pain Points and Bottlenecks
│   ├── Data and Information Flow
│   └── Current Tools and Systems
├── Stakeholder Analysis
│   ├── Stakeholder Map
│   ├── Interview Summaries
│   └── Requirements by Stakeholder
├── Requirements Specification
│   ├── Functional Requirements
│   ├── Non-Functional Requirements
│   └── Data Requirements
├── Use Cases
│   ├── Primary Use Cases
│   └── Edge Cases
├── Gap Analysis
│   ├── Current vs. Future State
│   └── Automation Opportunities
├── Integration Requirements
├── Success Metrics
└── Recommendations
    ├── Priority Features
    ├── Implementation Approach
    └── Risk Assessment
```

---

## 10. Practical Approach for Your Project

### Week 1: Discovery

**Day 1-2: Preparation**
- Review existing RIA documents
- Prepare interview questions
- Set up Trello board structure
- Schedule stakeholder meetings

**Day 3-4: Current State Mapping**
- Interview RIA creators (2-3 people)
- Map current workflow
- Document tools and processes
- Identify pain points

**Day 5: Consolidation**
- Create workflow diagrams
- Document findings
- Identify key questions for follow-up

### Week 2: Requirements Gathering

**Day 1-2: Stakeholder Interviews**
- Interview reviewers/validators
- Interview policy makers
- Interview IAC representative (if scheduled)
- Document requirements

**Day 3: Requirements Analysis**
- Organize requirements by functional area
- Prioritize requirements
- Identify conflicts or gaps

**Day 4: Use Case Development**
- Define primary use cases
- Document workflows
- Identify edge cases

**Day 5: Documentation**
- Write functional analysis V1
- Create diagrams
- Prepare for review

---

## 11. Key Questions to Answer

### About Current Process:
1. How long does it take to complete an RIA currently?
2. How many people are involved?
3. What percentage of time is spent on each activity?
4. What are the most time-consuming tasks?
5. Where do errors commonly occur?
6. What information is hardest to find?

### About Requirements:
1. What must the system do (must-have)?
2. What should the system do (should-have)?
3. What could the system do (nice-to-have)?
4. What must the system NOT do?
5. What are the critical success factors?
6. What would make users reject the system?

### About Administrative Burdens (PoC Focus):
1. How is administrative burden currently assessed?
2. What data is needed for this assessment?
3. What are the current vs. draft regulation comparison requirements?
4. How are formalities and obligations documented?
5. What mitigation measures are typically identified?
6. What would make this assessment better?

---

## 12. Tools and Techniques

### For Workflow Mapping:
- **Swimlane diagrams** (show who does what)
- **Process flowcharts** (show steps and decisions)
- **Value stream mapping** (identify waste)
- **BPMN notation** (if using process modeling tools)

### For Requirements Gathering:
- **User stories** (As a... I want... So that...)
- **MoSCoW prioritization** (Must/Should/Could/Won't)
- **Requirements traceability matrix**
- **Acceptance criteria** (definition of done)

### For Documentation:
- **Confluence/Notion** (collaborative documentation)
- **Trello** (task tracking)
- **Draw.io/Lucidchart** (diagrams)
- **Markdown** (structured documentation)

---

## 13. Deliverables Checklist

**Functional Analysis V1 should include:**

- [ ] Current state workflow diagram
- [ ] Pain points and bottlenecks list
- [ ] Stakeholder map and interview summaries
- [ ] Functional requirements (organized by area)
- [ ] Non-functional requirements
- [ ] Use case specifications (3-5 primary use cases)
- [ ] Data requirements (input/output)
- [ ] Gap analysis (current vs. future)
- [ ] Success metrics definition
- [ ] Recommendations for implementation
- [ ] Risk assessment
- [ ] Next steps

---

## 14. Focus Areas for PoC (Administrative Burdens)

**Since PoC focuses on administrative burdens, ensure:**

1. **Deep dive into administrative burden assessment:**
   - Current methodology
   - Required data and information
   - Comparison requirements (current vs. draft)
   - Documentation standards
   - Review and validation process

2. **Specific requirements for administrative burdens:**
   - How to identify target groups
   - How to compare regulations
   - How to document formalities
   - How to assess mitigation measures
   - How to format the output

3. **Success criteria for PoC:**
   - What constitutes success for administrative burden automation?
   - How will you measure improvement?
   - What feedback is needed?

---

## 15. Recommendations

### Best Practices:

1. **Start with the end in mind**
   - Define what success looks like
   - Work backwards to requirements

2. **Involve stakeholders early and often**
   - Get buy-in
   - Validate assumptions
   - Build trust

3. **Focus on value**
   - Prioritize high-impact, high-frequency activities
   - Address biggest pain points first

4. **Document as you go**
   - Don't wait until the end
   - Use templates
   - Keep it organized

5. **Validate continuously**
   - Check understanding with stakeholders
   - Confirm requirements
   - Adjust as needed

### For Your Specific Project:

- **Leverage existing work**: Use the LLM Council architecture already implemented
- **Focus on PoC scope**: Administrative burdens first, expand later
- **Plan for HITL**: Design review points from the start
- **Consider knowledge base**: Plan for EU-Belgium mapping early
- **Think scalability**: Design for multiple proposals from the beginning

---

## 16. Interview Guide Template

### For RIA Creators/Analysts:

**Opening:**
- What is your role in the RIA process?
- How long have you been creating RIAs?
- How many RIAs do you typically work on per month/year?

**Current Process:**
- Walk me through how you create an RIA from start to finish
- What tools do you use?
- What information do you need?
- Where do you get it from?

**Pain Points:**
- What takes the most time?
- What is most frustrating?
- Where do errors occur?
- What would make your job easier?

**Impact Classification:**
- How do you assess each of the 21 impact categories?
- How do you determine if impact is positive, negative, or none?
- What information do you need for each category?
- How do you handle administrative burdens specifically?

**Vision:**
- What would an ideal system look like?
- What must it do?
- What concerns do you have about automation?

### For Reviewers/Validators:

**Current Process:**
- What is your role in reviewing RIAs?
- What do you look for when reviewing?
- How long does review typically take?
- What are common issues you find?

**Quality Concerns:**
- What makes a good RIA?
- What makes a bad RIA?
- How do you ensure consistency?
- What standards must be met?

**Automation Concerns:**
- What concerns do you have about automated RIAs?
- What must remain human-reviewed?
- How would you want to provide feedback?

---

## 17. Workflow Mapping Template

### Current State Workflow

**Process Steps:**
1. [Step name]
   - Actor: [Who]
   - Input: [What]
   - Action: [How]
   - Output: [What]
   - Time: [How long]
   - Tools: [What tools]

2. [Step name]
   - ...

**Decision Points:**
- [Decision point]
  - If [condition] → [action]
  - If [condition] → [action]

**Handoffs:**
- From [Actor A] to [Actor B]
  - What is transferred
  - How it's transferred
  - When it happens

---

## 18. Requirements Template

### Functional Requirement Template

**FR-[ID]: [Requirement Name]**

- **Description**: [What the system must do]
- **Priority**: Must-have / Should-have / Could-have
- **Source**: [Which stakeholder/use case]
- **Acceptance Criteria**:
  - [Criterion 1]
  - [Criterion 2]
- **Dependencies**: [Other requirements this depends on]
- **Notes**: [Additional context]

### Example:

**FR-001: Classify Impact for Each of 21 Categories**

- **Description**: System must classify impact (positive/negative/no impact) for each of the 21 Belgian RIA impact categories
- **Priority**: Must-have
- **Source**: Primary use case - Create New RIA
- **Acceptance Criteria**:
  - System classifies all 21 categories
  - Classification includes impact type (positive/negative/no impact)
  - Classification includes brief explanation
  - Classification is accurate (validated by human reviewer)
- **Dependencies**: FR-002 (Proposal input), FR-003 (LLM Council processing)
- **Notes**: Special handling needed for themes 3 (gender), 10 (SMEs), 11 (administrative burdens)

---

## 19. Gap Analysis Template

### Current State vs. Future State

| Aspect | Current State | Future State | Gap | Solution |
|--------|---------------|--------------|-----|----------|
| Impact Classification | Manual, time-consuming | Automated via LLM Council | Need automation | Implement LLM Council |
| Knowledge Access | Scattered, hard to find | Centralized, searchable | Need knowledge base | Build vector DB + graph |
| Consistency | Varies by analyst | Standardized | Need standardization | Use templates + LLM |
| Review Process | Ad-hoc | Structured workflow | Need workflow | Implement review system |
| Report Generation | Manual formatting | Automated | Need automation | Build report generator |

---

## 20. Success Metrics Template

### Quantitative Metrics

| Metric | Current Baseline | Target | Measurement Method |
|--------|------------------|--------|-------------------|
| Time to complete RIA | [X] hours | [Y] hours | Track processing time |
| Accuracy of classifications | [X]% | [Y]% | Human review validation |
| Consistency across RIAs | [X]% | [Y]% | Compare similar RIAs |
| Human review approval rate | [X]% | [Y]% | Track review decisions |
| System uptime | [X]% | 99.5% | Monitor system availability |

### Qualitative Metrics

- User satisfaction score (survey)
- Quality of assessments (expert review)
- Ease of use (usability testing)
- Transparency (audit trail completeness)

---

## Conclusion

This methodology provides a comprehensive framework for conducting the functional analysis. The key is to:

1. **Understand the current state** thoroughly
2. **Engage stakeholders** meaningfully
3. **Document requirements** clearly
4. **Plan for the future** strategically
5. **Focus on value** (administrative burdens for PoC)

By following this approach, you'll produce a Functional Analysis V1 that provides a solid foundation for system implementation.

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Status**: Methodology Guide
