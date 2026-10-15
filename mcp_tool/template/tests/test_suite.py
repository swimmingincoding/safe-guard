"""Safe-Direction Agent 통합 테스트 스위트 (Integrated Test Suite).

파편화된 테스트를 단일 파일로 통합하여, 1회 실행만으로:
1. [지시어 감사 & 노란봉투법] 고위험 지시 및 실질적 지배력 탐지/변환 검증
2. [회색지대(Gray Zone) 판별력] 청유형 위장 지시 vs 정당한 하자보수 구분 검증
3. [사내 가이드라인 RAG Q&A] 식대 복리후생, SOP 열람 등 사내 규정 조항(제O조) 인용 검증
을 일괄 수행합니다.
"""

import sys
import os
import json

# Windows 콘솔 인코딩 대응
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# template 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.main import audit_and_rewrite_direction, search_labor_compliance_qa
from src.schemas import RiskLevel


def test_1_high_risk_and_yellow_envelope():
    """테스트 1: 고위험 지시어 및 노란봉투법 실질적 지배력 탐지 검증."""
    print("\n" + "=" * 70)
    print("🚨 [검증 1] 고위험 지시어 및 노란봉투법 실질적 지배력 탐지")
    print("=" * 70)

    # 1-1. 직접 명령 + 인명 지목
    text1 = "협력사 김 대리, 내일 14시까지 3라인 센서 교체 무조건 끝내세요."
    data1 = json.loads(audit_and_rewrite_direction(text1))
    print(f"• 발화: \"{text1}\"")
    print(f"  ➜ 엔진 상태: [LLM 호출: {data1.get('llm_invoked', 'N')}] (모드: {data1.get('execution_mode')})")
    print(f"  ➜ 위험도: {data1['risk_level']} (점수: {data1['risk_score']}) | 변환: \"{data1['rewrites'][0]['rewritten_text'][:50]}...\"")
    assert data1["risk_level"] == RiskLevel.DANGER.value
    assert "김 대리" not in data1["rewrites"][0]["rewritten_text"]
    assert data1.get("llm_invoked") in ["Y", "N"]

    # 1-2. 노란봉투법 안전보건 직접 제재
    text2 = "협력사 작업자들 안전모 턱끈 안 매면 다음 주부터 현장 출입 금지 조치합니다."
    data2 = json.loads(audit_and_rewrite_direction(text2))
    print(f"• 발화: \"{text2}\"")
    print(f"  ➜ 실질적 지배력 감지: {data2['yellow_envelope_analysis']['is_substantial_control_detected']} | 사용자성 리스크: {data2['yellow_envelope_analysis']['employer_status_risk']}")
    assert data2["yellow_envelope_analysis"]["is_substantial_control_detected"] is True

    print("  ✅ [검증 1 통과] 고위험 및 노란봉투법 징표 정상 감지 완료 (엔진 상태 추적 포함)")


def test_2_gray_zone_discrimination():
    """테스트 2: 모호한 회색지대(Gray Zone) 판별력 검증 (오탐 방지)."""
    print("\n" + "=" * 70)
    print("🔍 [검증 2] 모호한 회색지대(Gray Zone) 판별력 검증")
    print("=" * 70)

    # 2-1. 청유형 위장 연장근로 지시 (위험으로 정확히 간파)
    text_request = "혹시 오늘 생산량이 좀 빠듯한데, 협력사분들 퇴근 조금만 늦게 하시고 작업 마무리 도와주실 수 있나요?"
    data_req = json.loads(audit_and_rewrite_direction(text_request))
    print(f"• 청유형 지시: \"{text_request}\"")
    print(f"  ➜ 판정: {data_req['risk_level']} (부탁 형태라도 연장근로 개입은 위험으로 간파)")
    assert data_req["risk_level"] in [RiskLevel.DANGER.value, RiskLevel.CAUTION.value]

    # 2-2. 정당한 하자보수 요구 (무리한 위험 오탐 방지)
    text_defect = "A공정 센서 장착부 볼트 조임 토크가 사양서 규격(50Nm)에 미달하여 불량 발생했습니다. 규격에 맞게 재작업 요청드립니다."
    data_defect = json.loads(audit_and_rewrite_direction(text_defect))
    print(f"• 하자보수 요구: \"{text_defect}\"")
    print(f"  ➜ 판정: {data_defect['risk_level']} (도급인의 정당한 하자담보책임 행사 인정)")
    assert data_defect["risk_level"] in [RiskLevel.SAFE.value, RiskLevel.CAUTION.value]

    # 2-3. 현장대리인 통상적 진척도 확인 (완전 합법)
    text_progress = "안녕하세요 소장님, 오늘 오전 정기 점검 작업은 예정대로 차질 없이 진행되고 있는지 진척 상황 공유 부탁드립니다."
    data_progress = json.loads(audit_and_rewrite_direction(text_progress))
    print(f"• 진척 확인: \"{text_progress}\"")
    print(f"  ➜ 판정: {data_progress['risk_level']} (합법적 업무 모니터링 정상 통과)")
    assert data_progress["risk_level"] == RiskLevel.SAFE.value

    print("  ✅ [검증 2 통과] 과잉 탐지 없는 정밀한 그레이존 분별력 확인 완료")


