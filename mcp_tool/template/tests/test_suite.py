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
    print(f"  ➜ 위험도: {data1['risk_level']} (점수: {data1['risk_score']}) | 변환: \"{data1['rewrites'][0]['rewritten_text'][:50]}...\"")
    assert data1["risk_level"] == RiskLevel.DANGER.value
    assert "김 대리" not in data1["rewrites"][0]["rewritten_text"]

    # 1-2. 노란봉투법 안전보건 직접 제재
    text2 = "협력사 작업자들 안전모 턱끈 안 매면 다음 주부터 현장 출입 금지 조치합니다."
    data2 = json.loads(audit_and_rewrite_direction(text2))
    print(f"• 발화: \"{text2}\"")
    print(f"  ➜ 실질적 지배력 감지: {data2['yellow_envelope_analysis']['is_substantial_control_detected']} | 사용자성 리스크: {data2['yellow_envelope_analysis']['employer_status_risk']}")
    assert data2["yellow_envelope_analysis"]["is_substantial_control_detected"] is True

    print("  ✅ [검증 1 통과] 고위험 및 노란봉투법 징표 정상 감지 완료")


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
    """테스트 3: 사내 도급 가이드라인 RAG 지식 기반 노무 Q&A 검증."""
    print("\n" + "=" * 70)
    print("📚 [검증 3] 사내 규정 RAG 지식 기반 노무 Q&A 검증")
    print("=" * 70)

    # 복리후생 식대 지원 질문
    query = "협력사 직원들에게 사내 식당 식대나 통근버스 이용을 지원해도 불법파견에 안 걸리나요?"
    qa_data = json.loads(search_labor_compliance_qa(query))
    print(f"• 질문: \"{query}\"")
    print(f"  ➜ 판정 상태: {qa_data['compliance_status']}")
    print(f"  ➜ 답변 요약: {qa_data['summary_answer']}")
    print(f"  ➜ 인용 규정: {qa_data['legal_basis'][:80]}...")
    print(f"  ➜ 참조 출처: {qa_data['references']}")

    assert len(qa_data["do_and_dont"]) >= 2
    assert len(qa_data["references"]) >= 1

    print("  ✅ [검증 3 통과] 사내 도급 가이드라인 조항 인용 및 실무 가이드 완성")


def run_all_tests():
    print("=" * 70)
    print("🚀 Safe-Direction Agent 통합 검증 시작")
    print("=" * 70)
    test_1_high_risk_and_yellow_envelope()
    test_2_gray_zone_discrimination()
    test_3_rag_labor_compliance_qa()
    print("\n" + "=" * 70)
    print("🎉 모든 검증 성공! (All Integrated Tests Passed 100%)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
