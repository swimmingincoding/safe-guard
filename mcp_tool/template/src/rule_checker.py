"""Pre-Guardrail Rule Checker with Yellow Envelope Law (노란봉투법) Specialization.

순수 파이썬 코드로 동작하여 0.001초 만에:
1) 전통적 파견법상 불법파견 징표(인명 지목, 직접 지휘명령, 시간 통제, 디지털 지휘명령, 비공식 채널, 혼재작업, 근태개입)
2) 노란봉투법상 원청의 '실질적 지배력(사용자성)' 인정 징표(안전보건 직접제재, 휴게시간 단축, 배치전환 강제, 속도 통제)
3) 산업안전보건법상 정당한 긴급 대피/작업중지권 예외 식별
4) 협력사 현장대리인(소장, 관리자) 공식 채널 적법성 분별
을 고정밀 정규식으로 사전 검출하는 하네스 모듈입니다.
"""

import re
from typing import List
from .schemas import PreCheckResult, RuleFinding, ViolationType


# =========================================================================
# [0] 적법성 인정 및 예외 패턴 (오탐 방지)
# =========================================================================

# 0-1. 산업안전보건법 제51조/제52조에 따른 급박한 위험 시 긴급 대피/작업중지권 패턴
EMERGENCY_EVACUATION_PATTERN = re.compile(
    r"(화재|폭발|가스\s*누출|유독\s*(가스|물질)|질식|붕괴|추락\s*위험|감전\s*위험|비상\s*사태|비상\s*벨|사이렌)\s*.*?"
    r"(대피|피신|작업\s*중지|현장\s*철수|피하세요|나가세요|대피하세요|철수하세요)|"
    r"(즉시|당장|모두)\s*(대피하세요|피하세요|작업을?\s*중지하고\s*대피|현장에서\s*철수|안전한\s*곳으로)"
)

# 0-2. 협력사 현장대리인(소장/총괄) 공식 수신처 명시 패턴
SITE_REPRESENTATIVE_PATTERN = re.compile(
    r"(?<![가-힣\w])((협력사|도급사|수급사)\s*)?(소장님|현장대리인|총괄관리자|현장관리인|소장\s*귀하|대리인님|안전관리자)(?![가-힣\w])"
)

# 0-3. 민법 제667조에 따른 정당한 도급 하자담보책임(결과물 사양 미달 재작업 요청) 패턴
LEGITIMATE_DEFECT_REMEDY_PATTERN = re.compile(
    r"(사양서|규격|도면|품질\s*기준|토크|치수|불량률|납품된\s*제품|도급\s*결과물|완성물)\s*.*?"
    r"(미달|불일치|하자|불량|결함)\s*.*?(재작업|보수|수정|시정)\s*(요청|부탁|바랍니다)"
)


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

# 2-4. 위장 청유형/부탁형 직접 지시 패턴 (대법원 판례상 청유형 위장도 지휘명령으로 인정)
POLITE_COMMAND_PATTERN = re.compile(
    r"([가-힣\w]*)(해주실\s*수\s*있나요|해주시겠어요|해주실래요|부탁드립니다|부탁드려요|부탁해요|"
    r"도와주세요|봐주세요|조치\s*부탁|마무리\s*부탁|작업\s*부탁|와주실\s*수\s*있나요|와주세요)(?![가-힣\w])"
)

# 2-5. 시간 강제 및 마감 시점 압박 패턴
TIME_CONSTRAINT_PATTERN = re.compile(
    r"([0-9]{1,2}시([0-9]{1,2}분)?\s*까지|오늘\s*중으로|당장|지금\s*즉시|금일\s*내로|퇴근\s*전까지|오전\s*중으로|"
    r"퇴근\s*(조금만\s*)?늦게|야근\s*좀|잔업\s*좀|철야)"
)

# 2-6. 구체적 작업 방법/절차 직접 통제 패턴
METHOD_CONTROL_PATTERN = re.compile(
    r"(내가\s*말한\s*대로|내\s*지시대로|지시한\s*방법대로|이렇게\s*작업|순서를\s*바꿔서|임의로\s*하지\s*말고|"
    r"작업\s*순서\s*(바꾸지\s*말고|지키세요)|매뉴얼대로\s*안\s*하고)"
)

