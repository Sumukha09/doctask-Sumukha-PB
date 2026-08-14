"""Prompts and LLM output schemas for workflow nodes."""
from typing import Literal
from pydantic import BaseModel, Field


class ExtractedClaim(BaseModel):
    statement: str = Field(..., description="A standalone factual claim made in the text.")
    exact_quote: str = Field(..., description="The exact substring from the source text that supports this claim.")

class ExtractionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list, description="List of extracted claims.")


class ExtractedFinding(BaseModel):
    title: str = Field(..., description="A short, descriptive title for the finding.")
    summary: str = Field(..., description="A clear explanation of the conflict or finding.")
    severity: Literal["low", "medium", "high", "critical", "passed"] = Field(..., description="Severity of the finding. Use 'passed' ONLY for satisfied compliance rules.")
    claim_ids: list[str] = Field(default_factory=list, description="List of the exact Claim IDs involved in this finding. DO NOT use this for compliance checks against the corpus.")
    new_claims: list[ExtractedClaim] = Field(default_factory=list, description="Evidence directly inferred from the raw corpus. You MUST provide a new claim with a verbatim exact_quote from the raw corpus for EVERY compliance finding (whether satisfied, missing, or contradicted).")

class AnalysisResult(BaseModel):
    findings: list[ExtractedFinding] = Field(default_factory=list, description="List of discovered findings or conflicts.")


class VerificationResult(BaseModel):
    supports_claim: Literal["verified", "contradicted", "insufficient_evidence"] = Field(
        ..., description="Whether the evidence verifies, contradicts, or is insufficient to support the claim."
    )
    relevance_score: float = Field(
        ..., description="Score between 0.0 and 1.0 indicating how strongly the evidence relates to the claim."
    )



EXTRACT_SYSTEM_PROMPT = """You are an expert document analyst.
Your task is to extract atomic, factual claims from the provided text chunk.
For each claim, you MUST provide the exact, verbatim quote from the text that serves as evidence.
Do not hallucinate claims. Do not modify the quote.
If no meaningful factual claims exist, return an empty list.
"""

ANALYZE_SYSTEM_PROMPT = """You are an expert auditor analyzing the Raw Source Documents (corpus) against a set of compliance rules. You may also receive a list of extracted claims, but YOU MUST IGNORE THE EXTRACTED CLAIMS WHEN EVALUATING COMPLIANCE RULES.

CRITICAL INSTRUCTIONS FOR COMPLIANCE EVALUATION:
1. THE RAW SOURCE DOCUMENTS ARE THE ONLY SOURCE OF TRUTH for compliance.
2. The compliance engine must evaluate EXACTLY the supplied compliance rule.
   - It must NOT invent additional criteria, interpretations, or stricter requirements.
   - Never create a finding because an explanation, justification, or "necessity" statement is absent unless the compliance rule explicitly requires that explanation. (i.e. "Requirement is present" does NOT mean "Requirement is explained").
3. For EACH compliance rule, scan the Raw Source Documents directly.
4. If the exact requirement is PRESENT in the source documents:
   - Create a finding with severity `"passed"` stating it is satisfied.
   - You MUST extract the exact quote from the Raw Source Documents as a `new_claim` to serve as evidence.
   - Do NOT report it as missing just because you couldn't find it in the "Extracted Claims" list.
4. If the rule is ABSENT after adequate corpus inspection:
   - Create a "Missing Requirement" finding. You MUST assign a severity of "low", "medium", "high", or "critical". NEVER use "passed" for a missing requirement.
   - You MUST create a `new_claim` explicitly stating that the requirement is absent from the corpus, and provide an empty string or relevant surrounding quote as `exact_quote`.
5. If the source material is ambiguous or lacks sufficient context:
   - Classify as 'insufficient_evidence'.
6. Evidence for Requirement A must NEVER be copied from Requirement B. Evaluate each rule independently.

CRITICAL RULES FOR "CONTRADICTION" FINDINGS:
1. Contradictions require strict semantic incompatibility (e.g. "Rent is 500" vs "Rent is 600").
2. Do NOT report a contradiction merely because statements mention different values, categories, scopes, or contexts (e.g., "lease duration up to 11 months" vs "rent agreement more than a year" is NOT a contradiction, as they refer to different types of agreements).
3. If the evidence does not firmly establish a contradiction, do not report one. Never bluff.

Include any compliance evidence as `new_claims` (with exact verbatim quotes from the source). Use `claim_ids` ONLY if you are pointing out a cross-claim contradiction between two previously extracted claims.

"""

VERIFY_SYSTEM_PROMPT = """You are an expert fact-checker.
You will be provided with a Claim and a piece of Evidence text.
Evaluate if the Evidence supports the Claim, contradicts the Claim, or is insufficient.
Provide a relevance score (0.0 to 1.0). Do not provide explanations.
"""
