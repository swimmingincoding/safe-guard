"""Pre-Guardrail Rule Checker with Yellow Envelope Law (노란봉투법) Specialization.

순수 파이썬 코드로 동작하여 0.001초 만에:
1) 전통적 파견법상 불법파견 징표(인명 지목, 직접 지휘명령, 시간 통제)
2) 노란봉투법상 원청의 '실질적 지배력(사용자성)' 인정 징표(안전보건 직접제재, 휴게시간 단축, 배치전환 강제, 속도 통제)
를 고정밀 Lookaround 정규식으로 사전 검출하는 하네스 모듈입니다.
"""

import re
from typing import List
from .schemas import PreCheckResult, RuleFinding, ViolationType


# =========================================================================
# [1] 노란봉투법(노조법 제2조 제2호) 실질적 지배력 탐지 정규식 패턴
# =========================================================================

# 1-1. 안전보건 및 보호구 직접 제재/벌점/출입금지 패턴
SAFETY_DISCIPLINE_PATTERN = re.compile(
    r"(보호구|안전모|방진마스크|안전경|보안경|안전화|귀마개)\s*(안\s*쓰면|미착용\s*시|벌점|패널티|경고|작업\s*중지|출입\s*정지|현장\s*퇴장)|"
    r"(안전수칙|사내규정|안전기준)\s*(위반\s*시|어기면|미준수\s*시)\s*(출입\s*금지|패널티|벌점|퇴장|조치합니다)"
)

# 1-2. 근로시간·휴게시간·식사시간 일방적 단축 및 배분 강제 패턴
REST_MEAL_TIME_PATTERN = re.compile(
    r"(휴게시간|점심시간|식사시간|휴식시간|교대시간)\s*([0-9]{1,2}분\s*(단축|줄이|늦추|당기)|줄여서|미루고|뒤로\s*미루고|교대하세요|단축하세요|맞춰서\s*쉬세요)"
)

# 1-3. 인사·징계·출입증 회수 및 라인 배치전환 강제 패턴
DISCIPLINE_REASSIGN_PATTERN = re.compile(
    r"(출입증\s*(회수|반납)|현장\s*(퇴출|출입\s*금지|출입\s*제한)|다른\s*(라인|조|공정)로\s*(바꿔|돌려|배치해|보내)|"
    r"야간조로\s*(돌려|바꿔|편성해)|교체해라|교체하세요|작업에서\s*빼세요)"
)

# 1-4. 택트타임 및 작업 속도(노동강도) 통제 패턴
WORK_SPEED_TEMPO_PATTERN = re.compile(
    r"(택트타임|라인\s*속도|라인\s*스피드|컨베이어|작업\s*속도)\s*(올려라|올리세요|맞추세요|높이세요|빨리\s*돌려|스피드업)"
)


# =========================================================================
# [2] 파견법(파견근로자보호법) 불법 파견 요건 탐지 정규식 패턴
# =========================================================================

# 2-1. 특정 인명 + 직함/호칭 정규식 패턴 (한국 성씨 1~4글자 + 직급/호칭)
NAME_TITLE_PATTERN = re.compile(
    r"(?<![가-힣\w])([가-힣]{1,4})\s*(대리|과장|차장|부장|반장|기사|주임|조장|프로|선임|매니저|담당자|엔지니어|씨|님)(?![가-힣\w])"
)

# 2-2. 협력사/외주 직접 지목 패턴
OUTSOURCING_DIRECT_PATTERN = re.compile(
    r"(?<![가-힣\w])(협력사|하청|도급|외주|용역)\s*(직원|인력|기사|담당|작업자|분들|사람)(?![가-힣\w])"
)

# 2-3. 직접적 업무 명령/강제 종결어미 패턴
COMMAND_ENDINGS_PATTERN = re.compile(
    r"([가-힣\w]*)(끝내세요|끝내라|마치세요|마쳐라|수행하세요|진행하세요|작업하세요|보고하세요|"
    r"보고할\s*것|대기하세요|대기해라|투입하세요|투입해라|출근하세요|출근해라|야근하세요|잔업하세요|"
    r"조치하세요|확인하세요|처리하세요|해놓으세요|해라|하시오|하도록\s*하세요)(?![가-힣\w])"
)

# 2-4. 시간 강제 및 마감 시점 압박 패턴
TIME_CONSTRAINT_PATTERN = re.compile(
    r"([0-9]{1,2}시([0-9]{1,2}분)?\s*까지|오늘\s*중으로|당장|지금\s*즉시|금일\s*내로|퇴근\s*전까지|오전\s*중으로)"
)

