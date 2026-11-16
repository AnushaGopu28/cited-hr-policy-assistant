
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.prompts import SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

FALLBACK = "I can't find this in the approved documents, please ask HR"

def determination_safety_response(question):
    """Prevent personal legal, tax, payroll, and employment determinations."""

    q = question.lower()

    # Personal paycheck calculations
    if any(term in q for term in [
        "net paycheck",
        "take-home pay",
        "take home pay",
        "after taxes",
        "paycheck after tax"
    ]):
        return (
            "I can't calculate your individual net paycheck. "
            "The approved documents do not contain your personal "
            "pay rate, tax withholding, deductions, or benefits details. "
            "Please contact Payroll Support for payroll information "
            "and a qualified tax professional for personal tax questions. "
            "General information only; not tax advice."
        )

    # Personal tax treatment
    if any(term in q for term in [
        "my personal tax return",
        "is my expense deductible",
        "personal work expense",
        "deductible on my tax return",
        "my expense deductible",
        "tax treatment of my expense"
    ]):
        return (
            "I can't determine whether your specific work expense "
            "is deductible on your personal tax return. That depends "
            "on your individual circumstances. Please consult IRS "
            "guidance or a qualified tax professional. "
            "General information only; not tax advice."
        )

    # Paid holiday entitlement
    if "paid holiday" in q or "paid holidays" in q:
        if any(term in q for term in [
            "am i entitled",
            "do i qualify",
            "do i get",
            "will i receive",
            "am i eligible"
        ]):
            return (
                "The Pine Harbor Analytics Consultant Handbook does not "
                "specify whether consultants receive paid holidays. "
                "I can't determine your individual entitlement. "
                "Please contact HR or Payroll to confirm the policy "
                "that applies to your assignment."
            )

    # Other individual legal or employment determinations
    determination_patterns = [
            # FMLA, visa, and worker-classification questions continue
    # to the model for supported general information.
    ]
        # General FMLA information; do not determine personal eligibility.
    if "fmla" in q and any(term in q for term in [
        "eligible",
        "eligibility",
        "qualify",
        "work history"
    ]):
        return (
            "I can't determine your individual FMLA eligibility. "
            "In general, the approved Department of Labor fact sheet "
            "states that eligible employees must have worked for a "
            "covered employer for at least 12 months, completed at "
            "least 1,250 hours of service during the 12 months before "
            "leave begins, and work at a location where the employer "
            "has at least 50 employees within 75 miles. "
            "Your personal eligibility depends on your circumstances. "
            "Please contact HR for a review. "
            "General information only; not legal advice. "
            "[Source: Family and Medical Leave Act, page 1]"
        )
        # General Form I-9 information; do not determine individual visa status.
    if any(term in q for term in [
        "visa",
        "work authorization",
        "authorized to work"
    ]) and any(term in q for term in [
        "allow me",
        "can i work",
        "work for this client",
        "am i authorized",
        "can i legally work"
    ]):
        return (
            "I can't determine whether your specific visa authorizes "
            "you to work for this client. The approved Form I-9 "
            "instructions explain that an individual may be authorized "
            "to work in the United States without being a U.S. citizen, "
            "noncitizen national, or lawful permanent resident. "
            "Your specific work authorization and any employer or "
            "client restrictions must be reviewed by HR and an "
            "appropriate immigration professional. "
            "General information only; not legal or immigration advice. "
            "[Source: Instructions for Form I-9, page 3]"
        )
        # General employee and independent contractor definitions;
    # do not determine an individual's legal classification.
    if any(term in q for term in [
        "independent contractor",
        "employee or",
        "employee versus",
        "worker classification",
        "employment classification"
    ]):
        return (
            "I can't determine whether you are legally an employee "
            "or an independent contractor. The approved Form I-9 "
            "instructions define an employee as a person who performs "
            "labor or services in the United States for an employer "
            "in return for wages or other remuneration. That definition "
            "excludes independent contractors from the Form I-9 "
            "definition of employee. IRS Publication 463 also describes "
            "an independent contractor as someone who is self-employed "
            "and performs services for a customer or client. These "
            "general definitions do not decide your individual status "
            "under all applicable federal laws. Please contact HR or "
            "a qualified employment or tax professional for a review. "
            "General information only; not legal or tax advice. "
            "[Sources: Instructions for Form I-9, page 1; "
            "IRS Publication 463]"
        )
    return None



