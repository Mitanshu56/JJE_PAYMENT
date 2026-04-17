"""
Excel parsing utilities for label-based invoice extraction
"""
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class InvoiceParser:
    """
    Parser for label-based Excel invoices.
    Handles dynamic invoice block detection and field extraction.
    """
    
    # Define label patterns for field identification
    FIELD_PATTERNS = {
        'invoice_no': [r'invoice\s*no\.?', r'invoice\s*number', r'inv\s*no\.?', r'bill\s*no\.?'],
        'date': [r'invoice\s*date', r'date', r'dated'],
        'party_name': [r'party\s*name', r'vendor', r'supplier', r'buyer', r'billed\s*to'],
        'gst_no': [r'party\s*gst\s*no\.?', r'gst\s*no\.?', r'gstin', r'tax\s*id'],
        'net_amount': [r'net\s*amount', r'sub\s*total', r'subtotal'],
        'cgst': [r'cgst', r'central\s*gst'],
        'sgst': [r'sgst', r'state\s*gst'],
        'grand_total': [r'grand\s*total', r'total\s*amount', r'final\s*amount'],
        'site': [r'site', r'location', r'branch', r'project'],
    }

    # Fallback patterns for standard row/column invoice sheets
    TABLE_COLUMN_PATTERNS = {
        'invoice_no': [r'invoice\s*no', r'invoice\s*number', r'inv\s*no', r'bill\s*no'],
        'invoice_date': [r'invoice\s*date', r'bill\s*date', r'^date$', r'dated'],
        'party_name': [r'party\s*name', r'customer', r'vendor', r'supplier', r'buyer', r'client', r'name'],
        'gst_no': [r'party\s*gst\s*no', r'gst\s*no', r'gstin', r'tax\s*id'],
        'net_amount': [r'net\s*amount', r'taxable\s*amount', r'sub\s*total', r'subtotal', r'basic\s*amount'],
        'cgst': [r'^cgst$', r'central\s*gst'],
        'sgst': [r'^sgst$', r'state\s*gst'],
        'grand_total': [r'grand\s*total', r'total\s*amount', r'invoice\s*amount', r'^total$', r'^amount$'],
        'site': [r'site', r'location', r'branch', r'project'],
    }

    GSTIN_REGEX = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b', re.IGNORECASE)
    
    def __init__(self, file_path: str):
        """Initialize parser with file path"""
        self.file_path = file_path
        self.workbook = None
        self.invoices = []
    
    def parse(self) -> List[Dict]:
        """
        Parse invoices from Excel file.
        Detects multiple invoices per sheet or multiple sheets.
        
        Returns:
            List of extracted invoice dictionaries
        """
        try:
            # Read all sheets and close workbook handle immediately after parsing.
            all_invoices = []
            with pd.ExcelFile(self.file_path) as xls:
                for sheet_name in xls.sheet_names:
                    # Strategy 1: label-driven extraction from semi-structured sheets
                    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                    label_invoices = self._extract_invoices_from_sheet(df, sheet_name)

                    # Strategy 2: column/table extraction for standard invoice lists
                    table_df = pd.read_excel(xls, sheet_name=sheet_name)
                    table_invoices = self._extract_invoices_from_table(table_df, sheet_name)

                    # Merge both strategies to avoid missing invoices on mixed-format sheets.
                    sheet_invoices = self._merge_invoice_lists(label_invoices, table_invoices)
                    all_invoices.extend(sheet_invoices)
            
            logger.info(f"✓ Extracted {len(all_invoices)} invoices from {self.file_path}")
            self.invoices = all_invoices
            return all_invoices
            
        except Exception as e:
            logger.exception(f"✗ Error parsing Excel file: {str(e)}")
            raise

    def _merge_invoice_lists(self, primary: List[Dict], secondary: List[Dict]) -> List[Dict]:
        """Merge invoices from two extraction strategies by invoice number."""
        merged = {}

        for invoice in primary + secondary:
            inv_no = str(invoice.get('invoice_no') or '').strip()
            if not inv_no:
                continue

            if inv_no not in merged:
                merged[inv_no] = invoice
                continue

            # Keep richer invoice when duplicate invoice numbers are found.
            existing = merged[inv_no]
            if sum(v is not None and v != '' for v in invoice.values()) > sum(v is not None and v != '' for v in existing.values()):
                merged[inv_no] = invoice

        return list(merged.values())
    
    def _extract_invoices_from_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[Dict]:
        """
        Extract invoices from a single sheet.
        Handles multiple invoices per sheet by detecting invoice blocks.
        """
        # Strategy A: specialized block extraction for invoice forms like user's workbook.
        block_invoices = self._extract_block_invoices_from_sheet(df, sheet_name)
        if block_invoices:
            logger.info(f"Extracted {len(block_invoices)} block invoices from sheet: {sheet_name}")
            return block_invoices

        # Strategy B: generic label extraction (legacy behavior).
        invoices = []
        current_invoice = {}
        invoice_count = 0

        for idx, row in df.iterrows():
            row_data = [str(cell).strip() if pd.notna(cell) else "" for cell in row]
            row_text = " ".join(row_data).lower()

            # Detect invoice boundaries
            if self._is_invoice_start(row_text, idx):
                if current_invoice:
                    # Clean and validate previous invoice
                    cleaned = self._clean_invoice_data(current_invoice)
                    if self._is_valid_invoice(cleaned):
                        invoices.append(cleaned)
                        invoice_count += 1
                current_invoice = {'sheet': sheet_name, 'row_start': idx}

            # Extract field values
            if current_invoice is None:
                current_invoice = {'sheet': sheet_name, 'row_start': idx}

            for field_name in self.FIELD_PATTERNS:
                if field_name not in current_invoice:
                    value = self._extract_field_value(row_data, field_name)
                    if value is not None:
                        current_invoice[field_name] = value

        # Don't forget the last invoice
        if current_invoice and self._is_invoice_start("", 0):  # Check if we actually collected data
            cleaned = self._clean_invoice_data(current_invoice)
            if self._is_valid_invoice(cleaned):
                invoices.append(cleaned)
                invoice_count += 1

        logger.info(f"Extracted {invoice_count} invoices from sheet: {sheet_name}")
        return invoices

    def _extract_block_invoices_from_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[Dict]:
        """Extract invoice blocks where labels and values are separated by blank columns/rows."""
        rows = [[str(cell).strip() if pd.notna(cell) else "" for cell in row] for _, row in df.iterrows()]
        invoices = []
        current = None

        def finalize_current():
            if not current:
                return
            cleaned = self._clean_invoice_data(current)
            if self._is_valid_invoice(cleaned):
                invoices.append(cleaned)

        for idx, row_data in enumerate(rows):
            row_lower = [c.lower() for c in row_data]
            joined = " ".join(row_lower)

            # Start of new invoice block
            if 'invoice no' in joined or 'invoice number' in joined:
                finalize_current()
                current = {'sheet': sheet_name, 'row_start': idx}

                inv_no = self._extract_after_label_in_row(row_data, ['invoice no', 'invoice number'])
                if inv_no is None:
                    inv_no = self._extract_below_same_column(rows, idx, row_lower, ['invoice no', 'invoice number'])
                if inv_no is not None:
                    normalized_inv_no = self._normalize_field('invoice_no', inv_no)
                    # If the detected value is actually a date, use it as invoice_date instead.
                    if normalized_inv_no is not None:
                        current['invoice_no'] = normalized_inv_no
                    elif 'invoice_date' not in current:
                        current['invoice_date'] = inv_no

                inv_date = self._extract_after_label_in_row(row_data, ['date'])
                if inv_date is None:
                    inv_date = self._extract_below_same_column(rows, idx, row_lower, ['date'])
                if inv_date is not None:
                    current['invoice_date'] = inv_date

            if not current:
                continue

            # GST block labels like "Party GST No.:"
            gst_no = self._extract_after_label_in_row(row_data, ['party gst no', 'gst no', 'gstin', 'tax id'])
            if gst_no is None:
                gst_no = self._extract_gstin_from_row_text(row_data)
            if gst_no is None and any(token in joined for token in ['party gst', 'gst no', 'gstin']):
                gst_no = self._extract_gstin_from_nearby_rows(rows, idx, lookahead=4)
            if gst_no is not None:
                normalized_gst = self._normalize_field('gst_no', gst_no)
                if normalized_gst:
                    current['gst_no'] = normalized_gst

            # Party block
            if any(cell in ('to.', 'bill to') for cell in row_lower):
                party = self._extract_first_non_empty_below_in_col(rows, idx, 0)
                if party:
                    current['party_name'] = party

            # Site often appears as "Site: ..."
            for cell in row_data:
                if isinstance(cell, str) and 'site:' in cell.lower():
                    current['site'] = cell.split(':', 1)[1].strip() if ':' in cell else cell.strip()

            # Totals block labels
            net_amt = self._extract_after_label_in_row(row_data, ['net amt', 'net amount'])
            if net_amt is not None:
                self._update_numeric_field(current, 'net_amount', net_amt)

            cgst_amt = self._extract_after_label_in_row(row_data, ['cgst amt', 'cgst'])
            if cgst_amt is not None:
                self._update_numeric_field(current, 'cgst', cgst_amt)

            sgst_amt = self._extract_after_label_in_row(row_data, ['sgst amt', 'sgst'])
            if sgst_amt is not None:
                self._update_numeric_field(current, 'sgst', sgst_amt)

            grand_total = self._extract_after_label_in_row(row_data, ['g. total', 'grand total', 'invoice amount'])
            if grand_total is not None:
                self._update_numeric_field(current, 'grand_total', grand_total)

        finalize_current()
        return invoices

    def _extract_after_label_in_row(self, row_data: List[str], label_tokens: List[str]):
        """Find label in row and return first non-empty value to its right."""
        for i, cell in enumerate(row_data):
            cell_lower = str(cell).lower()
            if any(token in cell_lower for token in label_tokens):
                for j in range(i + 1, len(row_data)):
                    val = row_data[j]
                    if val not in ("", None):
                        return val
        return None

    def _extract_below_same_column(self, rows: List[List[str]], row_idx: int, row_lower: List[str], label_tokens: List[str]):
        """Find label column in current row and read first non-empty value below it."""
        for col_idx, cell in enumerate(row_lower):
            if any(token in cell for token in label_tokens):
                for next_row in range(row_idx + 1, min(row_idx + 4, len(rows))):
                    val = rows[next_row][col_idx] if col_idx < len(rows[next_row]) else ""
                    if val not in ("", None):
                        return val
        return None

    def _extract_first_non_empty_below_in_col(self, rows: List[List[str]], row_idx: int, col_idx: int):
        """Read first non-empty value below the given column, skipping helper labels."""
        skip_tokens = ('invoice', 'challan', 'order', 'gst', 'date', 'site', 'sr. no')
        for next_row in range(row_idx + 1, min(row_idx + 8, len(rows))):
            if col_idx >= len(rows[next_row]):
                continue
            val = rows[next_row][col_idx]
            if val in ("", None):
                continue
            lower = str(val).lower().strip()
            if any(tok in lower for tok in skip_tokens):
                continue
            return val
        return None

    def _update_numeric_field(self, invoice: Dict, field_name: str, raw_value):
        """Update numeric field only when new value is stronger than existing value."""
        if invoice is None:
            return

        new_value = self._normalize_field(field_name, raw_value)
        if new_value in (None, 0.0):
            return
        current_value = invoice.get(field_name)
        if current_value in (None, 0.0) or float(new_value) > float(current_value):
            invoice[field_name] = new_value

    def _extract_gstin_from_row_text(self, row_data: List[str]) -> Optional[str]:
        """Extract a GSTIN value from cells in the current row."""
        for cell in row_data:
            if not cell:
                continue
            match = self.GSTIN_REGEX.search(str(cell).upper().replace(' ', ''))
            if match:
                return match.group(0)
        return None

    def _extract_gstin_from_nearby_rows(self, rows: List[List[str]], row_idx: int, lookahead: int = 4) -> Optional[str]:
        """Scan nearby rows around a GST label row to find a valid GSTIN."""
        end_idx = min(len(rows), row_idx + lookahead + 1)
        for i in range(row_idx, end_idx):
            gstin = self._extract_gstin_from_row_text(rows[i])
            if gstin:
                return gstin
        return None

    def _extract_invoices_from_table(self, df: pd.DataFrame, sheet_name: str) -> List[Dict]:
        """Extract invoices from standard tabular sheets with column headers."""
        if df is None or df.empty:
            return []

        column_map = self._map_table_columns(df.columns)
        if not column_map:
            return []

        invoices = []
        for _, row in df.iterrows():
            invoice = {'sheet': sheet_name}

            for field_name, col_name in column_map.items():
                raw_val = row.get(col_name, None)
                if pd.isna(raw_val):
                    continue

                normalized_field = 'invoice_date' if field_name == 'invoice_date' else field_name
                invoice[normalized_field] = self._normalize_field(normalized_field, raw_val)

            # Fill missing totals from available amount columns.
            if not invoice.get('grand_total') and invoice.get('net_amount') is not None:
                cgst_val = float(invoice.get('cgst') or 0)
                sgst_val = float(invoice.get('sgst') or 0)
                invoice['grand_total'] = float(invoice['net_amount']) + cgst_val + sgst_val

            if self._is_valid_invoice(invoice):
                invoices.append(invoice)

        logger.info(f"Extracted {len(invoices)} table invoices from sheet: {sheet_name}")
        return invoices

    def _map_table_columns(self, columns) -> Dict[str, str]:
        """Map incoming table headers to invoice fields."""
        mapped = {}
        normalized_columns = {col: str(col).strip().lower() for col in columns}

        for field_name, patterns in self.TABLE_COLUMN_PATTERNS.items():
            for col, col_lower in normalized_columns.items():
                if any(re.search(pattern, col_lower) for pattern in patterns):
                    mapped[field_name] = col
                    break

        return mapped
    
    def _is_invoice_start(self, row_text: str, row_idx: int) -> bool:
        """Detect if this row marks the start of a new invoice"""
        indicators = [
            'invoice' in row_text,
            'bill' in row_text,
            row_idx == 0  # First row of sheet
        ]
        return any(indicators)
    
    def _extract_field_value(self, row_data: List[str], field_name: str) -> Optional[str]:
        """
        Extract field value from a row using label matching.
        Returns the value if label is found, None otherwise.
        """
        patterns = self.FIELD_PATTERNS.get(field_name, [])
        row_text = " ".join(row_data).lower()
        
        # Check if any pattern matches
        for pattern in patterns:
            if re.search(pattern, row_text):
                # Try to find the value after the label
                for i, cell in enumerate(row_data):
                    cell_lower = cell.lower()
                    if re.search(pattern, cell_lower):
                        # Value might be in the same cell or next cell
                        if i + 1 < len(row_data):
                            value = row_data[i + 1].strip()
                            if value and value not in row_data[i]:
                                return value
                        # Or extract from after the label in the same cell
                        match = re.search(pattern + r'\s*:?\s*(.+)', cell_lower)
                        if match:
                            return match.group(1).strip()
        
        return None
    
    def _clean_invoice_data(self, invoice_data: Dict) -> Dict:
        """Clean and normalize invoice data"""
        cleaned = {}
        
        # Required fields mapping
        field_mapping = {
            'invoice_no': 'invoice_no',
            'party_name': 'party_name',
            'invoice_date': 'invoice_date',
            'net_amount': 'net_amount',
            'cgst': 'cgst',
            'sgst': 'sgst',
            'grand_total': 'grand_total',
        }
        
        # Optional fields
        optional_mapping = {
            'gst_no': 'gst_no',
            'site': 'site',
        }
        
        try:
            # Clean required fields
            for source_key, target_key in field_mapping.items():
                if source_key in invoice_data:
                    value = invoice_data[source_key]
                    cleaned[target_key] = self._normalize_field(target_key, value)
            
            # Clean optional fields
            for source_key, target_key in optional_mapping.items():
                if source_key in invoice_data:
                    value = invoice_data[source_key]
                    cleaned[target_key] = self._normalize_field(target_key, value)
            
        except Exception as e:
            logger.warning(f"Error cleaning invoice data: {str(e)}")

        # Fill grand_total when taxable and tax values are present.
        if not cleaned.get('grand_total') and cleaned.get('net_amount') is not None:
            cgst_val = float(cleaned.get('cgst') or 0)
            sgst_val = float(cleaned.get('sgst') or 0)
            cleaned['grand_total'] = float(cleaned['net_amount']) + cgst_val + sgst_val
        
        return cleaned
    
    def _normalize_field(self, field_name: str, value: str) -> any:
        """Normalize field values"""
        if not value or value == "":
            return None
        
        if field_name == 'invoice_no':
            # Prevent date cells from being stored as invoice numbers.
            if isinstance(value, (datetime, pd.Timestamp)):
                return None

            text = str(value).strip()
            text = re.sub(r'(?i)^invoice\s*(?:no\.?|number)\s*:?\s*', '', text).strip()

            # Ignore values that are purely date-like.
            date_like_patterns = [
                r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$',
                r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$'
            ]
            if any(re.match(pattern, text) for pattern in date_like_patterns):
                return None

            # Keep as string to preserve invoice formatting.
            return text if text else None

        if field_name == 'gst_no':
            text = str(value).strip().upper()
            # Remove spaces and trailing punctuation often present in printed invoice labels.
            text = re.sub(r'\s+', '', text)
            text = text.rstrip(':;,.')
            match = self.GSTIN_REGEX.search(text)
            return match.group(0) if match else None

        if field_name in ['party_name', 'site']:
            return str(value).strip()
        
        elif field_name == 'invoice_date':
            try:
                # Try multiple date formats
                for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%y']:
                    try:
                        return datetime.strptime(str(value).strip(), fmt)
                    except ValueError:
                        continue
                # Try pandas parsing as fallback
                return pd.to_datetime(value)
            except Exception as e:
                logger.warning(f"Could not parse date: {value}")
                return datetime.now()
        
        elif field_name in ['net_amount', 'cgst', 'sgst', 'grand_total']:
            try:
                # Remove currency symbols and parse first numeric token from mixed strings.
                text = str(value).replace('₹', '').replace('$', '').replace(',', '').strip()
                numeric_match = re.search(r'-?\d+(?:\.\d+)?', text)
                if numeric_match:
                    return float(numeric_match.group(0))
                return 0.0
            except ValueError:
                logger.warning(f"Could not parse amount: {value}")
                return 0.0
        
        return value
    
    def _is_valid_invoice(self, invoice: Dict) -> bool:
        """Check if invoice has minimum required fields"""
        # Party name is often absent in raw invoice summaries; keep import usable.
        if not invoice.get('party_name'):
            invoice['party_name'] = 'Unknown Party'

        required = ['invoice_no', 'grand_total']
        has_required = all(field in invoice and invoice[field] not in (None, '') for field in required)
        return has_required


