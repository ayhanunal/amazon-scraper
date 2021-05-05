import xlrd
from collections import OrderedDict
import glob
import os
from pathlib import Path
import xlsxwriter
import json
import time

path = 'excel/' 
data_list = []
for filename in glob.glob(os.path.join(path, '*.xlsx')):

    wb = xlrd.open_workbook(filename)
    sh = wb.sheet_by_index(0)

    for rownum in range(1, sh.nrows):
        data = OrderedDict()
        row_values = sh.row_values(rownum)
        data["product_url"] = row_values[0]
        data['condition'] = row_values[1]
        data['title'] = row_values[2]
        data['brand'] = row_values[3]
        data['categories'] = row_values[4]
        data['username'] = row_values[5]
        data['likes'] = row_values[6]
        data['price'] = row_values[7]
        data['discounted_price'] = row_values[8]
        data['size'] = row_values[9]
        data['colors'] = row_values[10]
        data['description'] = row_values[11]
        data['images'] = row_values[12]
        data['list_date'] = row_values[13]
        data['sold_date'] = row_values[14]
        
        data_list.append(data)

    # j = json.dumps(data_list)

    # with open('posh.json', 'w') as f:
    #     f.write(j)

def export(outfile, path, data):
    outfile = outfile.replace(".json", "")

    columnkeys1 = OrderedDict()

    # data1 = []
    # with open(path, "r") as f:
    #     raw = f.read()
    #     data1 = json.loads(raw)

    columns = [ "product_url", "condition", "title", "brand", "categories", "username", "likes", "price", "discounted_price", "size", "colors", "description", "images", "list_date", "sold_date"]


    for c in columns:
        columnkeys1[c] = c

    print("Starting export")
    workbook = xlsxwriter.Workbook(outfile + "_" + time.strftime("%Y%m%d_%H%M%S") + '.xlsx', {'strings_to_urls': False})

    try:
        worksheet = workbook.add_worksheet("Export")
      # worksheet.set_default_row(65)
        export_sheet(worksheet, data, columnkeys1)

        print("Closing export")
        workbook.close()
    except e:
        print(str(e))

def export_sheet(worksheet, data, columnkeys):

    letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
               'V', 'W', 'X', 'Y', 'Z', 'AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL', 'AM',
               'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ']

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

            # 130 x 66
            width = 66
            if key == "cover" and len(val) > 0:
                worksheet.insert_image(letters[col] + str(row), val, {'x_scale': 0.5, 'y_scale': 0.5})
                worksheet.set_column(row, col, width * .5)
            else:
                worksheet.write(letters[col] + str(row), val)
            col += 1   
