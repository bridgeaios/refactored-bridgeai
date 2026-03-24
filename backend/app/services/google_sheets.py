"""
Google Sheets service for BridgeLiveWall
Handles authentication and data synchronization with Google Sheets
"""
import logging
import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Google Sheets client using service account credentials"""
        try:
            # Check for service account credentials file
            creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
            if creds_file and os.path.exists(creds_file):
                # Use service account authentication
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                credentials = Credentials.from_service_account_file(
                    creds_file,
                    scopes=scopes
                )
                self.client = gspread.authorize(credentials)
                logger.info("Google Sheets client initialized with service account")
            else:
                # Fallback to environment variables for credentials
                creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
                if creds_json:
                    import json
                    creds_dict = json.loads(creds_json)
                    scopes = [
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                    credentials = Credentials.from_service_account_info(
                        creds_dict,
                        scopes=scopes
                    )
                    self.client = gspread.authorize(credentials)
                    logger.info("Google Sheets client initialized with JSON credentials")
                else:
                    logger.warning("Google Sheets credentials not found. Service will be disabled.")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if Google Sheets service is available"""
        return self.client is not None

    async def read_spreadsheet(
        self,
        spreadsheet_id: str,
        range_name: str = "A:Z"
    ) -> list[list[Any]] | None:
        """
        Read data from a Google Spreadsheet

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to read (default: A:Z)

        Returns:
            List of rows, where each row is a list of cell values, or None if failed
        """
        if not self.is_available():
            logger.error("Google Sheets service not available")
            return None

        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.sheet1  # Default to first sheet

            # If range_name specifies a different sheet, try to get it
            if "!" in range_name:
                sheet_name, cell_range = range_name.split("!", 1)
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    logger.warning(f"Worksheet '{sheet_name}' not found, using first sheet")
                    worksheet = spreadsheet.sheet1
                    cell_range = range_name  # Use original range
            else:
                cell_range = range_name

            data = worksheet.get(cell_range)
            logger.info(f"Read {len(data)} rows from Google Sheets")
            return data

        except Exception as e:
            logger.error(f"Failed to read from Google Sheets: {e}")
            return None

    async def write_spreadsheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]]
    ) -> bool:
        """
        Write data to a Google Spreadsheet

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to write to
            values: 2D list of values to write

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("Google Sheets service not available")
            return False

        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.sheet1  # Default to first sheet

            # Handle sheet specification in range
            if "!" in range_name:
                sheet_name, cell_range = range_name.split("!", 1)
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    # Create worksheet if it doesn't exist
                    try:
                        worksheet = spreadsheet.add_worksheet(
                            title=sheet_name,
                            rows=1000,
                            cols=26
                        )
                    except Exception as e:
                        logger.error(f"Failed to create worksheet '{sheet_name}': {e}")
                        worksheet = spreadsheet.sheet1
                        cell_range = range_name  # Fallback to original
            else:
                cell_range = range_name

            worksheet.update(cell_range, values)
            logger.info(f"Wrote {len(values)} rows to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to write to Google Sheets: {e}")
            return False

    async def append_spreadsheet(
        self,
        spreadsheet_id: str,
        values: list[list[Any]],
        sheet_name: str = "Sheet1"
    ) -> bool:
        """
        Append data to a Google Spreadsheet

        Args:
            spreadsheet_id: The ID of the spreadsheet
            values: 2D list of values to append
            sheet_name: Name of the worksheet to append to

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("Google Sheets service not available")
            return False

        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)

            try:
                worksheet = spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                # Create worksheet if it doesn't exist
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=26
                )

            worksheet.append_rows(values)
            logger.info(f"Appended {len(values)} rows to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to append to Google Sheets: {e}")
            return False

    async def get_sheet_info(self, spreadsheet_id: str) -> dict[str, Any] | None:
        """
        Get information about a spreadsheet

        Args:
            spreadsheet_id: The ID of the spreadsheet

        Returns:
            Dictionary with spreadsheet info or None if failed
        """
        if not self.is_available():
            logger.error("Google Sheets service not available")
            return None

        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            info = {
                "id": spreadsheet.id,
                "title": spreadsheet.title,
                "url": spreadsheet.url,
                "worksheets": [
                    {
                        "title": ws.title,
                        "id": ws.id,
                        "row_count": ws.row_count,
                        "col_count": ws.col_count
                    }
                    for ws in spreadsheet.worksheets()
                ]
            }
            return info

        except Exception as e:
            logger.error(f"Failed to get spreadsheet info: {e}")
            return None

# Global service instance
google_sheets_service = GoogleSheetsService()
