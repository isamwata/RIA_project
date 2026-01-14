# PROJECT DRAFT

**Draft: RIA Automation & Human‑in‑the‑Loop Impact Classification Project**

## 1. Project Understanding and Current Status

The objective of the project is to modernize and partially automate the Regulatory Impact Analysis (RIA) workflow used across Belgian federal administrations. The primary focus is to enhance the quality, consistency, and analytical depth of RIAs while reducing manual workload and facilitating data-driven decision-making. As an ethical consideration, automation will not replace human judgment; instead, the project aims to embed human‑in‑the‑loop (HITL) validation at every stage to ensure accuracy, transparency, and accountability.

To support collaboration, the Uhasselt team will create a shared Trello workspace that includes internal and external stakeholders. The workspace can accommodate up to 10 participants. The key idea is to centralize task tracking, documentation, and communication, ensuring transparency and alignment across teams.

A functional analysis phase will begin next Monday in a working session with Frank. The goal is to map the current RIA workflow, identify bottlenecks, and define functional requirements for the automated system. Version 1 (V1) of the functional analysis will be delivered by the end of the month.

**Observations so far:**

Belgian RIAs are a generic, standardized framework comprising 21 fixed impact themes, along with administrative burdens.

EU impact assessments are domain-specific and analytical in nature. They identify policy-relevant thematic areas (environmental law → ecosystem types) and provide deeper analysis within those domains. Yielding more targeted and detailed assessments but with less standardization across policy areas.

**Key distinction:** Belgian RIAs prioritize standardization (utilizing the same 21 themes for all), whereas EU assessments prioritize domain relevance (thematic areas tailored to the specific policy domain).

## 2. Human‑in‑the‑Loop Design Philosophy

All proposed implementation strategies incorporate a human‑in‑the‑loop mechanism. This ensures:

- Expert oversight of automated classifications
- Continuous quality control
- A feedback loop for iterative improvement
- The possibility of training reward models for reinforcement learning in later phases

## 3. Proposed Implementation Strategies

### Phase 1: LLM‑Based Prompting for Direct Impact Classification

Fastest and most feasible short‑term approach.

**Concept:**
- Use a Large Language Model (LLM) to classify the impact of each RIA element using carefully engineered prompts.

**Workflow:**
- The system generates two separate RIA impact reports for the same input.
- A human reviewer (single‑blind) selects the more accurate report.
- Their selection becomes feedback data for iterative improvement.

**Advantages:**
- Rapid prototyping
- Minimal engineering overhead
- Immediate value for stakeholders
- Built‑in feedback loop for future reinforcement learning

**Limitations:**
- Dependent on prompt quality
- Harder to guarantee consistency across RIAs
- Model-dependent, some LLM models may produce better output than others

This approach is ideal for Phase 1.

### Phase 2: EU Impact Assessment as Gold Standard + Graph‑Based Category Mapping with Multi‑LLM Evaluation

Phase 2 introduces a structured knowledge layer that aligns Belgian RIA themes with the EU Impact Assessment (IA) framework.

**Concept:**
- Use the EU IA framework as a gold‑standard ontology, then map Belgian RIA categories onto EU categories using a graph‑based knowledge network.

**Workflow:**
- Create a graph that links EU IA categories to Belgian RIA themes.
- Merge overlapping or semantically similar categories.
- Use the graph as a constraint layer for downstream classification.

**Multi‑LLM Evaluation:**
- Multiple LLMs classify impacts using graph‑guided prompts.
- Each LLM evaluates the others across bootstrap evaluation contexts (multiple iterations, varied criteria, randomized order).
- Rankings are aggregated using a consensus method (e.g., Borda count).
- A dedicated chairman model synthesizes the final classification.
- Integrate HITL validation

**Advantages:**
- Harmonizes Belgian RIA with EU best practices
- Reduces category fragmentation
- Produces more robust, consensus‑based classifications
- Ensures neutrality through a dedicated chairman model

**Limitations:**
- Multi‑LLM evaluation may increase computational overhead
- Need vast amounts of EU-IA to cover all categories in Belgian RIA

### Phase 3: Neural Network Classification + LLM‑Generated Reporting

Most advanced and long‑term strategy.

**Concept:**
- Train a neural network to classify the impact of each RIA segment, then use an LLM to generate a full narrative report.

**Workflow:**
- Segment each RIA into thematic units
- Train a supervised classifier on labeled segments
- Use the classifier to predict impacts
- Feed predictions into an LLM to generate a coherent RIA report

**Advantages:**
- Highest potential accuracy
- Scalable and consistent
- Enables reinforcement learning from human feedback

**Limitations:**
- Requires a large labeled dataset
- Feature engineering and model training—but decoder/encoder models can be used.

The approach is ideal for Phase 3, once sufficient data and feedback have been collected.

### Phase 4: RIA–SDG Dashboard Integration and Visualization Layer

Implementation of this phase focuses on connecting the RIA automation platform to a centralized dashboard that visualizes how each RIA thematic area contributes to the UN Sustainable Development Goals (SDGs). This transforms the RIA system from a classification engine into a strategic policy‑intelligence tool, enabling policymakers, analysts, and external stakeholders to understand the broader societal impact of regulatory proposals.

**Concept:**
- Develop a dynamic dashboard that links:
  - RIA thematic areas (SMEs, gender equality, administrative burden, environment, poverty) to relevant SDGs and SDG targets (e.g., SDG 5 Gender Equality, SDG 8 Decent Work, SDG 13 Climate Action).
- The dashboard functions as a visual policy map, illustrating how federal regulations align with Belgium's commitments under the 2030 Agenda.

**Workflow:**
- Connect the structured outputs generated in Phases 1–3 to a unified data pipeline feeding the dashboard.
- Use the EU–Belgium graph ontology developed in Phase 2 to automatically map RIA themes to corresponding SDGs and targets.

## 4. Next Steps and Immediate Deliverables

### Short‑Term (Next 2 Weeks)
- Finalize and share the Trello workspace
- Begin functional analysis with Frank
- Document current RIA workflow and pain points
- Prepare initial prompt‑engineering prototypes for Phase 1

### By End of Month
- Deliver V1 of the functional analysis
- Present a prototype of the LLM‑based classification workflow
- Define evaluation metrics for HITL validation

### Medium‑Term
- Begin building the EU–Belgium category graph
- Collect human feedback for reinforcement learning
- Assess feasibility of dataset creation for neural network training
