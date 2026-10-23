
import hashlib
import json
import os
import re
import threading
import time
from collections import OrderedDict, deque
from typing import Any, Callable, Deque, Dict, List, Optional

import httpx

import config

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_TIMEOUT_SECONDS: float = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", 15))
GEMINI_RATE_LIMIT: int = int(os.environ.get("GEMINI_RATE_LIMIT_PER_MINUTE", 10))
EXPLAIN_CACHE_SIZE = 512
MAX_TOOL_ROUNDS = 4
MAX_HISTORY_TURNS = 8
MAX_TOOL_RESULT_CHARS = 6000

EXPLAIN_FIELDS = (
    "tenTruong", "maTruong", "tenChuongTrinh", "tenNganh", "maToHop", "maPhuongThuc", "khuVuc",
    "diemXetTuyen", "diemChuanThamChieu", "namThamChieu", "coDuBao", "diemChuanDuBao", "namMucTieu",
    "khoangTinCay80", "delta", "chiSoThuanLoi", "nhomNguyenVong", "hocPhiUocTinh", "trangThaiHocPhi",
    "lyDoDeXuat",
)

EXPLAIN_SYSTEM = (
    "Bạn là trợ lý tư vấn tuyển sinh đại học cho học sinh THPT Việt Nam. "
    "Hãy giải thích bằng tiếng Việt, 3-5 câu, văn bản thuần không dùng Markdown, giọng thân thiện, vì sao nguyện vọng dưới đây được xếp vào nhóm đã cho. "
    "Chỉ dùng đúng các con số được cung cấp, không bịa thêm số liệu. "
    "Nói rõ điểm chuẩn năm tới chỉ là dự báo có sai số, và kết quả chỉ mang tính tham khảo."
)

CHAT_SYSTEM = (
    "Bạn là trợ lý hỏi đáp của Hệ hỗ trợ quyết định gợi ý nguyện vọng đại học cho học sinh THPT dựa trên dự báo điểm chuẩn bằng Random Forest, triển khai qua REST API. Trả lời bằng tiếng Việt, ngắn gọn, văn bản thuần (không dùng Markdown như ** hay #; được xuống dòng và dùng dấu - đầu dòng). "
    "Mọi số liệu (điểm chuẩn, điểm xét tuyển, học phí, nguyện vọng gợi ý, độ chính xác mô hình) "
    "BẮT BUỘC phải lấy bằng cách gọi các hàm được cung cấp; tuyệt đối không trả lời số liệu từ trí nhớ. "
    "Nếu hàm không trả về dữ liệu, nói rõ là hệ thống chưa có dữ liệu. "
    "Từ chối lịch sự các câu hỏi ngoài chủ đề tuyển sinh. Không hỏi và không nhắc lại thông tin cá nhân."
)

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)\d{8,10}(?!\d)")


class GeminiError(Exception):
    pass


def che_thong_tin_ca_nhan(text: str) -> str:
    return _PHONE_RE.sub("[đã ẩn]", _EMAIL_RE.sub("[đã ẩn]", text))


