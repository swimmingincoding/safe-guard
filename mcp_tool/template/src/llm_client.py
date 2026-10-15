"""Internal LLM Client supporting both Closed Network (OpenAI-compatible) and Test Gemini API with Yellow Envelope Law support."""

import os
import json
import logging
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

from .schemas import PreCheckResult, ViolationType

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "internal-secret-token")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "npo-maxis-llm")


def call_gemini_api(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Google GenAI SDK를 사용하여 실제 Gemini 모델을 호출합니다."""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
            response_mime_type="application/json"
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=config
        )
        return response.text
    except Exception as e:
        logger.error("Gemini API call failed: %s", e)
        return None


def call_internal_openai_api(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 15.0
) -> Optional[str]:
    """사내 폐쇄망 OpenAI 규격(vLLM / NPO-MAXIS) API를 호출합니다."""
    ssl_verify = os.getenv("SSL_VERIFY", "true").lower() in ("true", "1", "yes")
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        with httpx.Client(timeout=timeout, verify=ssl_verify) as client:
            resp = client.post(f"{LLM_BASE_URL}/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            # 사내 vLLM 서버가 response_format 파라미터를 지원하지 않아 400 에러를 뱉는 경우 대비
            elif resp.status_code == 400:
                logger.info("Internal LLM returned 400. Retrying without response_format parameter...")
                payload.pop("response_format", None)
                retry_resp = client.post(f"{LLM_BASE_URL}/chat/completions", headers=headers, json=payload)
                if retry_resp.status_code == 200:
                    data = retry_resp.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.info("Internal LLM endpoint not reachable: %s", e)

    return None


def call_internal_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    timeout: float = 15.0
) -> Optional[str]:
    """설정된 프로바이더에 따라 LLM 호출을 라우팅합니다."""
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        resp = call_gemini_api(system_prompt, user_prompt)
        if resp:
            return resp

    resp = call_internal_openai_api(system_prompt, user_prompt, timeout=timeout)
    if resp:
        return resp

    return None


def generate_llm_audit_fallback(
    text: str,
    pre_check: PreCheckResult,
    context: str = ""
) -> Dict[str, Any]:
    """노란봉투법과 파견법 법리를 완벽 반영한 하네스 Fallback 생성기."""
    # [A] 긴급 대피/작업중지권 상황 (산업안전보건법 제51조/제52조 정당한 긴급피난)
    if pre_check.is_emergency_evacuation:
        return {
            "risk_level": "SAFE",
            "risk_score": 0,
            "summary": "산업안전보건법 제51조 및 제52조에 의거한 급박한 위험 시 정당한 근로자 긴급 대피 및 작업중지 조치입니다 (컴플라이언스 위반 소지 없음).",
            "violations": [],
            "flagged_phrases": pre_check.emergency_phrases,
            "legal_basis": (
                "산업안전보건법 제51조(사업주의 작업중지) 및 제52조(근로자의 작업중지)에 따르면, "
                "화재, 폭발, 가스누출 등 산업재해가 발생할 급박한 위험이 있을 때의 즉각적 대피 명령은 "
                "원청의 불법 지휘명령이나 노란봉투법상 부당한 노무제재에 해당하지 않으며, 법령상 인정되는 정당한 긴급구호권 행사입니다."
            ),
            "yellow_envelope_analysis": {
                "is_substantial_control_detected": False,
                "employer_status_risk": "LOW",
                "statutory_articles": ["산업안전보건법 제51조", "산업안전보건법 제52조"],
                "precedents": ["대법원 판례상 긴급구호 및 피난 조치의 정당성 인정 법리"],
                "collective_bargaining_risk": "산업재해 예방을 위한 긴급 대피 조치이므로 부당노동행위 리스크가 없습니다."
            },
            "rewrites": [
                {
                    "channel": "현장 비상 방송 / 협력사 전 작업자 및 관리자",
                    "rewritten_text": text,
                    "key_points": ["비상 상황 대피 명령은 현 상태 그대로 즉시 전파하셔도 법적으로 완전 정당합니다."]
                }
            ],
            "action_guides": [
                "작업자 전원 안전 구역으로 즉각 대피 완료 후, 협력사 현장대리인 및 안전관리자에게 상황을 즉시 공유하십시오.",
                "원청-협력사 합동 안전 점검 및 위험 요소 완전 제거 전까지는 작업을 재개하지 마십시오."
            ]
        }

    yellow_envelope_triggered = any(
        f.violation_type in [
            ViolationType.SUBSTANTIAL_CONTROL_SAFETY,
            ViolationType.SUBSTANTIAL_CONTROL_TIME_REST,
            ViolationType.SUBSTANTIAL_CONTROL_DISCIPLINE,
            ViolationType.SUBSTANTIAL_CONTROL_WORKLOAD
        ]
        for f in pre_check.findings
    )

    if not pre_check.has_risk:
        return {
            "risk_level": "SAFE",
            "risk_score": 10,
            "summary": "원청의 실질적 지배력 행사(노란봉투법)나 직접 지휘·명령(파견법) 요건이 발견되지 않은 적법한 도급 요청입니다.",
            "violations": [],
            "flagged_phrases": [],
            "legal_basis": "도급계약의 본지에 부합하며, 수급인의 독립적 노무관리권을 침해하지 않습니다.",
            "yellow_envelope_analysis": {
                "is_substantial_control_detected": False,
                "employer_status_risk": "LOW",
                "statutory_articles": ["노동조합 및 노동관계조정법 제2조 제2호"],
                "precedents": ["서울고등법원 2023누35795 판결"],
                "collective_bargaining_risk": "원청의 사용자성이 인정될 소지가 없어 하청노조의 직접 교섭 요구 리스크가 극히 낮습니다."
            },
            "rewrites": [
                {
                    "channel": "협력사 현장대리인(소장) 공식 채널",
                    "rewritten_text": text,
                    "key_points": ["현재 표현 그대로 소통하셔도 법적 리스크가 없습니다."]
                }
            ],
            "action_guides": ["도급 업무의 결과물 및 납기 기준 중심으로 소통을 지속해 주세요."]
        }

    # 위험도 산출
    if yellow_envelope_triggered or (len(pre_check.suspected_names) > 0 and len(pre_check.command_phrases) > 0):
        risk_level = "DANGER"
        risk_score = 92
        employer_risk = "HIGH"
    else:
        risk_level = "CAUTION"
        risk_score = 65
        employer_risk = "MEDIUM"

    violations = [f.violation_type.value for f in pre_check.findings]
    flagged = [f.matched_text for f in pre_check.findings]

    clean_text = text
    for name in pre_check.suspected_names:
        clean_text = clean_text.replace(name, "").strip()
    for phrase in pre_check.safety_discipline_phrases:
        clean_text = clean_text.replace(phrase, "안전수칙 준수").strip()
    for cmd in pre_check.command_phrases:
        clean_text = clean_text.replace(cmd, "진행").strip()
    import re
    clean_text = re.sub(r"\s+", " ", clean_text).strip(",. ")

    suggested_rewrite_1 = (
        f"[협력사 현장대리인(소장) 귀하] 금일 계획된 도급 업무 건({clean_text})과 관련하여, "
        "도급계약서상 안전보건 관리 기준 및 공정 일정을 준수하여 귀사 관리감독 하에 원활히 진행될 수 있도록 협조 요청드립니다."
    )

    suggested_rewrite_2 = (
        f"[협력사 공식 채널] 해당 공정의 정상 가동과 관련하여 협력사 자체 작업 계획에 따라 "
        "일정 내 품질 기준에 부합하게 완료될 수 있도록 현장 점검 부탁드립니다."
    )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "summary": (
            "노란봉투법상 원청의 '실질적 지배력(사용자성)' 인정 소지 및 파견법상 불법 지휘명령 요건이 "
            f"복합 감지되었습니다 (위험도: {risk_level})."
        ),
        "violations": list(set(violations)),
        "flagged_phrases": list(set(flagged)),
        "legal_basis": (
            "노동조합 및 노동관계조정법 제2조 제2호(실질적 지배력설) 및 서울고등법원 2023누35795(CJ대한통운 사건) 판례에 의거, "
            "원청이 협력사 근로자의 안전보건, 근로시간/휴게, 작업배치 등 본질적 근로조건을 직접 지배·통제할 경우 "
            "원청이 협력사 노조의 '사용자'로 인정되어 단체교섭 의무가 발생합니다."
        ),
        "yellow_envelope_analysis": {
            "is_substantial_control_detected": yellow_envelope_triggered,
            "employer_status_risk": employer_risk,
            "statutory_articles": [
                "노동조합 및 노동관계조정법 제2조 제2호 (사용자의 정의 확대)",
                "노동조합 및 노동관계조정법 제2조 제5호 (노동쟁의 대상 확대)"
            ],
            "precedents": [
                "서울고등법원 2024.1.12. 선고 2023누35795 판결 (CJ대한통운 사건)",
                "대법원 2010.3.25. 선고 2007두8881 판결 (현대중공업 사건)"
            ],
            "collective_bargaining_risk": (
                "원청이 협력사 근로자의 안전제재, 근로시간, 작업배치를 직접 통제하는 증거로 채택될 경우, "
                "협력사 노조가 원청에 직접 단체교섭을 요구할 권리가 발생하며, 거부 시 부당노동행위로 고발될 수 있습니다."
            )
        },
        "rewrites": [
            {
                "channel": "협력사 현장대리인(소장) 공식 메신저/공문",
                "rewritten_text": suggested_rewrite_1,
                "key_points": [
                    "원청의 직접 제재/명령을 배제하고 '도급 계약서상 협력사의 자체 관리 의무' 촉구로 전환",
                    "개별 근로자가 아닌 '협력사 현장대리인'을 공식 수신처로 지정하여 실질적 지배력 징표 차단"
                ]
            },
            {
                "channel": "협력사 관리자 유선/업무 연락망",
                "rewritten_text": suggested_rewrite_2,
                "key_points": [
                    "협력사의 작업 배정 및 인력 운용 자율권을 전적으로 보장하는 표현 사용"
                ]
            }
        ],
        "action_guides": [
            "협력사 작업자에게 안전수칙 위반 벌점 부과나 출입증 회수를 직접 통보하지 마십시오.",
            "휴게시간, 점심시간, 작업 속도(택트타임)를 원청 편의대로 일방 조정하지 마십시오.",
            "모든 조치는 도급 계약에 근거하여 협력사 현장대리인(소장)을 통해 자체 시정 조치를 요구해야 합니다."
        ]
    }
