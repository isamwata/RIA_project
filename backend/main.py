"""FastAPI backend for LLM Council and RIA Assessment - Optimized Version."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import asyncio

from . import storage
from . import ria_storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .impact_assessment_generator import generate_impact_assessment
from .workflows.ria_workflow import RIAWorkflow

app = FastAPI(title="RIA Assessment API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5176", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started (with defensive error handling)
            if title_task:
                try:
                    title = await asyncio.wait_for(title_task, timeout=30.0)
                    storage.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"Title generation failed: {e}")
                    # Continue with default title

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# RIA Assessment Endpoints
# ============================================================================

class CreateRIAAssessmentRequest(BaseModel):
    """Request to create a new RIA assessment."""
    proposal: str
    metadata: Optional[Dict[str, Any]] = None


class ReviewAssessmentRequest(BaseModel):
    """Request to review an assessment."""
    action: str  # "approve", "reject", "revise"
    comments: Optional[str] = ""


class RIAAssessmentMetadata(BaseModel):
    """RIA assessment metadata for list view."""
    assessment_id: str
    proposal: str
    metadata: Dict[str, Any]
    status: str
    created_at: str
    approved_at: Optional[str] = None
    review: Optional[Dict[str, Any]] = None


@app.post("/api/ria/assessments")
async def create_ria_assessment(request: CreateRIAAssessmentRequest):
    """Create a new RIA assessment and start generation."""
    assessment_id = str(uuid.uuid4())
    
    # Create assessment record
    assessment = ria_storage.create_assessment(
        assessment_id=assessment_id,
        proposal=request.proposal,
        metadata=request.metadata or {}
    )
    
    return {
        "assessment_id": assessment_id,
        "status": "generating",
        "created_at": assessment["created_at"]
    }


@app.get("/api/ria/assessments/{assessment_id}")
async def get_ria_assessment(assessment_id: str):
    """Get a specific RIA assessment."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@app.get("/api/ria/assessments/{assessment_id}/status")
async def get_ria_assessment_status(assessment_id: str):
    """Get the status of an RIA assessment."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    return {
        "assessment_id": assessment_id,
        "status": assessment.get("status", "unknown"),
        "created_at": assessment.get("created_at"),
        "updated_at": assessment.get("updated_at"),
        "has_report": assessment.get("report") is not None
    }


@app.get("/api/ria/assessments/{assessment_id}/report")
async def get_ria_report(assessment_id: str):
    """Get the formatted RIA report."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    report = assessment.get("report")
    if report is None:
        raise HTTPException(status_code=404, detail="Report not yet generated")
    
    return report


# ============================================================================
# Helper Functions
# ============================================================================

def _map_node_to_stage(node_name: str) -> Optional[str]:
    """Map LangGraph node names to frontend stage IDs."""
    node_to_stage = {
        "ingest_proposal": "ingestion",
        "route_retrieval": "ingestion",
        "retrieve_vector_store": "retrieval",
        "retrieve_knowledge_graph": "retrieval",
        "fetch_eurostat_data": "retrieval",
        "merge_context": "retrieval",
        "fetch_euia_questions": "retrieval",
        "synthesize_context": "synthesis",
        "council_stage1": "council_stage1",
        "council_stage2": "council_stage2",
        "council_stage3": "council_stage3",
        "validate_output": "validation",
        "structure_assessment": "validation",
        "filter_forbidden_sections": "validation",
        "extract_sections": "report_ready",
    }
    return node_to_stage.get(node_name)


