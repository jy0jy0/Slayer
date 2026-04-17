"""JD Parser page."""

import concurrent.futures
import json
import traceback
import streamlit as st

_EDIT_GEN_KEY = "jd_edit_gen"  # 파싱 성공마다 증가 → 위젯 key 갱신으로 강제 재초기화

def _edit_key(name: str) -> str:
    """현재 세대(gen)를 포함한 위젯 key 반환."""
    gen = st.session_state.get(_EDIT_GEN_KEY, 0)
    return f"{name}_{gen}"
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_keyword_tags, render_info_card


def _run_in_thread(fn, *args):
    """동기 함수를 ThreadPoolExecutor에서 실행."""
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(fn, *args).result()


def _crawl_page(url: str):
    """Step 2: 브라우저 크롤링만 수행 (LLM 없음)."""
    import asyncio
    import sys
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    from slayer.pipelines.jd_parser.scraper import _build_run_config
    from slayer.pipelines.jd_parser.registry import get_parser
    from slayer.pipelines.jd_parser.parser_base import JDCrawlError

    parser = get_parser(url)

    async def _run():
        browser_cfg = BrowserConfig(headless=True, verbose=False, user_agent_mode="random")
        run_cfg = _build_run_config(parser.get_crawl_config())
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
            if not result.success:
                raise JDCrawlError(f"크롤 실패: {result.error_message}")
            return result.html or "", result.markdown or ""

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(_run())


