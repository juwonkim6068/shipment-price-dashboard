"""Private template-based official notices and incoming document archive."""
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime, date, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from lxml import etree

BUCKET = "shipment-notices-private"
ANCHOR = "[시스템] 공문 보관함"
TEMPLATE_PATH = "templates/price_notice.docx"
PREFIX = "notice:v1:"
MAX_FILE_SIZE = 10 * 1024 * 1024
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": W[1:-1]}
MIMES = {
    ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
}


def now_text():
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def safe_filename(value):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(value))[:130] or "공문"


def storage(db):
    try:
        bucket = db.storage.get_bucket(BUCKET)
    except Exception as exc:
        code = str(getattr(exc, "status", getattr(exc, "status_code", "")))
        if "404" not in code and "not found" not in str(exc).lower():
            raise RuntimeError("공문 저장소에 연결하지 못했습니다.") from exc
        db.storage.create_bucket(BUCKET, options={"public": False, "file_size_limit": MAX_FILE_SIZE, "allowed_mime_types": list(set(MIMES.values()))})
        bucket = db.storage.get_bucket(BUCKET)
    public = bucket.get("public", False) if isinstance(bucket, dict) else getattr(bucket, "public", False)
    if public:
        raise RuntimeError("공문 저장소는 비공개로 설정되어 있어야 합니다.")
    return db.storage.from_(BUCKET)


def anchor_id(db):
    found = db.table("inspection_batches").select("id").eq("title", ANCHOR).limit(1).execute().data
    if found:
        return found[0]["id"]
    return db.table("inspection_batches").insert({"title": ANCHOR, "shipment_filename": "", "price_filename": "", "results": []}).execute().data[0]["id"]


def documents(db):
    result, offset = [], 0
    while True:
        rows = db.table("inspection_reviews").select("row_key,reason,updated_at").like("row_key", PREFIX + "%").order("updated_at", desc=True).range(offset, offset + 999).execute().data
        for row in rows:
            try:
                item = json.loads(row["reason"])
                if item.get("kind") in ["outgoing", "incoming"]:
                    result.append(item)
            except (ValueError, TypeError, AttributeError):
                continue
        if len(rows) < 1000:
            return result
        offset += 1000


def save_metadata(db, item):
    db.table("inspection_reviews").upsert({
        "batch_id": anchor_id(db), "row_key": PREFIX + item["id"],
        "status": "확인 중", "reason": json.dumps(item, ensure_ascii=False), "reviewer": item.get("owner", ""),
    }, on_conflict="batch_id,row_key").execute()


def own_nodes(paragraph):
    result = []
    for node in paragraph.iter(W + "t"):
        parent = node.getparent()
        while parent is not None and parent.tag != W + "p":
            parent = parent.getparent()
        if parent is paragraph:
            result.append(node)
    return result


def ptext(paragraph):
    return "".join(node.text or "" for node in own_nodes(paragraph))


def ctext(cell):
    return "".join(ptext(p) for p in cell.iter(W + "p"))


