from oauth2client.service_account import ServiceAccountCredentials
import gspread

"""Utility methods for management commands."""


def get_gspread_worksheet(oauth2_key_file, spreadsheet_id, worksheet_id):
    """Return a gspread worksheet with worksheet_id from the spreadsheet
    with spreadsheet_id and the given authorizing oauth2_key_file.

    Parameters:
        - oauth2_key_file (str): the path to a key file that authorizes
                                 access to the spreadsheet
        - spreadsheet_id (str): the ID of the spreadsheet being accessed
        - worksheet_id (str): the ID of the worksheet being accessed
                              within the spreadsheet

    Returns:
        - gspread Worksheet

    Raises:
        - Exception, if any errors occur.
    """
    scopes = ["https://spreadsheets.google.com/feeds"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        oauth2_key_file, scopes)
    c = gspread.authorize(credentials)
    spreadsheet = c.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(worksheet_id)


def get_gspread_worksheet_data(worksheet, row_start, row_end, col_start,
                               col_end):
    """Return a list of lists, where each row corresponds to a row in
    the given gspread worksheet. The lists are constrained by the row
    and column limits.

    Parameters:
        - worksheet (Worksheet): a gspread Worksheet
        - row_start (int): the first row of the worksheet to include
        - row_end (int): the last row of the worksheet to include
        - col_start (int): the first column of the worksheet to include
        - col_end (int): the last column of the worksheet to include

    Returns:
        - list of lists containing spreadsheet data

    Raises:
        - Exception, if any errors occur.
    """
    cell_list = worksheet.range(row_start, col_start, row_end, col_end)
    data = []
    num_rows = row_end - row_start + 1
    num_cols = int(len(cell_list) / num_rows)
    index = 0
    for i in range(num_rows):
        data.append(
            [cell.value.strip() for cell in cell_list[index:index + num_cols]])
        index = index + num_cols
    return data