# 2-7. 카카오톡/사내 비공식 메신저/단톡방을 통한 지시·보고 패턴 (포스코 판례 등)
INFORMAL_CHANNEL_PATTERN = re.compile(
    r"(카톡|카카오톡|단톡방|단톡|갠톡|개인\s*톡|사내\s*메신저|팀즈\s*채팅|라인\s*단톡)\s*(으로|에)?\s*"
    r"(지시|보고|공유|전달|알려|말해|올려|보내|주세요|하세요|바랍니다)"
)

# 2-8. 스마트팩토리 MES/전산 단말기 매개 실시간 작업 통제 패턴 (현대차 판례 등)
DIGITAL_SYSTEM_COMMAND_PATTERN = re.compile(
    r"(mes|전산망|전산\s*단말기|태블릿|모바일\s*단말기|바코드\s*스캐너)\s*"
    r"(보고\s*작업|순서\s*바꿔서|보고\s*투입|에\s*찍힌\s*대로|실시간\s*확인하고\s*바로|대로\s*작업하세요|화면\s*보고)"
)

# 2-9. 원하청 혼재 작업 및 원청 조직 편입 지시 패턴
MIXED_WORK_PATTERN = re.compile(
    r"(우리\s*(팀|부서|조|직원|사람)|원청\s*직원)\s*.*?"
    r"(옆에서\s*보조|같이\s*작업|에\s*붙어서|과\s*함께\s*수행|대신해서\s*작업|지원\s*나가세요|지원\s*가세요|한\s*조로)"
)

# 2-10. 휴가/조퇴/근태 직접 승인·반려 간섭 패턴
LEAVE_CONTROL_PATTERN = re.compile(
    r"(휴가|연차|조퇴|결근|반차|특근)\s*.*?"
    r"(쓰려면\s*나한테|원청에\s*보고|승인\s*못\s*해|허락\s*받고|미루세요|안\s*됩니다|원청에\s*제출|승인\s*안|결재\s*받으세요)"
)