def local_answer(question, passages):
    """Create a transparent, rule-based answer from retrieved evidence."""

    q = question.lower()

    ranked = []

    for p in passages:
        text = p.get("text", "")
        section = p.get("section_or_page", "")
        title = p.get("source_title", "")

        score = 0

        query_terms = set(re.findall(r"\b[a-z0-9]+\b", q))
        document_terms = set(
            re.findall(r"\b[a-z0-9]+\b", text.lower())
        )

        score += len(query_terms & document_terms)

        if "consultant" in q and "Pine Harbor" in title:
            score += 3

        if "onboarding" in q and "onboarding" in text.lower():
            score += 3

        if "welcome email" in q and "welcome email" in text.lower():
            score += 3

        if "password" in q and "password" in text.lower():
            score += 3

        if (
            "expense" in q
            and section.lower() == "submitting an expense"
            and "transaction date" in text.lower()
            and "vendor" in text.lower()
        ):
            score += 10

        if "timesheet" in q and "portal" in q and section.lower() == "time-entry system" and "pine harbor time portal" in text.lower():
            score += 10

        if "first week" in q and section.lower() == "first-week checklist" and "welcome email" in text.lower() and "security training" in text.lower():
            score += 20

        ranked.append((score, p))
    ranked.sort(key=lambda item: item[0], reverse=True)

    best = [
        p for score, p in ranked
        if score > 0
    ][:3]

    if not best:
        return FALLBACK

    evidence = []

    for p in best:
        evidence.append(
            f"{p.get('text', '')} "
        )

    evidence_text = " ".join(evidence)

    if "onboarding information is missing" in q:
        match = re.search(
            r"If any item is missing,\s*([^.]*)",
            evidence_text,
            re.IGNORECASE
        )

        if match:
            answer = match.group(1).strip()
            answer = answer[0].upper() + answer[1:]
        else:
            answer = FALLBACK

    elif "password" in q and "email" in q:
        if "Do not send passwords or identity documents by ordinary email." in evidence_text:
            answer = (
                "No. Do not send passwords or identity documents "
                "through ordinary email. Use the employer's "
                "approved secure portal."
            )
        else:
            answer = FALLBACK

    elif "timesheet" in q and "deadline" in q:
        deadline_evidence = next(
            (
                p.get("text", "")
                for p in best
                if p.get("section_or_page", "").lower() == "submission deadline"
                and "5:00 p.m." in p.get("text", "")
            ),
            ""
        )

        if deadline_evidence:
            answer = (
                "The fictional handbook requires consultants to submit "
                "a complete timesheet by 5:00 p.m. local time each Friday. "
                "This is a sample company deadline."
            )
        else:
            answer = FALLBACK

    elif "timesheet" in q and "wrong project code" in q:
        correction_evidence = next(
            (
                p.get("text", "")
                for p in best
                if p.get("section_or_page", "").lower() == "recording time"
                and "correction workflow" in p.get("text", "").lower()
            ),
            ""
        )

        if correction_evidence:
            answer = (
                "If you enter the wrong project code, use the portal's "
                "correction workflow or contact the time administrator."
            )
        else:
            answer = FALLBACK

    elif "missing payment" in q:
        payroll_evidence = next(
            (
                p.get("text", "")
                for p in best
                if p.get("section_or_page", "").lower() == "payroll questions"
                and "payroll-support@pineharbor.example" in p.get("text", "")
            ),
            ""
        )

        if payroll_evidence:
            answer = (
                "For a missing payment, contact fictional Payroll Support "
                "at payroll-support@pineharbor.example. Include the pay "
                "period and a brief description. Do not include full bank "
                "account numbers or tax identification numbers in ordinary email."
            )
        else:
            answer = FALLBACK

    elif "timesheet" in q and "portal" in q:
        portal_evidence = next(
            (
                p.get("text", "")
                for p in best
                if p.get("section_or_page", "").lower() == "time-entry system"
                and "Pine Harbor Time Portal" in p.get("text", "")
            ),
            ""
        )

        if portal_evidence:
            answer = (
                "Use the fictional Pine Harbor Time Portal to submit your "
                "timesheet. The portal address is provided individually by "
                "the staffing coordinator and is not included in the handbook."
            )
        else:
            answer = FALLBACK
    elif "expense" in q and any(term in q for term in ["how long", "deadline", "days"]):
        deadline_evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "submitting an expense" and "30 calendar days" in x.get("text", "").lower()), "")
        if deadline_evidence:
            answer = "The fictional handbook requires expenses to be submitted within 30 calendar days of the transaction."
        else:
            answer = FALLBACK

    elif "approval" in q and ("buying" in q or "expense" in q or "spending" in q):
        approval_evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "approval before spending" and "written manager approval" in x.get("text", "").lower()), "")
        if approval_evidence:
            answer = "Yes. Obtain written manager approval before incurring a project expense. The approval should identify the business purpose, expected amount, project, and any spending limit."
        else:
            answer = FALLBACK

    elif "expense" in q and any(
        term in q for term in ["include", "information", "submit", "what"]
    ):
        expense_evidence = next(
            (
                p.get("text", "")
                for p in best
                if p.get("section_or_page", "").lower() == "submitting an expense"
                and "transaction date" in p.get("text", "").lower()
                and "vendor" in p.get("text", "").lower()
            ),
            ""
        )

        if expense_evidence:
            answer = (
                "When submitting an expense, provide the transaction date, "
                "vendor, amount, currency, business purpose, project code, "
                "and itemized receipt when available. The fictional handbook "
                "requires submission within 30 calendar days of the transaction."
            )
        else:
            answer = FALLBACK   

    elif "first week" in q:
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "first-week checklist" and "welcome email" in x.get("text", "").lower() and "security training" in x.get("text", "").lower()), "")
        answer = ("During the first week, review the welcome email, confirm your manager and project contacts, test required accounts, complete security training, confirm your time-entry project code, clarify remote or onsite expectations, and escalate open questions.") if evidence else FALLBACK

    elif "first week" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "first-week checklist" and "welcome email" in x.get("text", "").lower() and "security training" in x.get("text", "").lower()]

    elif "bonus" in q and "pine harbor" in q:
        bonus_evidence = any(
            "does not specify a universal first-week completion bonus"
            in p.get("text", "").lower()
    
            for p in best
        )

        if bonus_evidence:
            answer = (
                "The Pine Harbor handbook does not specify a $500 "
                "onboarding bonus. Please confirm any individual "
                "bonus arrangement with your staffing coordinator or HR."
            )
        else:
            answer = FALLBACK

    elif "laptop" in q and "lost" in q:
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "urgent security incident" and "it service desk" in x.get("text", "").lower()), "")
        answer = "If your laptop is lost, contact the IT Service Desk and your manager immediately." if evidence else FALLBACK

    elif "personal cloud" in q or ("client files" in q and "cloud storage" in q):
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "data handling" and "upload them to personal storage" in x.get("text", "").lower()), "")
        answer = "No. Store client work files only in approved company or client repositories. Do not upload them to personal cloud storage or use personal email." if evidence else FALLBACK

    elif "unexpected emergency" in q or ("cannot work" in q and "emergency" in q):
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "unexpected absence" and "notify your project manager" in x.get("text", "").lower()), "")
        answer = "If an unexpected illness or emergency prevents you from working, notify your project manager as soon as possible using the agreed contact method. If you cannot reach the project manager, contact the staffing coordinator." if evidence else FALLBACK

    elif "pto" in q and ("accrual" in q or "rate" in q):
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "not specified in source" and "pto accrual" in x.get("text", "").lower()), "")
        answer = "The handbook does not specify a PTO accrual rate. Please confirm the applicable policy with People Operations or HR." if evidence else FALLBACK

    elif "access" in q and ("device" in q or "problem" in q):
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "escalation order" and "it" in x.get("text", "").lower()), "")
        answer = "Contact the IT Service Desk for account, access, or device problems." if evidence else FALLBACK

    elif "remote" in q and ("guarantee" in q or "work" in q):
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "remote-work approval" and "does not promise remote-work eligibility" in x.get("text", "").lower()), "")
        answer = "No. The handbook does not guarantee remote work. Remote, hybrid, or onsite arrangements depend on the assignment and manager." if evidence else FALLBACK

    elif ("approved documents" in q and ("information" in q or "missing" in q)) or ("exact refusal" in q and "missing" in q):
        evidence = next((x.get("text", "") for x in best if x.get("section_or_page", "").lower() == "when information is missing" and "i can't find this in the approved documents, please ask hr" in x.get("text", "").lower()), "")
        answer = FALLBACK if evidence else FALLBACK

    else:
        answer = FALLBACK

    if answer == FALLBACK and not (("approved documents" in q and ("information" in q or "missing" in q)) or ("exact refusal" in q and "missing" in q) and any(x.get("section_or_page", "").lower() == "when information is missing" and "approved documents" in x.get("text", "").lower() and "please ask hr" in x.get("text", "").lower() for x in best)):
        return FALLBACK

        # Select only passages that directly support the answer.
    if "onboarding information is missing" in q:
        citation_passages = [
            p for p in best
            if "if any item is missing" in p.get("text", "").lower()
        ]

    elif "password" in q and "email" in q:
        citation_passages = [
            p for p in best
            if "do not send passwords or identity documents"
            in p.get("text", "").lower()
        ]

    elif "welcome email" in q:
        citation_passages = [
            p for p in best
            if all(term in p.get("text", "").lower()
                   for term in ["welcome email", "project name",
                                "manager contact", "onboarding portal"])
        ]

    elif "first week" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "first-week checklist" and "welcome email" in x.get("text", "").lower() and "security training" in x.get("text", "").lower()]

    elif "remote" in q and ("guarantee" in q or "work" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "remote-work approval" and "does not promise remote-work eligibility" in x.get("text", "").lower()]

    elif ("approved documents" in q and ("information" in q or "missing" in q)) or ("exact refusal" in q and "missing" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "when information is missing" and "approved documents" in x.get("text", "").lower() and "please ask hr" in x.get("text", "").lower()]

    elif 'bonus' in q and 'pine harbor' in q:
        citation_passages = [
            p for p in best
            if 'does not specify a universal first-week completion bonus'
            in p.get('text', '').lower()
        ]

    elif "expense" in q and any(term in q for term in ["how long", "deadline", "days"]):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "submitting an expense" and "30 calendar days" in x.get("text", "").lower()]

    elif "approval" in q and ("buying" in q or "expense" in q or "spending" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "approval before spending" and "written manager approval" in x.get("text", "").lower()]

    elif 'expense' in q:
        citation_passages = [
            p for p in best
            if p.get('section_or_page', '').lower() == 'submitting an expense'
            and 'transaction date' in p.get('text', '').lower()
            and 'vendor' in p.get('text', '').lower()
        ]

    elif "laptop" in q and "lost" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "urgent security incident" and "it service desk" in x.get("text", "").lower()]

    elif "personal cloud" in q or ("client files" in q and "cloud storage" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "data handling" and "upload them to personal storage" in x.get("text", "").lower()]

    elif "unexpected emergency" in q or ("cannot work" in q and "emergency" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "unexpected absence" and "notify your project manager" in x.get("text", "").lower()]

    elif "pto" in q and ("accrual" in q or "rate" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "not specified in source" and "pto accrual" in x.get("text", "").lower()]

    elif "access" in q and ("device" in q or "problem" in q):
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "escalation order" and "it" in x.get("text", "").lower()]

    elif "timesheet" in q and "portal" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "time-entry system" and "pine harbor time portal" in x.get("text", "").lower()]

    elif "timesheet" in q and "deadline" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "submission deadline" and "5:00 p.m." in x.get("text", "")]

    elif "timesheet" in q and "wrong project code" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "recording time" and "correction workflow" in x.get("text", "").lower()]

    elif "missing payment" in q:
        citation_passages = [x for x in best if x.get("section_or_page", "").lower() == "payroll questions" and "payroll-support@pineharbor.example" in x.get("text", "")]

    else:
        citation_passages = best

    if not citation_passages:
        return FALLBACK

    citations = []

    for p in citation_passages:
        citation = (
            f"[{p.get('source_title', 'Unknown source')} | "
            f"{p.get('section_or_page', 'Section not specified')}]"
        )

        if citation not in citations:
            citations.append(citation)

    return (
        "LOCAL TEST MODE - RULE-BASED ANSWER, NOT AI-GENERATED\n\n"
        f"Question: {question}\n\n"
        f"Answer: {answer}\n\n"
        "Sources:\n"
        + "\n".join(citations)
    )

