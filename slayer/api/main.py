"""FastAPI application factory."""

# ── 아래 코드는 FastAPI 서버를 실제로 띄울 때 주석 해제 ──────────────
#
# import logging
#
# from fastapi import FastAPI
# from slayer.api.routes import resumes, applications, health
#
#
# def create_app() -> FastAPI:
#     # logging.basicConfig()는 앱 전체의 로그 설정을 한 번에 담당한다.
#     # 각 모듈(generator.py 등)은 getLogger(__name__)만 선언해두면,
#     # 여기서 설정한 포맷·레벨이 slayer.* 하위 모든 모듈에 자동 적용된다.
#     # → FastAPI 서버를 켤 때 이 한 줄로 전체 로그가 활성화됨.
#     logging.basicConfig(
#         level=logging.INFO,
#         format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
#         datefmt="%H:%M:%S",
#     )
#
#     app = FastAPI(title="Slayer API", version="0.1.0")
#     app.include_router(health.router)
#     app.include_router(resumes.router, prefix="/api/v1")
#     app.include_router(applications.router, prefix="/api/v1")
#     return app
