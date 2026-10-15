import csv
import json
import io
import re
from typing import List, Dict, Any, Optional
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

class ExportService:
    @staticmethod
    def sanitize_filename_part(part: Optional[str]) -> str:
        r"""
        Sanitize a string for safe inclusion in a download filename:
        - Replaces whitespace with underscores
        - Strips any characters outside [a-zA-Z0-9_\-\.]
        - Deduplicates underscores
        """
        if not part:
            return ""
        s = re.sub(r'\s+', '_', str(part).strip())
        s = re.sub(r'[^a-zA-Z0-9_\-\.]', '', s)
        s = re.sub(r'_+', '_', s)
        return s.strip('_')

    @classmethod
    def build_safe_filename(
        cls,
        student_id: Optional[str] = None,
        course_name: Optional[str] = None,
        dataset_name: str = "Dataset",
        format_type: str = "csv"
    ) -> str:
        """
        Construct standard sanitized dataset filename:
        Format: {StudentID}_{CourseName}_{DatasetName}.{ext}
        or {StudentID}_{DatasetName}.{ext}
        or {CourseName}_{DatasetName}.{ext}
        """
        NAME_MAP = {
            "interaction_telemetry": "Interaction_Telemetry",
            "interactions": "Interaction_Telemetry",
            "telemetry": "Interaction_Telemetry",
            "concept_event_mapping": "Concept_Event_Mapping",
            "concept-mappings": "Concept_Event_Mapping",
            "mappings": "Concept_Event_Mapping",
            "mapping": "Concept_Event_Mapping",
            "difficulty": "Difficulty",
            "transcripts": "Course_Transcripts",
            "course_transcripts": "Course_Transcripts",
            "concepts": "Concept_Segments",
            "concept_segments": "Concept_Segments"
        }
        clean_ds = NAME_MAP.get(dataset_name.strip().lower(), cls.sanitize_filename_part(dataset_name) or "Dataset")
        parts = []
        if student_id:
            s_id = cls.sanitize_filename_part(student_id)
            if s_id:
                parts.append(s_id)
        if course_name:
            c_name = cls.sanitize_filename_part(course_name)
            if c_name:
                parts.append(c_name)
        parts.append(clean_ds)

        base_name = "_".join(parts) if parts else "CogniTrace_Dataset"
        ext = format_type.lower().strip('.')
        return f"{base_name}.{ext}"

    @staticmethod
    def generate_csv(data: List[Dict[str, Any]], fieldnames: List[str]) -> bytes:
        """
        Generate CSV bytes from a list of dictionaries.
        Ensures Unicode characters, commas, and newlines are safely escaped.
        """
        if not data:
            # Return just the header if empty
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            return output.getvalue().encode('utf-8')
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore', quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        
        for row in data:
            # Ensure safe text (prevent formulas starting with =, +, -, @ just to be safe, though mainly for Excel)
            safe_row = {}
            for k in fieldnames:
                val = row.get(k, "")
                # Convert None to empty string
                if val is None:
                    val = ""
                safe_row[k] = val
            writer.writerow(safe_row)
            
        return output.getvalue().encode('utf-8')

    @staticmethod
    def generate_json(data: List[Dict[str, Any]], fieldnames: List[str]) -> bytes:
        """
        Generate JSON bytes from a list of dictionaries.
        Only exports explicitly allowed fieldnames.
        """
        filtered_data = []
        for row in data:
            filtered_row = {k: row.get(k) for k in fieldnames}
            filtered_data.append(filtered_row)
            
        return json.dumps(filtered_data, ensure_ascii=False, indent=2).encode('utf-8')

    @staticmethod
    def generate_excel(data: List[Dict[str, Any]], fieldnames: List[str]) -> bytes:
        """
        Generate Excel (.xlsx) bytes from a list of dictionaries.
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "Dataset"
        
        # Write headers
        for col_idx, header in enumerate(fieldnames, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            
        # Write rows
        for row_idx, row in enumerate(data, start=2):
            for col_idx, key in enumerate(fieldnames, start=1):
                val = row.get(key)
                
                # Excel safety for string formula execution prevention
                if isinstance(val, str) and val.startswith(('=', '+', '-', '@')):
                    val = f"'{val}"
                    
                ws.cell(row=row_idx, column=col_idx, value=val)
                
        # Auto-adjust column widths for better readability
        for col_idx in range(1, len(fieldnames) + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 20

        # Save to bytes buffer
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @classmethod
    def get_export_response(cls, data_list: list, fieldnames: list, filename: str, format_type: str):
        from fastapi import Response, HTTPException
        fmt = format_type.lower().strip('.')
        if fmt == "csv":
            content = cls.generate_csv(data_list, fieldnames)
            media_type = "text/csv"
        elif fmt == "json":
            content = cls.generate_json(data_list, fieldnames)
            media_type = "application/json"
        elif fmt == "xlsx":
            content = cls.generate_excel(data_list, fieldnames)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format.")

        full_filename = filename if filename.endswith(f".{fmt}") else f"{filename}.{fmt}"

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{full_filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

