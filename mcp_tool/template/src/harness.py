"""Core Harness Pipeline Module with Yellow Envelope Law & Subcontracting Compliance Specialization.

Pre-guardrail -> LLM Orchestration (노란봉투법 전문 & 실질적 지배력설 주입) -> Post-guardrail Verifier -> Final Sanitized Response.
"""

import json
import logging
from typing import List
from .schemas import (
    DirectionAuditResponse,
    LaborQAResponse,
    RewriteSuggestion,
    RiskLevel,
    ViolationType,
    YellowEnvelopeAnalysis
)
from .rule_checker import run_pre_guardrail
from .verifier import verify_rewrite_suggestion
from .llm_client import call_internal_llm, generate_llm_audit_fallback
from .knowledge import search_knowledge, COMPLIANCE_STANDARDS
from .yellow_envelope_law import YELLOW_ENVELOPE_LAW_ARTICLES, LEADING_PRECEDENTS

logger = logging.getLogger(__name__)


def audit_direction_harness(instruction_text: str, context_info: str = "") -> DirectionAuditResponse:
    """원청의 지시어 텍스트를 노란봉투법 및 파견법 법리로 정밀 감사하고, 적법 도급 제안문으로 변환합니다."""
    # [1단계] Pre-Guardrail (규칙 기반 사전 검사: 0.001초 소요)
    pre_check = run_pre_guardrail(instruction_text)

    # [2단계] LLM 호출 준비 (노란봉투법 실제 법문 및 대법원/고법 판례 전문 주입)
    system_prompt = f"""당신은 사내 외주/도급 컴플라이언스 및 '노란봉투법(노동조합 및 노동관계조정법 개정안)' 최고 전문 법무 노무 AI 에이전트입니다.

[적용 필수 핵심 법률 전문]
1. {YELLOW_ENVELOPE_LAW_ARTICLES['ARTICLE_2_CLAUSE_2']['law_name']}:
{YELLOW_ENVELOPE_LAW_ARTICLES['ARTICLE_2_CLAUSE_2']['original_text']}
- 법리: {YELLOW_ENVELOPE_LAW_ARTICLES['ARTICLE_2_CLAUSE_2']['core_implication']}

2. {YELLOW_ENVELOPE_LAW_ARTICLES['ARTICLE_2_CLAUSE_5']['law_name']}:
{YELLOW_ENVELOPE_LAW_ARTICLES['ARTICLE_2_CLAUSE_5']['original_text']}

[적용 판례 기준]
- {LEADING_PRECEDENTS[0]['case_name']}: {LEADING_PRECEDENTS[0]['key_ruling']}
- {LEADING_PRECEDENTS[1]['case_name']}: {LEADING_PRECEDENTS[1]['key_ruling']}
- {LEADING_PRECEDENTS[2]['case_name']}: {LEADING_PRECEDENTS[2]['key_ruling']}

[원청의 실질적 지배력 5대 위험 징표]
1) 안전보건/보호구 직접 제재 또는 벌점/출입금지 위협 (SUBSTANTIAL_CONTROL_SAFETY)
2) 근로시간, 휴게시간, 식사시간의 일방적 배분/단축 통제 (SUBSTANTIAL_CONTROL_TIME_REST)
3) 협력사 직원의 징계, 출입증 회수, 라인 배치전환 강제 (SUBSTANTIAL_CONTROL_DISCIPLINE)
4) 택트타임, 라인속도 통제를 통한 노동강도 직접 지배 (SUBSTANTIAL_CONTROL_WORKLOAD)
5) 특정 작업자 직접 지휘명령 및 개별 작업 할당 (DIRECT_COMMAND, SPECIFIC_PERSON)

원청 실무자의 문장을 위 법조문과 판례에 비추어 철저히 검증하고, 반드시 유효한 JSON 형식으로만 응답하십시오.
"""

    findings_summary = "\n".join([f"- {f.description}" for f in pre_check.findings])
    user_prompt = f"""
[검토 대상 업무 지시문]
"{instruction_text}"

[부속 맥락 정보]
{context_info if context_info else "없음"}

[사전 검출된 규칙 징표]
{findings_summary if findings_summary else "명시적 위험 키워드 없음"}

다음 JSON 스키마 규격으로만 응답하세요:
{{
  "risk_level": "SAFE" | "CAUTION" | "DANGER",
  "risk_score": 0~100 숫자,
  "summary": "핵심 판정 요약 1~2문장",
  "violations": ["SUBSTANTIAL_CONTROL_SAFETY", "SUBSTANTIAL_CONTROL_TIME_REST", "SUBSTANTIAL_CONTROL_DISCIPLINE", "SUBSTANTIAL_CONTROL_WORKLOAD", "DIRECT_COMMAND", "SPECIFIC_PERSON", "ATTENDANCE_TIME_CONTROL"],
  "flagged_phrases": ["위반 소지가 있는 원문 내 단어들"],
  "legal_basis": "노조법 제2조 제2호 및 관련 판례(서울고법 2023누35795 등) 인용 요약",
  "yellow_envelope_analysis": {{
    "is_substantial_control_detected": true 또는 false,
    "employer_status_risk": "HIGH" | "MEDIUM" | "LOW",
    "statutory_articles": ["노동조합 및 노동관계조정법 제2조 제2호", "노동조합 및 노동관계조정법 제2조 제5호 등"],
    "precedents": ["서울고등법원 2023누35795 판결 등"],
    "collective_bargaining_risk": "협력사 노조의 원청 대상 단체교섭 요구 및 부당노동행위 고발 리스크 분석"
  }},
  "rewrites": [
    {{
      "channel": "협력사 현장대리인(소장) 공식 채널",
      "rewritten_text": "원청의 실질적 지배력 오인을 원천 차단한 적법 도급 권고문",
      "key_points": ["수정 포인트"]
    }}
  ],
  "action_guides": ["실무자 행동 지침 2~3개"]
}}
"""

    raw_response = call_internal_llm(system_prompt, user_prompt)
    audit_data = None

    if raw_response:
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
            audit_data = json.loads(cleaned.strip())
        except Exception as e:
            logger.warning("LLM output JSON parse error: %s. Using harness fallback.", e)

    if not audit_data:
        audit_data = generate_llm_audit_fallback(instruction_text, pre_check, context_info)

    # [3단계] Post-Guardrail Verifier (출력문 적법성 검증 및 자동 보정)
    verified_rewrites: List[RewriteSuggestion] = []
    all_passed = True

    raw_rewrites = audit_data.get("rewrites", [])
    for rw in raw_rewrites:
        suggestion = RewriteSuggestion(
            channel=rw.get("channel", "협력사 현장대리인 경유"),
            rewritten_text=rw.get("rewritten_text", ""),
            key_points=rw.get("key_points", [])
        )
        passed, issues, corrected = verify_rewrite_suggestion(suggestion, pre_check.suspected_names)
        if not passed:
            all_passed = False
        verified_rewrites.append(corrected)

    parsed_violations = []
    for v in audit_data.get("violations", []):
        try:
            parsed_violations.append(ViolationType(v))
        except ValueError:
            pass

    ye_raw = audit_data.get("yellow_envelope_analysis", {})
    yellow_envelope = YellowEnvelopeAnalysis(
        is_substantial_control_detected=ye_raw.get("is_substantial_control_detected", False),
        employer_status_risk=ye_raw.get("employer_status_risk", "LOW"),
        statutory_articles=ye_raw.get("statutory_articles", ["노동조합 및 노동관계조정법 제2조 제2호"]),
        precedents=ye_raw.get("precedents", []),
        collective_bargaining_risk=ye_raw.get("collective_bargaining_risk", "")
    )

    # [4단계] 최종 응답 조립
    return DirectionAuditResponse(
        original_text=instruction_text,
        risk_level=RiskLevel(audit_data.get("risk_level", "SAFE")),
        risk_score=int(audit_data.get("risk_score", 0)),
        summary=audit_data.get("summary", ""),
        violations=parsed_violations,
        flagged_phrases=audit_data.get("flagged_phrases", []),
        legal_basis=audit_data.get("legal_basis", ""),
        yellow_envelope_analysis=yellow_envelope,
        rewrites=verified_rewrites,
        action_guides=audit_data.get("action_guides", []),
        verification_passed=all_passed
    )


