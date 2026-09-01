import csv
import json
import io
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

class ExportService:
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
        if format_type == "csv":
            content = cls.generate_csv(data_list, fieldnames)
            media_type = "text/csv"
            filename = f"{filename}.csv"
        elif format_type == "json":
            content = cls.generate_json(data_list, fieldnames)
            media_type = "application/json"
            filename = f"{filename}.json"
        elif format_type == "xlsx":
            content = cls.generate_excel(data_list, fieldnames)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{filename}.xlsx"
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format.")
            
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

