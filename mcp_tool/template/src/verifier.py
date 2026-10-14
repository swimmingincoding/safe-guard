"""Post-Guardrail Verifier (Output Scaffolding).

LLM이 생성한 리라이팅 문장을 검증하여,
1) 협력사 직원 실명이 남아있는지
2) 직접 지시 어투가 남아있는지
3) 현장대리인 경유 형식을 갖추었는지
결정론적으로 검사하고 필요 시 자동 보정(Sanitization)하는 하네스 모듈입니다.
"""

import re
from typing import List, Tuple
from .schemas import RewriteSuggestion


# 허용되는 정중한 비즈니스/도급 요청 종결 어투
COMPLIANT_REQUEST_ENDINGS = [
    "요청드립니다", "협조 바랍니다", "협조를 부탁드립니다", "안내드립니다",
    "확인을 부탁드립니다", "공유 부탁드립니다", "전달 바랍니다"
]

# 재작성문에 절대 남아있으면 안 되는 직접 명령형 어투
STRICT_FORBIDDEN_ENDINGS = [
    "끝내세요", "끝내라", "마치세요", "마쳐라", "수행하세요", "작업하세요",
    "보고하세요", "해놓으세요", "해라", "출근하세요", "잔업하세요"
]


def verify_rewrite_suggestion(
    suggestion: RewriteSuggestion,
    suspected_names: List[str]
) -> Tuple[bool, List[str], RewriteSuggestion]:
    """제안된 변환 문장의 적법성을 최종 검증하고 보정합니다."""
    text = suggestion.rewritten_text
    issues: List[str] = []

    # 1. 원문에서 감지되었던 특정 인명이 재작성문에 잔존하는지 검사
    for name in suspected_names:
        if name in text:
            issues.append(f"잔존 인명 검출: '{name}'이 변환문에서 완전히 제거되지 않음")
            # 자동 보정: 특정 인명을 도급 업무 주체 표현으로 교체
            text = text.replace(name, "해당 공정 담당 작업자")

    # 2. 금지된 직접 명령 어투 잔존 검사
    for forbidden in STRICT_FORBIDDEN_ENDINGS:
        if forbidden in text:
            issues.append(f"직접 명령 어투 잔존: '{forbidden}' 표현 발견")
            # 자동 보정: 정중한 도급 협조 요청으로 치환
            text = text.replace(forbidden, "완료될 수 있도록 협조 요청드립니다")

    # 3. 현장 대리인 / 공식 채널 명시 여부 검사
    channel_valid = any(
        kw in suggestion.channel or kw in text
        for kw in ["현장대리인", "소장", "반장", "관리자", "협력사 대표", "귀하"]
    )
    if not channel_valid:
        issues.append("전달 채널 미흡: 현장 대리인(소장/관리자) 경유 표기 누락")
        # 채널 보정
        if not text.startswith("["):
            text = "[협력사 현장대리인(소장) 귀하] " + text

    # 보정된 내용 반영
    corrected_suggestion = RewriteSuggestion(
        channel=suggestion.channel if channel_valid else "협력사 현장대리인(소장) 공식 채널",
        rewritten_text=text,
        key_points=suggestion.key_points + (["Harness 자동 보정을 통한 적법성 강화"] if issues else [])
    )

    passed = len(issues) == 0
    return passed, issues, corrected_suggestion
