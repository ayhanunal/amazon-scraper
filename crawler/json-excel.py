import time
from collections import OrderedDict
import xlsxwriter
import json, sys


columnkeys1 = OrderedDict()
letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
           'V', 'W', 'X', 'Y', 'Z', 'AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL', 'AM',
           'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ']

def export(outfile):
    outfile = outfile.replace(".json", "")
        
    data1 = []
    with open( "output/thredup" + ".json", "r") as f:
        data1 = json.loads(f.read())
    
    columns = ["list_date", "availability", "product_url", "title", "categories", "brand", "favorites", "price", "discounted_price", "materials", "colors", "size", "item_id", "images"]
    # columns = [ "product_url", "condition", "title", "brand", "categories", "username", "likes", "price", "discounted_price", "size", "colors", "description", "images", "list_date", "sold_date"]

    for d in data1:
        for k in d.keys():
            if k not in columns:
                columns.append(k)
    
    for c in columns:
        columnkeys1[c] = c

    print("Starting export")
    workbook = xlsxwriter.Workbook(outfile + "_" + time.strftime("%Y%m%d_%H%M%S") + '.xlsx', {'strings_to_urls': False})
    worksheet = workbook.add_worksheet("Export")
    export_sheet(worksheet, data1, columnkeys1)

    print("Closing export")
    workbook.close()

def export_sheet(worksheet, data, columnkeys):
    row = 1
    col = 0
    for key in columnkeys.keys():
        header = columnkeys[key]
        worksheet.write(letters[col] + str(row), header)
        col += 1

    for item in data:
        row += 1
        col = 0

        for key in columnkeys.keys():
            val = ""
            if key in item:
                val = item[key]
            worksheet.write(letters[col] + str(row), val)
            col += 1