import io
import re
import time
import os
from PIL import Image
import pymupdf
import Vision, Quartz
from Foundation import NSData
import pandas as pd

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

def extract_roll(pdf_path, output_excel_path):
    print(f"Opening {pdf_path}...")
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")
    
    metadata = {
        'state': 'Karnataka',
        'ac_no_name': '170 - BASAVANAGUDI (GEN)',
        'pc_no_name': '26 - BANGALORE SOUTH (GEN)',
        'part_no': 1,
        'town_village': 'BANGALORE',
        'ward': 'SRINAGAR',
        'post_office': 'BANASHANKARI 1ST STAGE',
        'police_station': 'HANUMANTHANAGARA',
        'pincode': '560050',
        'ps_name': '1 - BBMP Samudaya Bhavana,Room No. 1',
        'ps_address': 'B B MP Samudaya Bhavana, Kalidasa Circle, Srinagar, Bengaluru'
    }
    
    sections_map = {
        1: '1st Cross, 1st main, Kalidas Layout',
        2: '2nd A Cross Kalidas Layout',
        3: '3rd Cross Kalidas Layout'
    }
    
    # Grid coordinates for voter cards (10 rows x 3 columns)
    row_bounds = [
        (0.032, 0.125), (0.125, 0.218), (0.218, 0.312), (0.312, 0.406), (0.406, 0.500),
        (0.500, 0.594), (0.594, 0.688), (0.688, 0.781), (0.781, 0.875), (0.875, 0.965)
    ]
    col_bounds = [(0.02, 0.33), (0.33, 0.66), (0.66, 0.98)]
    
    epic_pattern = re.compile(r'\b([A-Z]{2,4}\s?[0-9]{6,8})\b')
    
    voters = []
    current_serial = 1
    current_section = 1
    
    start_time = time.time()
    
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
        
        if '1-1st cross' in header_str or 'section no and name 1' in header_str:
            current_section = 1
        elif '2-2nd a cross' in header_str or 'section no and name 2' in header_str:
            current_section = 2
        elif '3-3rd cross' in header_str or 'section no and name 3' in header_str:
            current_section = 3
            
        page_voters_count = 0
        
        for r_idx, (r_min, r_max) in enumerate(row_bounds):
            for c_idx, (c_min, c_max) in enumerate(col_bounds):
                crop = im.crop((int(c_min * w), int(r_min * h), int(c_max * w), int(r_max * h)))
                buf = io.BytesIO()
                crop.save(buf, format='PNG')
                raw_texts = run_vision_ocr(buf.getvalue())
                texts = [normalize_text(t) for t in raw_texts]
                
                # Check if this cell is a valid voter card
                has_name = any('name' in t.lower() for t in texts)
                has_age = any('age' in t.lower() for t in texts)
                has_epic = any(epic_pattern.search(t) for t in texts)
                
                if not (has_name or has_age or has_epic):
                    continue
                
                # Parse voter card fields
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
                    
                    # EPIC
                    m_epic = epic_pattern.search(t_str)
                    if m_epic and not epic_no:
                        epic_no = m_epic.group(1).replace(' ', '')
                        
                    # Name
                    m_name = re.search(r'\bName\s*[:\u2022\.\-]?\s*(.*)', t_str, re.I)
                    if m_name and not any(k in t_str.lower() for k in ['father', 'husband', 'mother', 'other']):
                        cand_name = m_name.group(1).strip()
                        if cand_name and not any(cand_name.startswith(p) for p in ['#', '$']):
                            name = cand_name
                        
                    # Relation
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
                        
                    # House Number
                    m_house = re.search(r'House\s*Number\s*[:\$\u2022\.\-]?\s*(.*)', t_str, re.I)
                    if m_house:
                        house_no = m_house.group(1).strip()
                        
                    # Age & Gender
                    m_age = re.search(r'Age\s*[:\u2022\.\-]?\s*(\d+)', t_str, re.I)
                    if m_age:
                        age = int(m_age.group(1))
                        
                    m_gen = re.search(r'Gender\s*[:\u2022\.\-]?\s*([A-Za-z]+)', t_str, re.I)
                    if m_gen:
                        gender = m_gen.group(1).capitalize()
                        
                    # Collect candidate integer numbers
                    if re.fullmatch(r'#?\s*(\d{1,4})', t_str):
                        val = int(re.sub(r'\D', '', t_str))
                        if 1 <= val <= 1000:
                            all_candidate_numbers.append(val)
                
                # Resolve serial number and section number
                detected_serial = None
                if len(all_candidate_numbers) == 1:
                    detected_serial = all_candidate_numbers[0]
                elif len(all_candidate_numbers) > 1:
                    # Sort by proximity to current expected serial
                    sorted_by_prox = sorted(all_candidate_numbers, key=lambda n: abs(n - current_serial))
                    detected_serial = sorted_by_prox[0]
                    # If any other number is in [1, 2, 3] and detected_serial > 10, it represents section
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
                
                # Clean house number
                clean_house = house_no.strip().lstrip('#').strip().lstrip('$').strip()
                
                # Full Address formatting
                addr_parts = []
                if clean_house:
                    addr_parts.append(f"No. {clean_house}")
                if sec_name:
                    addr_parts.append(sec_name)
                addr_parts.append(metadata['ward'])
                addr_parts.append(metadata['post_office'])
                addr_parts.append(f"{metadata['town_village']} - {metadata['pincode']}")
                addr_parts.append(metadata['state'])
                full_address = ", ".join(addr_parts)
                
                photo_status = 'Available' if any('available' in t.lower() for t in texts) else 'Not Available'
                
                voters.append({
                    'Serial No': final_serial,
                    'Voter ID (EPIC)': epic_no,
                    'Voter Name': name,
                    'Relation Type': relation_type,
                    'Relation Name': relation_name,
                    'House No': clean_house,
                    'Full Address': full_address,
                    'Section No': card_section,
                    'Section / Street Name': sec_name,
                    'Ward / Locality': metadata['ward'],
                    'City / Town': metadata['town_village'],
                    'Post Office': metadata['post_office'],
                    'Police Station': metadata['police_station'],
                    'Pin Code': metadata['pincode'],
                    'Age': age,
                    'Gender': gender,
                    'Photo Status': photo_status,
                    'Polling Station': metadata['ps_name'],
                    'Polling Station Address': metadata['ps_address'],
                    'Assembly Constituency': metadata['ac_no_name'],
                    'Parliamentary Constituency': metadata['pc_no_name'],
                    'Part No': metadata['part_no'],
                    'PDF Page': page_num
                })
                page_voters_count += 1
                
        print(f"Page {page_num}/{total_pages}: Extracted {page_voters_count} voters (Cumulative: {len(voters)})")
        
    elapsed = time.time() - start_time
    print(f"\nCompleted extraction of {len(voters)} voters in {elapsed:.1f}s")
    
    # Create DataFrame and Excel
    df = pd.DataFrame(voters)
    
    # Sort by Serial No
    df['Serial No'] = pd.to_numeric(df['Serial No'], errors='coerce')
    df = df.sort_values(by='Serial No').reset_index(drop=True)
    
    print(f"Writing to Excel: {output_excel_path}...")
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Electoral Roll Voters', index=False)
        
        # Style the Excel worksheet
        wb = writer.book
        ws = writer.sheets['Electoral Roll Voters']
        
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
            
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.border = border_thin
                cell.font = Font(name="Calibri", size=10)
                if cell.column_letter in ['A', 'H', 'N', 'O', 'P', 'U', 'V']:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(vertical="center")
                    
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)
            
        ws.row_dimensions[1].height = 28
        ws.freeze_panes = 'C2'
        
    print(f"Successfully created {output_excel_path}!")

if __name__ == '__main__':
    extract_roll('sample_roll.pdf', 'Basavanagudi_Part_1_Electoral_Roll.xlsx')