def run_pre_guardrail(text: str) -> PreCheckResult:
    """원문 지시어를 분석하여 노란봉투법 및 파견법 위반 패턴을 사전 검출합니다."""
    findings: List[RuleFinding] = []
    suspected_names: List[str] = []
    command_phrases: List[str] = []
    time_constraints: List[str] = []
    safety_discipline_phrases: List[str] = []
    emergency_phrases: List[str] = []

    # ---------------------------------------------------------
    # [0] 적법 예외 및 현장대리인 사전 식별
    # ---------------------------------------------------------
    has_site_rep = bool(SITE_REPRESENTATIVE_PATTERN.search(text))

    # 긴급 대피/작업중지권 확인 (산업안전보건법 제51조/제52조)
    is_emergency = False
    for match in EMERGENCY_EVACUATION_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        emergency_phrases.append(matched_str)
        is_emergency = True

    # ---------------------------------------------------------
    # [A] 노란봉투법(노조법 제2조 제2호) 실질적 지배력 검사
    # ---------------------------------------------------------

    # 1. 안전보건 직접 제재 검사 (단, 긴급 대피 상황은 제재가 아닌 정당 조치)
    if not is_emergency:
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

    # 5. 특정 개인/직책 지명 검사 (현장대리인 호칭은 정당한 소통 창구이므로 제외)
    for match in NAME_TITLE_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        # 현장대리인/소장/총괄 직책이 명시된 경우 제외 (정당한 소통 채널)
        if any(rep in matched_str for rep in ["소장", "현장대리인", "총괄", "대리인", "관리인", "안전관리자"]):
            continue
        # 만약 현장대리인 수신자(소장님 등)가 이미 명시되어 있고, "반장님"이 경어체로 함께 쓰인 경우 제외
        if has_site_rep and any(rep in matched_str for rep in ["반장", "조장"]):
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

    # 8. 위장 청유형/부탁형 직접 지시 검사
    # (개별 직원 지목 또는 시간 강제와 결합될 때 지휘명령으로 판정)
    for match in POLITE_COMMAND_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        # 정당한 하자보수 요청문이거나 수신처가 현장대리인인 정식 협조 요청이면 제외
        if LEGITIMATE_DEFECT_REMEDY_PATTERN.search(text) and not suspected_names:
            continue
        if has_site_rep and not suspected_names:
            continue
        # 협력사 직원 지목 또는 시간 압박이 수반된 청유형은 위장 지휘명령
        command_phrases.append(matched_str)
        findings.append(
            RuleFinding(
                violation_type=ViolationType.DIRECT_COMMAND,
                matched_text=matched_str,
                description=f"[불법파견 징표] 부탁·청유형 어투이나 실질적 업무수행 직접 지시로 인정('{matched_str}')"
            )
        )

    # 9. 시간 강제 검사
    for match in TIME_CONSTRAINT_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        time_constraints.append(matched_str)
        findings.append(
            RuleFinding(
                violation_type=ViolationType.ATTENDANCE_TIME_CONTROL,
                matched_text=matched_str,
                description=f"[불법파견 징표] 구체적 작업 완료 시점 강제 및 근무시간 통제('{matched_str}')"
            )
        )

    # 10. 작업 방법 직접 통제 검사
    for match in METHOD_CONTROL_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.WORK_METHOD_CONTROL,
                matched_text=matched_str,
                description=f"[불법파견 징표] 작업 방법 및 절차에 대한 직접적 관여/구속('{matched_str}')"
            )
        )

    # 11. 비공식 메신저/단톡방을 통한 지시 검사
    for match in INFORMAL_CHANNEL_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.INFORMAL_COMMUNICATION,
                matched_text=matched_str,
                description=f"[불법파견 징표] 비공식 메신저/단톡방을 통한 실시간 업무 지시 및 보고 통제('{matched_str}')"
            )
        )

    # 12. 스마트팩토리 MES/전산 단말기 매개 실시간 작업 통제 검사
    for match in DIGITAL_SYSTEM_COMMAND_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.DIGITAL_SYSTEM_CONTROL,
                matched_text=matched_str,
                description=f"[불법파견 징표] MES/전산 단말기를 매개로 한 실시간 작업순서 통제 및 지휘명령('{matched_str}')"
            )
        )

    # 13. 원하청 혼재 작업 및 원청 조직 편입 검사
    for match in MIXED_WORK_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.MIXED_WORK_ORGANIZATION,
                matched_text=matched_str,
                description=f"[불법파견 징표] 원하청 혼재작업 및 원청 고유 조직으로의 실질적 노무 편입('{matched_str}')"
            )
        )

    # 14. 휴가/조퇴/근태 직접 승인·반려 개입 검사
    for match in LEAVE_CONTROL_PATTERN.finditer(text):
        matched_str = match.group(0).strip()
        findings.append(
            RuleFinding(
                violation_type=ViolationType.ATTENDANCE_TIME_CONTROL,
                matched_text=matched_str,
                description=f"[불법파견 징표] 수급인 고유 권한인 휴가·근태에 대한 원청의 직접 승인/반려/통제('{matched_str}')"
            )
        )

    # 긴급 대피 상황인 경우: 단순 위험이 아니라 법령상 적법한 긴급 조치이므로 위험 플래그 해제/조정
    if is_emergency:
        findings.clear()
        has_risk = False
    else:
        has_risk = len(findings) > 0

    return PreCheckResult(
        has_risk=has_risk,
        is_emergency_evacuation=is_emergency,
        has_site_representative=has_site_rep,
        suspected_names=list(set(suspected_names)),
        command_phrases=list(set(command_phrases)),
        time_constraints=list(set(time_constraints)),
        safety_discipline_phrases=list(set(safety_discipline_phrases)),
        emergency_phrases=list(set(emergency_phrases)),
        findings=findings
    )

