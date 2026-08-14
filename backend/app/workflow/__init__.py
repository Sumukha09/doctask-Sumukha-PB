"""Workflow layer for FlowDocs V2.

This package owns the data contracts that flow through the pipeline. At Step 3
it contains exactly one thing: the canonical ``WorkflowState`` TypedDict in
:mod:`app.workflow.state`. No graph, no nodes, no LLM integration, and no
orchestration code live here yet; those land in later steps.
"""
