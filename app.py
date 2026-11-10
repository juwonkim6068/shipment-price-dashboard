"""출고 단가 관리 대시보드."""

import hashlib
import io
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from supabase import create_client


STATUSES = [
    "확인 중",
    "정상",
    "수정 필요",
    "기준정보 수정 필요",
]

JUDGMENTS = [
    "단가차이 확인",
    "기준단가 확인",
    "데이터 확인",
    "조정·반품 확인",
    "일치",
]

CSS = """
<style>
.stApp {
    background: #F3F5F9;
    color: #172B46;
}

[data-testid="stHeader"] {
    background: rgba(243, 245, 249, 0.96);
}

.block-container {
    max-width: 1460px;
    padding-top: 2.6rem;
    padding-bottom: 4rem;
}

html, body, .stApp, input, button, textarea {
    font-family:
        "Pretendard", "Noto Sans KR",
        "Malgun Gothic", sans-serif;
}

h1, h2, h3 {
    color: #172B46;
    letter-spacing: -0.04em;
}

h3 {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
}

[data-testid="stCaptionContainer"] {
    color: #718096;
    line-height: 1.7;
}

.hero {
    background: linear-gradient(115deg, #152840, #24496D);
    border-radius: 20px;
    padding: 32px 36px;
    margin-bottom: 24px;
    box-shadow: 0 12px 30px #15284012;
}

.eyebrow {
    color: #A9C7E5;
    font-size: 11px;
    letter-spacing: 0.19em;
    font-weight: 700;
}

.hero-title {
    color: white;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -0.05em;
    margin: 10px 0;
}

.hero-description {
    color: #D5E0ED;
    font-size: 14px;
    line-height: 1.85;
}

.steps {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 22px;
}

.steps span {
    color: #EDF3FB;
    border: 1px solid #FFFFFF25;
    background: #FFFFFF10;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 12px;
}

.section {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin: 28px 0 16px;
}

.section-num {
    background: #E5ECFB;
    color: #285FD1;
    min-width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    font-size: 12px;
    font-weight: 800;
}

.section-title {
    font-size: 19px;
    font-weight: 750;
    letter-spacing: -0.04em;
    line-height: 1.5;
}

.section-description {
    font-size: 12px;
    color: #718096;
    margin-top: 3px;
    line-height: 1.7;
}

[data-testid="stExpander"] {
    background: white;
    border: 1px solid #E1E7F0;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 12px;
}

[data-testid="stExpander"] summary {
    padding-top: 14px;
    padding-bottom: 14px;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E1E7F0;
    border-radius: 14px;
    padding: 20px;
    min-height: 128px;
    box-shadow: 0 3px 12px #172B4605;
}

[data-testid="stMetricLabel"] {
    color: #718096;
    font-size: 13px;
}

[data-testid="stMetricValue"] {
    font-size: clamp(24px, 2.5vw, 34px);
    font-weight: 700;
    color: #172B46;
    letter-spacing: -0.05em;
}

[data-testid="stForm"] {
    background: white;
    border: 1px solid #E1E7F0;
    border-radius: 14px;
    padding: 24px;
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-color: #E1E7F0 !important;
    border-radius: 14px !important;
}

[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}

[data-testid="stAlert"] {
    border-radius: 10px;
}

.stButton button,
.stDownloadButton button,
.stFormSubmitButton button {
    border-radius: 9px;
    min-height: 42px;
    font-weight: 600;
}

button[kind="primary"],
button[kind="primaryFormSubmit"] {
    background: #285FD1;
    border-color: #285FD1;
    color: white;
}

button[kind="primary"]:hover,
button[kind="primaryFormSubmit"]:hover {
    background: #204FAD;
    border-color: #204FAD;
    color: white;
}

.footer {
    border-top: 1px solid #DDE5EF;
    margin-top: 36px;
    padding-top: 18px;
    font-size: 12px;
    color: #8190A4;
    line-height: 1.8;
}

@media (max-width: 640px) {
    .block-container {
        padding: 1.5rem 1rem 3rem;
    }

    .hero {
        padding: 24px 22px;
    }

    .hero-title {
        font-size: 27px;
    }

    [data-testid="stMetric"] {
        min-height: 105px;
        padding: 16px;
    }
}
</style>
"""