def set_ptext(paragraph, value):
    nodes = own_nodes(paragraph)
    if not nodes:
        run = etree.SubElement(paragraph, W + "r")
        nodes = [etree.SubElement(run, W + "t")]
    for node in nodes:
        node.text = ""
    lines = str(value).split("\n")
    nodes[0].text = lines[0]
    nodes[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    run = nodes[0].getparent()
    for line in lines[1:]:
        etree.SubElement(run, W + "br")
        node = etree.SubElement(run, W + "t")
        node.text = line
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def set_cell(cell, value):
    paragraphs = list(cell.iter(W + "p"))
    if not paragraphs:
        paragraphs = [etree.SubElement(cell, W + "p")]
    set_ptext(paragraphs[0], value)
    for paragraph in paragraphs[1:]:
        set_ptext(paragraph, "")


def labelled_cells(root):
    fields = {}
    for row in root.iter(W + "tr"):
        cells = row.findall(W + "tc")
        if len(cells) >= 2:
            label = re.sub(r"\s+", "", ctext(cells[0]))
            if label in ["문서번호", "시행일자", "업체명", "수신", "참조"]:
                fields[label] = cells[1]
    return fields


def price_table(root):
    for table in root.iter(W + "tbl"):
        rows = table.findall(W + "tr")
        if len(rows) >= 2:
            cells = rows[0].findall(W + "tc")
            if [re.sub(r"\s+", "", ctext(c)) for c in cells] == ["품목", "규격", "조정단가", "비고"]:
                return table
    raise ValueError("양식에서 품목·규격·조정단가·비고 표를 찾지 못했습니다.")


def template_defaults(raw):
    if len(raw) > MAX_FILE_SIZE:
        raise ValueError("양식은 10MB 이하 DOCX 파일이어야 합니다.")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(x.file_size for x in archive.infolist()) > 40 * 1024 * 1024:
                raise ValueError("압축 해제 용량이 너무 큰 양식입니다.")
            root = etree.fromstring(archive.read("word/document.xml"), etree.XMLParser(resolve_entities=False, no_network=True))
    except (zipfile.BadZipFile, KeyError, etree.XMLSyntaxError) as exc:
        raise ValueError("올바른 Word DOCX 양식이 아닙니다.") from exc
    fields = labelled_cells(root)
    required = {"문서번호", "시행일자", "업체명", "수신", "참조"}
    if required - set(fields):
        raise ValueError("양식의 문서번호·시행일자·업체명·수신·참조 항목을 확인해 주세요.")
    paragraphs = [ptext(p) for p in root.iter(W + "p")]
    title = next((t for t in paragraphs if re.match(r"^제\s*목\s*:", t)), None)
    body = next((t for t in paragraphs if re.match(r"^2\s*[.]", t)), None)
    ending = next((t for t in paragraphs if t.startswith("시행일자")), None)
    if not title or not body or not ending:
        raise ValueError("양식의 제목·2번 문단·하단 시행일자를 확인해 주세요.")
    rows = price_table(root).findall(W + "tr")[1:]
    items = [[ctext(c) for c in row.findall(W + "tc")] for row in rows]
    contact = next((t for t in paragraphs if "TEL" in t and "담당자" in t), "")
    owner = re.search(r"담당자\s*:\s*(.+)$", contact)
    number = ctext(fields["문서번호"]).strip()
    prefix = re.sub(r"\d{2}-\d{4}-\d+$", "", number)
    return {
        "number": number, "number_prefix": prefix,
        "customer_name": ctext(fields["업체명"]).strip(),
        "recipient": ctext(fields["수신"]).strip(), "reference": ctext(fields["참조"]).strip(),
        "title": re.sub(r"^제\s*목\s*:\s*", "", title), "body": body,
        "owner": owner.group(1).strip() if owner else "", "items": items,
    }


def fill_template(raw, values):
    template_defaults(raw)
    items = values["items"]
    if not 1 <= len(items) <= 8:
        raise ValueError("단가표는 1~8개 품목으로 입력해 주세요.")
    for key in ["number", "customer_name", "title", "body"]:
        if not str(values.get(key, "")).strip():
            raise ValueError("문서번호·거래처·제목·안내문은 필수입니다.")
    effective = datetime.fromisoformat(values["effective_at"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = etree.fromstring(archive.read("word/document.xml"), etree.XMLParser(resolve_entities=False, no_network=True))
        fields = labelled_cells(root)
        for label, value in {
            "문서번호": values["number"], "시행일자": effective.strftime("%Y.%m.%d."),
            "업체명": values["customer_name"], "수신": values.get("recipient", ""), "참조": values.get("reference", ""),
        }.items():
            set_cell(fields[label], value)
        for paragraph in list(root.iter(W + "p")):
            text = ptext(paragraph)
            if re.match(r"^제\s*목\s*:", text):
                set_ptext(paragraph, "제   목 : " + values["title"])
            elif re.match(r"^2\s*[.]", text):
                body = values["body"].strip()
                set_ptext(paragraph, body if re.match(r"^2\s*[.]", body) else "2. " + body)
            elif text.startswith("시행일자"):
                set_ptext(paragraph, f"시행일자 : {effective:%Y년 %m월 %d일 %H시 %M분}.  끝.")
            elif "TEL" in text and "담당자" in text:
                set_ptext(paragraph, re.sub(r"(담당자\s*:\s*).*$", lambda m: m.group(1) + values.get("owner", ""), text))
        table = price_table(root)
        old_rows = table.findall(W + "tr")
        model = deepcopy(old_rows[1])
        for row in old_rows[1:]:
            table.remove(row)
        for item in items:
            if not str(item.get("품목", "")).strip() or not str(item.get("조정단가", "")).strip():
                raise ValueError("단가표의 품목과 조정단가를 입력해 주세요.")
            row = deepcopy(model)
            for cell, column in zip(row.findall(W + "tc"), ["품목", "규격", "조정단가", "비고"]):
                set_cell(cell, item.get(column, ""))
            table.append(row)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as result:
            for item in archive.infolist():
                result.writestr(item, etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True) if item.filename == "word/document.xml" else archive.read(item.filename))
    return output.getvalue()


def convert_to_pdf(raw, executable=None):
    executable = executable or shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        raise RuntimeError("PDF 변환 도구를 준비 중입니다. 잠시 후 다시 시도해 주세요.")
    with tempfile.TemporaryDirectory(prefix="notice-pdf-") as folder:
        root = Path(folder)
        source = root / "notice.docx"
        source.write_bytes(raw)
        profile = (root / "profile").as_uri()
        result = subprocess.run([
            executable, "-env:UserInstallation=" + profile, "--headless", "--nologo", "--nodefault", "--nolockcheck", "--nofirststartwizard",
            "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(root), str(source),
        ], capture_output=True, timeout=60)
        pdf = root / "notice.pdf"
        if result.returncode != 0 or not pdf.exists():
            raise RuntimeError("PDF 변환에 실패했습니다. 입력 분량과 양식을 확인해 주세요.")
        output = pdf.read_bytes()
        if not output.startswith(b"%PDF-") or len(output) > MAX_FILE_SIZE:
            raise RuntimeError("생성된 PDF를 확인할 수 없거나 파일이 너무 큽니다.")
        return output


def clean_upload(upload):
    raw = upload.getvalue()
    ext = Path(upload.name).suffix.lower()
    if not raw or len(raw) > MAX_FILE_SIZE or ext not in MIMES:
        raise ValueError("10MB 이하 PDF·DOCX·PNG·JPG 파일을 선택해 주세요.")
    if ext == ".pdf":
        import fitz
        try:
            document = fitz.open(stream=raw, filetype="pdf")
            if document.needs_pass or document.page_count == 0:
                raise ValueError("암호가 없는 PDF를 등록해 주세요.")
            document.close()
        except Exception as exc:
            raise ValueError("읽을 수 있는 PDF 파일을 등록해 주세요.") from exc
    elif ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("DOCX 파일을 확인해 주세요.")
                if sum(x.file_size for x in archive.infolist()) > 40 * 1024 * 1024:
                    raise ValueError("압축 해제 용량이 너무 큽니다.")
        except zipfile.BadZipFile as exc:
            raise ValueError("DOCX 파일을 확인해 주세요.") from exc
    else:
        from PIL import Image
        try:
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
        except Exception as exc:
            raise ValueError("이미지 파일을 확인해 주세요.") from exc
    return raw, ext


def preview_pdf(raw):
    import fitz
    document = fitz.open(stream=raw, filetype="pdf")
    st.caption(f"PDF 미리보기 · {document.page_count}페이지" + (" · 처음 2페이지 표시" if document.page_count > 2 else ""))
    for index in range(min(document.page_count, 2)):
        page = document[index]
        st.image(page.get_pixmap(matrix=fitz.Matrix(1.15, 1.15)).tobytes("png"), use_container_width=True)
    document.close()


def customer_inputs(data, owners, key):
    options = [("", "직접 입력")]
    if not data.empty and {"코드", "거래처명"}.issubset(data.columns):
        pairs = data[["코드", "거래처명"]].drop_duplicates().sort_values(["거래처명", "코드"])
        options += list(pairs.itertuples(index=False, name=None))
    selected = st.selectbox("거래처 선택", range(len(options)), format_func=lambda i: f"{options[i][1]}" + (f" · {options[i][0]}" if options[i][0] else ""), key=key + "_customer")
    code, name = options[selected]
    if selected == 0:
        a, b = st.columns([1, 2])
        code = a.text_input("거래처코드(선택)", key=key + "_code", max_chars=40).strip()
        name = b.text_input("거래처명", key=key + "_name", max_chars=100).strip()
    return str(code), str(name), owners.get(str(code), "")


def create_outgoing(db, store, values, docx_raw, pdf_raw, version):
    ident = str(uuid.uuid4())
    stem = "outgoing/" + hashlib.sha256(values["number"].strip().encode()).hexdigest()
    item = {**values, "id": ident, "kind": "outgoing", "created_at": now_text(), "template_sha256": version,
            "pdf_path": stem + ".pdf", "docx_path": stem + ".docx"}
    created = []
    try:
        store.upload(item["pdf_path"], pdf_raw, {"content-type": MIMES[".pdf"], "upsert": "false"})
        created.append(item["pdf_path"])
        store.upload(item["docx_path"], docx_raw, {"content-type": MIMES[".docx"], "upsert": "false"})
        created.append(item["docx_path"])
        save_metadata(db, item)
    except Exception:
        if created:
            try:
                store.remove(created)
            except Exception:
                pass
        raise
    return item


def outgoing_form(db, store, template, records, data, owners):
    defaults = template_defaults(template)
    code, customer, owner = customer_inputs(data, owners, "notice_out")
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    prefix = defaults["number_prefix"] + today.strftime("%y-%m%d-")
    used = {r.get("number", "") for r in records if r["kind"] == "outgoing"}
    sequence = 1
    while prefix + f"{sequence:02d}" in used:
        sequence += 1
    with st.form("notice_outgoing_form"):
        a, b = st.columns(2)
        number = a.text_input("문서번호", value=prefix + f"{sequence:02d}", max_chars=120)
        title = b.text_input("제목", value=defaults["title"], max_chars=180)
        a, b, c = st.columns(3)
        effective_date = a.date_input("시행일", value=today)
        effective_time = b.time_input("시행 시각", value=time(0, 0))
        contact = c.text_input("발신 담당자", value=owner if owner and not owner.startswith("미지정") else defaults["owner"], max_chars=30)
        a, b = st.columns(2)
        recipient = a.text_input("수신", value=defaults["recipient"], max_chars=120)
        reference = b.text_input("참조", value=defaults["reference"], max_chars=120)
        body = st.text_area("안내문 · 본문 2번 문단", value=defaults["body"], height=150, max_chars=1500)
        st.caption("로고·주소·연락처·1번/3번 문단·대표자·직인은 원본 양식을 유지합니다.")
        items = st.data_editor(pd.DataFrame(defaults["items"], columns=["품목", "규격", "조정단가", "비고"]), num_rows="dynamic", hide_index=True, use_container_width=True, key="notice_price_items")
        a, b = st.columns(2)
        preview = a.form_submit_button("PDF 미리보기", use_container_width=True)
        save = b.form_submit_button("저장 · PDF 생성", type="primary", use_container_width=True)
    if preview or save:
        try:
            values = {"number": number.strip(), "title": title.strip(), "customer_code": code, "customer_name": customer,
                      "recipient": recipient, "reference": reference, "owner": contact,
                      "effective_at": datetime.combine(effective_date, effective_time).isoformat(timespec="minutes"),
                      "body": body, "items": items.fillna("").astype(str).to_dict("records")}
            if save and values["number"] in used:
                raise ValueError("같은 문서번호가 이미 저장되어 있습니다. 문서번호를 변경해 주세요.")
            with st.spinner("원본 양식으로 PDF를 생성하고 있습니다."):
                raw_docx = fill_template(template, values)
                raw_pdf = convert_to_pdf(raw_docx)
                if save:
                    item = create_outgoing(db, store, values, raw_docx, raw_pdf, hashlib.sha256(template).hexdigest())
                    st.session_state["notice_last_saved"] = item
                    records.insert(0, item)
                st.session_state["notice_preview"] = {"pdf": raw_pdf, "docx": raw_docx, "number": values["number"], "customer_name": customer, "saved": save}
            if save:
                st.success("공문과 PDF를 저장했습니다. 발신 공문함에서도 다시 받을 수 있습니다.")
        except ValueError as exc:
            st.error(str(exc))
        except subprocess.TimeoutExpired:
            st.error("PDF 생성 시간이 초과됐습니다. 입력 내용을 줄이거나 다시 시도해 주세요.")
        except Exception:
            st.error("PDF 생성·저장에 실패했습니다. 변환 도구 준비 상태, 문서번호 중복 또는 저장소 연결을 확인해 주세요.")
    result = st.session_state.get("notice_preview")
    if result:
        st.caption(("저장된 공문" if result["saved"] else "마지막 생성 미리보기") + " · " + result.get("customer_name", "") + " · " + result["number"])
        a, b = st.columns(2)
        a.download_button("PDF 다운로드", result["pdf"], safe_filename(result["number"]) + ".pdf", MIMES[".pdf"])
        b.download_button("Word 다운로드", result["docx"], safe_filename(result["number"]) + ".docx", MIMES[".docx"])
        preview_pdf(result["pdf"])


def incoming_form(db, store, records, data, owners):
    code, customer, owner = customer_inputs(data, owners, "notice_in")
    with st.form("notice_incoming_form"):
        title = st.text_input("수신 공문 제목", max_chars=180)
        a, b = st.columns(2)
        received_date = a.date_input("수신일", value=datetime.now(ZoneInfo("Asia/Seoul")).date())
        effective_date = b.text_input("적용일(선택)", placeholder="예: 2026-12-01", max_chars=30)
        a, b = st.columns(2)
        contact = a.text_input("관리 담당자", value=owner if not owner.startswith("미지정") else "", max_chars=40)
        product = b.text_input("관련 품목·품번", max_chars=200)
        memo = st.text_area("의견·설명", max_chars=2000)
        upload = st.file_uploader("수신 공문 원본 · 10MB 이하", type=["pdf", "docx", "png", "jpg", "jpeg"])
        allow_duplicate = st.checkbox("같은 파일이 있어도 별도 공문으로 등록")
        save = st.form_submit_button("수신 공문 저장", type="primary")
    if save:
        try:
            if not customer or not title.strip() or not upload:
                raise ValueError("거래처명·제목·수신 공문 파일을 입력해 주세요.")
            raw, ext = clean_upload(upload)
            digest = hashlib.sha256(raw).hexdigest()
            if any(r.get("file_sha256") == digest for r in records) and not allow_duplicate:
                raise ValueError("이미 등록된 동일 파일이 있습니다. 기존 공문을 확인해 주세요.")
            ident = str(uuid.uuid4())
            path = "incoming/" + ident + ext
            item = {"id": ident, "kind": "incoming", "title": title.strip(), "customer_code": code,
                    "customer_name": customer, "owner": contact, "received_date": received_date.isoformat(),
                    "effective_at": effective_date.strip(), "product": product, "memo": memo,
                    "file_path": path, "file_name": upload.name, "mime": MIMES[ext],
                    "file_sha256": digest, "created_at": now_text()}
            store.upload(path, raw, {"content-type": MIMES[ext], "upsert": "false"})
            try:
                save_metadata(db, item)
            except Exception:
                try:
                    store.remove([path])
                except Exception:
                    pass
                raise
            records.insert(0, item)
            st.success("수신 공문을 저장했습니다. 아래 목록에서 확인하세요.")
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("수신 공문을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.")


def archive_list(store, records, kind):
    subset = [r for r in records if r["kind"] == kind]
    query = st.text_input("거래처·제목·품목·담당자 검색", key="notice_search_" + kind)
    if query:
        subset = [r for r in subset if query.casefold() in " ".join(str(r.get(k, "")) for k in ["customer_code", "customer_name", "title", "product", "owner", "number"]).casefold()]
    st.caption(f"등록 공문 {len(subset):,}건")
    if not subset:
        st.info("등록된 공문이 없습니다.")
        return
    if kind == "outgoing":
        labels = [{"문서번호": r.get("number", ""), "거래처": r.get("customer_name", ""), "제목": r["title"], "담당자": r.get("owner", ""), "시행일": r.get("effective_at", "")[:10], "작성일": r.get("created_at", "")[:10]} for r in subset]
    else:
        labels = [{"수신일": r.get("received_date", ""), "거래처": r.get("customer_name", ""), "제목": r["title"], "관련 품목": r.get("product", ""), "담당자": r.get("owner", ""), "적용일": r.get("effective_at", "")} for r in subset]
    st.dataframe(pd.DataFrame(labels), use_container_width=True, hide_index=True)
    selected = st.selectbox("열람할 공문", range(len(subset)), format_func=lambda i: f"{subset[i].get('customer_name', '')} · {subset[i]['title']} · {subset[i].get('number', subset[i].get('received_date', ''))}", key="notice_selected_" + kind)
    item = subset[selected]
    st.write("**거래처:** " + item.get("customer_name", "") + " · **담당자:** " + item.get("owner", ""))
    if kind == "incoming" and item.get("memo"):
        st.text(item["memo"])
    if st.button("원본 열기 · 다운로드 준비", key="notice_open_" + kind):
        try:
            if kind == "outgoing":
                raw = store.download(item["pdf_path"])
                docx = store.download(item["docx_path"])
                st.session_state["notice_opened_" + kind] = {"id": item["id"], "raw": raw, "docx": docx}
            else:
                st.session_state["notice_opened_" + kind] = {"id": item["id"], "raw": store.download(item["file_path"])}
        except Exception:
            st.error("공문 파일을 불러오지 못했습니다.")
    opened = st.session_state.get("notice_opened_" + kind)
    if opened and opened["id"] == item["id"]:
        raw = opened["raw"]
        if kind == "outgoing":
            st.download_button("PDF 다운로드", raw, safe_filename(item["number"]) + ".pdf", MIMES[".pdf"], key="archive_pdf")
            st.download_button("Word 다운로드", opened["docx"], safe_filename(item["number"]) + ".docx", MIMES[".docx"], key="archive_docx")
            preview_pdf(raw)
        else:
            st.download_button("수신 공문 다운로드", raw, safe_filename(item["file_name"]), item["mime"], key="archive_incoming")
            if item["mime"] == MIMES[".pdf"]:
                preview_pdf(raw)
            elif item["mime"].startswith("image/"):
                st.image(raw, use_container_width=True)


def render_notice_workspace(db, owners):
    st.subheader("공문 관리")
    if st.button("공문 목록 새로 고침", key="refresh_notices"):
        st.rerun()
    try:
        store = storage(db)
        records = documents(db)
        entries = store.list("templates", {"limit": 20})
        exists = any(x.get("name") == "price_notice.docx" for x in entries)
        template = store.download(TEMPLATE_PATH) if exists else None
    except Exception:
        st.error("비공개 공문 저장소에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return
    # 공개 저장소에는 양식·로고·직인을 포함하지 않습니다.
    if not template:
        with st.expander("기준 공문 양식 최초 등록", expanded=True):
            upload = st.file_uploader("기준 공문 DOCX 양식", type=["docx"], key="notice_template_upload")
            if upload and st.button("기준 양식 저장", key="save_notice_template"):
                try:
                    raw = upload.getvalue()
                    template_defaults(raw)
                    store.upload(TEMPLATE_PATH, raw, {"content-type": MIMES[".docx"], "upsert": "false"})
                    st.success("기준 양식을 비공개 저장했습니다.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("기준 양식을 저장하지 못했습니다. 다시 시도해 주세요.")
    try:
        batch_rows = db.table("inspection_batches").select("id,title,created_at").order("created_at", desc=True).limit(200).execute().data
        batch_rows = [r for r in batch_rows if r["title"] != ANCHOR]
        data = pd.DataFrame()
        if batch_rows:
            saved = db.table("inspection_batches").select("results").eq("id", batch_rows[0]["id"]).single().execute().data
            data = pd.DataFrame(saved["results"])
    except Exception:
        data = pd.DataFrame()
    tabs = st.tabs(["공문 작성", "발신 공문함", "수신 공문함"])
    with tabs[0]:
        if template:
            outgoing_form(db, store, template, records, data, owners)
        else:
            st.info("기준 양식 등록 후 공문을 작성할 수 있습니다.")
    with tabs[1]:
        archive_list(store, records, "outgoing")
    with tabs[2]:
        incoming_form(db, store, records, data, owners)
        st.divider()
        archive_list(store, records, "incoming")