from .rag_engine import get_rag_engine


def answer_labor_qa_harness(question: str) -> LaborQAResponse:
    """data/guidelines/ 실제 사내 도급 가이드 및 판례 문서를 RAG 검색하여 근거 기반으로 답변합니다."""
    rag_engine = get_rag_engine()
    retrieved_chunks = rag_engine.search(question, top_k=2)

    # 검색된 사내 규정 문서 문맥 조합
    context_text = ""
    references = []
    if retrieved_chunks:
        for idx, chunk in enumerate(retrieved_chunks, 1):
            context_text += f"\n[참조 {idx}: {chunk['source_file']} - {chunk['title']}]\n{chunk['content']}\n"
            references.append(f"{chunk['title']} ({chunk['source_file']})")

    # LLM Grounded 추론 프롬프트 구성
    system_prompt = (
        "당신은 사내 외주/도급 컴플라이언스 및 노무 전문 최고 AI 법무 에이전트입니다.\n"
        "제공된 [사내 도급 운영 가이드라인 및 판례 원문]을 바탕으로 현장 실무자의 질문에 정확하고 구체적으로 답변해야 합니다.\n"
        "답변 시 반드시 관련된 사내 규정 조항(예: 사내 도급 가이드라인 제10조 등)을 명확히 인용하고, "
        "현장 실무자가 해야 할 행동(DO)과 하지 말아야 할 행동(DONT)을 명확하게 제시하세요.\n"
        "반드시 유효한 JSON 형식으로만 응답하십시오."
    )

    user_prompt = f"""
[실무자 질문]
"{question}"

[RAG 검색된 사내 도급 규정 및 판례 원문]
{context_text if context_text else "직접 매칭된 특수 규정 없음. 일반 도급 원칙에 따라 회신."}

다음 JSON 스키마 규격으로만 응답하세요:
{{
  "summary_answer": "핵심 요약 답변 1~2문장 (명확하고 실무적인 결론)",
  "compliance_status": "허용(적법)" | "원칙적 불가(위법 소지)" | "조건부 허용 (협력사 소장 경유 및 계약 근거 필요)",
  "legal_basis": "관련 사내 규정 조항(제O조) 및 대법원 판례 요약",
  "do_and_dont": [
    "DO: 권장 행동 지침",
    "DO: 추가 조치 사항",
    "DONT: 절대 하지 말아야 할 금지 행동"
  ],
  "recommended_action": "현장 실무자가 즉시 취해야 할 구체적 후속 조치 1문장"
}}
"""

    raw_response = call_internal_llm(system_prompt, user_prompt)
    qa_data = None

    if raw_response:
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
            qa_data = json.loads(cleaned.strip())
        except Exception as e:
            logger.warning("Labor QA LLM JSON parse error: %s. Using RAG fallback.", e)

    # LLM 미응답/오류 시 RAG 검색 원문 기반 Fallback 응답 조립
    if not qa_data:
        if retrieved_chunks:
            top_chunk = retrieved_chunks[0]
            qa_data = {
                "summary_answer": f"{top_chunk['title']}에 의거, 해당 사안은 도급 계약상 정해진 절차와 권한 범위 내에서만 허용됩니다.",
                "compliance_status": "조건부 허용 (사내 도급 가이드 준수)",
                "legal_basis": f"{top_chunk['title']}: {top_chunk['content'][:150]}...",
                "do_and_dont": [
                    "DO: 모든 업무 협의는 협력사 현장대리인(소장) 채널을 통해 서면으로 진행하십시오.",
                    "DONT: 협력사 직원 개인에게 직접 인사명령이나 복리후생 금전을 지급하지 마십시오."
                ],
                "recommended_action": f"{top_chunk['title']} 규정을 준수하여 협력사 관리자와 공식 협의를 진행하십시오."
            }
        else:
            qa_data = {
                "summary_answer": "도급계약의 본질상 원청은 '일의 완성(결과물)'만을 관리할 수 있으며, 구체적 노무 관리는 협력사 대표자에게 전속됩니다.",
                "compliance_status": "조건부 검토 필요",
                "legal_basis": "노조법 제2조 제2호(실질적 지배력설) 및 파견법 제2조",
                "do_and_dont": [
                    "DO: 협력사 현장대리인(소장) 채널을 통해 공식 협의하십시오.",
                    "DONT: 협력사 근로자 개인에게 직접 지시하지 마십시오."
                ],
                "recommended_action": "사내 외주운영팀 또는 노무팀과 사전 협의를 권장합니다."
            }

    return LaborQAResponse(
        question=question,
        summary_answer=qa_data.get("summary_answer", ""),
        compliance_status=qa_data.get("compliance_status", "조건부 허용"),
        legal_basis=qa_data.get("legal_basis", ""),
        do_and_dont=qa_data.get("do_and_dont", []),
        recommended_action=qa_data.get("recommended_action", ""),
        references=references if references else ["사내 도급 운영 가이드라인"]
    )