def render():
    st.html(GLOBAL_CSS)
    render_page_header("JD Parser", "Parse job descriptions from URLs and extract structured information.")

    # ── Input ─────────────────────────────────────────────────────────
    jd_url = st.text_input("JD URL", placeholder="https://www.jobkorea.co.kr/...", key="jd_parser_url_input")

    with st.expander("⚙️ Options"):
        job_title_filter = st.text_input(
            "Job Title Filter (optional)",
            placeholder="e.g. 백엔드 개발자 — filter when posting has multiple positions",
            key="jd_parser_job_title",
        )

    if st.button("🔍 Parse JD", type="primary", use_container_width=True, disabled=not jd_url):
        # 캐시 확인
        # - job_title 없음 → URL만으로 캐시 조회
        # - job_title 있음 → 같은 URL + 같은 직무명이 DB에 있을 때만 캐시 사용
        #   (같은 URL이라도 다른 직무를 파싱하려는 경우 캐시 무시)
        job_title_input = (job_title_filter or "").strip()
        _cache_hit = False
        try:
            from slayer.db.repository import get_cached_job_posting
            from slayer.schemas import JDSchema
            cached = get_cached_job_posting(
                jd_url,
                position=job_title_input if job_title_input else None,
            )
            if cached and cached.parsed_data:
                jd_schema = JDSchema(**cached.parsed_data)
                jd_json_str = json.dumps(cached.parsed_data, ensure_ascii=False, indent=2)
                st.session_state["jd_parser_result"] = jd_json_str
                st.session_state["jd_data"] = jd_json_str
                st.session_state["jd_source"] = "jd_parser"
                st.session_state[_EDIT_GEN_KEY] = st.session_state.get(_EDIT_GEN_KEY, 0) + 1
                st.session_state["_cache_msg"] = f"✅ DB 캐시에서 로드 — **{jd_schema.company}** / {jd_schema.title}"
                _cache_hit = True
        except Exception as e:
            _cache_err = e

        if _cache_hit:
            st.rerun()

        with st.status("🌐 JD 파싱 시작...", expanded=True) as status:
            try:
                from slayer.pipelines.jd_parser.registry import get_parser
                from slayer.pipelines.jd_parser.parser_base import JDCrawlError, JDLLMError
                from slayer.pipelines.jd_parser.scraper import _save_raw_markdown, _save_parsed_jd

                # Step 1: 파서 선택 (즉시)
                parser = get_parser(jd_url)
                parser_name = type(parser).__name__.replace("Parser", "")
                status.write(f"✅ **[1/4] 파서 선택** — {parser_name}")

                # Step 2: 브라우저 크롤링
                status.update(label="🌐 [2/4] 브라우저 시작 및 페이지 크롤링 중...")
                status.write("⏳ **[2/4] 크롤링** — headless 브라우저 실행 후 페이지 렌더링 중...")
                raw_html, crawl_md = _run_in_thread(_crawl_page, jd_url)
                md_len = len(str(crawl_md))
                status.write(f"✅ **[2/4] 크롤링 완료** — {md_len:,}자 추출")

                # Step 3: LLM 추출
                status.update(label="🤖 [3/4] Gemini LLM 추출 중...")
                status.write("⏳ **[3/4] LLM 추출** — Gemini가 JD 내용을 구조화 중...")

                def _parse():
                    return parser.parse(raw_html, crawl_md, jd_url,
                                        save_raw=False, job_title=job_title_filter or None)

                parse_result = _run_in_thread(_parse)
                jd_schema = parse_result.jd
                suspicious = parse_result.suspicious_items
                image_urls = parse_result.image_urls
                status.write(
                    f"✅ **[3/4] LLM 추출 완료** — "
                    f"스킬 {len(jd_schema.skills)}개 · "
                    f"업무 {len(jd_schema.responsibilities)}개 · "
                    f"요건 {len(jd_schema.requirements.required)}개"
                )
                if image_urls:
                    status.write(f"🖼️ 이미지 기반 공고 — {len(image_urls)}개 이미지 감지")
                if suspicious:
                    status.write(f"⚠️ **Hallucination 의심 {len(suspicious)}건** — 결과 확인 필요")

                # Step 4: 저장
                status.update(label="💾 [4/4] 저장 중...")
                status.write("⏳ **[4/4] 저장** — 파일 및 DB 저장 중...")
                md_text = crawl_md.raw_markdown if hasattr(crawl_md, "raw_markdown") else str(crawl_md)
                _save_raw_markdown(jd_url, md_text)
                _save_parsed_jd(jd_url, jd_schema)

                try:
                    from slayer.db.repository import save_job_posting
                    save_job_posting(jd_schema)
                    status.write("✅ **[4/4] 저장 완료** — 파일 + DB")
                except Exception as db_err:
                    status.write(f"✅ **[4/4] 파일 저장 완료** (DB 저장 실패: {db_err})")

                jd_json_str = json.dumps(jd_schema.model_dump(), ensure_ascii=False, indent=2)
                st.session_state["jd_parser_result"] = jd_json_str
                st.session_state["jd_data"] = jd_json_str
                st.session_state["jd_source"] = "jd_parser"
                st.session_state["jd_suspicious"] = suspicious
                st.session_state["jd_image_urls"] = image_urls

                status.update(label=f"✅ 파싱 완료 — {jd_schema.company} / {jd_schema.title}", state="complete")
                st.session_state[_EDIT_GEN_KEY] = st.session_state.get(_EDIT_GEN_KEY, 0) + 1
                st.rerun()

            except Exception as e:
                from slayer.pipelines.jd_parser.parser_base import JDCrawlError, JDLLMError
                if isinstance(e, JDCrawlError):
                    label = "❌ [2/4] 크롤링 실패"
                    msg = f"페이지를 가져오지 못했습니다.\n\n**원인:** {e}"
                    hint = "URL이 올바른지, 또는 사이트가 접근 가능한지 확인해주세요."
                elif isinstance(e, JDLLMError):
                    label = "❌ [3/4] LLM 추출 실패"
                    msg = f"LLM이 JD 내용을 추출하지 못했습니다.\n\n**단계:** {getattr(e, 'stage', '?')}  **원인:** {getattr(e, 'cause', e)}"
                    hint = "GOOGLE_API_KEY가 올바른지 확인해주세요."
                else:
                    label = "❌ JD 파싱 실패"
                    msg = f"**{type(e).__name__}:** {e}"
                    hint = None

                status.update(label=label, state="error")
                st.error(msg)
                if hint:
                    st.info(hint)
                with st.expander("🔍 상세 에러 (디버깅용)"):
                    st.code(traceback.format_exc(), language="python")
                st.session_state.pop("jd_parser_result", None)

    if "jd_parser_result" not in st.session_state:
        st.info("Enter a JobKorea or Wanted URL and click Parse JD.")
        return

    # ── Result ────────────────────────────────────────────────────────
    if "_cache_msg" in st.session_state:
        st.success(st.session_state.pop("_cache_msg"))
    st.divider()


    try:
        jd = json.loads(st.session_state["jd_parser_result"])
    except json.JSONDecodeError:
        st.error("Invalid result data.")
        return

    image_urls = st.session_state.get("jd_image_urls", [])
    if image_urls:
        with st.expander(f"🖼️ 원본 이미지 {len(image_urls)}개 — 파싱 결과와 직접 비교해보세요", expanded=True):
            st.caption("이미지 기반 공고입니다. 아래 원본 이미지와 파싱 결과를 직접 비교해 확인해주세요.")
            for i, img_url in enumerate(image_urls, 1):
                st.image(img_url, caption=f"JD 이미지 {i}", use_container_width=True)

    suspicious = st.session_state.get("jd_suspicious", [])
    if suspicious:
        with st.expander(f"⚠️ Hallucination 의심 {len(suspicious)}건 — 원본에서 확인되지 않은 내용이 있습니다"):
            st.caption("아래 항목들은 원본 페이지에서 확인되지 않았습니다. 실제 공고와 비교해 직접 검토해주세요.")
            for i, item in enumerate(suspicious, 1):
                st.markdown(f"**{i}.** {item}")

    overview = jd.get("overview", {})

    # 기본 정보 카드
    render_info_card(
        title=f"{jd.get('company', '')} — {jd.get('title', '')}",
        icon="📄",
        rows=[
            ("Position", jd.get("position", "")),
            ("Employment Type", overview.get("employment_type", "")),
            ("Experience", overview.get("experience", "")),
            ("Education", overview.get("education", "")),
            ("Salary", overview.get("salary", "")),
            ("Location", overview.get("location", "")),
            ("Deadline", overview.get("deadline", "")),
            ("Headcount", overview.get("headcount", "")),
            ("Platform", jd.get("platform", "")),
        ],
    )

    st.markdown("")

    # 주요 업무 / 자격 요건
    col_resp, col_req = st.columns(2)
    with col_resp:
        responsibilities = jd.get("responsibilities", [])
        if responsibilities:
            st.markdown("**주요 업무**")
            for r in responsibilities:
                st.markdown(f"- {r}")

    with col_req:
        requirements = jd.get("requirements", {})
        required = requirements.get("required", [])
        preferred = requirements.get("preferred", [])
        if required:
            st.markdown("**필수 요건**")
            for r in required:
                st.markdown(f"- {r}")
        if preferred:
            st.markdown("**우대 사항**")
            for p in preferred:
                st.markdown(f"- {p}")

    # 기술 스택
    skills = jd.get("skills", [])
    if skills:
        st.markdown("")
        st.markdown("**기술 스택**")
        render_keyword_tags(skills, [])

    # 복리후생 / 채용 절차
    benefits = jd.get("benefits", [])
    process = jd.get("process", [])
    if benefits or process:
        col_ben, col_proc = st.columns(2)
        with col_ben:
            if benefits:
                st.markdown("**복리후생**")
                for b in benefits:
                    st.markdown(f"- {b}")
        with col_proc:
            if process:
                st.markdown("**채용 절차**")
                for i, p in enumerate(process, 1):
                    st.markdown(f"{i}. {p}")

    notes = jd.get("notes")
    if notes:
        st.info(notes)

    st.success("✅ JD data saved — go to **JD-Resume Match** to run matching analysis.")

    # ── 인라인 편집 ───────────────────────────────────────────────────
    st.divider()
    with st.expander("✏️ 파싱 결과 수정 — 틀린 내용이 있으면 여기서 고쳐주세요"):
        st.caption("항목은 **줄바꿈(Enter)으로 구분**해서 입력하세요. 수정 후 아래 저장 버튼을 누르면 DB에도 반영됩니다.")

        edited_responsibilities = st.text_area(
            "주요 업무",
            value="\n".join(jd.get("responsibilities", [])),
            height=150,
            key=_edit_key("edit_responsibilities"),
        )

        col_req_edit, col_pref_edit = st.columns(2)
        with col_req_edit:
            edited_required = st.text_area(
                "필수 요건",
                value="\n".join(jd.get("requirements", {}).get("required", [])),
                height=150,
                key=_edit_key("edit_required"),
            )
        with col_pref_edit:
            edited_preferred = st.text_area(
                "우대 사항",
                value="\n".join(jd.get("requirements", {}).get("preferred", [])),
                height=150,
                key=_edit_key("edit_preferred"),
            )

        edited_skills = st.text_area(
            "기술 스택",
            value="\n".join(jd.get("skills", [])),
            height=100,
            key=_edit_key("edit_skills"),
        )

        col_ben_edit, col_proc_edit = st.columns(2)
        with col_ben_edit:
            edited_benefits = st.text_area(
                "복리후생",
                value="\n".join(jd.get("benefits", [])),
                height=120,
                key=_edit_key("edit_benefits"),
            )
        with col_proc_edit:
            edited_process = st.text_area(
                "채용 절차",
                value="\n".join(jd.get("process", [])),
                height=120,
                key=_edit_key("edit_process"),
            )

        if st.button("💾 수정 저장", type="primary", use_container_width=True):
            def _parse_lines(text: str) -> list[str]:
                return [line.strip() for line in text.splitlines() if line.strip()]

            def _parse_skills(text: str) -> list[str]:
                """normalize_skills validator와 동일: 소문자 + 중복 제거."""
                seen: set[str] = set()
                result: list[str] = []
                for line in text.splitlines():
                    normalized = line.strip().lower()
                    if normalized and normalized not in seen:
                        seen.add(normalized)
                        result.append(normalized)
                return result

            updated_fields = {
                "responsibilities": _parse_lines(edited_responsibilities),
                "requirements": {
                    "required": _parse_lines(edited_required),
                    "preferred": _parse_lines(edited_preferred),
                },
                "skills": _parse_skills(edited_skills),
                "benefits": _parse_lines(edited_benefits),
                "process": _parse_lines(edited_process),
            }

            # session_state 업데이트
            jd.update(updated_fields)
            jd_json_str = json.dumps(jd, ensure_ascii=False, indent=2)
            st.session_state["jd_parser_result"] = jd_json_str
            st.session_state["jd_data"] = jd_json_str

            # DB 업데이트
            try:
                from slayer.db.repository import update_job_posting
                update_job_posting(jd.get("url", ""), updated_fields)
                st.session_state["jd_edit_saved"] = "db"
            except Exception as db_err:
                st.session_state["jd_edit_saved"] = f"file_only:{db_err}"

            # gen 증가 → 수정 저장 후 edit 위젯이 저장된 값으로 재초기화됨
            st.session_state[_EDIT_GEN_KEY] = st.session_state.get(_EDIT_GEN_KEY, 0) + 1
            st.rerun()

    with st.expander("📋 Raw JSON"):
        st.json(jd)

    # 수정 저장 완료 메시지 (rerun 후 한 번만 표시)
    if "jd_edit_saved" in st.session_state:
        saved_state = st.session_state["jd_edit_saved"]
        del st.session_state["jd_edit_saved"]
        if saved_state == "db":
            st.success("✅ 수정 저장 완료 — 화면과 DB가 모두 업데이트되었습니다.")
        else:
            err = saved_state.replace("file_only:", "")
            st.warning(f"✅ 화면 업데이트 완료 — DB 저장 실패: {err}")
