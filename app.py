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
    padding: 12px 16px;
    min-height: 84px;
    box-shadow: 0 3px 12px #172B4605;
}

[data-testid="stMetricLabel"] {
    color: #718096;
    font-size: 12px;
}
[data-testid="stMetricLabel"] p {font-size:12px !important;}


[data-testid="stMetricValue"] {
    font-size: clamp(21px,1.8vw,26px);
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
        min-height: 76px;
        padding: 10px 12px;
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


.shipment-detail{background:#f8fafc;border:1px solid #e7edf5;border-radius:12px;padding:18px 20px;margin:8px 0 14px}
.shipment-detail-title{font-size:12px;font-weight:750;color:#245bd7;margin-bottom:14px}
.shipment-detail-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:18px 22px}
.shipment-original-note{font-size:12px;line-height:1.7;color:#66758a;margin-top:16px;padding-top:12px;border-top:1px solid #e4eaf3;white-space:pre-wrap;overflow-wrap:anywhere}
@media(max-width:900px){.shipment-detail-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:600px){.shipment-detail-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.shipment-detail{padding:16px}}

.section-description:empty {display:none;}

[data-testid="stColumn"] [data-testid="stForm"] {padding:0 !important;border:0 !important;background:transparent;}
.shipment-details-gap {height:14px;border-top:1px solid #edf1f6;margin-top:10px;}


.review-customer{display:flex;justify-content:space-between;align-items:center;padding:2px 2px 18px;border-bottom:1px solid #edf1f6;margin-bottom:10px}
.review-customer-code{display:inline-block;background:#eef3fb;color:#5c7291;font-size:11px;font-weight:600;padding:4px 8px;border-radius:6px;margin-right:10px}
.review-customer-name{font-size:15px;color:#20354f;font-weight:750}
.review-customer-count{font-size:11px;color:#8190a4;background:#f6f8fb;padding:4px 9px;border-radius:12px}
.review-grid{display:grid;grid-template-columns:minmax(160px,2.3fr) minmax(75px,1fr) repeat(4,minmax(65px,1fr));gap:16px;align-items:center}
.review-grid-head{color:#8492a5;font-size:11px;padding:8px 0 14px}
.review-grid-head span:nth-child(n+3){text-align:right}
.review-column-label{font-size:11px;color:#8492a5;padding:8px 0 14px}
.review-data-row{padding:16px 0 14px;border-bottom:1px solid #f0f3f8;min-width:0}
.review-product{display:flex;flex-direction:column;gap:4px;min-width:0}
.review-product strong{font-size:13px;color:#263c56;font-weight:650;overflow-wrap:anywhere}
.review-product-code{font-size:11px;color:#647e9d;letter-spacing:.02em}
.review-meta{font-size:10px;color:#96a2b2;line-height:1.7;overflow-wrap:anywhere}
.review-destination{font-size:12px;color:#64748b;overflow-wrap:anywhere}
.review-number{text-align:right;font-size:12px;color:#66768d;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.review-actual{color:#2b4566;font-weight:650}
.review-difference{color:#b8753b;font-weight:650}
.review-row-bottom{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
.review-badge{font-size:10px;font-weight:600;padding:4px 8px;border-radius:14px;line-height:1.4;background:#f0f3f7;color:#71829a}
.review-badge.difference{background:#fff2e7;color:#ae6a30}
.review-badge.reference{background:#f1edfa;color:#7b65a0}
.review-badge.adjustment{background:#ecf2fa;color:#607c9f}
.review-badge.matched{background:#edf7f1;color:#508367}
.review-basis{font-size:10px;color:#8b98aa}
.review-details{margin-top:8px;color:#8b98aa;font-size:10px}
.review-details summary{cursor:pointer;display:list-item;width:fit-content}
.review-detail-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;background:#f7f9fc;border-radius:10px;padding:16px;margin-top:10px}
.review-detail-fields div{display:flex;flex-direction:column;gap:5px}
.review-detail-fields span{font-size:10px;color:#8a97a8}
.review-detail-fields strong{font-size:12px;font-weight:500;color:#4e637e;overflow-wrap:anywhere;white-space:pre-wrap}
@media(max-width:1000px){.review-grid{grid-template-columns:minmax(130px,2fr) minmax(65px,1fr) repeat(4,minmax(50px,1fr));gap:8px}.review-number{font-size:11px}}
@media(max-width:640px){.review-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.review-grid-head{display:none}.review-product{grid-column:1 / -1}.review-number{text-align:left}.review-detail-fields{grid-template-columns:repeat(2,minmax(0,1fr))}}



[class*="st-key-review_card_confirmed_"] {background:#eaf4ee !important;border-color:#cadfd0 !important;border-radius:14px;}
[class*="st-key-review_card_confirmed_"] .review-customer {border-bottom-color:#d5e5d9;}
[class*="st-key-review_card_partial_"] [class*="st-key-review_row_confirmed_"] {background:#eaf4ee;border-radius:10px;}

[class*="st-key-review_row_"] [data-testid="stSelectbox"] {margin-top:16px;}
[class*="st-key-shipment_opinion_"] textarea {background:rgba(255,255,255,.85);border-radius:8px;font-size:12px;}

/* 옅은 색과 얇은 경계로 자료 설정과 화면 전환을 구분합니다. */
.st-key-source_upload_panel [data-testid="stExpander"]{border:1px solid #dbe3ef !important;border-radius:12px;box-shadow:none;}
.st-key-source_upload_panel summary{background:#f5f8fd !important;min-height:54px;padding:13px 18px !important;}
.st-key-source_upload_panel summary p,.st-key-source_upload_panel summary span,.st-key-source_upload_panel summary svg{color:#426286 !important;fill:currentColor;font-size:14px !important;font-weight:600 !important;}
.st-key-source_upload_panel summary:hover{background:#eef3fa !important;}
.st-key-source_selection_panel{background:#fff !important;border:1px solid #e0e6ef !important;border-radius:12px;padding:18px 20px !important;box-shadow:0 2px 10px #1b3a6603;}
.st-key-source_selection_panel [data-testid="stWidgetLabel"] p,.st-key-month_selection_panel [data-testid="stWidgetLabel"] p{color:#4c6079 !important;font-size:12px !important;font-weight:600 !important;}
.st-key-source_selection_panel [data-baseweb="select"]>div{background:#f8fafc !important;border:1px solid #dce4ee !important;border-radius:8px;min-height:44px;}
.st-key-source_selection_panel [data-baseweb="select"]>div:focus-within{border-color:#9cb1cf !important;box-shadow:0 0 0 2px #eaf0f8;}
.st-key-source_selection_panel [data-baseweb="select"] span{font-size:13px;color:#344c68;}
.st-key-source_selection_panel [data-testid="stCaptionContainer"]{color:#8997a9 !important;font-size:11px;}
.st-key-source_selection_panel button[kind="primary"]{background:#edf2fa !important;border:1px solid #dae3f1 !important;color:#426286 !important;min-height:44px;border-radius:8px;box-shadow:none;}
.st-key-source_selection_panel button[kind="primary"]:hover{background:#e3ebf7 !important;border-color:#c4d2e7 !important;}
.st-key-month_selection_panel{background:#fff !important;border:1px solid #e3e8f0 !important;border-radius:12px;padding:14px 20px !important;}
.st-key-month_selection_panel [data-baseweb="select"]>div{background:#f9fafc !important;border:1px solid #e1e6ef !important;border-radius:8px;}
[data-testid="stTabs"] [role="tablist"]{display:flex;gap:4px !important;background:#edf1f6 !important;padding:4px !important;border:1px solid #e3e8f0 !important;border-radius:11px !important;margin-top:20px !important;margin-bottom:14px !important;flex-wrap:wrap;}
[data-testid="stTabs"] [role="tab"]{flex:1 !important;min-height:44px !important;height:auto !important;padding:10px 18px !important;border:0 !important;border-radius:8px !important;background:transparent !important;color:#7b899d !important;justify-content:center !important;font-weight:600 !important;}
[data-testid="stTabs"] [role="tab"] p{font-size:13px !important;font-weight:600 !important;color:inherit !important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{background:#fff !important;color:#355a86 !important;box-shadow:0 1px 5px #203a5b0d !important;}
[data-testid="stTabs"] [role="tab"][aria-selected="false"]:hover{background:#f6f8fb !important;color:#4e6786 !important;}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],[data-testid="stTabs"] [data-baseweb="tab-border"]{display:none !important;}
@media(max-width:640px){.st-key-source_selection_panel{padding:14px 16px !important;}.st-key-month_selection_panel{padding:12px 16px !important;}[data-testid="stTabs"] [role="tab"]{padding:10px 8px !important;}[data-testid="stTabs"] [role="tab"] p{font-size:12px !important;}}
.review-owner{display:inline-block;margin-left:12px;font-size:11px;font-weight:500;color:#6a8099;}
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
    """통합단가: 납품처별 단가 우선, 없으면 거래처 공통단가 적용."""
    import math

    price = price.copy()
    shipment = shipment.copy()
    for frame in [price, shipment]:
        # 새 파일의 거래처코드를 내부 표준 이름으로 연결합니다.
        for source, target in [
            ("거래처코드", "코드"),
            ("품목코드", "품번"),
            ("품목명", "품명"),
        ]:
            if target not in frame.columns and source in frame.columns:
                frame.rename(columns={source: target}, inplace=True)
    requirements = [
        (price, ["코드", "품번", "판매단가"], "기준단가 파일"),
        (shipment, ["코드", "품번", "출고번호", "출고일자", "출고수량", "단가"], "출고현황"),
    ]
    for frame, required, label in requirements:
        missing = set(required) - set(frame.columns)
        if missing:
            display = ["거래처코드" if col == "코드" else col for col in sorted(missing)]
            raise ValueError(f"{label}에 필요한 열이 없습니다: {', '.join(display)}")
        for col in ["코드", "품번"]:
            frame[col] = frame[col].fillna("").astype(str).str.strip()
    # 새 통합파일에는 사용여부가 없어도 됩니다. 구형 파일도 계속 지원합니다.
    if "사용여부" in price.columns:
        price = price[price["사용여부"].fillna("").astype(str).str.strip().eq("1.사용")].copy()
    if "납품처명" not in price.columns:
        price["납품처명"] = ""
    price["납품처명"] = price["납품처명"].fillna("").astype(str).str.strip()
    if price.empty:
        raise ValueError("기준단가 파일에 사용할 단가가 없습니다.")
    invalid_key = price["코드"].eq("") | price["품번"].eq("")
    if invalid_key.any():
        raise ValueError("기준단가 파일에 거래처코드 또는 품번이 빈 행이 있습니다. 빈 행을 정리해 주세요.")
    price["기준단가"] = number(price["판매단가"])
    valid_price = price["기준단가"].map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    if not valid_price.all():
        raise ValueError(f"판매단가가 숫자가 아니거나 비어 있는 행이 {int((~valid_price).sum()):,}건 있습니다.")
    keys = ["코드", "납품처명", "품번"]
    duplicates = price.duplicated(keys, keep=False)
    if duplicates.any():
        raise ValueError(
            f"거래처코드·납품처명·품번이 같은 기준단가가 {int(duplicates.sum()):,}행 중복됩니다. "
            "납품처가 다른 행은 중복이 아니며, 같은 조합의 중복만 정리해 주세요."
        )
    shipment = shipment[
        shipment["출고번호"].fillna("").astype(str).str.strip().ne("")
        & shipment["품번"].ne("")
    ].copy()
    if shipment.empty:
        raise ValueError("출고 상세 데이터가 없습니다.")
    if "납품처명" not in shipment.columns:
        shipment["납품처명"] = ""
    shipment["납품처명"] = shipment["납품처명"].fillna("").astype(str).str.strip()
    # 기존 출고별 확인 기록의 식별 방식을 유지합니다.
    shipment["행키"] = [
        hashlib.sha256(f"{i}|{row['출고번호']}|{row['품번']}".encode()).hexdigest()
        for i, row in shipment.iterrows()
    ]
    specific = price[price["납품처명"].ne("")][keys + ["기준단가"]].rename(
        columns={"기준단가": "_납품처단가"}
    )
    common = price[price["납품처명"].eq("")][["코드", "품번", "기준단가"]].rename(
        columns={"기준단가": "_공통단가"}
    )
    result = shipment.merge(specific, on=keys, how="left", validate="many_to_one", sort=False)
    result = result.merge(common, on=["코드", "품번"], how="left", validate="many_to_one", sort=False)
    result["기준단가"] = result["_납품처단가"].combine_first(result["_공통단가"])
    result["기준구분"] = "기준단가 없음"
    result.loc[result["_공통단가"].notna(), "기준구분"] = "거래처 공통단가"
    result.loc[result["_납품처단가"].notna(), "기준구분"] = "납품처별 단가"
    result.drop(columns=["_납품처단가", "_공통단가"], inplace=True)
    for col in ["출고수량", "단가"]:
        result[col] = number(result[col])
    result["단가차이"] = result["단가"] - result["기준단가"]
    result["출고월"] = result["출고일자"].astype(str).str[:4] + "-" + result["출고일자"].astype(str).str[4:6]

    def judge(row):
        if pd.isna(row["출고수량"]) or pd.isna(row["단가"]):
            return "데이터 확인"
        if row["출고수량"] <= 0:
            return "조정·반품 확인"
        if pd.isna(row["기준단가"]):
            return "기준단가 확인"
        return "단가차이 확인" if abs(row["단가차이"]) > tolerance else "일치"

    result["판정"] = result.apply(judge, axis=1)
    result["차이금액"] = (result["단가차이"] * result["출고수량"]).where(
        result["판정"].isin(["일치", "단가차이 확인"])
    )
    result["차이규모"] = result["차이금액"].abs()
    result["기준정보주의"] = result["기준단가"].map(
        lambda value: "기준단가 1원 이하" if pd.notna(value) and value <= 1 else ""
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
        columns=["행키", "_자료지문"],
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


def load_customer_owners(db):
    mapping, offset = {}, 0
    while True:
        rows = (
            db.table("inspection_reviews").select("row_key,reason,updated_at")
            .like("row_key", "owner:v1:%")
            .order("updated_at", desc=True).range(offset, offset + 999)
            .execute().data
        )
        for row in rows:
            code = row["row_key"].removeprefix("owner:v1:")
            if code not in mapping:
                mapping[code] = row.get("reason") or "미지정"
        if len(rows) < 1000:
            return mapping
        offset += 1000


def parse_customer_owners(frame):
    frame = frame.copy()
    if "코드" not in frame and "거래처코드" in frame:
        frame.rename(columns={"거래처코드": "코드"}, inplace=True)
    if not {"코드", "담당자"}.issubset(frame.columns):
        raise ValueError("담당자 파일에는 코드(또는 거래처코드)와 담당자 열이 필요합니다.")
    frame["코드"] = frame["코드"].fillna("").astype(str).str.strip()
    frame["담당자"] = frame["담당자"].fillna("").astype(str).str.strip()
    frame = frame[frame["코드"].ne("")].copy()
    if frame.empty:
        raise ValueError("담당자 파일에 거래처코드가 없습니다.")
    if frame.duplicated("코드").any():
        raise ValueError("담당자 파일에 같은 거래처코드가 중복됩니다. 담당자를 하나로 정리해 주세요.")
    deleted = int(frame["담당자"].eq("삭제").sum())
    frame.loc[frame["담당자"].eq("삭제"), "담당자"] = "미지정(삭제 표기)"
    frame.loc[frame["담당자"].eq(""), "담당자"] = "미지정"
    return dict(zip(frame["코드"], frame["담당자"])), deleted


def upload_fingerprint(price_bytes, shipment_bytes, tolerance):
    parts = [hashlib.sha256(price_bytes).hexdigest(), hashlib.sha256(shipment_bytes).hexdigest(), str(float(tolerance))]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def find_duplicate_upload(db, fingerprint):
    return (
        db.table("inspection_batches").select("id,title")
        .contains("results", [{"_자료지문": fingerprint}])
        .limit(1).execute().data
    )


def inspect_upload(price, shipment, tolerance, owners):
    import math
    errors, warnings = [], []
    price, shipment = price.copy(), shipment.copy()
    for frame in [price, shipment]:
        for old, new in [("거래처코드", "코드"), ("품목코드", "품번"), ("품목명", "품명")]:
            if new not in frame and old in frame:
                frame.rename(columns={old: new}, inplace=True)
    for name, frame, required in [
        ("통합단가", price, ["코드", "품번", "판매단가"]),
        ("출고현황", shipment, ["코드", "품번", "출고번호", "출고일자", "출고수량", "단가"]),
    ]:
        missing = set(required) - set(frame.columns)
        if missing:
            errors.append(f"{name}: 필수 열 누락 · {', '.join(sorted(missing))}")
    if errors:
        return {"errors": errors, "warnings": warnings, "result": None}
    for frame in [price, shipment]:
        for col in ["코드", "품번"]:
            frame[col] = frame[col].fillna("").astype(str).str.strip()
    details = shipment[shipment["출고번호"].fillna("").astype(str).str.strip().ne("")].copy()
    if details.empty:
        errors.append("출고현황: 출고 상세가 없습니다.")
    blank_keys = details["코드"].eq("") | details["품번"].eq("")
    if blank_keys.any():
        errors.append(f"출고현황: 거래처코드 또는 품번 공란 {int(blank_keys.sum()):,}건")
    for col in ["출고수량", "단가"]:
        invalid = ~number(details[col]).map(lambda value: pd.notna(value) and math.isfinite(float(value)))
        if invalid.any():
            errors.append(f"출고현황: {col} 숫자 오류·공란 {int(invalid.sum()):,}건")
    dates = pd.to_datetime(details["출고일자"].astype(str), format="%Y%m%d", errors="coerce")
    if dates.isna().any():
        errors.append(f"출고현황: 출고일자 오류 {int(dates.isna().sum()):,}건")
    if "순번" in details:
        keys = [col for col in ["사업장", "출고번호", "순번"] if col in details]
        count = int(details.duplicated(keys, keep=False).sum())
        if count:
            warnings.append(f"출고 전표·순번 중복 {count:,}행 · 중복 업로드 여부 확인")
    result = None
    if not errors:
        try:
            result = validate(price, shipment, tolerance)
        except ValueError as exc:
            errors.append(str(exc))
    if result is not None:
        missing = int(result["기준단가"].isna().sum())
        if missing:
            warnings.append(f"기준단가 미연결 {missing:,}건 · 거래처·품목·납품처명 확인")
        unspecified = sum(str(code) not in owners or str(owners.get(str(code), "")).startswith("미지정") for code in result["코드"])
        if unspecified:
            warnings.append(f"담당자 미지정 출고 {unspecified:,}건 · 담당자 파일 등록·확인")
        low = int(result["기준단가"].le(1).sum())
        if low:
            warnings.append(f"기준단가 1원 이하 {low:,}건 · 정상 등록 여부 확인")
    return {"errors": errors, "warnings": warnings, "result": result}


def closing_report(data, title, month, owner, filenames):
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    data = data.copy()
    attention = data[data["판정"].ne("일치") | data["기준정보주의"].fillna("").ne("")]
    difference = data[data["판정"].eq("단가차이 확인")]
    summary = pd.DataFrame([
        ["자료명", title], ["출고월", month], ["담당자 필터", owner],
        ["작성일시", datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")],
        ["출고 파일", filenames[0]], ["기준단가 파일", filenames[1]],
        ["전체 출고", len(data)], ["단가 차이", len(difference)],
        ["기준단가 없음", int(data["기준단가"].isna().sum())],
        ["확인 대상", len(attention)], ["확인 대상 중 확인", int(attention["확인결과"].eq("확인").sum())],
        ["확인 대상 중 미확인", int(attention["확인결과"].ne("확인").sum())],
        ["차이규모 합계", float(difference["차이규모"].sum())],
        ["금액 의미", "차액 절댓값 합계이며 확정 손실액이 아닙니다."],
    ], columns=["항목", "내용"])
    temp = data.assign(
        단가차이건수=data["판정"].eq("단가차이 확인").astype(int),
        확인대상건수=(data["판정"].ne("일치") | data["기준정보주의"].fillna("").ne("")).astype(int),
        미확인건수=((data["판정"].ne("일치") | data["기준정보주의"].fillna("").ne("")) & data["확인결과"].ne("확인")).astype(int),
        차이합계=data["차이규모"].where(data["판정"].eq("단가차이 확인"), 0),
    )
    def aggregate(keys):
        return temp.groupby(keys, dropna=False).agg(
            출고건수=("행키", "size"), 단가차이건수=("단가차이건수", "sum"),
            확인대상건수=("확인대상건수", "sum"), 미확인건수=("미확인건수", "sum"),
            차이규모=("차이합계", "sum"),
        ).reset_index()
    rename = {"코드": "거래처코드", "품번": "품목코드", "품명": "품목명"}
    preferred = ["담당자", "코드", "거래처명", "납품처명", "품번", "품명", "규격", "출고일자", "출고번호", "순번", "출고수량", "기준단가", "단가", "단가차이", "차이규모", "판정", "확인결과", "의견/설명", "확인사유", "기준구분", "기준정보주의", "확인작성자"]
    cols = [col for col in preferred if col in data]
    frames = {
        "마감요약": summary,
        "담당자별현황": aggregate(["담당자"]),
        "거래처별현황": aggregate(["담당자", "코드", "거래처명"]).rename(columns=rename),
        "확인대상상세": attention[cols].rename(columns=rename),
        "전체출고상세": data[cols].rename(columns=rename),
    }
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in frames.items():
            safe = frame.copy()
            for col in safe.select_dtypes(include=["object", "string"]).columns:
                safe[col] = safe[col].map(lambda value: ILLEGAL_CHARACTERS_RE.sub("", value) if isinstance(value, str) else value)
            safe.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            ws.sheet_view.showGridLines = False
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor="203B5C")
                cell.font = Font(color="FFFFFF", bold=True)
            ws.row_dimensions[1].height = 26
            for column in ws.columns:
                header = column[0].value
                ws.column_dimensions[column[0].column_letter].width = 45 if header in ["의견/설명", "확인사유"] else 22
                for cell in column[1:]:
                    if cell.data_type == "f":
                        cell.data_type = "s"
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
            if name == "마감요약":
                ws.column_dimensions['B'].width = 65
    return output.getvalue()


def render_upload(db, owners):
    with st.container(key="source_upload_panel"):
        with st.expander("＋ 새 엑셀 등록 · 사전검사 후 저장", expanded=False):
            today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
            title = st.text_input("등록 이름", value=f"{today} 단가 점검")
            p, s = st.columns(2)
            price_file = p.file_uploader("① 통합단가 · 거래처·납품처별 판매단가", type=["xls", "xlsx"])
            shipment_file = s.file_uploader("② 출고현황 · 실제 출고된 내역", type=["xls", "xlsx"])
            tolerance = st.number_input("허용할 단가 차이(원)", min_value=0.0, value=0.01, step=0.01, format="%.4f")
            if not price_file or not shipment_file:
                st.caption("두 파일 선택 → 사전검사 → 결과 확인 → 공유 저장")
                return
            fingerprint = upload_fingerprint(price_file.getvalue(), shipment_file.getvalue(), tolerance)
            if st.button("③ 업로드 사전검사", type="primary"):
                try:
                    inspection = inspect_upload(read_excel(price_file), read_excel(shipment_file), tolerance, owners)
                    inspection["fingerprint"] = fingerprint
                    inspection["duplicate"] = find_duplicate_upload(db, fingerprint)
                    st.session_state["upload_precheck"] = inspection
                except Exception:
                    st.error("파일을 읽거나 검사하지 못했습니다. Excel 파일 형식과 서버 연결을 확인해 주세요.")
            inspection = st.session_state.get("upload_precheck")
            if not inspection or inspection.get("fingerprint") != fingerprint:
                st.caption("파일 또는 허용 차이가 변경되면 다시 검사해 주세요.")
                return
            for message in inspection["errors"]:
                st.error(message)
            for message in inspection["warnings"]:
                st.warning(message)
            if inspection["errors"]:
                st.caption("오류를 수정한 파일로 다시 검사하면 저장할 수 있습니다.")
                return
            result = inspection["result"]
            st.success(f"사전검사 통과 · 출고 상세 {len(result):,}건 · 차이 {result['판정'].eq('단가차이 확인').sum():,}건")
            allow_duplicate = False
            if inspection["duplicate"]:
                st.warning("같은 파일과 허용 차이로 등록한 자료가 있습니다.")
                allow_duplicate = st.checkbox("동일 자료를 별도 검증 건으로 다시 등록합니다", key=f"allow_duplicate_{fingerprint}")
            acknowledged = not inspection["warnings"] or st.checkbox("경고 내용을 확인했습니다", key=f"acknowledge_{fingerprint}")
            blocked = not acknowledged or (bool(inspection["duplicate"]) and not allow_duplicate)
            if st.button("④ 검증 결과 공유 저장", type="primary", disabled=blocked):
                if not title.strip():
                    st.warning("등록 이름을 입력해 주세요.")
                    return
                try:
                    duplicate = find_duplicate_upload(db, fingerprint)
                    if duplicate and not allow_duplicate:
                        st.warning("다른 사용자가 동일 자료를 등록했습니다. 다시 검사해 주세요.")
                        return
                    output = result.copy()
                    output["_자료지문"] = ""
                    output.loc[output.index[0], "_자료지문"] = fingerprint
                    response = db.table("inspection_batches").insert({
                        "title": title.strip(), "shipment_filename": shipment_file.name,
                        "price_filename": price_file.name,
                        "results": json.loads(output.to_json(orient="records", force_ascii=False, double_precision=15)),
                    }).execute()
                    st.session_state["batch_id"] = response.data[0]["id"]
                    st.session_state.pop("upload_precheck", None)
                    st.success("등록 완료 · 아래에서 검토할 자료를 선택하세요.")
                except Exception:
                    st.error("저장하지 못했습니다. 잠시 후 다시 시도해 주세요.")


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
        .agg(차이규모=("차이규모", "sum"), 출고건수=("행키", "size"), 상세행키=("행키", list))
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


def render_card_shipments(diff, row):
    """카드 집계에 실제 포함된 상세행만 접어서 표시합니다."""
    from html import escape

    shipments = diff[diff["행키"].isin(row["상세행키"])].copy()
    sort_cols = [col for col in ["출고일자", "출고번호", "순번"] if col in shipments.columns]
    if sort_cols:
        shipments = shipments.sort_values(sort_cols, kind="stable")
    with st.expander(
        f"출고 상세 {len(shipments):,}건 합산 · 클릭하여 세부 내역 보기",
        expanded=False,
    ):
        st.caption("위 카드에 합산된 실제 출고 내역입니다. 단가와 수량, 출고번호를 건별로 확인하세요.")
        for index, item in enumerate(shipments.to_dict("records"), 1):
            def text_value(value):
                return "—" if value is None or pd.isna(value) or str(value).strip() == "" else str(value)

            def amount(value, suffix="원"):
                return "—" if value is None or pd.isna(value) else f"{float(value):,.2f}{suffix}"

            date = text_value(item.get("출고일자"))
            if len(date) == 8 and date.isdigit():
                date = f"{date[:4]}.{date[4:6]}.{date[6:]}"
            fields = [
                ("출고일자", date),
                ("출고번호", text_value(item.get("출고번호"))),
                ("순번", text_value(item.get("순번"))),
                ("납품처", text_value(item.get("납품처명"))),
                ("적용 기준", text_value(item.get("기준구분"))),
                ("출고수량", amount(item.get("출고수량"), "") + " " + text_value(item.get("단위"))),
                ("기준단가", amount(item.get("기준단가"))),
                ("출고단가", amount(item.get("단가"))),
                ("단가차이", amount(item.get("단가차이"))),
                ("차이금액", amount(item.get("차이금액"))),
                ("차이규모", amount(item.get("차이규모"))),
            ]
            html_fields = "".join(
                '<div class="price-field"><span class="price-label">'
                + escape(label)
                + '</span><span class="price-value '
                + ("price-emphasis" if label == "차이규모" else "")
                + '">' + escape(value) + '</span></div>'
                for label, value in fields
            )
            original_notes = []
            for col in ["비고", "비고(상세)", "비고(상세).1", "승인사유"]:
                value = text_value(item.get(col))
                if value != "—":
                    original_notes.append(f"{col}: {value}")
            note_html = (
                '<div class="shipment-original-note">'
                + escape(" / ".join(original_notes)) + '</div>'
                if original_notes else ""
            )
            st.markdown(
                '<div class="shipment-detail"><div class="shipment-detail-title">'
                + f'출고 내역 {index:02d}'
                + '</div><div class="shipment-detail-grid">'
                + html_fields + '</div>' + note_html + '</div>',
                unsafe_allow_html=True,
            )


def render_price_cards(diff, db, selected, review_map, month):
    from html import escape
    import math

    st.subheader("거래처·품목별 단가 확인")
    saved_note_key = st.session_state.pop("price_note_saved", None)
    cards = build_price_cards(diff)
    if not cards.empty and "담당자" in diff:
        owner_map = diff.drop_duplicates("코드").set_index("코드")["담당자"].to_dict()
        cards["담당자"] = cards["코드"].map(owner_map).fillna("미지정")
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
    st.caption(f"{len(cards):,}개 항목 · 단가별 구분")
    if cards.empty:
        st.info("검색 결과가 없습니다. 검색어를 변경해 주세요.")
        return
    page_count = math.ceil(len(cards) / page_size)
    page_options = list(range(1, page_count + 1))
    if page_count > 1:
        page = st.selectbox(
            "페이지", page_options,
            format_func=lambda value: f"{value} / {page_count} 페이지",
            key=f"card_page_{selected}_{month}_{page_size}_{hashlib.sha256(search.encode()).hexdigest()[:10]}",
        )
    else:
        page = 1
    visible = cards.iloc[(page - 1) * page_size:page * page_size]
    for row in visible.to_dict("records"):
        key = row["비고키"]
        saved = review_map.get(key, {})
        revision = hashlib.sha256(
            json.dumps(
                [saved.get("reason", ""), saved.get("updated_at", "")],
                ensure_ascii=False,
            ).encode()
        ).hexdigest()[:12]
        with st.container(border=True):
            details, note = st.columns([2.8, 1.2], gap="medium", vertical_alignment="top")
            fields = [
                ("거래처코드", row["코드"]),
                ("거래처명", row["거래처명"]),
                ("품목코드", row["품번"]),
                ("품목명", row["품명"]),
                ("담당자", row.get("담당자", "미지정")),
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
            with note:
                with st.form(f"card_note_{selected}_{key}_{revision}", border=False):
                    text = st.text_area(
                        "비고", value=saved.get("reason", ""),
                        placeholder="확인완료 / 의견 등을 입력하세요",
                        height=90, max_chars=2000,
                        key=f"price_note_{selected}_{key}_{revision}",
                    )
                    submitted = st.form_submit_button(
                        "비고 저장", type="primary", use_container_width=True
                    )
                if submitted:
                    if text == saved.get("reason", ""):
                        st.caption("변경된 내용이 없습니다.")
                    else:
                        try:
                            db.table("inspection_reviews").upsert(
                                {
                                    "batch_id": selected,
                                    "row_key": key,
                                    "status": "확인 중",
                                    "reason": text,
                                    "reviewer": "",
                                },
                                on_conflict="batch_id,row_key",
                            ).execute()
                            st.session_state["price_note_saved"] = key
                            st.rerun()
                        except Exception:
                            st.error("저장하지 못했습니다. 다시 시도해 주세요.")
                if saved_note_key == key:
                    st.success("저장 완료")
            st.markdown('<div class="shipment-details-gap"></div>', unsafe_allow_html=True)
            render_card_shipments(diff, row)


def confirmation_key(row_key):
    return "confirm:v1:" + str(row_key)


def confirmation_value(row_key, detailed_status, review_map):
    record = review_map.get(confirmation_key(row_key))
    if record and record.get("reason") in ["미확인", "확인"]:
        return record["reason"]
    return "확인" if detailed_status in ["정상", "수정 필요", "기준정보 수정 필요"] else "미확인"


def confirmation_record(batch_id, row_key, value):
    # 확인 여부는 별도 기록으로 보관하여 기존 처리결과와 사유를 보존합니다.
    return {
        "batch_id": batch_id,
        "row_key": confirmation_key(row_key),
        "status": "확인 중",
        "reason": value,
        "reviewer": "",
    }


def auto_save_confirmation(db, batch_id, row_key, widget_key, previous):
    """선택 변경 시 한 건만 저장하며, 실패하면 마지막 저장값으로 되돌립니다."""
    value = st.session_state.get(widget_key, previous)
    if value not in ["미확인", "확인"] or value == previous:
        return
    try:
        db.table("inspection_reviews").upsert(
            confirmation_record(batch_id, row_key, value),
            on_conflict="batch_id,row_key",
        ).execute()
        st.session_state["confirmation_autosave_notice"] = {
            "batch_id": batch_id, "ok": True,
        }
    except Exception:
        st.session_state[widget_key] = previous
        st.session_state["confirmation_autosave_notice"] = {
            "batch_id": batch_id, "ok": False,
        }


def opinion_key(row_key):
    return "opinion:v1:" + str(row_key)


def auto_save_opinion(db, batch_id, row_key, widget_key, previous):
    value = st.session_state.get(widget_key, previous)
    error_key = f"{batch_id}:{row_key}"
    errors = dict(st.session_state.get("opinion_autosave_errors", {}))
    if value == previous:
        errors.pop(error_key, None)
        st.session_state["opinion_autosave_errors"] = errors
        return
    try:
        db.table("inspection_reviews").upsert(
            {
                "batch_id": batch_id,
                "row_key": opinion_key(row_key),
                "status": "확인 중",
                "reason": value,
                "reviewer": "",
            },
            on_conflict="batch_id,row_key",
        ).execute()
        errors.pop(error_key, None)
        st.session_state["opinion_autosave_errors"] = errors
        st.session_state["opinion_autosave_notice"] = batch_id
    except Exception:
        errors[error_key] = {"value": value}
        st.session_state["opinion_autosave_errors"] = errors


def render_opinion_input(container, row, db, selected):
    row_key = row["행키"]
    saved = row.get("의견/설명", "")
    if saved is None or pd.isna(saved):
        saved = ""
    saved = str(saved)
    revision = hashlib.sha256(saved.encode()).hexdigest()[:12]
    widget_key = f"shipment_opinion_{selected}_{row_key}_{revision}"
    failure = st.session_state.get("opinion_autosave_errors", {}).get(f"{selected}:{row_key}")
    container.text_area(
        "의견/설명",
        value=failure["value"] if failure else saved,
        placeholder="확인 내용이나 의견을 입력하세요",
        height=70, max_chars=2000,
        key=widget_key,
        on_change=auto_save_opinion,
        args=(db, selected, row_key, widget_key, saved),
        help="입력 후 다른 곳을 클릭하면 자동 저장됩니다.",
    )
    if failure:
        container.error("의견을 저장하지 못했습니다. 작성한 내용은 유지됩니다.")
        container.button(
            "의견 저장 다시 시도",
            key=f"retry_opinion_{selected}_{row_key}",
            on_click=auto_save_opinion,
            args=(db, selected, row_key, widget_key, saved),
        )


def render_confirmation_editor(view, db, selected):
    """거래처별 부드러운 목록형 표. 확인결과 변경·저장은 그대로 유지합니다."""
    from html import escape
    import math

    if st.session_state.pop("opinion_autosave_notice", None) == selected:
        st.toast("의견/설명 자동 저장 완료", icon="✅")
    notice = st.session_state.pop("confirmation_autosave_notice", None)
    if notice and notice.get("batch_id") == selected:
        if notice.get("ok"):
            st.toast("확인결과 자동 저장 완료", icon="✅")
        else:
            st.error("자동 저장에 실패했습니다. 이전 값으로 되돌렸습니다. 다시 선택해 주세요.")
    if view.empty:
        st.info("조회된 출고가 없습니다.")
        return
    count = len(view)
    search_identity = hashlib.sha256("|".join(view["행키"].astype(str)).encode()).hexdigest()[:12]
    pages = math.ceil(count / 20)
    page = 1
    if pages > 1:
        page = st.selectbox(
            "조회 페이지", list(range(1, pages + 1)),
            format_func=lambda value: f"{value} / {pages} 페이지 · 20건씩",
            key=f"review_page_{selected}_{search_identity}",
        )
    visible = view.iloc[(page - 1) * 20:page * 20]
    st.caption("확인결과 즉시 저장 · 의견/설명은 입력 후 다른 곳을 클릭하면 저장됩니다.")

    def clean(value):
        if value is None or pd.isna(value) or str(value).strip() == "":
            return "—"
        return str(value)

    def text(value):
        return escape(clean(value))

    def money(value):
        if value is None or pd.isna(value):
            return "—"
        return f"{float(value):,.2f}"

    with st.container():
        groups = [col for col in ["코드", "거래처명"] if col in visible.columns]
        grouped = visible.groupby(groups, sort=False, dropna=False) if groups else [(('', ''), visible)]
        for identity, rows in grouped:
            if not isinstance(identity, tuple):identity=(identity, '')
            customer_code, customer_name = (list(identity) + ['',''])[:2]
            all_confirmed = rows['확인결과'].eq('확인').all()
            any_confirmed = rows['확인결과'].eq('확인').any()
            card_status = 'confirmed' if all_confirmed else ('partial' if any_confirmed else 'pending')
            group_identity = hashlib.sha256('|'.join(rows['행키'].astype(str)).encode()).hexdigest()[:16]
            with st.container(border=True, key=f"review_card_{card_status}_{selected}_{group_identity}"):
                st.markdown(
                    '<div class="review-customer"><div><span class="review-customer-code">'
                    + text(customer_code) + '</span><span class="review-customer-name">'
                    + text(customer_name) + '</span><span class="review-owner">담당자 ' + text(rows.iloc[0].get('담당자', '미지정')) + '</span></div><span class="review-customer-count">'
                    + f'{len(rows):,}건' + '</span></div>',
                    unsafe_allow_html=True,
                )
                left, right = st.columns([0.8, 6.5])
                left.markdown('<div class="review-column-label">확인결과</div>', unsafe_allow_html=True)
                right.markdown(
                    '<div class="review-grid review-grid-head"><span>품목 · 출고내역</span><span>납품처</span><span>수량</span><span>기준단가</span><span>출고단가</span><span>차이규모</span></div>',
                    unsafe_allow_html=True,
                )
                for row in rows.to_dict('records'):
                    row_key = row['행키']
                    current = row.get('확인결과', '미확인')
                    row_status = 'confirmed' if current == '확인' else 'pending'
                    with st.container(key=f"review_row_{row_status}_{selected}_{row_key}"):
                        state, content = st.columns([0.8, 6.5], vertical_alignment='top')
                        widget_key = f"auto_check_{selected}_{row_key}_{current}"
                        state.selectbox(
                            f"확인결과 · {row.get('출고번호', '')} / {row.get('순번', '')}",
                            ['미확인', '확인'], index=1 if current == '확인' else 0,
                            key=widget_key,
                            label_visibility='collapsed',
                            on_change=auto_save_confirmation,
                            args=(db, selected, row_key, widget_key, current),
                        )
                        judgment = clean(row.get('판정'))
                        badge_class = {
                            '일치':'matched', '단가차이 확인':'difference',
                            '기준단가 확인':'reference', '조정·반품 확인':'adjustment',
                        }.get(judgment, 'neutral')
                        date = clean(row.get('출고일자'))
                        if len(date)==8 and date.isdigit():date=f'{date[:4]}.{date[4:6]}.{date[6:]}'
                        subtitle = ' · '.join([date, clean(row.get('출고번호')), clean(row.get('순번'))])
                        detail_fields = [
                            ('품목코드',row.get('품번')),('품목명',row.get('품명')),
                            ('규격',row.get('규격')),('납품처명',row.get('납품처명')),
                            ('적용 기준',row.get('기준구분')),('단가차이',money(row.get('단가차이'))),
                            ('차이금액',money(row.get('차이금액'))),
                            ('기준정보 주의',row.get('기준정보주의')),
                            ('상세 처리결과',row.get('처리결과')),
                            ('확인사유',row.get('확인사유')),('담당자',row.get('담당자')),
                        ]
                        detail_html=''.join('<div><span>'+escape(label)+'</span><strong>'+text(val)+'</strong></div>' for label,val in detail_fields)
                        html = (
                            '<div class="review-data-row"><div class="review-grid">'
                            '<div class="review-product"><strong>'+text(row.get('품명'))+'</strong>'
                            '<span class="review-product-code">'+text(row.get('품번'))+'</span>'
                            '<span class="review-meta">'+escape(subtitle)+'</span></div>'
                            '<div class="review-destination">'+text(row.get('납품처명'))+'</div>'
                            '<div class="review-number">'+money(row.get('출고수량'))+'</div>'
                            '<div class="review-number">'+money(row.get('기준단가'))+'</div>'
                            '<div class="review-number review-actual">'+money(row.get('단가'))+'</div>'
                            '<div class="review-number review-difference">'+money(row.get('차이규모'))+'</div></div>'
                            '<div class="review-row-bottom"><span class="review-badge '+badge_class+'">'+escape(judgment)+'</span>'
                            '<span class="review-basis">'+text(row.get('기준구분'))+'</span></div>'
                            '<details class="review-details"><summary>상세내역</summary><div class="review-detail-fields">'+detail_html+'</div></details></div>'
                        )
                        content.markdown(html, unsafe_allow_html=True)
                        render_opinion_input(content, row, db, selected)


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

    try:
        owners = load_customer_owners(db)
    except Exception:
        st.error("담당자 정보를 불러오지 못했습니다. 잠시 후 새로 고침해 주세요.")
        st.stop()
    render_upload(db, owners)

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

    with st.container(border=True, key="source_selection_panel"):
        a, b = st.columns(
            [5, 1],
            vertical_alignment="bottom",
        )

        selected = a.selectbox(
            "현재 검토할 자료",
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
            type="primary",
            use_container_width=True,
        ):
            st.rerun()

        created = pd.to_datetime(
            batch_map[selected]["created_at"],
            utc=True,
        ).tz_convert("Asia/Seoul")

        st.caption(
            f"등록 {created:%Y.%m.%d %H:%M} · 팀원의 최신 기록은 오른쪽 버튼으로 갱신"
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

    data["확인작성자"] = data["담당자"]
    data["담당자"] = data["코드"].astype(str).map(owners).fillna("미지정")

    data["의견/설명"] = [
        review_map.get(opinion_key(key), {}).get("reason", previous or "")
        for key, previous in zip(data["행키"], data["확인사유"])
    ]
    data["처리결과"] = data["확인결과"]
    data["확인결과"] = [
        confirmation_value(key, status, review_map)
        for key, status in zip(data["행키"], data["처리결과"])
    ]

    with st.container(border=True, key="month_selection_panel"):
        month = st.selectbox(
            "조회할 출고월",
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

    owner_filter = st.selectbox(
        "담당자별 조회", ["전체"] + sorted(data["담당자"].dropna().unique().tolist()),
        key=f"owner_filter_{selected}",
    )
    if owner_filter != "전체":
        monthly = monthly[monthly["담당자"].eq(owner_filter)]

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
        "② 점검 현황",
        "③ 출고 상세 · 확인",
    ])

    with tabs[0]:
        section(
            "02",
            "점검 현황",
            "",
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "전체 출고",
            f"{len(monthly):,}건",
            help="소계·합계를 제외한 출고 상세행 수입니다.",
        )

        b.metric(
            "단가 차이",
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
            "기준단가 없음",
            f"{missing_count:,}건",
        )

        d.metric(
            "미확인·진행 중",
            f"{len(pending):,}건",
            help=(
                "자동 판정이 일치가 아니거나 "
                "기준정보 주의사항이 있는 출고 중 "
                "미확인·확인 중인 건입니다."
            ),
        )

        done = len(attention) - len(pending)
        st.progress(
            done / len(attention) if len(attention) else 1.0,
            text=f"결과 등록 {done:,} / {len(attention):,}건",
        )

        with st.expander("마감 보고서 다운로드"):
            st.caption("선택한 출고월·담당자 기준 · 요약 / 담당자별 / 거래처별 / 확인 대상 / 전체 출고")
            st.download_button(
                "마감 보고서 Excel 다운로드",
                closing_report(monthly, batch_map[selected]["title"], month, owner_filter,
                               (batch["shipment_filename"], batch["price_filename"])),
                file_name=f"마감보고서_{datetime.now(ZoneInfo('Asia/Seoul')):%Y%m%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


        render_price_cards(diff, db, selected, review_map, month)

        st.caption(
            f"차이규모 {diff['차이규모'].sum():,.1f}원 · 차액 절댓값 합계"
        )

    with tabs[1]:
        section(
            "03",
            "확인할 출고를 찾으세요",
            "거래처·품목으로 검색하세요. 확인결과는 변경 즉시 자동 저장됩니다.",
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
                ["미확인", "확인"],
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
                "품명", "출고번호", "담당자", "납품처명",
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

        sort_cols = [
            col for col in ["코드", "거래처명", "품번", "출고일자", "출고번호", "순번"]
            if col in view.columns
        ]
        if sort_cols:
            view = view.sort_values(sort_cols, kind="stable", na_position="last")
        st.subheader(f"조회 결과 · {len(view):,}건")
        render_confirmation_editor(view, db, selected)

        export_date = datetime.now(
            ZoneInfo("Asia/Seoul")
        ).strftime("%Y%m%d")

        st.download_button(
            "조회한 내역 엑셀로 내려받기",
            export_excel(view.rename(columns={"코드": "거래처코드", "품번": "품목코드", "품명": "품목명"})),
            file_name=(
                f"출고단가_점검결과_{export_date}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
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

