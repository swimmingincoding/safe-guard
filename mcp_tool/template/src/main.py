"""Safe-Direction Agent - FastMCP Server.

원하청 적법 도급(Compliance) 관리를 위한 실시간 업무 지시 가이드 및 노무 Q&A MCP 도구 서버.
Dify 워크플로우에서 Custom Tool(MCP)로 호출되어 구동됩니다.
"""

import json
from fastmcp import FastMCP
from src.harness import audit_direction_harness, answer_labor_qa_harness

mcp = FastMCP(name="safe_direction_agent")


@mcp.tool()
def audit_and_rewrite_direction(instruction_text: str, context_info: str = "") -> str:
    """원청의 업무 지시문에서 불법 파견 요건을 정밀 진단(필터링)하고, 적법한 도급 요청문으로 변환 제안합니다.

    Args:
        instruction_text (str): 현장에서 전송하려는 업무 지시 원문 (예: '김 대리, 14시까지 3라인 센서 교체 끝내세요')
        context_info (str, optional): 공정명, 협력사명 등 부가 정보 (기본값: 빈 문자열)

    Returns:
        str: JSON 포맷의 컴플라이언스 진단 결과 문자열.
             - risk_level: SAFE(안전) / CAUTION(주의) / DANGER(위험)
             - risk_score: 위험도 점수 (0~100)
             - summary: 진단 핵심 요약
             - violations: 위반 유형 목록 (DIRECT_COMMAND, SPECIFIC_PERSON, ATTENDANCE_TIME_CONTROL 등)
             - flagged_phrases: 원문 내 위반 키워드 목록
             - legal_basis: 관련 대법원 판례 및 법적 근거
             - rewrites: 협력사 현장대리인 경유의 적법 도급문 제안 목록
             - action_guides: 실무자 행동 지침
             - verification_passed: Harness 검증기 통과 여부
    """
    result = audit_direction_harness(instruction_text, context_info)
    return result.model_dump_json(indent=2)


@mcp.tool()
def search_labor_compliance_qa(question: str) -> str:
    """휴가, 근태, 잔업, 장비 대여, 작업 배치 등 원하청 업무 경계에 대한 법무/노무 가이드를 제공합니다.

    Args:
        question (str): 현장에서 발생하는 노무/도급 관련 질문 (예: '협력사 직원에게 잔업을 시켜도 되나요?')

    Returns:
        str: JSON 포맷의 법무 가이드 결과 문자열.
             - question: 입력 질문
             - summary_answer: 핵심 요약 답변
             - compliance_status: 허용(적법) / 원칙적 불가(위법 소지) / 조건부 허용
             - legal_basis: 관련 법령 및 판례 근거
             - do_and_dont: 현장 실무자가 해야 할 행동(DO)과 하지 말아야 할 행동(DONT) 리스트
             - recommended_action: 권장 조치 사항
             - references: 참조 가이드라인 및 판례 조항
    """
    result = answer_labor_qa_harness(question)
    return result.model_dump_json(indent=2)


import os

if __name__ == "__main__":
    # Dify 등 외부 오케스트레이터와 통신하기 위해 HTTP 스트리밍 전송 모드로 서빙합니다.
    # 주최측 기본 포트는 80이며, 로컬 테스트 시 PORT 환경변수로 변경 가능합니다.
    port = int(os.getenv("PORT", "80"))
    host = os.getenv("HOST", "0.0.0.0")
    mcp.run(transport="streamable-http", host=host, port=port)