# 2-5. 구체적 작업 방법/절차 직접 통제 패턴
METHOD_CONTROL_PATTERN = re.compile(
    r"(내가\s*말한\s*대로|내\s*지시대로|지시한\s*방법대로|이렇게\s*작업|순서를\s*바꿔서|임의로\s*하지\s*말고)"
)


def run_pre_guardrail(text: str) -> PreCheckResult:
    """원문 지시어를 분석하여 노란봉투법 및 파견법 위반 패턴을 사전 검출합니다."""
    findings: List[RuleFinding] = []
    suspected_names: List[str] = []
    command_phrases: List[str] = []
    time_constraints: List[str] = []
    safety_discipline_phrases: List[str] = []

    # ---------------------------------------------------------
    # [A] 노란봉투법(노조법 제2조 제2호) 실질적 지배력 검사
    # ---------------------------------------------------------

    # 1. 안전보건 직접 제재 검사
    for match in SAFETY_DISCIPLINE_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        safety_discipline_phrases.append(matched_str)
        findings.append(
            RuleFinding(
                violation_type=ViolationType.SUBSTANTIAL_CONTROL_SAFETY,
                matched_text=matched_str,
                description=f"[노란봉투법 징표] 원청의 협력사 근로자 대상 안전보건 직접 제재/처벌권 행사('{matched_str}')"
            )
        )

    # 2. 휴게/식사시간 일방 통제 검사
    for match in REST_MEAL_TIME_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.SUBSTANTIAL_CONTROL_TIME_REST,
                matched_text=matched_str,
                description=f"[노란봉투법 징표] 본질적 근로조건인 휴게·식사시간의 일방적 배분/단축 간섭('{matched_str}')"
            )
        )

    # 3. 인사·징계 및 출입통제·배치전환 검사
    for match in DISCIPLINE_REASSIGN_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.SUBSTANTIAL_CONTROL_DISCIPLINE,
                matched_text=matched_str,
                description=f"[노란봉투법 징표] 수급인 고유 인사권 침해 및 원청의 출입증 회수/배치전환 강제('{matched_str}')"
            )
        )

    # 4. 택트타임/작업속도 통제 검사
    for match in WORK_SPEED_TEMPO_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.SUBSTANTIAL_CONTROL_WORKLOAD,
                matched_text=matched_str,
                description=f"[노란봉투법 징표] 라인 스피드/택트타임 통제를 통한 노동강도 직접 지배('{matched_str}')"
            )
        )

    # ---------------------------------------------------------
    # [B] 파견법 불법파견 요건 검사
    # ---------------------------------------------------------

    # 5. 특정 개인/직책 지명 검사
    for match in NAME_TITLE_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        if any(rep in matched_str for rep in ["소장", "현장대리인", "총괄"]):
            continue
        suspected_names.append(matched_str)
        findings.append(
            RuleFinding(
                violation_type=ViolationType.SPECIFIC_PERSON_ASSIGNMENT,
                matched_text=matched_str,
                description=f"[불법파견 징표] 특정 작업자 개인({matched_str})에 대한 직접 업무 할당"
            )
        )

    # 6. 협력사 직원 직접 지목 검사
    for match in OUTSOURCING_DIRECT_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.SPECIFIC_PERSON_ASSIGNMENT,
                matched_text=matched_str,
                description=f"[불법파견 징표] 협력사 개별 근로자({matched_str})를 직접 지목하는 표현"
            )
        )

    # 7. 직접 명령형 종결어미 검사
    for match in COMMAND_ENDINGS_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        command_phrases.append(matched_str)
        findings.append(
            RuleFinding(
                violation_type=ViolationType.DIRECT_COMMAND,
                matched_text=matched_str,
                description=f"[불법파견 징표] 원청의 직접적인 업무수행 지휘·명령 어투('{matched_str}')"
            )
        )

    # 8. 시간 강제 검사
    for match in TIME_CONSTRAINT_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        time_constraints.append(matched_str)
        findings.append(
            RuleFinding(
                violation_type=ViolationType.ATTENDANCE_TIME_CONTROL,
                matched_text=matched_str,
                description=f"[불법파견 징표] 구체적 작업 완료 시점 강제 및 시간 통제('{matched_str}')"
            )
        )

    # 9. 작업 방법 직접 통제 검사
    for match in METHOD_CONTROL_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.WORK_METHOD_CONTROL,
                matched_text=matched_str,
                description=f"[불법파견 징표] 작업 방법 및 절차에 대한 직접적 관여/구속('{matched_str}')"
            )
        )

    has_risk = len(findings) > 0
    return PreCheckResult(
        has_risk=has_risk,
        suspected_names=list(set(suspected_names)),
        command_phrases=list(set(command_phrases)),
        time_constraints=list(set(time_constraints)),
        safety_discipline_phrases=list(set(safety_discipline_phrases)),
        findings=findings
    )
