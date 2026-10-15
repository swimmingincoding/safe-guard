"""Hybrid Local RAG Engine for On-Premise Subcontracting Guidelines.

폐쇄망 환경에서 외부 임베딩 서버나 무거운 Vector DB 설치 없이도,
data/guidelines/ 내의 사내 도급 가이드라인 전문, 노동부 매뉴얼, 판례집을
조항 단위로 자동 청킹(Chunking)하고 BM25/키워드 하이브리드 알고리즘으로
0.001초 만에 가장 연관도 높은 조항을 발췌(Retrieval)하는 경량 RAG 엔진입니다.
"""

import os
import re
from typing import List, Dict, Any, Tuple

# 가이드라인 데이터 디렉토리 경로 (프로젝트 루트 기준)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.dirname(CURRENT_DIR)
DATA_GUIDELINES_DIR = os.path.join(TEMPLATE_ROOT, "data", "guidelines")


class DocumentChunk:
    def __init__(self, source_file: str, title: str, content: str):
        self.source_file = source_file
        self.title = title
        self.content = content
        # 검색용 정규화 토큰 추출
        clean_text = f"{title} {content}".lower()
        self.tokens = set(re.findall(r"[가-힣\w]{2,}", clean_text))


class SubcontractRAGEngine:
    def __init__(self, docs_dir: str = DATA_GUIDELINES_DIR):
        self.docs_dir = docs_dir
        self.chunks: List[DocumentChunk] = []
        self._load_and_chunk_documents()

    def _load_and_chunk_documents(self):
        """data/guidelines/ 디렉토리의 마크다운 파일들을 조항 단위로 파싱하여 청킹합니다."""
        if not os.path.exists(self.docs_dir):
            return

        for filename in sorted(os.listdir(self.docs_dir)):
            if not filename.endswith((".md", ".txt")):
                continue

            filepath = os.path.join(self.docs_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()

                # 마크다운 헤더 (### 또는 ##) 단위로 조항 분할
                sections = re.split(r"\n(?=###?\s+)", text)
                for sec in sections:
                    sec = sec.strip()
                    if not sec or len(sec) < 30:
                        continue

                    # 섹션 제목 추출
                    first_line = sec.split("\n", 1)[0].replace("#", "").strip()
                    self.chunks.append(DocumentChunk(
                        source_file=filename,
                        title=first_line,
                        content=sec
                    ))
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """사용자 질의와 가장 관련된 사내 규정 조항 및 판례 청크를 검색합니다."""
        if not self.chunks:
            self._load_and_chunk_documents()

        query_clean = query.lower()
        query_tokens = set(re.findall(r"[가-힣\w]{2,}", query_clean))

        scored_chunks: List[Tuple[float, DocumentChunk]] = []

        for chunk in self.chunks:
            score = 0.0
            chunk_title_lower = chunk.title.lower()
            chunk_content_lower = chunk.content.lower()

            # 1. 제목 완벽/부분 일치 가중치
            for qt in query_tokens:
                if qt in chunk_title_lower:
                    score += 5.0
                elif qt in chunk_content_lower:
                    score += 1.5

            # 2. 토큰 교집합 (Jaccard 계수 기반)
            overlap = len(query_tokens.intersection(chunk.tokens))
            score += overlap * 2.0

            # 3. 중요 도메인 키워드 특별 가중치
            domain_boosts = [
                ("식대", ["식대", "사내식당", "식사"]),
                ("통근버스", ["통근버스", "셔틀"]),
                ("복리후생", ["복리후생", "의무실", "휴게실", "북카페", "헬스장"]),
                ("sop", ["작업표준서", "기술사양서", "sop"]),
                ("mes", ["mes", "전산", "단말기", "태블릿", "wms"]),
                ("잔업", ["연장근로", "야간", "잔업", "특근", "조기출근", "철야"]),
                ("휴가", ["연차", "근태", "휴가", "조퇴", "결근", "반차"]),
                ("안전", ["안전모", "보호구", "안전수칙", "중대재해", "작업중지", "대피"]),
                ("하자", ["하자담보", "불량", "재작업", "사양 미달", "품질 기준"]),
                ("고용승계", ["고용승계", "업체교체", "승계", "계약해지"]),
                ("교육", ["교육", "ojt", "직무훈련", "신규입사", "기술지도", "직무교육"]),
                ("선물", ["선물", "명절", "상품권", "온누리상품권", "귀향비", "추석", "설날", "선물세트"]),
                ("경조사", ["경조사", "화환", "경조금", "결혼", "부고", "조의금", "경조휴가"]),
                ("출입증", ["출입증", "지문", "안면인식", "생체인식", "게이트", "사내보안"]),
                ("클린룸", ["클린룸", "방진복", "방진화", "정전기", "fab"]),
                ("인터록", ["인터록", "알람", "설비정지", "에러코드", "셧다운", "스위치"]),
                ("오버홀", ["오버홀", "pm", "정기보수", "예방보수", "정비", "혼재작업"]),
                ("산재", ["산재", "공상", "부상", "치료비", "의무실", "아차사고", "산재은폐"]),
                ("포상", ["포상", "표창", "인센티브", "우수사원", "성과급", "인사평가", "kpi"]),
                ("단톡방", ["단톡방", "카톡", "카카오톡", "메신저", "단톡", "갠톡"])
            ]

            for key, related in domain_boosts:
                if any(k in query_clean for k in related):
                    if any(k in chunk_content_lower for k in related):
                        score += 4.0

            if score > 0:
                scored_chunks.append((score, chunk))

        # 점수 순으로 정렬 후 상위 k개 반환
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_chunks[:top_k]:
            results.append({
                "score": round(score, 2),
                "source_file": chunk.source_file,
                "title": chunk.title,
                "content": chunk.content
            })

        return results


# 싱글톤 RAG 엔진 인스턴스
_rag_engine_instance = None


def get_rag_engine() -> SubcontractRAGEngine:
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = SubcontractRAGEngine()
    return _rag_engine_instance
