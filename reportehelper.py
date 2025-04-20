html_1 = '''
<!doctype html>
<html lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <meta name="viewport"
        content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Invoice</title>
    <style>
        h4 {
            margin: 0;
        }
        .margin-top {
            margin-top: 1.25rem;
        }
        table {
            width: 100%;
            border-spacing: 0;
        }
        td, tr, th, div {
            font-size: 12px;
            font-family: Arial, Helvetica, sans-serif;
        }
        table, th, td {
            border: 0.05px solid black;
        }
        .simple {
            border: 0px solid black;
        }
    </style>
</head>
<body>
<div style="text-align: center">
    <br><br>
    <b style="font-size: 30px">REPORTE DE '''
html_2 = '</b><br></div><br><div><table class="products simple"><tr>'
html_3 = '</tr>'
html_4 = '</table></div></body></html>'
    
import psycopg2 # type: ignore
from flask import make_response # type: ignore
import pdfkit # type: ignore
import pandas # type: ignore
from io import BytesIO

conn = psycopg2.connect(
        host="localhost",
        database="flask_db",
        user="sammy",
        password="password"
        )


def create_pdf_header(headers: list):
    string = ''
    for item in headers:
        string += "<th><b>{0}</b></th>".format(item)
    return string
        
def create_pdf_contents(res):
    string = ''
    for item in res:
        string += "<tr>"
        for i in item:
            string += '<td style="text-align: center">{0}</td>'.format(i)
        string += "</tr>"
    return string
        
def create_excel(headers, res):
    item = []
    items = []
    items.append(headers)
    for i in res:
        for j in i:
            item.append(j)
        items.append(item)
        item = []
    return items


def reportes(title, query, headers, format):
    cur = conn.cursor()
    cur.execute(query)
    res = cur.fetchall()
    if format == 'pdf':
        html = html_1 + title + html_2 + create_pdf_header(headers) + html_3 + create_pdf_contents(res) + html_4
        pdf = pdfkit.from_string(html, False)  
        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=output.pdf"
        return response
    df = pandas.DataFrame.from_records(create_excel(headers, res))  
    out = BytesIO()
    wri = pandas.ExcelWriter(out) 
    df.to_excel(wri) 
    wri.close() 
    response = make_response(out.getvalue())
    response.headers["Content-Type"] = "application/excel"
    response.headers["Content-Disposition"] = "inline; filename=output.xlsx"
    return response