def section(number, title, description):
    # 고정된 화면 문구에만 사용하는 함수입니다.
    st.markdown(
        f"""
        <div class="section">
            <div class="section-num">{number}</div>
            <div>
                <div class="section-title">{title}</div>
                <div class="section-description">{description}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def read_excel(upload):
    upload.seek(0)

    engine = (
        "xlrd"
        if upload.name.lower().endswith(".xls")
        else "openpyxl"
    )

    frame = pd.read_excel(
        upload,
        engine=engine,
        dtype=str,
        keep_default_na=False,
    )
    frame.columns = frame.columns.astype(str).str.strip()

    return frame


def number(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def validate(price, shipment, tolerance):
    price = price.copy()
    shipment = shipment.copy()

    requirements = [
        (
            price,
            [
                "코드", "품번", "판매단가",
                "사용여부", "시작일자", "종료일자",
            ],
            "단가현황",
        ),
        (
            shipment,
            [
                "코드", "품번", "출고번호",
                "출고일자", "출고수량", "단가",
            ],
            "출고현황",
        ),
    ]

    for frame, required, name in requirements:
        missing = set(required) - set(frame.columns)

        if missing:
            raise ValueError(
                f"{name}에 필요한 열이 없습니다: "
                f"{', '.join(sorted(missing))}"
            )

    for frame in [price, shipment]:
        for col in ["코드", "품번"]:
            frame[col] = frame[col].astype(str).str.strip()

    price = price[
        price["사용여부"].str.strip().eq("1.사용")
    ].copy()

    if price.duplicated(["코드", "품번"]).any():
        raise ValueError(
            "사용 중인 기준단가에 코드·품번 중복이 있습니다. "
            "중복을 정리한 후 다시 등록해 주세요."
        )

    price["기준단가"] = number(price["판매단가"])

    price = price[
        ["코드", "품번", "기준단가", "시작일자", "종료일자"]
    ].rename(
        columns={
            "시작일자": "기준시작일",
            "종료일자": "기준종료일",
        }
    )

    shipment = shipment[
        shipment["출고번호"].str.strip().ne("")
        & shipment["품번"].ne("")
    ].copy()

    if shipment.empty:
        raise ValueError("출고 상세 데이터가 없습니다.")

    # 기존 버전과 동일한 방식으로 상세행을 식별합니다.
    shipment["행키"] = [
        hashlib.sha256(
            f"{i}|{row['출고번호']}|{row['품번']}".encode()
        ).hexdigest()
        for i, row in shipment.iterrows()
    ]

    result = shipment.merge(
        price,
        on=["코드", "품번"],
        how="left",
        validate="many_to_one",
    )

    for col in ["출고수량", "단가"]:
        result[col] = number(result[col])

    result["단가차이"] = (
        result["단가"] - result["기준단가"]
    )

    result["출고월"] = (
        result["출고일자"].str[:4]
        + "-"
        + result["출고일자"].str[4:6]
    )

    def judge(row):
        if (
            pd.isna(row["출고수량"])
            or pd.isna(row["단가"])
        ):
            return "데이터 확인"

        if row["출고수량"] <= 0:
            return "조정·반품 확인"

        if pd.isna(row["기준단가"]):
            return "기준단가 확인"

        if abs(row["단가차이"]) > tolerance:
            return "단가차이 확인"

        return "일치"

    result["판정"] = result.apply(judge, axis=1)

    comparable = result["판정"].isin(
        ["일치", "단가차이 확인"]
    )

    result["차이금액"] = (
        result["단가차이"] * result["출고수량"]
    ).where(comparable)

    result["차이규모"] = result["차이금액"].abs()

    def reference_note(row):
        notes = []

        if (
            pd.notna(row["기준단가"])
            and row["기준단가"] <= 1
        ):
            notes.append("기준단가 1원 이하")

        start = pd.to_datetime(
            str(row["기준시작일"]),
            format="%Y%m%d",
            errors="coerce",
        )
        end = pd.to_datetime(
            str(row["기준종료일"]),
            format="%Y%m%d",
            errors="coerce",
        )
        shipped = pd.to_datetime(
            str(row["출고일자"]),
            format="%Y%m%d",
            errors="coerce",
        )

        if (
            pd.notna(start)
            and pd.notna(end)
            and end < start
        ):
            notes.append("기준단가 적용기간 역전")

        if (
            pd.notna(start)
            and pd.notna(shipped)
            and shipped < start
        ):
            notes.append("출고 후 적용되는 최신단가")

        if (
            pd.notna(end)
            and pd.notna(shipped)
            and shipped > end
        ):
            notes.append("기준단가 적용기간 종료")

        return " / ".join(notes)

    result["기준정보주의"] = result.apply(
        reference_note,
        axis=1,
    )

    return result


def judgment_style(value):
    colors = {
        "단가차이 확인": ("#FFF1E8", "#AC540E"),
        "기준단가 확인": ("#F1ECFF", "#6C39AC"),
        "데이터 확인": ("#FFF0F0", "#B83838"),
        "조정·반품 확인": ("#EDF3FC", "#3E608D"),
        "일치": ("#EDF8F1", "#24744E"),
    }

    if value not in colors:
        return ""

    background, foreground = colors[value]

    return (
        f"background-color:{background};"
        f"color:{foreground};"
        "font-weight:600"
    )


def format_table(frame):
    formats = {
        col: "{:,.2f}"
        for col in [
            "출고수량", "단가", "기준단가",
            "단가차이", "차이금액", "차이규모",
        ]
        if col in frame.columns
    }

    return (
        frame.style
        .format(formats, na_rep="—")
        .map(judgment_style, subset=["판정"])
    )


def draw_judgments(monthly):
    labels = {
        "단가차이 확인": "단가 차이",
        "기준단가 확인": "기준단가 없음",
        "데이터 확인": "데이터 확인",
        "조정·반품 확인": "조정·반품",
        "일치": "일치",
    }

    counts = (
        monthly["판정"]
        .value_counts()
        .reindex(list(labels), fill_value=0)
    )

    chart_data = pd.DataFrame({
        "판정": list(labels.values()),
        "건수": [int(counts[key]) for key in labels],
    })

    spec = {
        "height": 250,
        "padding": {"right": 45},
        "encoding": {
            "y": {
                "field": "판정",
                "type": "nominal",
                "sort": list(labels.values()),
                "axis": {
                    "title": None,
                    "labelFontSize": 12,
                    "labelPadding": 12,
                    "labelLimit": 150,
                    "ticks": False,
                    "domain": False,
                },
            },
            "x": {
                "field": "건수",
                "type": "quantitative",
                "scale": {"zero": True},
                "axis": None,
            },
        },
        "layer": [
            {
                "mark": {
                    "type": "bar",
                    "cornerRadiusEnd": 5,
                    "height": 20,
                },
                "encoding": {
                    "color": {
                        "condition": {
                            "test": "datum['판정'] === '일치'",
                            "value": "#CBD5E1",
                        },
                        "value": "#3B6FE8",
                    },
                    "tooltip": [
                        {
                            "field": "판정",
                            "type": "nominal",
                        },
                        {
                            "field": "건수",
                            "type": "quantitative",
                            "format": ",",
                        },
                    ],
                },
            },
            {
                "mark": {
                    "type": "text",
                    "align": "left",
                    "dx": 8,
                    "fontSize": 12,
                    "fontWeight": 600,
                    "color": "#334155",
                },
                "encoding": {
                    "text": {
                        "field": "건수",
                        "type": "quantitative",
                        "format": ",",
                    }
                },
            },
        ],
        "config": {
            "background": "transparent",
            "view": {"stroke": None},
            "font": "Malgun Gothic, sans-serif",
        },
    }

    st.vega_lite_chart(
        chart_data,
        spec,
        use_container_width=True,
    )


def export_excel(frame):
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

    output = io.BytesIO()

    safe = frame.drop(
        columns=["행키"],
        errors="ignore",
    ).copy()

    for col in safe.select_dtypes(
        include=["object", "string"]
    ).columns:
        safe[col] = safe[col].map(
            lambda value: (
                ILLEGAL_CHARACTERS_RE.sub("", value)
                if isinstance(value, str)
                else value
            )
        )

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        safe.to_excel(
            writer,
            index=False,
            sheet_name="점검결과",
        )

        sheet = writer.sheets["점검결과"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        # 입력 문자열이 Excel 수식으로 실행되지 않게 합니다.
        for row in sheet:
            for cell in row:
                if cell.data_type == "f":
                    cell.data_type = "s"

        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = 19

    return output.getvalue()


def main():
    st.set_page_config(
        page_title="출고 단가 관리",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">
                SHIPMENT PRICE MANAGEMENT
            </div>
            <div class="hero-title">
                출고 단가 관리
            </div>
            <div class="hero-description">
                출고 내역과 기준단가를 한눈에 비교하고,<br>
                확인이 필요한 건부터 팀과 함께 처리하세요.
            </div>
            <div class="steps">
                <span>01 · 엑셀 등록</span>
                <span>02 · 단가 비교</span>
                <span>03 · 내역 확인</span>
                <span>04 · 처리 기록</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        db = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
        )
    except Exception:
        st.info(
            "서버 연결 설정이 필요합니다. "
            "Streamlit의 Secrets를 확인해 주세요."
        )
        st.stop()

    with st.expander(
        "새 자료 등록 · 단가현황과 출고현황 업로드",
        expanded=False,
    ):
        st.caption(
            "같은 파일을 다시 저장하면 별도의 검증 자료로 "
            "등록됩니다. 기존 확인 기록은 원래 자료에 유지됩니다."
        )

        today = datetime.now(
            ZoneInfo("Asia/Seoul")
        ).strftime("%Y-%m-%d")

        title = st.text_input(
            "등록 이름",
            value=f"{today} 단가 점검",
        )

        left, right = st.columns(2)

        price_file = left.file_uploader(
            "① 기준단가 파일 · 단가현황",
            type=["xls", "xlsx"],
        )

        shipment_file = right.file_uploader(
            "② 출고내역 파일 · 출고현황",
            type=["xls", "xlsx"],
        )

        tolerance = st.number_input(
            "허용 단가 차이(원)",
            min_value=0.0,
            value=0.01,
            step=0.01,
            format="%.4f",
            help=(
                "설정 금액을 초과하는 단가 차이를 "
                "확인 대상으로 표시합니다."
            ),
        )

        if st.button(
            "검증하고 팀에 공유",
            type="primary",
        ):
            if not price_file or not shipment_file:
                st.warning(
                    "단가현황과 출고현황을 모두 선택해 주세요."
                )

            elif not title.strip():
                st.warning("등록 이름을 입력해 주세요.")

            else:
                try:
                    with st.spinner(
                        "단가 비교 및 공유 저장 중입니다."
                    ):
                        result = validate(
                            read_excel(price_file),
                            read_excel(shipment_file),
                            tolerance,
                        )

                        payload = {
                            "title": title.strip(),
                            "shipment_filename": shipment_file.name,
                            "price_filename": price_file.name,
                            "results": json.loads(
                                result.to_json(
                                    orient="records",
                                    force_ascii=False,
                                    double_precision=15,
                                )
                            ),
                        }

                        response = (
                            db.table("inspection_batches")
                            .insert(payload)
                            .execute()
                        )

                        st.session_state["batch_id"] = (
                            response.data[0]["id"]
                        )

                    st.success(
                        "공유 저장이 완료됐습니다. "
                        "아래에서 결과를 확인하세요."
                    )

                except ValueError as exc:
                    st.error(str(exc))

                except Exception:
                    st.error(
                        "등록하지 못했습니다. "
                        "파일 형식과 서버 설정을 확인해 주세요."
                    )

    try:
        batches = (
            db.table("inspection_batches")
            .select("id,title,created_at")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
            .data
        )
    except Exception:
        st.error(
            "공유 자료를 불러오지 못했습니다. "
            "서버 연결 상태를 확인해 주세요."
        )
        st.stop()

    if not batches:
        st.info(
            "등록된 자료가 없습니다. 위의 ‘새 자료 등록’을 "
            "열어 엑셀 두 개를 업로드해 주세요."
        )
        st.stop()

    batch_map = {
        item["id"]: item
        for item in batches
    }

    ids = list(batch_map)
    current = st.session_state.get("batch_id")

    with st.container(border=True):
        select_col, refresh_col = st.columns(
            [5, 1],
            vertical_alignment="bottom",
        )

        selected = select_col.selectbox(
            "공유 자료 선택 · 최근 200개",
            ids,
            index=(
                ids.index(current)
                if current in ids
                else 0
            ),
            format_func=lambda key: (
                f"{batch_map[key]['title']} · {key[:8]}"
            ),
        )

        if refresh_col.button(
            "자료 새로 고침",
            use_container_width=True,
        ):
            st.rerun()

        created = pd.to_datetime(
            batch_map[selected]["created_at"],
            utc=True,
        ).tz_convert("Asia/Seoul")

        st.caption(
            f"등록일시 {created:%Y.%m.%d %H:%M} · "
            "다른 직원이 저장한 최신 내용은 "
            "‘자료 새로 고침’으로 확인하세요."
        )

    try:
        batch = (
            db.table("inspection_batches")
            .select("results")
            .eq("id", selected)
            .single()
            .execute()
            .data
        )

        reviews = []
        offset = 0

        while True:
            page = (
                db.table("inspection_reviews")
                .select("*")
                .eq("batch_id", selected)
                .order("row_key")
                .range(offset, offset + 999)
                .execute()
                .data
            )

            reviews.extend(page)

            if len(page) < 1000:
                break

            offset += 1000

    except Exception:
        st.error(
            "상세 내역을 불러오지 못했습니다. "
            "잠시 후 새로 고침해 주세요."
        )
        st.stop()

    data = pd.DataFrame(batch["results"])

    if data.empty:
        st.info("선택한 자료에 출고 상세가 없습니다.")
        st.stop()

    for col in [
        "단가", "기준단가", "출고수량",
        "단가차이", "차이금액", "차이규모",
    ]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce",
        )

    review_map = {
        row["row_key"]: row
        for row in reviews
    }

    for col, field, default in [
        ("확인결과", "status", "미확인"),
        ("확인사유", "reason", ""),
        ("담당자", "reviewer", ""),
    ]:
        data[col] = data["행키"].map(
            lambda key, f=field, d=default: (
                review_map.get(key, {}).get(f, d)
            )
        )

    month = st.selectbox(
        "출고월",
        ["전체"]
        + sorted(
            data["출고월"].dropna().unique().tolist()
        ),
        key=f"month_{selected}",
    )

    monthly = (
        data
        if month == "전체"
        else data[data["출고월"].eq(month)]
    )

    diff = monthly[
        monthly["판정"].eq("단가차이 확인")
    ]

    section(
        "01",
        "단가 점검 요약",
        "선택한 출고월의 현황입니다. "
        "단가 차이가 있는 출고부터 확인하세요.",
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "전체 출고",
        f"{len(monthly):,}건",
        help="소계와 합계행을 제외한 출고 상세행 수입니다.",
    )

    b.metric(
        "단가 차이 · 확인 필요",
        f"{len(diff):,}건",
        help=(
            "허용 범위를 초과해 최신 기준단가와 "
            "차이가 나는 출고입니다."
        ),
    )

    missing_count = (
        monthly["판정"]
        .eq("기준단가 확인")
        .sum()
    )

    c.metric(
        "기준단가 · 확인 필요",
        f"{missing_count:,}건",
    )

    d.metric(
        "차이규모",
        f"{diff['차이규모'].sum():,.1f}원",
        help=(
            "단가 차이 확인 건의 차액 절댓값 합계입니다. "
            "확정 손실액은 아닙니다."
        ),
    )

    st.caption(
        "비교 기준: 거래처 코드 + 품번 · "
        "사용 중인 최신 판매단가와 비교합니다. "
        "단가 차이는 확인 대상이며 실제 오류 여부는 "
        "계약 조건과 적용기간을 확인해 판단하세요."
    )

    section(
        "02",
        "확인 우선순위",
        "판정별 현황을 살펴보고, "
        "차이규모가 큰 거래처부터 검토하세요.",
    )

    left, right = st.columns(
        [1, 1.15],
        gap="large",
    )

    with left:
        with st.container(border=True):
            st.subheader("판정별 출고 건수")
            st.caption(
                "파란색은 확인 대상 · 회색은 일치한 출고"
            )
            draw_judgments(monthly)

    with right:
        with st.container(border=True):
            st.subheader("거래처별 차이규모")
            st.caption(
                "단가 차이가 있는 거래처 · "
                "금액이 큰 순서 · 최대 15개"
            )

            if (
                "거래처명" in diff.columns
                and not diff.empty
            ):
                group_cols = [
                    col
                    for col in ["코드", "거래처명"]
                    if col in diff.columns
                ]

                ranking = (
                    diff.groupby(
                        group_cols,
                        dropna=False,
                    )
                    .agg(
                        확인건수=("차이규모", "size"),
                        차이규모=("차이규모", "sum"),
                    )
                    .sort_values(
                        "차이규모",
                        ascending=False,
                    )
                    .head(15)
                    .reset_index()
                )

                ranking.insert(
                    0,
                    "순위",
                    range(1, len(ranking) + 1),
                )

                ranking = ranking.rename(
                    columns={
                        "확인건수": "확인 건수",
                        "차이규모": "차이규모(원)",
                    }
                )

                st.dataframe(
                    ranking.style.format({
                        "확인 건수": "{:,.0f}",
                        "차이규모(원)": "{:,.1f}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                    height=300,
                )

            else:
                st.success(
                    "선택한 출고월에는 단가 차이가 없습니다."
                )

    section(
        "03",
        "출고 상세 내역",
        "판정·확인결과·검색어로 대상을 좁혀보세요. "
        "현재 조회 결과는 엑셀로 내려받을 수 있습니다.",
    )

    with st.container(border=True):
        p, r = st.columns(2)

        judgments = p.multiselect(
            "자동 판정 · 비워두면 전체",
            JUDGMENTS,
            default=(
                ["단가차이 확인"]
                if "단가차이 확인" in monthly["판정"].values
                else []
            ),
            key=f"judgment_{selected}",
        )

        review_filters = r.multiselect(
            "확인결과 · 비워두면 전체",
            ["미확인"] + STATUSES,
            key=f"review_filter_{selected}",
        )

        search = st.text_input(
            "거래처명 · 코드 · 품번 · 품명 · 출고번호 검색",
            placeholder="검색어를 입력하세요",
            key=f"search_{selected}",
        )

        view = monthly.copy()

        if judgments:
            view = view[
                view["판정"].isin(judgments)
            ]

        if review_filters:
            view = view[
                view["확인결과"].isin(review_filters)
            ]

        if search:
            matches = pd.Series(
                False,
                index=view.index,
            )

            for col in [
                "거래처명", "코드", "품번",
                "품명", "출고번호",
            ]:
                if col in view.columns:
                    matches |= (
                        view[col]
                        .astype(str)
                        .str.contains(
                            search,
                            case=False,
                            regex=False,
                            na=False,
                        )
                    )

            view = view[matches]

        view = view.sort_values(
            "차이규모",
            ascending=False,
            na_position="last",
        )

        preferred = [
            "출고일자",
            "출고번호",
            "순번",
            "코드",
            "거래처명",
            "품번",
            "품명",
            "규격",
            "출고수량",
            "단가",
            "기준단가",
            "단가차이",
            "차이금액",
            "차이규모",
            "판정",
            "기준정보주의",
            "확인결과",
            "확인사유",
            "담당자",
        ]

        visible = [
            col
            for col in preferred
            if col in view.columns
        ]

        st.caption(
            f"현재 조회 {len(view):,}건 · "
            "금액은 소수 둘째 자리까지 표시하며 "
            "원래 계산값은 유지합니다."
        )

        st.dataframe(
            format_table(view[visible]),
            use_container_width=True,
            hide_index=True,
            height=440,
            column_config={
                "거래처명": st.column_config.TextColumn(
                    "거래처명",
                    width="medium",
                ),
                "품명": st.column_config.TextColumn(
                    "품명",
                    width="medium",
                ),
                "판정": st.column_config.TextColumn(
                    "자동 판정",
                    width="medium",
                ),
                "기준정보주의": st.column_config.TextColumn(
                    "기준정보 확인사항",
                    width="large",
                ),
                "확인사유": st.column_config.TextColumn(
                    "확인사유",
                    width="large",
                ),
            },
        )

        export_date = datetime.now(
            ZoneInfo("Asia/Seoul")
        ).strftime("%Y%m%d")

        st.download_button(
            "조회 결과 엑셀 다운로드",
            export_excel(view),
            file_name=(
                f"출고단가_점검결과_{export_date}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    section(
        "04",
        "확인 결과 기록",
        "출고를 선택하고 확인결과·사유·담당자를 남기세요. "
        "저장한 기록은 팀원에게 공유됩니다.",
    )

    st.caption(
        "담당자는 직접 입력합니다. "
        "같은 출고를 여러 사람이 수정하면 "
        "마지막으로 저장한 내용이 반영됩니다."
    )

    if view.empty:
        st.info(
            "현재 조건에 해당하는 출고가 없습니다. "
            "위의 검색 조건을 변경해 주세요."
        )

    else:
        row_map = {
            row["행키"]: row
            for row in view.to_dict("records")
        }

        def row_label(key):
            row = row_map[key]

            return (
                f"{row.get('거래처명', '')} · "
                f"{row.get('품명', '')} · "
                f"{row.get('출고번호', '')} / "
                f"{row.get('순번', '')} · "
                f"{row.get('품번', '')}"
            )

        row_key = st.selectbox(
            "기록할 출고",
            list(row_map),
            format_func=row_label,
            key=f"row_{selected}",
        )

        row = row_map[row_key]

        with st.container(border=True):
            x, y, z = st.columns(3)

            x.metric(
                "출고단가",
                (
                    "—"
                    if pd.isna(row.get("단가"))
                    else f"{row['단가']:,.2f}원"
                ),
            )

            y.metric(
                "기준단가",
                (
                    "—"
                    if pd.isna(row.get("기준단가"))
                    else f"{row['기준단가']:,.2f}원"
                ),
            )

            z.metric(
                "단가 차이",
                (
                    "—"
                    if pd.isna(row.get("단가차이"))
                    else f"{row['단가차이']:+,.2f}원"
                ),
            )

            if row.get("기준정보주의"):
                st.warning(
                    "기준정보 확인사항: "
                    f"{row['기준정보주의']}"
                )

        saved = review_map.get(row_key, {})

        with st.form(
            f"review_{selected}_{row_key}"
        ):
            l, r = st.columns(2)

            status = l.selectbox(
                "확인결과",
                STATUSES,
                index=STATUSES.index(
                    saved.get("status", "확인 중")
                ),
            )

            reviewer = r.text_input(
                "담당자",
                value=saved.get("reviewer", ""),
                max_chars=100,
                placeholder="이름 입력",
            )

            reason = st.text_area(
                "확인사유",
                value=saved.get("reason", ""),
                max_chars=2000,
                placeholder=(
                    "예: 별도 계약단가 적용 확인 / "
                    "출고단가 수정 요청"
                ),
                height=110,
            )

            if st.form_submit_button(
                "확인 기록 저장 · 팀에 공유",
                type="primary",
            ):
                try:
                    (
                        db.table("inspection_reviews")
                        .upsert(
                            {
                                "batch_id": selected,
                                "row_key": row_key,
                                "status": status,
                                "reason": reason,
                                "reviewer": reviewer,
                            },
                            on_conflict="batch_id,row_key",
                        )
                        .execute()
                    )

                    st.session_state["review_saved"] = True
                    st.rerun()

                except Exception:
                    st.error(
                        "확인 기록을 저장하지 못했습니다. "
                        "잠시 후 다시 시도해 주세요."
                    )

        if st.session_state.pop(
            "review_saved",
            False,
        ):
            st.success(
                "확인 기록을 저장했습니다. "
                "조회표에도 반영됐습니다."
            )

    st.markdown(
        """
        <div class="footer">
            출고 단가 관리 · 팀 공유 대시보드<br>
            검증 결과는 등록 당시 기준단가를 기준으로 보관됩니다.
            최신 기준으로 다시 비교하려면 두 파일을 새로 등록하세요.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