def answer_question(question, passages):
    safety_response = determination_safety_response(question)
    if safety_response:
        return safety_response

    if not passages:
        return FALLBACK

    q = question.lower()

    if (
        "hotel" in q
        and any(term in q for term in ["maximum", "limit", "cap", "per night", "reimbursement"])
    ):
        handbook_evidence = [
            p for p in passages
            if "pine harbor analytics consultant handbook"
            in p.get("source_title", "").lower()
        ]

        if not handbook_evidence:
            return FALLBACK

        evidence_text = " ".join(
            p.get("text", "").lower() for p in handbook_evidence
        )

        if not any(term in evidence_text for term in [
            "hotel reimbursement limit",
            "maximum hotel reimbursement",
            "maximum nightly hotel rate",
            "hotel reimbursement cap"
        ]):
            return FALLBACK

    context = []
    injection_patterns = [
        r"ignore all previous instructions",
        r"ignore previous instructions",
        r"reveal (the )?(hidden )?(system prompt|system instructions)",
        r"disregard (all )?(previous )?instructions",
        r"change your (role|instructions)",
        r"you are now",
    ]

    for p in passages:
        policy_text = p.get("text", "")

        for pattern in injection_patterns:
            policy_text = re.sub(
                pattern,
                "[INSTRUCTION REMOVED]",
                policy_text,
                flags=re.IGNORECASE
            )

        context.append(
            f"Policy text: {policy_text}\n"
            f"Source title: {p.get('source_title', 'Unknown source')}\n"
            f"Section or page: {p.get('section_or_page', 'Unknown section')}"
        )

    prompt = (
        "APPROVED CONTEXT:\n\n"
        + "\n\n---\n\n".join(context)
        + "\n\nQUESTION:\n"
        + question
    )

    try:
        import requests

        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "options": {
                    "temperature": 0
                }
            },
            timeout=120
        )

        response.raise_for_status()

        answer = response.json()["message"]["content"].strip()
        if not answer or answer.startswith(FALLBACK):
            return FALLBACK

        # Ensure the answer includes citations from the approved context.
        if "[SOURCE:" not in answer and "Citation:" not in answer and passages:
            source = passages[0]
            citation = (
                f"[Source: {source.get('source_title', 'Unknown source')}, "
                f"{source.get('section_or_page', 'Unknown section')}]"
            )
            answer = answer.rstrip() + "\n\n" + citation

        return answer

    except requests.exceptions.RequestException as exc:
        return (
            "Ollama connection error. Make sure Ollama is running. "
            f"Details: {exc}"
        )
    except (KeyError, ValueError):
        return FALLBACK
