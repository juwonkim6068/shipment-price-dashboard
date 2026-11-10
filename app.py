import hashlib
import io
import json

import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(
    page_title="출고 단가 점검",
    page_icon="📊",
    layout="wide",
)

st.title("출고 단가 점검")
st.caption("엑셀을 등록하고 검증 결과와 확인 기록을 함께 관리합니다.")

try:
    db = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )
except Exception:
    st.info("서버 연결 설정이 필요합니다. 배포 설정을 완료해 주세요.")
    st.stop()


def read_excel(upload):
    engine = "xlrd" if upload.name.lower().endswith(".xls") else "openpyxl"
    return pd.read_excel(
        upload,
        engine=engine,
        dtype=str,
        keep_default_na=False,
    )


def number(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def validate(price, shipment, tolerance):
    for frame, required, name in [
        (
            price,
            ["코드", "품번", "판매단가", "사용여부", "시작일자", "종료일자"],
            "단가현황",
        ),
        (
            shipment,
            ["코드", "품번", "출고번호", "출고일자", "출고수량", "단가"],
            "출고현황",
        ),
    ]:
        missing = set(required) - set(frame.columns)
        if missing:
            raise ValueError(f"{name}에 필요한 열이 없습니다: {', '.join(missing)}")

    for frame in [price, shipment]:
        for col in ["코드", "품번"]:
            frame[col] = frame[col].str.strip()

    price = price[
        price["사용여부"].str.strip().eq("1.사용")
    ].copy()

    if price.duplicated(["코드", "품번"]).any():
        raise ValueError(
            "사용 중인 단가에 코드·품번 중복이 있습니다. "
            "기준단가를 하나로 정리한 후 다시 등록해 주세요."
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

    # 원본의 상세행 위치를 보존합니다.
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

    result["출고수량"] = number(result["출고수량"])
    result["단가"] = number(result["단가"])
    result["단가차이"] = result["단가"] - result["기준단가"]
    result["출고월"] = (
        result["출고일자"].str[:4] + "-"
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
    comparable = result["판정"].isin(["일치", "단가차이 확인"])
    result["차이금액"] = (
        result["단가차이"] * result["출고수량"]
    ).where(comparable)
    result["차이규모"] = result["차이금액"].abs()

    def reference_note(row):
        notes = []
        if pd.notna(row["기준단가"]) and row["기준단가"] <= 1:
            notes.append("기준단가 1원 이하")

        start = pd.to_datetime(
            str(row["기준시작일"]), format="%Y%m%d", errors="coerce"
        )
        end_text = str(row["기준종료일"])
        end = pd.to_datetime(
            end_text, format="%Y%m%d", errors="coerce"
        )
        shipped = pd.to_datetime(
            str(row["출고일자"]), format="%Y%m%d", errors="coerce"
        )

        if pd.notna(start) and pd.notna(end) and end < start:
            notes.append("기준단가 적용기간 역전")
        if pd.notna(start) and pd.notna(shipped) and shipped < start:
            notes.append("출고 후 적용되는 최신단가")
        if pd.notna(end) and pd.notna(shipped) and shipped > end:
            notes.append("기준단가 적용기간 종료")
        return " / ".join(notes)

    result["기준정보주의"] = result.apply(reference_note, axis=1)
    return result


with st.expander("새 엑셀 등록", expanded=True):
    title = st.text_input(
        "등록 이름",
        value=f"{pd.Timestamp.now(tz='Asia/Seoul'):%Y-%m-%d} 단가 점검",
    )
    left, right = st.columns(2)
    price_file = left.file_uploader(
        "① 단가현황", type=["xls", "xlsx"]
    )
    shipment_file = right.file_uploader(
        "② 출고현황", type=["xls", "xlsx"]
    )
    tolerance = st.number_input(
        "허용 단가 차이(원)",
        min_value=0.0,
        value=0.01,
        step=0.01,
        format="%.4f",
    )

    if st.button("단가 검증 후 공유 저장", type="primary"):
        if not price_file or not shipment_file:
            st.warning("두 파일을 모두 선택해 주세요.")
        elif not title.strip():
            st.warning("등록 이름을 입력해 주세요.")
        else:
            try:
                with st.spinner("검증 결과를 저장하고 있습니다."):
                    result = validate(
                        read_excel(price_file),
                        read_excel(shipment_file),
                        tolerance,
                    )
                    response = db.table("inspection_batches").insert({
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
                    }).execute()
                    st.session_state["batch_id"] = response.data[0]["id"]
                st.success("저장했습니다. 다른 직원도 같은 결과를 볼 수 있습니다.")
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("등록에 실패했습니다. 파일 형식과 서버 설정을 확인해 주세요.")


if st.button("공유 자료 새로 고침"):
    st.rerun()

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
    st.error("공유 자료를 불러오지 못했습니다. 서버 설정을 확인해 주세요.")
    st.stop()

if not batches:
    st.info("아직 등록된 자료가 없습니다. 위에서 엑셀 두 개를 등록하세요.")
    st.stop()

batch_map = {item["id"]: item for item in batches}
ids = list(batch_map)
current = st.session_state.get("batch_id")
selected = st.selectbox(
    "공유 자료 선택 · 최근 200개",
    ids,
    index=ids.index(current) if current in ids else 0,
    format_func=lambda key: (
        f"{batch_map[key]['title']} · "
        f"{batch_map[key]['created_at'][:10]} · {key[:8]}"
    ),
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
    st.error("상세 데이터를 불러오지 못했습니다. 다시 시도해 주세요.")
    st.stop()

data = pd.DataFrame(batch["results"])
if data.empty:
    st.info("선택한 자료에 출고 상세가 없습니다.")
    st.stop()

for col in ["단가", "기준단가", "출고수량", "단가차이", "차이금액", "차이규모"]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

review_map = {row["row_key"]: row for row in reviews}
data["확인결과"] = data["행키"].map(
    lambda key: review_map.get(key, {}).get("status", "미확인")
)
data["확인사유"] = data["행키"].map(
    lambda key: review_map.get(key, {}).get("reason", "")
)
data["담당자"] = data["행키"].map(
    lambda key: review_map.get(key, {}).get("reviewer", "")
)

month = st.selectbox(
    "출고월", ["전체"] + sorted(data["출고월"].dropna().unique().tolist())
)
monthly = data if month == "전체" else data[data["출고월"].eq(month)]
diff = monthly[monthly["판정"].eq("단가차이 확인")]

a, b, c, d = st.columns(4)
a.metric("출고 상세", f"{len(monthly):,}건")
b.metric("단가차이 확인", f"{len(diff):,}건")
c.metric(
    "기준단가 확인",
    f"{monthly['판정'].eq('기준단가 확인').sum():,}건",
)
d.metric("차이규모", f"{diff['차이규모'].sum():,.1f}원")

st.caption(
    "차이규모는 최신 기준단가 대비 차액의 절댓값 합계입니다. "
    "단가 차이는 확인 대상이며 실제 오류 확정은 아닙니다."
)

left, right = st.columns(2)
with left:
    st.subheader("판정별 건수")
    st.bar_chart(monthly["판정"].value_counts())
with right:
    st.subheader("거래처별 차이규모")
    if "거래처명" in diff.columns and not diff.empty:
        ranking = (
            diff.groupby("거래처명")["차이규모"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
        )
        st.dataframe(ranking, use_container_width=True)
    else:
        st.info("표시할 단가 차이가 없습니다.")

st.subheader("출고 상세")
judgments = st.multiselect(
    "판정 선택 · 비워두면 전체",
    sorted(monthly["판정"].unique()),
    default=["단가차이 확인"]
    if "단가차이 확인" in monthly["판정"].values else [],
)
search = st.text_input("거래처명·코드·품번·품명·출고번호 검색")
view = monthly.copy()
if judgments:
    view = view[view["판정"].isin(judgments)]
if search:
    columns = [
        col for col in ["거래처명", "코드", "품번", "품명", "출고번호"]
        if col in view.columns
    ]
    matches = pd.Series(False, index=view.index)
    for col in columns:
        matches |= view[col].astype(str).str.contains(
            search, case=False, regex=False, na=False
        )
    view = view[matches]

view = view.sort_values("차이규모", ascending=False, na_position="last")
preferred = [
    "출고일자", "출고번호", "순번", "코드", "거래처명", "품번",
    "품명", "규격", "출고수량", "단가", "기준단가", "단가차이",
    "차이금액", "차이규모", "판정", "기준정보주의",
    "확인결과", "확인사유", "담당자",
]
visible = [col for col in preferred if col in view.columns]
st.dataframe(view[visible], use_container_width=True, hide_index=True)

output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    view.drop(columns=["행키"]).to_excel(
        writer, index=False, sheet_name="점검결과"
    )
st.download_button(
    "현재 조회 결과 엑셀 다운로드",
    output.getvalue(),
    file_name="출고단가_점검결과.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.subheader("확인 기록 저장")
st.caption("담당자는 직접 입력합니다. 같은 건은 마지막 저장 내용으로 갱신됩니다.")

if view.empty:
    st.info("현재 조회 조건에 해당하는 출고가 없습니다.")
else:
    row_map = {row["행키"]: row for row in view.to_dict("records")}

    def row_label(key):
        row = row_map[key]
        return (
            f"{row.get('출고번호', '')} / "
            f"{row.get('순번', '')} / "
            f"{row.get('거래처명', '')} / "
            f"{row.get('품번', '')} / "
            f"{row.get('품명', '')}"
        )

    row_key = st.selectbox(
        "기록할 출고 선택",
        list(row_map),
        format_func=row_label,
        key=f"row_{selected}",
    )
    saved = review_map.get(row_key, {})
    statuses = ["확인 중", "정상", "수정 필요", "기준정보 수정 필요"]
    form_key = f"{selected}_{row_key}"

    with st.form(f"review_{form_key}"):
        status = st.selectbox(
            "확인결과",
            statuses,
            index=statuses.index(saved.get("status", "확인 중")),
        )
        reason = st.text_area(
            "확인사유", value=saved.get("reason", ""), max_chars=2000
        )
        reviewer = st.text_input(
            "담당자", value=saved.get("reviewer", ""), max_chars=100
        )
        if st.form_submit_button("확인 기록 공유 저장"):
            try:
                db.table("inspection_reviews").upsert(
                    {
                        "batch_id": selected,
                        "row_key": row_key,
                        "status": status,
                        "reason": reason,
                        "reviewer": reviewer,
                    },
                    on_conflict="batch_id,row_key",
                ).execute()
                st.rerun()
            except Exception:
                st.error("저장하지 못했습니다. 다시 시도해 주세요.")