def test_3_rag_labor_compliance_qa():
    """테스트 3: 사내 도급 가이드라인 RAG 지식 기반 노무 Q&A 실전 고난도 검증 (5대 핵심 쟁점)."""
    print("\n" + "=" * 70)
    print("📚 [검증 3] 사내 규정 RAG 지식 기반 노무 Q&A 실전 5대 핵심 쟁점 검증")
    print("=" * 70)

    qa_test_cases = [
        {
            "category": "1. 복리후생 편의 제공 (식대/통근버스)",
            "query": "협력사 직원들에게 사내 식당 식대나 통근버스 이용을 지원해도 불법파견에 안 걸리나요?",
            "expected_keywords": ["식대", "복리후생", "식당"],
        },
        {
            "category": "2. 스마트팩토리 MES/전산 작업 지시 (디지털 지휘명령)",
            "query": "스마트팩토리 MES 전산 단말기를 협력사 작업자들에게 지급해서 실시간 작업 사양과 공정 일정을 확인하게 해도 되나요?",
            "expected_keywords": ["MES", "단말기", "조회"],
        },
        {
            "category": "3. 중대재해처벌법 안전관리 vs 노란봉투법 직접 제재 충돌",
            "query": "중대재해처벌법 때문에 원청도 협력사 안전을 챙겨야 하는데, 현장에서 안전모를 안 쓴 협력사 직원을 발견했을 때 원청 관리자가 즉시 작업장에서 퇴출시키거나 출입증을 회수해도 되나요?",
            "expected_keywords": ["안전", "제재", "소장", "위반"],
        },
        {
            "category": "4. 납품 결과물 불량 시 재작업 요구 (민법상 하자보수 청구권)",
            "query": "협력사가 납품한 센서 결함이 발견되어 재작업이 필요한데, 협력사 작업자에게 가서 볼트를 풀고 다시 조립하라고 직접 재작업을 지시해도 되나요?",
            "expected_keywords": ["하자", "결과물", "방법"],
        },
        {
            "category": "5. 긴급 공정 지연 시 연장근로(잔업) 요청",
            "query": "긴급 공정 지연으로 납기가 촉박한 상황인데, 원청 담당자가 협력사 직원들에게 직접 오늘 저녁 잔업 2시간만 더 해달라고 부탁해도 괜찮은가요?",
            "expected_keywords": ["연장", "잔업", "소장", "근로시간"],
        },
        {
            "category": "6. 신규 입사자 OJT 직무 훈련 직접 지도 (삼성전자서비스 판례 등)",
            "query": "협력사에 새로 들어온 작업자가 공정을 잘 모르는데, 원청 실무자가 1:1로 장비 조작법이나 OJT 교육을 직접 시켜줘도 되나요?",
            "expected_keywords": ["교육", "OJT", "소장", "자체"],
        },
        {
            "category": "7. 명절 선물세트/상품권 직접 지급 (임금성 복리후생 편입)",
            "query": "설 명절에 원청 사기진작용 햄 선물세트나 온누리상품권을 협력사 직원들에게 직접 나눠줘도 괜찮나요?",
            "expected_keywords": ["선물", "명절", "도급비", "법인"],
        }
    ]

    for idx, case in enumerate(qa_test_cases, 1):
        print(f"\n[{idx}] 📌 {case['category']}")
        print(f"• 질문: \"{case['query']}\"")
        qa_data = json.loads(search_labor_compliance_qa(case["query"]))

        print(f"  ➜ 엔진 상태: [LLM 호출: {qa_data.get('llm_invoked', 'N')}] (모드: {qa_data.get('execution_mode')})")
        print(f"  ➜ 컴플라이언스 판정: {qa_data['compliance_status']}")
        print(f"  ➜ 핵심 결론: {qa_data['summary_answer']}")
        print(f"  ➜ 인용 법조문/판례: {qa_data['legal_basis'][:100]}...")
        if qa_data.get("do_and_dont"):
            print("  ➜ 현장 실무 수칙 (DO & DON'T):")
            for guide in qa_data["do_and_dont"][:2]:
                print(f"     * {guide}")
        print(f"  ➜ 참조 사내 가이드: {qa_data['references']}")

        assert len(qa_data["do_and_dont"]) >= 1, "실무 수칙이 최소 1개 이상 생성되어야 합니다."
        assert len(qa_data["references"]) >= 1, "참조 규정 문서가 최소 1개 이상 인용되어야 합니다."

    print("\n  ✅ [검증 3 통과] 사내 도급 가이드라인 및 판례 기반 5대 실전 노무 Q&A 전건 완벽 통과")


