import os
import pytest
from app.llm.schemas import LLMRequest
from app.config import get_settings
from app.workflow.prompts import ANALYZE_SYSTEM_PROMPT, AnalysisResult
from app.workflow.graph import get_llm

real_test_enabled = (
    os.environ.get("FLOWDOCS_REAL_LLM_TESTS") == "1" and
    os.environ.get("LLM_PROVIDER") == "groq" and
    bool(os.environ.get("GROQ_API_KEY"))
)

@pytest.fixture
def llm():
    return get_llm()

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_no_false_missing_rent_deposit(llm):
    """
    Test 1: A document explicitly containing 'Details regarding rent and deposit' 
    must NOT produce 'missing rent/deposit'.
    """
    corpus_text = "--- Document Chunk 1 ---\nThe agreement must contain details regarding rent and deposit."
    claims_text = ""
    compliance_rules = "- Must contain rent and deposit details."
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    # We should NOT see a finding about missing rent/deposit because it's explicitly in the corpus.
    # We might see a finding about 'Alignment' since the rule is satisfied, or 'insufficient_evidence', but NOT a missing requirement violation.
    for finding in parsed.findings:
        title_lower = finding.title.lower()
        assert not ("missing" in title_lower and "rent" in title_lower), f"False missing requirement detected: {finding.title}"
        if "rent" in title_lower or "deposit" in title_lower:
            assert finding.severity == "passed", f"Expected satisfied rule to have severity 'passed', got '{finding.severity}'"

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_no_false_missing_termination(llm):
    """
    Test 2: A document explicitly containing 'Lease/Rent termination and extension' 
    must NOT produce 'missing termination/extension'.
    """
    corpus_text = "--- Document Chunk 1 ---\nThe document specifies Lease/Rent termination and extension rules."
    claims_text = ""
    compliance_rules = "- Agreement must cover termination and extension."
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    for finding in parsed.findings:
        title_lower = finding.title.lower()
        assert not ("missing" in title_lower and "termination" in title_lower), f"False missing requirement detected: {finding.title}"

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_no_false_missing_signing_date(llm):
    """
    Test 3: A document explicitly containing 'Date of signing of the agreement' 
    must NOT produce 'missing signing date'.
    """
    corpus_text = "--- Document Chunk 1 ---\nDate of signing of the agreement: January 1, 2024."
    claims_text = ""
    compliance_rules = "- Agreement must have a signing date."
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    for finding in parsed.findings:
        title_lower = finding.title.lower()
        assert not ("missing" in title_lower and "date" in title_lower), f"False missing requirement detected: {finding.title}"

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_no_false_contradiction_lease_vs_rent(llm):
    """
    Test 4: The lease/rent 11-month vs more-than-a-year statements must NOT 
    automatically become a contradiction when the source distinguishes the agreement types.
    """
    corpus_text = "--- Document Chunk 1 ---\nA rent agreement can be an agreement of more than a year. A lease agreement is typically up to 11 months."
    claims_text = "ID: 1 | Statement: A rent agreement can be an agreement of more than a year.\nID: 2 | Statement: A lease agreement is typically up to 11 months."
    compliance_rules = ""
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    for finding in parsed.findings:
        title_lower = finding.title.lower()
        assert not ("contradiction" in title_lower or "conflict" in title_lower), f"False contradiction detected: {finding.title}"

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_genuine_missing_requirement(llm):
    """
    Test 5: A genuinely missing requirement must still produce a finding.
    """
    corpus_text = "--- Document Chunk 1 ---\nThis agreement has no termination clause whatsoever."
    claims_text = ""
    compliance_rules = "- Agreement must contain a deposit amount."
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    # We MUST see a finding about missing deposit
    found_missing = False
    for finding in parsed.findings:
        if "missing" in finding.title.lower() and "deposit" in finding.title.lower():
            found_missing = True
            break
            
    assert found_missing, "Failed to detect genuinely missing deposit requirement."

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_no_false_missing_unexplained_clause(llm):
    """
    Test 6: A document explicitly containing a clause must NOT produce a missing requirement 
    merely because it does not explain the necessity of the clause.
    """
    corpus_text = "--- Document Chunk 1 ---\nClause regarding visitation rights of landlord: The landlord may visit the property with 24 hours notice."
    claims_text = ""
    compliance_rules = "- Documents mention the need for a visitation rights clause of landlord."
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    for finding in parsed.findings:
        title_lower = finding.title.lower()
        assert not ("missing" in title_lower and "visitation" in title_lower), f"False missing requirement detected: {finding.title}"
        if "visitation" in title_lower or "landlord" in title_lower:
            assert finding.severity == "passed", f"Expected satisfied rule to have severity 'passed', got '{finding.severity}'"

@pytest.mark.skipif(not real_test_enabled, reason="Real Groq tests are not enabled or configured.")
def test_no_false_missing_different_wording(llm):
    """
    Test 7: A document containing the requirement with different wording with equivalent meaning 
    must NOT produce a missing requirement.
    """
    corpus_text = "--- Document Chunk 1 ---\nThe property owner is permitted to enter the premises upon giving a day's warning."
    claims_text = ""
    compliance_rules = "- Documents mention the need for a visitation rights clause of landlord."
    
    user_prompt = f"Raw Source Documents:\n\n{corpus_text}\n\nExtracted Claims:\n\n{claims_text}"
    user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
    user_prompt += "\nPlease evaluate every compliance rule against the Raw Source Documents. Do NOT evaluate them against the Extracted Claims. Create a finding for any discrepancy, violation, or notable alignment."
    
    req = LLMRequest(
        system_prompt=ANALYZE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=AnalysisResult
    )
    resp = llm.generate(req)
    parsed = resp.parsed_content
    
    for finding in parsed.findings:
        title_lower = finding.title.lower()
        assert not ("missing" in title_lower and "visitation" in title_lower), f"False missing requirement detected: {finding.title}"
        if "visitation" in title_lower or "landlord" in title_lower:
            assert finding.severity == "passed", f"Expected satisfied rule to have severity 'passed', got '{finding.severity}'"
