import io
import re
import os
import sys
import json
import time
import argparse
import subprocess
import multiprocessing as mp
from PIL import Image
import pymupdf
import Vision, Quartz
from Foundation import NSData
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


CYRILLIC_TO_LATIN = {
    'Х': 'X', 'х': 'x',
    'Р': 'P', 'р': 'p',
    'Н': 'H', 'н': 'h',
    'А': 'A', 'а': 'a',
    'В': 'B', 'в': 'b',
    'Е': 'E', 'е': 'e',
    'К': 'K', 'к': 'k',
    'М': 'M', 'м': 'm',
    'О': 'O', 'о': 'o',
    'С': 'C', 'с': 'c',
    'Т': 'T', 'т': 't'
}

def normalize_text(text):
    for cyr, lat in CYRILLIC_TO_LATIN.items():
        text = text.replace(cyr, lat)
    return text

def run_vision_ocr(image_bytes):
    ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(ns_data, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(False)
    handler.performRequests_error_([req], None)
    
    results = []
    if req.results():
        for obs in req.results():
            results.append(obs.topCandidates_(1)[0].string())
    return results

def parse_single_pdf(pdf_path):
    """Parses all voters from a single electoral roll PDF with persistent cache."""
    cache_dir = os.path.join(os.path.dirname(pdf_path), ".cache")
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    cache_file = os.path.join(cache_dir, f"{base_name}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            if isinstance(cached_data, list) and len(cached_data) > 0:
                return cached_data
        except Exception:
            pass

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return []

        
    total_pages = len(doc)
    if total_pages < 3:
        return []

    # 1. Parse Metadata & Sections from Page 1
    page1 = doc[0]
    pix1 = page1.get_pixmap(dpi=150)
    buf1 = io.BytesIO()
    Image.frombytes('RGB', [pix1.width, pix1.height], pix1.samples).save(buf1, format='PNG')
    p1_texts = run_vision_ocr(buf1.getvalue())
    p1_raw = ' \n '.join([normalize_text(t) for t in p1_texts])
    
    # Defaults
    part_no = None
    m_part = re.search(r'Part\s*No\.?\s*:\s*(\d+)', p1_raw, re.I)
    if m_part:
        part_no = int(m_part.group(1))
    else:
        # Fallback to filename
        m_fn = re.search(r'-ENG-(\d+)-WI\.pdf', os.path.basename(pdf_path))
        if m_fn:
            part_no = int(m_fn.group(1))
            
    ac_name = ""
    m_ac = re.search(r'Assembly Constituency[^\n:]*:\s*([^\n]+)', p1_raw, re.I)
    if m_ac:
        ac_name = m_ac.group(1).split('\n')[0].strip()

    pc_name = ""
    m_pc = re.search(r'Parliamentary Constituency[^\n:]*:\s*([^\n]+)', p1_raw, re.I)
    if m_pc:
        pc_name = m_pc.group(1).split('\n')[0].strip()
        
    ward = ""
    m_ward = re.search(r'Ward\s*:\s*([^\n]+)', p1_raw, re.I)
    if m_ward:
        ward = m_ward.group(1).strip()
        
    post_office = ""
    m_po = re.search(r'Post\s*Office\s*:\s*([^\n]+)', p1_raw, re.I)
    if m_po:
        post_office = m_po.group(1).strip()
        
    police_station = ""
    m_ps = re.search(r'Police\s*Station\s*:\s*([^\n]+)', p1_raw, re.I)
    if m_ps:
        police_station = m_ps.group(1).strip()
        
    pincode = ""
    m_pin = re.search(r'Pin\s*code\s*:\s*(\d{6})', p1_raw, re.I)
    if m_pin:
        pincode = m_pin.group(1).strip()
        
    town_village = "BANGALORE"
    m_town = re.search(r'Main\s*Town\s*or\s*Village\s*:\s*([^\n]+)', p1_raw, re.I)
    if m_town:
        town_village = m_town.group(1).strip()
        
    ps_name = f"Part {part_no}"
    m_psn = re.search(r'No\.\s*and\s*Name\s*of\s*Polling\s*Station\s*:\s*([^\n]+)', p1_raw, re.I)
    if m_psn:
        ps_name = m_psn.group(1).strip()

    # Section numbers & names map
    sections_map = {}
    sec_matches = re.findall(r'(\d+)\s*-\s*([^\n]+Layout[^\n]*|[^\n]+Road[^\n]*|[^\n]+Street[^\n]*|[^\n]+Cross[^\n]*|[^\n]+Colony[^\n]*|[^\n]+Nagar[^\n]*|[^\n]+Block[^\n]*|[^\n]+Main[^\n]*)', p1_raw, re.I)
    for s_num, s_name in sec_matches:
        sections_map[int(s_num)] = s_name.strip().rstrip('-')

    row_bounds = [
        (0.032, 0.125), (0.125, 0.218), (0.218, 0.312), (0.312, 0.406), (0.406, 0.500),
        (0.500, 0.594), (0.594, 0.688), (0.688, 0.781), (0.781, 0.875), (0.875, 0.965)
    ]
    col_bounds = [(0.02, 0.33), (0.33, 0.66), (0.66, 0.98)]
    epic_pattern = re.compile(r'\b([A-Z]{2,4}\s?[0-9]{6,8})\b')

    voters = []
    current_serial = 1
    current_section = 1

    for p_idx in range(2, total_pages - 1):
        page_num = p_idx + 1
        page = doc[p_idx]
        pix = page.get_pixmap(dpi=150)
        im = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        w, h = im.size

        # Check header section for page
        clip_header = im.crop((0, 0, w, int(0.04 * h)))
        buf_h = io.BytesIO()
        clip_header.save(buf_h, format='PNG')
        header_texts = run_vision_ocr(buf_h.getvalue())
        header_str = ' '.join(header_texts).lower()

        # Update section if present in header
        m_sec = re.search(r'section\s*no\s*(?:and|&)?\s*name\s*[:\s]*(\d+)\s*-?\s*([^\n]+)', header_str)
        if m_sec:
            current_section = int(m_sec.group(1))
            sec_header_val = m_sec.group(2).strip().rstrip('-')
            if sec_header_val and current_section not in sections_map:
                sections_map[current_section] = sec_header_val
        else:
            m_sec_num = re.search(r'section\s*no\s*and\s*name\s*(\d+)', header_str)
            if m_sec_num:
                current_section = int(m_sec_num.group(1))

        for r_idx, (r_min, r_max) in enumerate(row_bounds):
            for c_idx, (c_min, c_max) in enumerate(col_bounds):
                crop = im.crop((int(c_min * w), int(r_min * h), int(c_max * w), int(r_max * h)))
                buf = io.BytesIO()
                crop.save(buf, format='PNG')
                raw_texts = run_vision_ocr(buf.getvalue())
                texts = [normalize_text(t) for t in raw_texts]

                has_name = any('name' in t.lower() for t in texts)
                has_age = any('age' in t.lower() for t in texts)
                has_epic = any(epic_pattern.search(t) for t in texts)

                if not (has_name or has_age or has_epic):
                    continue

                epic_no = ''
                name = ''
                relation_type = ''
                relation_name = ''
                house_no = ''
                age = None
                gender = ''
                all_candidate_numbers = []
                card_section = current_section

                for t in texts:
                    t_str = t.strip()

                    m_epic = epic_pattern.search(t_str)
                    if m_epic and not epic_no:
                        epic_no = m_epic.group(1).replace(' ', '')

                    m_name = re.search(r'\bName\s*[:\u2022\.\-]?\s*(.*)', t_str, re.I)
                    if m_name and not any(k in t_str.lower() for k in ['father', 'husband', 'mother', 'other']):
                        cand_name = m_name.group(1).strip()
                        if cand_name and not any(cand_name.startswith(p) for p in ['#', '$']):
                            name = cand_name

                    m_rel = re.search(r'(Father[\'s\s]*Name|Husband[\'s\s]*Name|Mother[\'s\s]*Name|Other[s\s]*(?:Name)?)\s*[:\u2022\.\-]?\s*(.*)', t_str, re.I)
                    if m_rel:
                        label = m_rel.group(1).lower()
                        if 'father' in label:
                            relation_type = 'Father'
                        elif 'husband' in label:
                            relation_type = 'Husband'
                        elif 'mother' in label:
                            relation_type = 'Mother'
                        else:
                            relation_type = 'Other'
                        relation_name = m_rel.group(2).strip()

                    m_house = re.search(r'House\s*Number\s*[:\$\u2022\.\-]?\s*(.*)', t_str, re.I)
                    if m_house:
                        house_no = m_house.group(1).strip()

                    m_age = re.search(r'Age\s*[:\u2022\.\-]?\s*(\d+)', t_str, re.I)
                    if m_age:
                        age = int(m_age.group(1))

                    m_gen = re.search(r'Gender\s*[:\u2022\.\-]?\s*([A-Za-z]+)', t_str, re.I)
                    if m_gen:
                        gender = m_gen.group(1).capitalize()

                    if re.fullmatch(r'#?\s*(\d{1,4})', t_str):
                        val = int(re.sub(r'\D', '', t_str))
                        if 1 <= val <= 1000:
                            all_candidate_numbers.append(val)

                detected_serial = None
                if len(all_candidate_numbers) == 1:
                    detected_serial = all_candidate_numbers[0]
                elif len(all_candidate_numbers) > 1:
                    sorted_by_prox = sorted(all_candidate_numbers, key=lambda n: abs(n - current_serial))
                    detected_serial = sorted_by_prox[0]
                    for other in sorted_by_prox[1:]:
                        if other in [1, 2, 3] and detected_serial > 10:
                            card_section = other
                            break

                final_serial = detected_serial if detected_serial is not None else current_serial
                if detected_serial is not None:
                    current_serial = detected_serial + 1
                else:
                    current_serial += 1

                sec_name = sections_map.get(card_section, f'Section {card_section}')
                clean_house = house_no.strip().lstrip('#').strip().lstrip('$').strip()

                addr_parts = []
                if clean_house:
                    addr_parts.append(f"No. {clean_house}")
                if sec_name:
                    addr_parts.append(sec_name)
                addr_parts.append(ward)
                addr_parts.append(post_office)
                addr_parts.append(f"{town_village} - {pincode}")
                addr_parts.append("Karnataka")
                full_address = ", ".join(addr_parts)

                photo_status = 'Available' if any('available' in t.lower() for t in texts) else 'Not Available'

                voters.append({
                    'Part No': part_no,
                    'Serial No': final_serial,
                    'Voter ID (EPIC)': epic_no,
                    'Voter Name': name,
                    'Relation Type': relation_type,
                    'Relation Name': relation_name,
                    'House No': clean_house,
                    'Full Address': full_address,
                    'Section No': card_section,
                    'Section / Street Name': sec_name,
                    'Ward / Locality': ward,
                    'City / Town': town_village,
                    'Post Office': post_office,
                    'Police Station': police_station,
                    'Pin Code': pincode,
                    'Age': age,
                    'Gender': gender,
                    'Photo Status': photo_status,
                    'Polling Station': ps_name,
                    'Assembly Constituency': ac_name,
                    'Parliamentary Constituency': pc_name,
                    'Source File': os.path.basename(pdf_path),
                    'PDF Page': page_num
                })

    print(f"  [Done] {os.path.basename(pdf_path)}: Extracted {len(voters)} voters")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(voters, f, ensure_ascii=False)
    except Exception:
        pass

    return voters

def process_constituency(constituency_folder_path, rclone_remote="gdrive:", root_folder_id="1mWKMVs2ibWWZG0bCO3QwK0yZtYGabZh5", workers=4, max_files=None, upload_after=True):
    """Downloads all PDFs in a constituency folder, processes them in parallel, 
    creates a single Master Excel file, and uploads it to the Drive folder."""
    
    clean_name = constituency_folder_path.strip('/').split('/')[-1]
    print(f"\n=======================================================")
    print(f" Processing Constituency: {clean_name}")
    print(f" Path: {constituency_folder_path}")
    print(f"=======================================================")
    
    # 1. List files in the Drive folder
    list_cmd = ['rclone', 'lsf', f"{rclone_remote}{constituency_folder_path}", '--files-only', '--include', '*.pdf']
    if root_folder_id:
        list_cmd.extend(['--drive-root-folder-id', root_folder_id])
    proc = subprocess.run(list_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Error listing files via rclone: {proc.stderr}")
        return
        
    pdf_files = [f.strip() for f in proc.stdout.splitlines() if f.strip().lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDFs in Drive folder.")
    if max_files:
        pdf_files = pdf_files[:max_files]
        print(f"Limited to first {max_files} PDFs as requested.")

    # Sort numerically by part number
    def part_key(fname):
        m = re.search(r'-ENG-(\d+)-WI\.pdf', fname)
        return int(m.group(1)) if m else 999999
    pdf_files = sorted(pdf_files, key=part_key)

    # 2. Local working directories
    local_dir = os.path.join(BASE_DIR, "downloads", clean_name)
    os.makedirs(local_dir, exist_ok=True)
    
    print(f"Downloading PDFs to local cache: {local_dir}...")
    if max_files:
        list_file = os.path.join(local_dir, "to_download.txt")
        with open(list_file, 'w') as f:
            f.write('\n'.join(pdf_files))
        dl_cmd = ['rclone', 'copy', f"{rclone_remote}{constituency_folder_path}", local_dir, '--files-from-raw', list_file]
    else:
        dl_cmd = ['rclone', 'copy', f"{rclone_remote}{constituency_folder_path}", local_dir, '--include', '*.pdf']
        
    if root_folder_id:
        dl_cmd.extend(['--drive-root-folder-id', root_folder_id])
    subprocess.run(dl_cmd)

    local_pdf_paths = [os.path.join(local_dir, f) for f in pdf_files if os.path.exists(os.path.join(local_dir, f))]
    print(f"Downloaded {len(local_pdf_paths)} PDFs locally. Starting parallel extraction with {workers} workers...")

    # 3. Parallel Extraction
    t0 = time.time()
    mp.set_start_method('spawn', force=True)
    all_voters = []
    completed_files = 0
    total_files = len(local_pdf_paths)
    
    with mp.Pool(workers) as pool:
        for v_list in pool.imap_unordered(parse_single_pdf, local_pdf_paths):
            completed_files += 1
            all_voters.extend(v_list)
            now_elapsed = time.time() - t0
            avg_per_file = now_elapsed / completed_files
            remaining_sec = avg_per_file * (total_files - completed_files)
            print(f"[{completed_files}/{total_files}] parts done | {len(all_voters)} total voters | ETA: {remaining_sec/60:.1f} mins", flush=True)

    elapsed = time.time() - t0
    print(f"\nExtracted total of {len(all_voters)} voters across {total_files} parts in {elapsed/60:.2f} minutes!", flush=True)

    # 4. Generate Master Excel File
    master_excel_filename = f"{clean_name}_Master_Electoral_Roll.xlsx"
    master_excel_path = os.path.join(BASE_DIR, master_excel_filename)
    
    print(f"Compiling Master Excel file: {master_excel_filename}...")
    df = pd.DataFrame(all_voters)
    if not df.empty:
        df['Part No'] = pd.to_numeric(df['Part No'], errors='coerce')
        df['Serial No'] = pd.to_numeric(df['Serial No'], errors='coerce')
        df = df.sort_values(by=['Part No', 'Serial No']).reset_index(drop=True)

    with pd.ExcelWriter(master_excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f'{clean_name} All Voters', index=False)
        wb = writer.book
        ws = writer.sheets[f'{clean_name} All Voters']
        
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border_thin = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )
        
        for col_idx in range(1, len(df.columns) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col[:100]) # sample first 100 for speed
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)
            
        ws.row_dimensions[1].height = 28
        ws.freeze_panes = 'D2'

    print(f"Created {master_excel_path} ({os.path.getsize(master_excel_path)/(1024*1024):.2f} MB)")

    # 5. Upload Master Excel directly to the Google Drive folder
    if upload_after:
        print(f"Uploading {master_excel_filename} to Google Drive: {constituency_folder_path}...")
        up_cmd = ['rclone', 'copy', master_excel_path, f"{rclone_remote}{constituency_folder_path}", '-v']
        if root_folder_id:
            up_cmd.extend(['--drive-root-folder-id', root_folder_id])
        up_proc = subprocess.run(up_cmd, capture_output=True, text=True)
        if up_proc.returncode == 0:
            print(f" Successfully uploaded {master_excel_filename} into {constituency_folder_path} on Google Drive!")
        else:
            print(f"Upload failed: {up_proc.stderr}")

    return master_excel_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automate Master Electoral Roll Excel generation per constituency folder")
    parser.add_argument('--constituency', type=str, default="BBMP South/Basavanagudi", help="Constituency folder path in Google Drive (e.g. 'BBMP South/Basavanagudi')")
    parser.add_argument('--root-id', type=str, default="1mWKMVs2ibWWZG0bCO3QwK0yZtYGabZh5", help="Google Drive Root Folder ID")
    parser.add_argument('--workers', type=int, default=4, help="Number of parallel OCR worker processes (default: 4)")
    parser.add_argument('--limit', type=int, default=None, help="Limit number of PDFs to process for testing")
    parser.add_argument('--no-upload', action='store_true', help="Skip uploading to Google Drive")
    args = parser.parse_args()

    process_constituency(args.constituency, root_folder_id=args.root_id, workers=args.workers, max_files=args.limit, upload_after=not args.no_upload)