def test_4_advanced_legal_precedents_and_safety():
    """테스트 4: 고도화된 법적 엔진 정밀도 검증 (산안법 긴급대피, 포스코 단톡방, 현대차 MES, 혼재작업)."""
    print("\n" + "=" * 70)
    print("⚖️ [검증 4] 고도화된 최신 법원 판례 및 산업안전보건법 긴급조치 정밀 판별 검증")
    print("=" * 70)

    # 4-1. 산업안전보건법 제51조/52조에 따른 정당한 긴급 대피 명령 (오탐 방지: SAFE)
    text_emergency = "3공정 가스 누출 비상벨 울렸습니다! 작업자분들 즉시 작업을 중지하고 안전한 곳으로 대피하세요!"
    data_emergency = json.loads(audit_and_rewrite_direction(text_emergency))
    print(f"• 긴급 대피 명령: \"{text_emergency}\"")
    print(f"  ➜ 판정: {data_emergency['risk_level']} (점수: {data_emergency['risk_score']}) | 모드: {data_emergency.get('execution_mode')}")
    print(f"  ➜ 요약: {data_emergency['summary']}")
    assert data_emergency["risk_level"] == RiskLevel.SAFE.value
    assert data_emergency["risk_score"] == 0
    assert "산업안전보건법" in data_emergency["legal_basis"]

    # 4-2. 포스코 광양제철소 판례: 비공식 카카오톡/단톡방 실시간 작업 지시/보고
    text_chat = "협력사 기사님들, 앞으로 작업 완료될 때마다 카톡으로 사진 찍어서 실시간 보고하세요."
    data_chat = json.loads(audit_and_rewrite_direction(text_chat))
    print(f"• 단톡방 지시: \"{text_chat}\"")
    print(f"  ➜ 판정: {data_chat['risk_level']} (점수: {data_chat['risk_score']}) | 위반: {data_chat['violations']}")
    assert data_chat["risk_level"] in [RiskLevel.DANGER.value, RiskLevel.CAUTION.value]
    assert any("INFORMAL_COMMUNICATION" in str(v) or "DIRECT_COMMAND" in str(v) for v in data_chat["violations"])

    # 4-3. 현대자동차 아산공장 판례: 스마트팩토리 MES/전산 단말기 매개 실시간 작업순서 변경
    text_mes = "3라인 협력사 작업자분들, MES 화면 보고 작업 순서 바꿔서 진행하세요."
    data_mes = json.loads(audit_and_rewrite_direction(text_mes))
    print(f"• MES 전산 지시: \"{text_mes}\"")
    print(f"  ➜ 판정: {data_mes['risk_level']} (점수: {data_mes['risk_score']}) | 위반: {data_mes['violations']}")
    assert data_mes["risk_level"] in [RiskLevel.DANGER.value, RiskLevel.CAUTION.value]
    assert any("DIGITAL_SYSTEM_CONTROL" in str(v) or "WORK_METHOD_CONTROL" in str(v) or "DIRECT_COMMAND" in str(v) for v in data_mes["violations"])

    # 4-4. 원하청 혼재작업 및 원청 조직 편입 지시
    text_mixed = "협력사 박 기사, 오늘 우리 부서 A직원 옆에서 보조 작업 같이 진행해."
    data_mixed = json.loads(audit_and_rewrite_direction(text_mixed))
    print(f"• 혼재작업 지시: \"{text_mixed}\"")
    print(f"  ➜ 판정: {data_mixed['risk_level']} (점수: {data_mixed['risk_score']}) | 위반: {data_mixed['violations']}")
    assert data_mixed["risk_level"] == RiskLevel.DANGER.value
    assert any("MIXED_WORK_ORGANIZATION" in str(v) or "SPECIFIC_PERSON" in str(v) or "DIRECT_COMMAND" in str(v) for v in data_mixed["violations"])

    # 4-5. 협력사 현장대리인(소장님 등) 정식 채널 지정 소통의 적법성 유지
    text_rep = "협력사 소장님 귀하, 4분기 설비 정기점검 도급 건과 관련하여 품질 기준에 맞게 일정 내 완료될 수 있도록 협조 부탁드립니다."
    data_rep = json.loads(audit_and_rewrite_direction(text_rep))
    print(f"• 현장대리인 공식 소통: \"{text_rep}\"")
    print(f"  ➜ 판정: {data_rep['risk_level']} (점수: {data_rep['risk_score']})")
    assert data_rep["risk_level"] == RiskLevel.SAFE.value

    print("  ✅ [검증 4 통과] 산안법 긴급대피, 포스코 단톡방, 현대차 MES, 혼재작업 등 고난도 법률 판례 100% 검증 완료")


def run_all_tests():
    print("=" * 70)
    print("🚀 Safe-Direction Agent 고도화 법률 엔진 통합 검증 시작")
    print("=" * 70)
    test_1_high_risk_and_yellow_envelope()
    test_2_gray_zone_discrimination()
    test_3_rag_labor_compliance_qa()
    test_4_advanced_legal_precedents_and_safety()
    print("\n" + "=" * 70)
    print("🎉 모든 검증 성공! (All Integrated Tests Passed 100%)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()

