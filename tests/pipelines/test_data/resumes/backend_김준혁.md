# 이력서

## 인적사항

| 항목 | 내용 |
|------|------|
| **이름** | 김준혁 |
| **생년월일** | 1996.03.15 |
| **연락처** | 010-0000-0001 |
| **이메일** | junhyuk.sample@example.com |
| **GitHub** | https://github.com/example/junhyuk-kim |

---

## 경력사항

### 쿠팡 — Senior Backend Engineer
**2023.01 ~ 현재** (3년)

물류 플랫폼팀 소속. 대규모 트래픽 환경에서의 주문/배송 시스템 설계 및 운영 담당.

- 일평균 주문 처리량 150만 건 규모의 주문 서비스 안정화
- 팀 내 코드 리뷰 문화 정착, 리뷰 커버리지 95% 이상 유지
- 신규 입사자 온보딩 프로그램 설계 및 멘토링 (4명)

### 네이버 — Backend Developer
**2021.01 ~ 2022.12** (2년)

검색 플랫폼팀. 네이버 쇼핑 검색 API 개발 및 운영.

- 상품 검색 API 응답 속도 개선 (평균 320ms → 180ms, 44% 개선)
- Elasticsearch 클러스터 운영 및 인덱싱 파이프라인 관리 (일 2,000만 건 색인)
- 검색 필터링 기능 고도화 (가격 범위, 브랜드 필터, 리뷰 점수 기반)

---

## 프로젝트

### 1. 결제 시스템 MSA 전환
**기간**: 2024.03 ~ 2024.09 | **소속**: 쿠팡

모놀리식 결제 시스템을 MSA로 분리. 결제 승인, 정산, 환불 서비스를 독립 배포 단위로 전환.

- **역할**: 기술 리드 (팀원 5명)
- **기술스택**: Java 17, Spring Boot 3.2, Kafka, gRPC, MySQL, Redis
- **성과**:
  - 배포 주기 월 1회 → 주 3회로 단축
  - 결제 실패율 0.8% → 0.2%로 감소
  - 장애 전파 차단을 위한 Circuit Breaker 도입 (Resilience4j)

### 2. 실시간 재고 관리 시스템
**기간**: 2023.06 ~ 2023.12 | **소속**: 쿠팡

전국 물류센터의 실시간 재고 현황을 통합 관리하는 시스템. 재고 정합성 문제 해결이 핵심 과제.

- **역할**: 백엔드 개발
- **기술스택**: Java 17, Spring WebFlux, Kafka Streams, DynamoDB, Redis
- **성과**:
  - 재고 정합성 99.7% → 99.95%로 개선
  - 재고 조회 API 처리량 초당 12,000 TPS 달성
  - 이벤트 소싱 패턴 적용으로 재고 변동 추적 가능

### 3. 물류 최적화 API 개발
**기간**: 2023.01 ~ 2023.05 | **소속**: 쿠팡

배송 경로 최적화를 위한 내부 API 서비스. 배송 기사별 최적 경로 및 물량 배분 알고리즘 적용.

- **역할**: 백엔드 개발
- **기술스택**: Java 17, Spring Boot, PostgreSQL, Redis, Docker
- **성과**:
  - 배송 기사 1인당 평균 배송 건수 15% 증가
  - 경로 계산 시간 8초 → 1.2초로 단축
  - A/B 테스트 프레임워크 구축으로 알고리즘 비교 검증 체계 확립

### 4. 네이버 쇼핑 검색 인증 시스템 개선
**기간**: 2022.03 ~ 2022.08 | **소속**: 네이버

외부 판매자 API 인증 체계를 OAuth 2.0 기반으로 전환. 기존 API Key 방식의 보안 취약점 해결.

- **역할**: 백엔드 개발
- **기술스택**: Java 11, Spring Security, OAuth 2.0, JWT, MySQL
- **성과**:
  - 인증 관련 보안 이슈 발생 건수 월 15건 → 0건
  - 외부 판매자 API 연동 시간 평균 5일 → 2일로 단축
  - API 호출 인증 처리 시간 50ms 이내 유지

---

## 기술스택

| 분류 | 기술 |
|------|------|
| **Language** | Java (17, 11), Kotlin |
| **Framework** | Spring Boot, Spring WebFlux, Spring Security, Spring Data JPA |
| **Database** | MySQL, PostgreSQL, DynamoDB, Redis, Elasticsearch |
| **Message Queue** | Apache Kafka, Kafka Streams |
| **Infra** | Docker, Kubernetes, AWS (EC2, RDS, SQS, S3) |
| **CI/CD** | Jenkins, GitHub Actions, ArgoCD |
| **Monitoring** | Datadog, Grafana, Prometheus |
| **기타** | gRPC, REST API, JUnit 5, Mockito |

---

## 학력

| 기간 | 학교 | 전공 | 학위 |
|------|------|------|------|
| 2015.03 ~ 2021.02 | 한양대학교 | 컴퓨터소프트웨어학부 | 학사 |

---

## 자격증

| 자격증명 | 취득일 | 발급기관 |
|----------|--------|----------|
| 정보처리기사 | 2020.08 | 한국산업인력공단 |
| AWS Solutions Architect Associate | 2022.03 | Amazon Web Services |
