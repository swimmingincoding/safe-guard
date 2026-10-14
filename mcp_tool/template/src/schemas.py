"""Pydantic schemas for Safe-Direction Compliance Agent with Yellow Envelope Law support."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    SAFE = "SAFE"        # 합법적/안전: 도급 계약 목적 및 결과 중심의 적법 요청
    CAUTION = "CAUTION"  # 주의: 직접 지시 또는 실질 지배력으로 오인될 수 있는 모호한 표현
    DANGER = "DANGER"    # 위험: 불법 파견 요건 충족 또는 노란봉투법상 원청 사용자성 인정 직결


class ViolationType(str, Enum):
    # [1] 노란봉투법(노조법 제2조 제2호) 실질적 지배력 위반 유형
    SUBSTANTIAL_CONTROL_SAFETY = "SUBSTANTIAL_CONTROL_SAFETY"          # 안전보건 및 작업환경 직접 통제/제재
    SUBSTANTIAL_CONTROL_TIME_REST = "SUBSTANTIAL_CONTROL_TIME_REST"    # 근로시간, 휴게/식사시간 일방적 배분/단축
    SUBSTANTIAL_CONTROL_DISCIPLINE = "SUBSTANTIAL_CONTROL_DISCIPLINE"  # 인사, 징계, 출입제한, 배치전환 개입
    SUBSTANTIAL_CONTROL_WORKLOAD = "SUBSTANTIAL_CONTROL_WORKLOAD"      # 택트타임, 라인속도 통제 등 노동강도 결정
    SUBSTANTIAL_CONTROL_PRICE = "SUBSTANTIAL_CONTROL_PRICE"            # 도급비/인건비 일방 결정 및 노동조건 구속

    # [2] 파견법(파견근로자보호법) 불법 파견 위반 유형
    DIRECT_COMMAND = "DIRECT_COMMAND"                                  # 개별 근로자에 대한 직접적 업무수행 지휘·명령
    SPECIFIC_PERSON_ASSIGNMENT = "SPECIFIC_PERSON"                     # 협력사 특정 근로자 개별 지목 및 작업 할당
    ATTENDANCE_TIME_CONTROL = "ATTENDANCE_TIME_CONTROL"                # 출퇴근, 연장/야간근로 등 직접 시간 통제
    WORK_METHOD_CONTROL = "WORK_METHOD_CONTROL"                        # 구체적 작업 방식, 순서, 절차 직접 구속/간섭
    EVALUATION_DISCIPLINE = "EVALUATION_DISCIPLINE"                    # 협력사 근로자 인사평가, 징계, 근태 승인 관여


class RuleFinding(BaseModel):
    """Pre-guardrail 룰 검사에서 발견된 이상 패턴"""
    violation_type: ViolationType
    matched_text: str
    description: str


class PreCheckResult(BaseModel):
    """사전 규칙(Harness Pre-Guardrail) 검사 결과"""
    has_risk: bool = False
    suspected_names: List[str] = Field(default_factory=list)
    command_phrases: List[str] = Field(default_factory=list)
    time_constraints: List[str] = Field(default_factory=list)
    safety_discipline_phrases: List[str] = Field(default_factory=list)
    findings: List[RuleFinding] = Field(default_factory=list)


class RewriteSuggestion(BaseModel):
    """적법 도급문 제안"""
    channel: str = Field(description="권장 전달 채널 (예: 협력사 현장대리인/소장 공식 채널)")
    rewritten_text: str = Field(description="수정된 적법 도급 요청문")
    key_points: List[str] = Field(default_factory=list, description="법적 리스크 제거 포인트")


class YellowEnvelopeAnalysis(BaseModel):
    """노란봉투법(노조법 제2조 및 제3조) 전용 컴플라이언스 정밀 분석 결과"""
    is_substantial_control_detected: bool = Field(description="실질적 지배력 행사 여부")
    employer_status_risk: str = Field(description="원청의 사용자성 인정 리스크: HIGH / MEDIUM / LOW")
    statutory_articles: List[str] = Field(default_factory=list, description="적용된 실제 법률 조항")
    precedents: List[str] = Field(default_factory=list, description="관련 법원 핵심 판례")
    collective_bargaining_risk: str = Field(description="하청노조의 단체교섭 요구 및 부당노동행위 리스크 경고")


class DirectionAuditResponse(BaseModel):
    """지시어 감사 및 변환 최종 결과 (Dify / 사용자에게 반환되는 구조체)"""
    original_text: str
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100, description="0: 완전안전 ~ 100: 극도위험")
    summary: str
    violations: List[ViolationType] = Field(default_factory=list)
    flagged_phrases: List[str] = Field(default_factory=list)
    legal_basis: str
    yellow_envelope_analysis: YellowEnvelopeAnalysis
    rewrites: List[RewriteSuggestion] = Field(default_factory=list)
    action_guides: List[str] = Field(default_factory=list)
    verification_passed: bool = Field(default=True, description="Harness Verifier 통과 여부")


class LaborQAResponse(BaseModel):
    """현장 맞춤형 노무/도급 Q&A 응답 구조체"""
    question: str
    summary_answer: str
    compliance_status: str = Field(description="허용(적법) / 원칙적 불가(위법 소지) / 조건부 허용")
    legal_basis: str
    do_and_dont: List[str] = Field(default_factory=list)
    recommended_action: str
    references: List[str] = Field(default_factory=list)
