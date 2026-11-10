"""출고 단가 점검 — 전체 교체용 app.py"""

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
    background: rgba(243,245,249,.96);
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
    letter-spacing: -.04em;
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
    background: linear-gradient(115deg,#152840,#24496D);
    border-radius: 20px;
    padding: 30px 36px;
    margin-bottom: 24px;
    box-shadow: 0 12px 30px #15284012;
}

.eyebrow {
    color: #A9C7E5;
    font-size: 11px;
    letter-spacing: .19em;
    font-weight: 700;
}

.hero-title {
    color: white;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -.05em;
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
    margin: 26px 0 16px;
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
    letter-spacing: -.04em;
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
    font-size: clamp(24px,2.5vw,34px);
    font-weight: 700;
    color: #172B46;
    letter-spacing: -.05em;
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

[data-baseweb="tab-list"] {
    gap: 8px;
    margin-top: 22px;
    border-bottom: 1px solid #DCE4EF;
    padding-bottom: 10px;
    flex-wrap: wrap;
}

[data-baseweb="tab"] {
    height: auto;
    min-height: 52px;
    padding: 14px 20px;
    border-radius: 10px;
    background: #E9EEF6;
    color: #54667E;
    font-weight: 650;
    white-space: normal;
}

[data-baseweb="tab"][aria-selected="true"] {
    background: #245BD7;
    color: white;
}

[data-baseweb="tab-highlight"] {
    display: none;
}

.footer {
    border-top: 1px solid #DDE5EF;
    margin-top: 36px;
    padding-top: 18px;
    font-size: 12px;
    color: #8190A4;
    line-height: 1.8;
}

@media (max-width:640px) {
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

    [data-baseweb="tab"] {
        padding: 12px;
        font-size: 12px;
    }
}

.price-card-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px 24px;padding:10px 4px 8px}
.price-field {display:flex;flex-direction:column;gap:7px;min-width:0}
.price-label {font-size:11px;color:#7b889c;font-weight:500;letter-spacing:.01em}
.price-value {font-size:15px;color:#172b46;font-weight:650;line-height:1.5;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.price-emphasis {color:#bf571c;font-weight:750}
@media(min-width:1400px){.price-card-grid{grid-template-columns:1fr 1.8fr 1fr 1.5fr}.price-field:nth-child(n+5){padding-top:10px;border-top:1px solid #edf1f6}}
@media(max-width:700px){.price-card-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.price-value{font-size:14px}}

</style>
"""


def section(number, title, description):
    # 고정된 화면 문구에만 사용합니다.
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

    # 기존 버전의 상세행 키 생성 방식을 유지합니다.
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

    result["단가차이"] = result["단가"] - result["기준단가"]
    result["출고월"] = (
        result["출고일자"].str[:4]
        + "-"
        + result["출고일자"].str[4:6]
    )

    def judge(row):
        if pd.isna(row["출고수량"]) or pd.isna(row["단가"]):
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

        for row in sheet:
            for cell in row:
                if cell.data_type == "f":
                    cell.data_type = "s"

        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = 19

    return output.getvalue()


def render_upload(db):
    with st.expander(
        "＋ 새 자료 등록하기 · 처음 이용하거나 새 엑셀을 받았을 때",
        expanded=False,
    ):
        st.info(
            "① 단가현황 선택 → ② 출고현황 선택 → "
            "③ 등록 이름 확인 → ‘검증하고 공유 저장’ 클릭"
        )

        today = datetime.now(
            ZoneInfo("Asia/Seoul")
        ).strftime("%Y-%m-%d")

        title = st.text_input(
            "등록 이름",
            value=f"{today} 단가 점검",
            help="예: 2026년 11월 마감 · 11월 10일 기준",
        )

        p, s = st.columns(2)

        price_file = p.file_uploader(
            "① 단가현황 · 기준이 되는 판매단가",
            type=["xls", "xlsx"],
        )

        shipment_file = s.file_uploader(
            "② 출고현황 · 실제 출고된 내역",
            type=["xls", "xlsx"],
        )

        tolerance = st.number_input(
            "허용할 단가 차이(원)",
            min_value=0.0,
            value=0.01,
            step=0.01,
            format="%.4f",
            help=(
                "이 금액을 초과하는 단가 차이를 "
                "확인 대상으로 분류합니다."
            ),
        )

        st.caption(
            "기존 자료는 삭제되지 않습니다. "
            "같은 파일을 다시 저장해도 별도 자료로 등록됩니다."
        )

        if st.button(
            "③ 검증하고 공유 저장",
            type="primary",
        ):
            if not price_file or not shipment_file:
                st.warning(
                    "두 엑셀 파일을 모두 선택해 주세요."
                )

            elif not title.strip():
                st.warning("등록 이름을 입력해 주세요.")

            else:
                try:
                    with st.spinner(
                        "단가를 비교하고 저장하고 있습니다."
                    ):
                        result = validate(
                            read_excel(price_file),
                            read_excel(shipment_file),
                            tolerance,
                        )

                        response = (
                            db.table("inspection_batches")
                            .insert({
                                "title": title.strip(),
                                "shipment_filename": (
                                    shipment_file.name
                                ),
                                "price_filename": price_file.name,
                                "results": json.loads(
                                    result.to_json(
                                        orient="records",
                                        force_ascii=False,
                                        double_precision=15,
                                    )
                                ),
                            })
                            .execute()
                        )

                        st.session_state["batch_id"] = (
                            response.data[0]["id"]
                        )

                    st.success(
                        "등록 완료 · 아래 ‘검토할 자료’에서 "
                        "결과를 확인하세요."
                    )

                except ValueError as exc:
                    st.error(str(exc))

                except Exception:
                    st.error(
                        "등록하지 못했습니다. "
                        "파일 형식과 서버 연결을 확인해 주세요."
                    )


def build_price_cards(diff):
    """기준단가·출고단가가 다른 내역은 같은 품목이어도 분리합니다."""
    if diff.empty:
        return pd.DataFrame()
    frame = diff.copy()
    group_cols = ["코드", "거래처명", "품번", "품명", "기준단가", "단가"]
    for col in ["코드", "거래처명", "품번", "품명"]:
        if col not in frame.columns:
            frame[col] = ""
        frame[col] = frame[col].fillna("").astype(str)
    cards = (
        frame.groupby(group_cols, dropna=False)
        .agg(차이규모=("차이규모", "sum"), 출고건수=("행키", "size"))
        .reset_index()
        .sort_values("차이규모", ascending=False)
        .reset_index(drop=True)
    )

    def note_key(row):
        values = [str(row[col]) for col in group_cols[:4]]
        values += [format(float(row[col]), ".15g") for col in group_cols[4:]]
        identity = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        return "price-note:v1:" + hashlib.sha256(identity.encode()).hexdigest()

    cards["비고키"] = cards.apply(note_key, axis=1)
    return cards


def render_price_cards(diff, db, selected, review_map, month):
    from html import escape
    import math

    st.subheader("거래처·품목별 단가 확인")
    st.caption(
        "거래처와 품목별로 기준단가·실제 출고단가를 비교하세요. "
        "오른쪽 비고에 바로 입력한 뒤 ‘비고 저장’을 누르면 팀원과 공유됩니다."
    )
    if st.session_state.pop("price_note_saved", False):
        st.success("비고를 저장했습니다. 다른 직원은 ‘최신 내용 불러오기’로 확인할 수 있습니다.")
    cards = build_price_cards(diff)
    if cards.empty:
        st.success("선택한 출고월에는 단가 차이가 있는 출고가 없습니다.")
        return
    find_col, size_col = st.columns([4, 1])
    search = find_col.text_input(
        "거래처·품목 검색",
        placeholder="거래처코드, 거래처명, 품목코드, 품목명 입력",
        key=f"card_search_{selected}",
    )
    page_size = size_col.selectbox(
        "한 번에 보기", [10, 20, 50], key=f"card_size_{selected}"
    )
    if search.strip():
        mask = pd.Series(False, index=cards.index)
        for col in ["코드", "거래처명", "품번", "품명"]:
            mask |= cards[col].str.contains(search.strip(), case=False, regex=False, na=False)
        cards = cards[mask].reset_index(drop=True)
    st.caption(
        f"조회 {len(cards):,}개 항목 · 같은 품목이라도 출고단가가 다르면 별도로 표시합니다. "
        "비고는 현재 등록 자료의 거래처·품목·기준단가·출고단가 조합별로 저장됩니다."
    )
    if cards.empty:
        st.info("검색 결과가 없습니다. 검색어를 변경해 주세요.")
        return
    page_count = math.ceil(len(cards) / page_size)
    page_options = list(range(1, page_count + 1))
    page = st.selectbox(
        "페이지", page_options,
        format_func=lambda value: f"{value} / {page_count} 페이지",
        key=f"card_page_{selected}_{month}_{page_size}_{hashlib.sha256(search.encode()).hexdigest()[:10]}",
    )
    visible = cards.iloc[(page - 1) * page_size:page * page_size]
    page_snapshot = [(key, review_map.get(key, {}).get("reason", ""), review_map.get(key, {}).get("updated_at", "")) for key in visible["비고키"]]
    page_identity = hashlib.sha256(json.dumps(page_snapshot, ensure_ascii=False).encode()).hexdigest()[:16]
    st.caption("입력 후 저장하지 않고 페이지·검색·월을 바꾸면 입력 내용이 사라질 수 있습니다. 먼저 비고를 저장하세요.")
    with st.form(f"price_notes_{selected}_{page_identity}"):
        edits = []
        for row in visible.to_dict("records"):
            key = row["비고키"]
            saved = review_map.get(key, {})
            with st.container(border=True):
                details, note = st.columns([2.8, 1.2], gap="medium")
                fields = [
                    ("거래처코드", row["코드"]),
                    ("거래처명", row["거래처명"]),
                    ("품목코드", row["품번"]),
                    ("품목명", row["품명"]),
                    ("기준단가", f"{row['기준단가']:,.2f}원"),
                    ("출고단가", f"{row['단가']:,.2f}원"),
                    ("차이규모", f"{row['차이규모']:,.1f}원"),
                ]
                fields_html = "".join(
                    '<div class="price-field"><span class="price-label">'
                    + escape(label)
                    + '</span><span class="price-value '
                    + ("price-emphasis" if label == "차이규모" else "")
                    + '">'
                    + escape(str(value))
                    + '</span></div>'
                    for label, value in fields
                )
                with details:
                    st.markdown(
                        '<div class="price-card-grid">' + fields_html + '</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"출고 상세 {row['출고건수']:,}건 합산")
                with note:
                    text = st.text_area(
                        "비고", value=saved.get("reason", ""),
                        placeholder="이 품목의 확인 내용이나 요청사항 입력",
                        height=100, max_chars=2000,
                        key=f"price_note_{selected}_{key}_{page_identity}",
                    )
                    if text != saved.get("reason", ""):
                        edits.append({
                            "batch_id": selected,
                            "row_key": key,
                            "status": "확인 중",
                            "reason": text,
                            "reviewer": "",
                        })
        submitted = st.form_submit_button(
            "입력한 비고 저장 · 팀과 공유", type="primary", use_container_width=True
        )
    if submitted:
        if not edits:
            st.info("변경된 비고가 없습니다.")
        else:
            try:
                db.table("inspection_reviews").upsert(
                    edits, on_conflict="batch_id,row_key"
                ).execute()
                st.session_state["price_note_saved"] = True
                st.rerun()
            except Exception:
                st.error("비고를 저장하지 못했습니다. 입력 내용은 유지되니 잠시 후 다시 저장해 주세요.")
    st.caption("카드별 비고는 출고별 확인결과·사유와 별도입니다. 같은 비고를 동시에 수정하면 마지막 저장 내용이 반영됩니다.")


def main():
    st.set_page_config(
        page_title="출고 단가 점검",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">
                MONTH-END PRICE REVIEW
            </div>
            <div class="hero-title">
                출고 단가 점검
            </div>
            <div class="hero-description">
                어떤 출고를 확인해야 하는지 찾고,
                확인한 결과를 팀과 공유하는 공간입니다.
            </div>
            <div class="steps">
                <span>01 자료 선택</span>
                <span>02 현황 확인</span>
                <span>03 출고 찾기</span>
                <span>04 결과 저장</span>
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
        st.error(
            "서버 연결 설정이 필요합니다. "
            "Streamlit Secrets를 확인해 주세요."
        )
        st.stop()

    section(
        "01",
        "먼저, 검토할 자료를 선택하세요",
        "이미 등록된 자료는 바로 선택하세요. "
        "새 파일을 받은 경우에만 ‘새 자료 등록하기’를 여세요.",
    )

    render_upload(db)

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
            "잠시 후 새로 고침해 주세요."
        )
        st.stop()

    if not batches:
        st.info(
            "아직 자료가 없습니다. "
            "위의 ‘새 자료 등록하기’를 열어 "
            "엑셀 두 개를 등록하세요."
        )
        st.stop()

    batch_map = {
        item["id"]: item
        for item in batches
    }

    ids = list(batch_map)
    current = st.session_state.get("batch_id")

    with st.container(border=True):
        a, b = st.columns(
            [5, 1],
            vertical_alignment="bottom",
        )

        selected = a.selectbox(
            "검토할 자료",
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

        if b.button(
            "최신 내용 불러오기",
            use_container_width=True,
        ):
            st.rerun()

        created = pd.to_datetime(
            batch_map[selected]["created_at"],
            utc=True,
        ).tz_convert("Asia/Seoul")

        st.caption(
            f"등록 {created:%Y.%m.%d %H:%M} · "
            "다른 직원이 저장한 기록은 "
            "‘최신 내용 불러오기’로 반영됩니다."
        )

    try:
        batch = (
            db.table("inspection_batches")
            .select(
                "results,shipment_filename,price_filename"
            )
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
            "잠시 후 다시 시도해 주세요."
        )
        st.stop()

    data = pd.DataFrame(batch["results"])

    if data.empty:
        st.info("출고 상세가 없는 자료입니다.")
        st.stop()

    for col in [
        "단가", "기준단가", "출고수량",
        "단가차이", "차이금액", "차이규모",
    ]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce",
        )

    if "기준정보주의" not in data.columns:
        data["기준정보주의"] = ""

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
        "확인할 출고월 · 아래 모든 화면에 적용",
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

    st.caption(
        f"출고 파일: {batch['shipment_filename']} / "
        f"기준단가 파일: {batch['price_filename']}"
    )

    # 자동 판정과 추가 기준정보 주의사항을 함께 반영합니다.
    attention = monthly[
        monthly["판정"].ne("일치")
        | monthly["기준정보주의"].fillna("").ne("")
    ].copy()

    pending = attention[
        attention["확인결과"].isin(
            ["미확인", "확인 중"]
        )
    ]

    tabs = st.tabs([
        "② 전체 현황 · 무엇이 문제인가요?",
        "③ 출고 찾기 · 어떤 건을 볼까요?",
        "④ 결과 기록 · 확인 후 저장하세요",
    ])

    with tabs[0]:
        section(
            "02",
            "무엇부터 확인하면 될까요?",
            "단가 차이와 기준단가 누락을 먼저 확인하고, "
            "조정·반품과 기준정보 주의사항을 따로 검토하세요.",
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "전체 출고",
            f"{len(monthly):,}건",
            help="소계·합계를 제외한 출고 상세행 수입니다.",
        )

        b.metric(
            "단가가 다른 출고",
            f"{len(diff):,}건",
            help=(
                "최신 기준단가와 허용 범위를 초과해 "
                "차이가 나는 출고입니다."
            ),
        )

        missing_count = (
            monthly["판정"]
            .eq("기준단가 확인")
            .sum()
        )

        c.metric(
            "기준단가를 못 찾은 출고",
            f"{missing_count:,}건",
        )

        d.metric(
            "확인 전·확인 중",
            f"{len(pending):,}건",
            help=(
                "자동 판정이 일치가 아니거나 "
                "기준정보 주의사항이 있는 출고 중 "
                "미확인·확인 중인 건입니다."
            ),
        )

        if len(pending):
            st.info(
                "다음 할 일: ‘③ 출고 찾기’에서 "
                f"{len(pending):,}건을 검토한 뒤, "
                "‘④ 결과 기록’에서 확인결과를 저장하세요."
            )
        else:
            st.success(
                "현재 자료의 확인 대상에 "
                "미확인·확인 중인 건이 없습니다. "
                "필요한 내역은 ‘③ 출고 찾기’에서 조회하세요."
            )

        done = len(attention) - len(pending)

        st.progress(
            (
                done / len(attention)
                if len(attention)
                else 1.0
            ),
            text=(
                f"확인 기록 진행 · 확인 대상 "
                f"{len(attention):,}건 중 "
                f"결과 등록 {done:,}건"
            ),
        )

        st.caption(
            "‘정상·수정 필요·기준정보 수정 필요’로 기록하면 "
            "결과 등록으로 집계합니다. "
            "수정 완료를 의미하지는 않습니다."
        )

        render_price_cards(diff, db, selected, review_map, month)

        st.caption(
            "단가 차이규모 합계 "
            f"{diff['차이규모'].sum():,.1f}원 · "
            "최신 기준단가 대비 차액의 절댓값 합계이며 확정 손실액은 아닙니다."
        )

    with tabs[1]:
        section(
            "03",
            "확인할 출고를 찾으세요",
            "조회 범위를 고르고 거래처나 품번을 검색하세요. "
            "표에서 내역을 확인한 뒤 ‘④ 결과 기록’으로 이동하세요.",
        )

        with st.container(border=True):
            scope = st.radio(
                "① 어떤 내역을 볼까요?",
                [
                    "확인이 필요한 전체",
                    "단가 차이만",
                    "기준단가 없는 건",
                    "전체 출고",
                ],
                horizontal=True,
                key=f"scope_{selected}",
            )

            a, b = st.columns(2)

            status_filters = a.multiselect(
                "② 처리 상태 · 비워두면 전체",
                ["미확인"] + STATUSES,
                key=f"status_{selected}",
            )

            search = b.text_input(
                "③ 거래처·품번·품명·출고번호 검색",
                placeholder="예: 거래처명 또는 002005",
                key=f"search_{selected}",
            )

        if scope == "단가 차이만":
            view = diff.copy()

        elif scope == "기준단가 없는 건":
            view = monthly[
                monthly["판정"].eq("기준단가 확인")
            ].copy()

        elif scope == "전체 출고":
            view = monthly.copy()

        else:
            view = attention.copy()

        if status_filters:
            view = view[
                view["확인결과"].isin(status_filters)
            ]

        if search:
            mask = pd.Series(
                False,
                index=view.index,
            )

            for col in [
                "코드", "거래처명", "품번",
                "품명", "출고번호",
            ]:
                if col in view.columns:
                    mask |= (
                        view[col]
                        .astype(str)
                        .str.contains(
                            search,
                            case=False,
                            regex=False,
                            na=False,
                        )
                    )

            view = view[mask]

        view = view.sort_values(
            "차이규모",
            ascending=False,
            na_position="last",
        )

        st.subheader(
            f"조회 결과 · {len(view):,}건"
        )

        st.caption(
            "표는 좌우로 이동할 수 있습니다. "
            "단가 차이의 양수(+)는 기준보다 높게, "
            "음수(-)는 낮게 출고됐다는 뜻입니다."
        )

        cols = [
            "확인결과",
            "판정",
            "거래처명",
            "품명",
            "규격",
            "품번",
            "출고일자",
            "출고번호",
            "순번",
            "출고수량",
            "단가",
            "기준단가",
            "단가차이",
            "차이금액",
            "차이규모",
            "기준정보주의",
            "확인사유",
            "담당자",
            "코드",
        ]

        cols = [
            col
            for col in cols
            if col in view.columns
        ]

        st.dataframe(
            format_table(view[cols]),
            use_container_width=True,
            hide_index=True,
            height=440,
            column_config={
                "판정": st.column_config.TextColumn(
                    "자동 판정",
                    width="medium",
                ),
                "거래처명": st.column_config.TextColumn(
                    "거래처명",
                    width="medium",
                ),
                "품명": st.column_config.TextColumn(
                    "품명",
                    width="medium",
                ),
                "기준정보주의": st.column_config.TextColumn(
                    "기준정보 주의사항",
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
            "조회한 내역 엑셀로 내려받기",
            export_excel(view),
            file_name=(
                f"출고단가_점검결과_{export_date}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

        st.info(
            "다음 할 일: ‘④ 결과 기록’ 탭을 누르세요. "
            "지금 조회한 출고 중에서 기록할 건을 "
            "선택할 수 있습니다."
        )

    with tabs[2]:
        section(
            "04",
            "확인한 내용을 저장하세요",
            "‘③ 출고 찾기’의 조회 결과와 연결됩니다. "
            "출고 선택 → 단가 확인 → 결과 입력 → 저장 "
            "순서로 진행하세요.",
        )

        if st.session_state.pop(
            "review_saved",
            False,
        ):
            st.success(
                "확인 기록을 저장했습니다. "
                "다른 직원도 ‘최신 내용 불러오기’를 "
                "누르면 확인할 수 있습니다."
            )

        if view.empty:
            st.info(
                "조회된 출고가 없습니다. "
                "‘③ 출고 찾기’에서 조회 범위를 변경해 주세요."
            )

        else:
            row_map = {
                row["행키"]: row
                for row in view.to_dict("records")
            }

            def row_label(key):
                row = row_map[key]

                return (
                    f"[{row.get('확인결과', '미확인')}] "
                    f"{row.get('거래처명', '')} · "
                    f"{row.get('품명', '')} · "
                    f"{row.get('출고번호', '')}/"
                    f"{row.get('순번', '')} · "
                    f"{row.get('품번', '')}"
                )

            row_key = st.selectbox(
                "① 기록할 출고를 선택하세요",
                list(row_map),
                format_func=row_label,
                key=f"row_{selected}",
            )

            row = row_map[row_key]

            with st.container(border=True):
                st.subheader(
                    "② 이 출고의 단가를 확인하세요"
                )

                st.write(
                    f"거래처: {row.get('거래처명', '')} / "
                    f"품명: {row.get('품명', '')} / "
                    f"품번: {row.get('품번', '')}"
                )

                st.caption(
                    f"출고일자 {row.get('출고일자', '')} · "
                    f"출고번호 {row.get('출고번호', '')} · "
                    f"자동 판정: {row.get('판정', '')}"
                )

                a, b, c = st.columns(3)

                for col, label, key in [
                    (a, "실제 출고단가", "단가"),
                    (b, "최신 기준단가", "기준단가"),
                    (c, "단가 차이", "단가차이"),
                ]:
                    value = row.get(key)

                    col.metric(
                        label,
                        (
                            "—"
                            if pd.isna(value)
                            else f"{value:,.2f}원"
                        ),
                    )

                if row.get("기준정보주의"):
                    st.warning(
                        "기준정보 주의: "
                        f"{row['기준정보주의']}"
                    )

                st.caption(
                    "최신 단가와 비교한 결과입니다. "
                    "계약별 예외와 적용기간을 확인한 후 "
                    "처리하세요."
                )

            saved = review_map.get(row_key, {})

            with st.form(
                f"review_{selected}_{row_key}"
            ):
                st.subheader(
                    "③ 확인결과와 사유를 입력하세요"
                )

                a, b = st.columns(2)

                status = a.selectbox(
                    "확인결과",
                    STATUSES,
                    index=STATUSES.index(
                        saved.get("status", "확인 중")
                    ),
                )

                reviewer = b.text_input(
                    "담당자",
                    value=saved.get("reviewer", ""),
                    max_chars=100,
                    placeholder="이름 입력",
                )

                reason = st.text_area(
                    "확인사유",
                    value=saved.get("reason", ""),
                    max_chars=2000,
                    height=115,
                    placeholder=(
                        "예: 별도 계약단가 적용 확인 / "
                        "출고단가 수정 요청"
                    ),
                )

                st.caption(
                    "정상: 계약 등 근거 확인 / "
                    "수정 필요: 출고단가 수정 대상 / "
                    "기준정보 수정 필요: 기준단가 등록 수정 대상"
                )

                if st.form_submit_button(
                    "④ 확인 기록 저장하고 팀에 공유",
                    type="primary",
                    use_container_width=True,
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

                        st.session_state[
                            "review_saved"
                        ] = True

                        st.rerun()

                    except Exception:
                        st.error(
                            "저장하지 못했습니다. "
                            "잠시 후 다시 시도해 주세요."
                        )

            st.caption(
                "같은 건을 여러 사람이 수정하면 "
                "마지막 저장 내용이 반영됩니다. "
                "확인결과를 저장해도 원본 엑셀이나 ERP 단가가 "
                "자동 변경되지는 않습니다."
            )

    st.markdown(
        """
        <div class="footer">
            출고 단가 점검 · 팀 공유 대시보드<br>
            검증 자료는 등록 당시 기준으로 보관됩니다.
            최신 단가로 다시 점검하려면 새 엑셀을 등록하세요.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