def _extract_final_report(final_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract final report from workflow state with fallback logic.
    
    Args:
        final_state: The final state from workflow execution
        
    Returns:
        Structured report dictionary
        
    Raises:
        ValueError: If no valid report content can be extracted
    """
    if not final_state:
        raise ValueError("Final state is empty")
    
    # Try primary report location
    final_report = final_state.get("final_report", {})
    
    # Fallback to structured_assessment
    if not final_report or not final_report.get("content"):
        final_report = final_state.get("structured_assessment", {})
    
    # Last fallback: build from stage3_result
    if not final_report or not final_report.get("content"):
        stage3_result = final_state.get("stage3_result", {})
        stage3_content = stage3_result.get("content") or stage3_result.get("response", "")
        
        if stage3_content:
            print(f"⚠️  Building report from stage3_result ({len(stage3_content)} chars)")
            final_report = {
                "content": stage3_content,
                "sections": {"21 Belgian Impact Themes Assessment": stage3_content},
                "metadata": {"model": stage3_result.get("model", "unknown")}
            }
        else:
            raise ValueError("No content found in final_report, structured_assessment, or stage3_result")
    
    # Structure the result
    structured_result = {
        "content": final_report.get("content", ""),
        "sections": final_report.get("sections", {}),
        "metadata": final_report.get("metadata", {}),
        "sources": final_report.get("sources", []),
        "eurostat_citations": final_report.get("eurostat_citations", []),
        "eurostat_data": final_report.get("eurostat_data", {})
    }
    
    # Final validation
    if not structured_result.get("content"):
        raise ValueError("Extracted report has empty content")
    
    return structured_result


async def _run_workflow_with_progress(
    workflow: RIAWorkflow,
    initial_state: Dict[str, Any],
    timeout: int = 300
):
    """
    Run LangGraph workflow and yield progress events.
    
    FIXED: Now properly handles LangGraph's stream completion and state collection.
    
    Args:
        workflow: RIAWorkflow instance
        initial_state: Initial workflow state
        timeout: Timeout in seconds
        
    Yields:
        Progress event dictionaries
        
    Returns:
        Final workflow state
        
    Raises:
        asyncio.TimeoutError: If workflow exceeds timeout
        ValueError: If workflow produces invalid state
    """
    last_node = None
    final_state = {}
    stream_completed = False
    
    try:
        print(f"🚀 Starting workflow stream (timeout: {timeout}s)")
        async with asyncio.timeout(timeout):
            node_count = 0
            async for state_update in workflow.stream(initial_state):
                # LangGraph stream format: {node_name: {state_updates}}
                if isinstance(state_update, dict):
                    # Get the node name (first key)
                    node_name = list(state_update.keys())[0] if state_update else None
                    
                    # Send progress update for new nodes only
                    if node_name and node_name != last_node:
                        node_count += 1
                        last_node = node_name
                        stage_id = _map_node_to_stage(node_name)
                        
                        if stage_id:
                            yield {
                                "type": "progress",
                                "stage": stage_id,
                                "node": node_name,
                                "message": f"Completed {node_name}"
                            }
                            print(f"📊 [{node_count}] Workflow progress: {node_name} → {stage_id}")
                    
                    # Keep track of the cumulative state
                    # LangGraph stream yields incremental updates
                    node_state = state_update.get(node_name, {}) if node_name else state_update
                    
                    if node_state:
                        # Deep merge for nested dictionaries
                        for key, value in node_state.items():
                            if key in final_state and isinstance(final_state[key], dict) and isinstance(value, dict):
                                # Deep merge nested dicts
                                final_state[key].update(value)
                            else:
                                # Replace value
                                final_state[key] = value
            
            stream_completed = True
            print(f"✅ Workflow stream completed successfully")
            print(f"   Total nodes executed: {node_count}")
            print(f"   Last node: {last_node}")
            print(f"   Final state keys: {list(final_state.keys())}")
        
    except asyncio.TimeoutError:
        print(f"⚠️  Workflow stream timed out after {timeout}s")
        raise
    except Exception as e:
        print(f"❌ Stream error: {type(e).__name__}: {e}")
        print(f"   Stream completed: {stream_completed}")
        print(f"   Last successful node: {last_node}")
        
        # If stream failed but we got some state, try to continue
        if not final_state:
            print(f"⚠️  No state collected from stream, attempting invoke() fallback")
            try:
                final_state = await workflow.invoke(initial_state)
                print(f"✅ Fallback invoke() successful")
            except Exception as invoke_error:
                print(f"❌ Fallback invoke() also failed: {invoke_error}")
                raise e  # Re-raise original error
        else:
            print(f"⚠️  Partial state collected ({len(final_state)} keys), attempting to continue")
    
    # Validate we got a final state
    if not final_state:
        raise ValueError(f"Workflow stream did not produce final state (stream_completed={stream_completed})")
    
    print(f"✅ Yielding complete event with final state ({len(final_state)} keys)")
    yield {"type": "complete", "final_state": final_state}


@app.post("/api/ria/assessments/{assessment_id}/stream")
async def stream_ria_assessment(assessment_id: str):
    """Stream RIA workflow progress using LangGraph."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    proposal = assessment["proposal"]
    metadata = assessment.get("metadata", {})
    
    async def event_generator():
        workflow_generator = None
        last_node = None
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STREAMING RIA ASSESSMENT: {assessment_id}")
            print(f"{'='*80}\n")
            
            # Initial state
            yield f"data: {json.dumps({'type': 'workflow_start', 'stage': 'ingestion'})}\n\n"
            
            # Update status to generating
            ria_storage.update_assessment(assessment_id, {
                "status": "generating"
            })
            print("✓ Status updated to 'generating'")
            
            # Initialize workflow
            workflow = RIAWorkflow()
            print("✓ Workflow initialized")
            
            initial_state = {
                "proposal": proposal,
                "context": {
                    **metadata,
                    "retrieval_strategy": metadata.get("retrieval_strategy", "hybrid"),
                    "top_k": metadata.get("top_k", 20)
                }
            }
            print(f"✓ Initial state prepared")
            
            # Run workflow with progress streaming
            print(f"🔄 Starting workflow execution...\n")
            workflow_generator = _run_workflow_with_progress(
                workflow, 
                initial_state, 
                timeout=300
            )
            
            final_state = None
            progress_count = 0
            
            async for event in workflow_generator:
                if event["type"] == "progress":
                    progress_count += 1
                    # Send progress event to frontend
                    last_node = event.get("node")
                    yield f"data: {json.dumps({'type': 'stage', 'stage': event['stage'], 'node': event['node'], 'message': event['message']})}\n\n"
                    
                elif event["type"] == "complete":
                    final_state = event["final_state"]
                    print(f"\n✅ Workflow completed. Final state received.")
                    print(f"   Progress events sent: {progress_count}")
            
            # Validate final state
            if not final_state:
                error_msg = "Workflow completed without final state"
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            print(f"\n{'='*80}")
            print(f"📊 FINAL STATE ANALYSIS")
            print(f"{'='*80}")
            print(f"State keys: {list(final_state.keys())}")
            
            # Check for workflow errors (filter out warnings)
            errors = final_state.get("errors", [])
            # Filter out warnings - only treat actual errors as failures
            actual_errors = [
                e for e in errors 
                if not e.startswith("⚠️") and not e.startswith("Warning:") 
                and "models responded" not in e
            ]
            
            if actual_errors:
                error_msg = "; ".join(actual_errors)
                print(f"❌ Workflow errors found: {error_msg}")
                ria_storage.update_assessment(assessment_id, {
                    "status": "failed",
                    "error": error_msg
                })
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            elif errors:
                # Log warnings but don't fail
                warnings = [e for e in errors if e.startswith("⚠️") or "Warning:" in e or "models responded" in e]
                if warnings:
                    print(f"ℹ️  Workflow warnings (non-critical): {len(warnings)} warnings")
                    for warning in warnings:
                        print(f"   {warning}")
            
            # Debug: Check what we have in final_state
            has_final_report = bool(final_state.get('final_report'))
            has_structured = bool(final_state.get('structured_assessment'))
            has_stage3 = bool(final_state.get('stage3_result'))
            
            print(f"Has final_report: {has_final_report}")
            print(f"Has structured_assessment: {has_structured}")
            print(f"Has stage3_result: {has_stage3}")
            
            if has_final_report:
                fr = final_state['final_report']
                if isinstance(fr, dict):
                    print(f"  final_report keys: {list(fr.keys())}")
                    content_len = len(fr.get('content', ''))
                    print(f"  final_report content: {content_len} chars")
            
            if has_stage3:
                s3 = final_state['stage3_result']
                if isinstance(s3, dict):
                    print(f"  stage3_result keys: {list(s3.keys())}")
                    content_len = len(s3.get('content') or s3.get('response', ''))
                    print(f"  stage3_result content: {content_len} chars")
            
            # Extract and validate report
            print(f"\n🔄 Extracting report from final state...")
            try:
                structured_result = _extract_final_report(final_state)
                content_length = len(structured_result.get('content', ''))
                print(f"✅ Report extracted successfully")
                print(f"   Content length: {content_length} chars")
                print(f"   Report keys: {list(structured_result.keys())}")
                print(f"   Sections: {list(structured_result.get('sections', {}).keys())}")
            except Exception as e:
                print(f"❌ Report extraction failed: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Update assessment with results
            print(f"\n💾 Saving assessment to storage...")
            try:
                ria_storage.update_assessment(assessment_id, {
                    "status": "review_required",
                    "report": structured_result,
                    "workflow_metadata": {
                        "workflow_type": "langgraph",
                        "chunks_used": len(final_state.get("merged_chunks", [])),
                        "retry_count": final_state.get("retry_count", 0),
                        "validation_passed": final_state.get("validation_passed", False)
                    }
                })
                print(f"✅ Assessment saved successfully")
            except Exception as e:
                print(f"❌ Failed to save assessment: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Verify it was saved
            print(f"\n🔍 Verifying storage...")
            verification = ria_storage.get_assessment(assessment_id)
            if verification and verification.get("report"):
                saved_content_len = len(verification["report"].get("content", ""))
                print(f"✅ Verification successful")
                print(f"   Status: {verification.get('status')}")
                print(f"   Report exists: Yes ({saved_content_len} chars)")
            else:
                print(f"⚠️  Warning: Report may not have been saved correctly")
                print(f"   Verification status: {verification.get('status') if verification else 'None'}")
            
            print(f"\n{'='*80}")
            print(f"✅ WORKFLOW COMPLETE")
            print(f"{'='*80}\n")
            
            # Send completion events (no large payloads over SSE)
            print(f"📤 Sending completion events to frontend...")
            yield f"data: {json.dumps({'type': 'workflow_complete', 'stage': 'report_ready', 'assessment_id': assessment_id})}\n\n"
            yield f"data: {json.dumps({'type': 'review_required', 'data': {'assessment_id': assessment_id}})}\n\n"
            print(f"✅ All events sent. Stream complete.\n")
            
        except asyncio.TimeoutError:
            error_msg = "Workflow execution timed out after 5 minutes"
            print(f"❌ {error_msg}")
            
            ria_storage.update_assessment(assessment_id, {
                "status": "failed",
                "error": error_msg
            })
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            
        except ValueError as e:
            # Validation errors (empty report, missing state, etc.)
            error_msg = f"Workflow validation failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            error_context = {
                "error": str(e),
                "last_node": last_node,
                "assessment_id": assessment_id,
            }
            print(f"Validation error context: {json.dumps(error_context, indent=2)}")
            
            ria_storage.update_assessment(assessment_id, {
                "status": "failed",
                "error": error_msg
            })
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            
        except Exception as e:
            import traceback
            error_msg = f"Workflow execution failed: {str(e)}"
            error_trace = traceback.format_exc()
            
            # Structured error context
            error_context = {
                "error": str(e),
                "error_type": type(e).__name__,
                "last_node": last_node,
                "assessment_id": assessment_id,
            }
            print(f"RIA workflow error: {json.dumps(error_context, indent=2)}\n{error_trace}")
            
            ria_storage.update_assessment(assessment_id, {
                "status": "failed",
                "error": error_msg
            })
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/ria/assessments/{assessment_id}/stream/legacy")
async def stream_ria_assessment_legacy(assessment_id: str):
    """Stream RIA workflow progress using legacy direct function calls."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    proposal = assessment["proposal"]
    metadata = assessment.get("metadata", {})
    
    async def event_generator():
        try:
            # Initial state
            yield f"data: {json.dumps({'type': 'workflow_start', 'stage': 'ingestion'})}\n\n"
            
            # Update status to generating
            ria_storage.update_assessment(assessment_id, {
                "status": "generating"
            })
            
            # Run the Impact Assessment Generator (same as test)
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'retrieval', 'message': 'Retrieving relevant context...'})}\n\n"
            
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'generation', 'message': 'Generating impact assessment...'})}\n\n"
            
            result = await generate_impact_assessment(
                query=proposal,
                context=metadata,
                use_council=True
            )
            
            # Check if generation failed
            if result.get("model") == "error" or not result.get("content"):
                error_msg = result.get("content", "Unable to generate assessment. Please check your API keys.")
                ria_storage.update_assessment(assessment_id, {
                    "status": "failed",
                    "error": error_msg
                })
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return
            
            # Structure the result to match expected format
            # generate_impact_assessment returns: {content, sections, metadata, sources, eurostat_citations, eurostat_data}
            final_report = {
                "content": result.get("content", ""),
                "sections": result.get("sections", {}),
                "metadata": result.get("metadata", {}),
                "sources": result.get("sources", []),
                "eurostat_citations": result.get("eurostat_citations", []),
                "eurostat_data": result.get("eurostat_data", {})
            }
            
            # Update assessment with results
            ria_storage.update_assessment(assessment_id, {
                "status": "review_required",
                "report": final_report,
                "workflow_metadata": {
                    "chunks_used": result.get("metadata", {}).get("chunks_used", 0),
                    "model": result.get("metadata", {}).get("model", "unknown"),
                    "retrieval_strategy": result.get("metadata", {}).get("retrieval_strategy", "unknown")
                }
            })
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'workflow_complete', 'stage': 'report_ready'})}\n\n"
            # IMPORTANT: Don't stream the full report payload over SSE (it can be very large,
            # especially with Eurostat baseline data). The frontend will fetch it via
            # GET /api/ria/assessments/{assessment_id} or /report.
            yield f"data: {json.dumps({'type': 'review_required', 'data': {'assessment_id': assessment_id}})}\n\n"
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"RIA workflow error: {error_msg}\n{error_trace}")
            
            # Update status to failed
            ria_storage.update_assessment(assessment_id, {
                "status": "failed",
                "error": error_msg
            })
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/ria/assessments/{assessment_id}/review")
async def review_ria_assessment(assessment_id: str, request: ReviewAssessmentRequest):
    """Submit review decision for an assessment."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    if request.action == "approve":
        updated = ria_storage.approve_assessment(
            assessment_id=assessment_id,
            reviewer="user",  # TODO: Get from auth
            comments=request.comments or ""
        )
        return {"status": "approved", "assessment": updated}
    
    elif request.action == "reject":
        updated = ria_storage.reject_assessment(
            assessment_id=assessment_id,
            reviewer="user",  # TODO: Get from auth
            comments=request.comments or ""
        )
        return {"status": "rejected", "assessment": updated}
    
    elif request.action == "revise":
        # Mark as needs revision, return to proposal editing
        updated = ria_storage.update_assessment(assessment_id, {
            "status": "revising",
            "review": {
                "reviewed_at": datetime.now().isoformat(),
                "reviewer": "user",
                "action": "revise",
                "comments": request.comments or ""
            }
        })
        return {"status": "revising", "assessment": updated}
    
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")


@app.get("/api/ria/assessments", response_model=List[RIAAssessmentMetadata])
async def list_ria_assessments(status: Optional[str] = None):
    """List all RIA assessments, optionally filtered by status."""
    assessments = ria_storage.list_assessments(status=status)
    return assessments


@app.get("/api/ria/assessments/{assessment_id}/report")
async def get_ria_report(assessment_id: str):
    """Get the formatted RIA report."""
    assessment = ria_storage.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    report = assessment.get("report")
    if report is None:
        raise HTTPException(status_code=404, detail="Report not yet generated")
    
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