class BankStatementParser:
    """Parser for bank statement Excel files"""
    
    # Column patterns for bank statements
    COLUMN_PATTERNS = {
        'date': [r'date', r'transaction\s*date'],
        'description': [r'description', r'narration', r'party'],
        'amount': [r'amount', r'credit', r'debit'],
        'reference': [r'reference', r'ref', r'cheque', r'transaction\s*id'],
    }
    
    def __init__(self, file_path: str):
        """Initialize parser with file path"""
        self.file_path = file_path
    
    def parse(self) -> List[Dict]:
        """
        Parse bank statement from Excel file.
        
        Returns:
            List of payment dictionaries
        """
        try:
            # Keep workbook lifetime scoped so Windows file handles are released.
            with pd.ExcelFile(self.file_path) as xls:
                df = pd.read_excel(xls, sheet_name=0)
            payments = []
            
            # Auto-detect header
            headers = self._detect_headers(df)
            
            for idx, row in df.iterrows():
                payment = self._extract_payment(row, headers)
                if payment:
                    payments.append(payment)
            
            logger.info(f"✓ Extracted {len(payments)} payments from {self.file_path}")
            return payments
            
        except Exception as e:
            logger.error(f"✗ Error parsing bank statement: {str(e)}")
            raise
    
    def _detect_headers(self, df: pd.DataFrame) -> Dict[str, str]:
        """Auto-detect column headers"""
        headers = {}
        df_lower = df.columns.str.lower()
        
        for field_name, patterns in self.COLUMN_PATTERNS.items():
            for col_idx, col_name in enumerate(df_lower):
                for pattern in patterns:
                    if re.search(pattern, col_name):
                        headers[field_name] = df.columns[col_idx]
                        break
        
        return headers
    
    def _extract_payment(self, row: pd.Series, headers: Dict) -> Optional[Dict]:
        """Extract payment from a row"""
        try:
            payment = {
                'payment_id': f"PAY-{datetime.now().timestamp()}",
                'payment_date': row.get(headers.get('date', ''), datetime.now()),
                'party_name': str(row.get(headers.get('description', ''), '')).strip(),
                'amount': float(str(row.get(headers.get('amount', ''), 0)).replace(',', '')),
                'reference': str(row.get(headers.get('reference', ''), '')).strip(),
            }
            
            if payment['amount'] > 0 and payment['party_name']:
                return payment
        except Exception as e:
            logger.debug(f"Error extracting payment: {str(e)}")
        
        return None