class GeminiClient:

    def __init__(self, api_key: Optional[str] = None, model: str = GEMINI_MODEL,
                 timeout: float = GEMINI_TIMEOUT_SECONDS):
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.model = model
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, contents: List[Dict[str, Any]], system: str,
                 tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.configured:
            raise GeminiError("Chua cau hinh GEMINI_API_KEY")
        body: Dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
                "thinkingConfig": {"thinkingLevel": "low"},
            },
        }
        if tools:
            body["tools"] = [{"functionDeclarations": tools}]
        try:
            resp = httpx.post(
                GEMINI_API_URL.format(model=self.model),
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=body,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise GeminiError(f"Goi Gemini that bai: {type(exc).__name__}") from exc


class RateLimiter:

    def __init__(self, limit: int = GEMINI_RATE_LIMIT, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._calls: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            calls = self._calls.setdefault(key, deque())
            while calls and now - calls[0] > self.window:
                calls.popleft()
            if len(calls) >= self.limit:
                return False
            calls.append(now)
            return True


def _text_of(content: Dict[str, Any]) -> str:
    return "".join(p.get("text", "") for p in content.get("parts", [])).strip()


class GeminiService:
    def __init__(self, client: Optional[GeminiClient] = None,
                 tools: Optional[Dict[str, Dict[str, Any]]] = None):
        self.client = client or GeminiClient()
        self.tools: Dict[str, Dict[str, Any]] = tools or {}
        self._cache: "OrderedDict[str, str]" = OrderedDict()
        self._cache_lock = threading.Lock()

    def register_tool(self, name: str, description: str, parameters: Optional[Dict[str, Any]],
                      handler: Callable[..., Any]) -> None:
        self.tools[name] = {"description": description, "parameters": parameters, "handler": handler}

    def giaiThichNguyenVong(self, item: Dict[str, Any]) -> Dict[str, Any]:
        du_lieu = {k: item.get(k) for k in EXPLAIN_FIELDS if item.get(k) not in (None, "")}
        du_phong = item.get("lyDoDeXuat") or "Chưa có lời giải thích cho nguyện vọng này."
        key = hashlib.sha256(json.dumps(du_lieu, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return {"giaiThich": self._cache[key], "nguon": "cache"}

        if not self.client.configured:
            return {"giaiThich": du_phong, "nguon": "du_phong", "lyDo": "Chua cau hinh Gemini"}
        prompt = "Dữ liệu nguyện vọng (JSON):\n" + json.dumps(du_lieu, ensure_ascii=False)
        try:
            text = _text_of(self.client.generate([{"role": "user", "parts": [{"text": prompt}]}], EXPLAIN_SYSTEM))
        except GeminiError as exc:
            return {"giaiThich": du_phong, "nguon": "du_phong", "lyDo": str(exc)}
        if not text:
            return {"giaiThich": du_phong, "nguon": "du_phong", "lyDo": "Gemini khong tra loi"}

        with self._cache_lock:
            self._cache[key] = text
            if len(self._cache) > EXPLAIN_CACHE_SIZE:
                self._cache.popitem(last=False)
        return {"giaiThich": text, "nguon": "gemini"}

    def _run_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            return {"loi": f"Không có hàm '{name}'"}
        try:
            result = tool["handler"](**(args or {}))
        except Exception as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            return {"loi": str(detail)[:500]}
        text = json.dumps(result, ensure_ascii=False, default=str)
        if len(text) > MAX_TOOL_RESULT_CHARS:
            return {"ketQua": text[:MAX_TOOL_RESULT_CHARS], "biCatBot": True}
        return {"ketQua": result}

    def hoiDap(self, cau_hoi: str, lich_su: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not self.client.configured:
            return {
                "traLoi": "Trợ lý AI chưa được bật trên máy chủ (thiếu GEMINI_API_KEY). "
                          "Bạn vẫn có thể dùng các chức năng tra cứu và gợi ý nguyện vọng.",
                "nguon": "du_phong", "hamDaGoi": [],
            }

        contents: List[Dict[str, Any]] = []
        for turn in (lich_su or [])[-MAX_HISTORY_TURNS:]:
            role = "model" if turn.get("vaiTro") == "model" else "user"
            contents.append({"role": role, "parts": [{"text": che_thong_tin_ca_nhan(str(turn.get("noiDung", "")))}]})
        contents.append({"role": "user", "parts": [{"text": che_thong_tin_ca_nhan(cau_hoi)}]})

        declarations = []
        for n, t in self.tools.items():
            decl = {"name": n, "description": t["description"]}
            if t["parameters"]:
                decl["parameters"] = t["parameters"]
            declarations.append(decl)
        ham_da_goi: List[str] = []
        try:
            for _ in range(MAX_TOOL_ROUNDS + 1):
                content = self.client.generate(contents, CHAT_SYSTEM, declarations)
                calls = [p["functionCall"] for p in content.get("parts", []) if "functionCall" in p]
                if not calls:
                    text = _text_of(content)
                    if not text:
                        break
                    return {"traLoi": text, "nguon": "gemini", "hamDaGoi": ham_da_goi}
                if len(ham_da_goi) >= MAX_TOOL_ROUNDS * 3:
                    break
                contents.append({"role": "model", "parts": content.get("parts", [])})
                responses = []
                for call in calls:
                    ham_da_goi.append(call.get("name", ""))
                    responses.append({"functionResponse": {
                        "name": call.get("name", ""),
                        "response": self._run_tool(call.get("name", ""), call.get("args", {})),
                    }})
                contents.append({"role": "user", "parts": responses})
        except GeminiError as exc:
            return {"traLoi": "Trợ lý AI tạm thời không phản hồi. Vui lòng thử lại sau.",
                    "nguon": "du_phong", "lyDo": str(exc), "hamDaGoi": ham_da_goi}
        return {"traLoi": "Xin lỗi, mình chưa tìm được câu trả lời phù hợp. Bạn thử hỏi cụ thể hơn nhé.",
                "nguon": "du_phong", "hamDaGoi": ham_da_goi}
