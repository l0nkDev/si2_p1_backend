
import psycopg2 # type: ignore

casos_especiales = {
    10: "diez",
    11: "once",
    12: "doce",
    13: "trece",
    14: "catorce",
    15: "quince"
}

def dividir_num(num: str) -> list:
    return [num[i:i+3] for i in range(0, len(num), 3)]

def armar_cientos(num: str) -> str:
    unidades =['', 'uno','dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    decenas = ['', 'dieci', 'veinti', 'treinta y ', 'cuarenta y ', 'cincuenta y ', 'sesenta y ', 'setenta y ', 'ochenta y ', 'noventa y ']
    centenas = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos']
    
    cientos = int(num[0]) if len(num) > 2 else 0

    if int(num[-2:]) in casos_especiales:
        return (f"{centenas[cientos]} " if cientos != 0 else '') + casos_especiales[int(num[-2:])]

    decena, unidad = num[-2:]
    return (f"{centenas[cientos]} " if cientos != 0 else '') + decenas[int(decena)] + unidades[int(unidad)]

def numeros_a_palabras(numero:int) -> str:
    if numero == 0:
        return 'Cero'
    elif numero == 1000000:
        return 'Un millon'
    
    en_palabras = ''
    
    str_numero = str(numero)
    longitud_num = len(str_numero)

    unidades =['', 'uno','dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    otros = ['', 'mil', 'millon']


    for i, parte in enumerate(dividir_num(str_numero[::-1])):
        parte = parte[::-1]
        num = int(parte)

        if num == 0: continue
        if len(str(num)) == 1: en_palabras =  unidades[num] + f"{otros[i]} " + en_palabras
        elif num > 15:
            resultado = armar_cientos(parte).strip()

            if resultado[-1] == 'i':
                resultado = resultado[:-1] + ('e' if parte[-2] == '2' else 'a')
            elif resultado == 'ciento': 
                resultado = 'cien'
            
            if i == 0: 
                en_palabras += f"{resultado} "
            else:
                en_palabras = resultado + f" {otros[i]} " + en_palabras
        else:
            en_palabras = casos_especiales[num] + f" {otros[i]} " + en_palabras
    
    if en_palabras.startswith('uno'):
        en_palabras = ('un ' if i > 1 else '') + en_palabras[3:]
    return en_palabras.strip().capitalize()

conn = psycopg2.connect(
        host="localhost",
        database="flask_db",
        user="sammy",
        password="password"
        )

def factura(purchaseid):

    cur = conn.cursor()
    cur.execute('select purchases.*, purchased.*, users.name, users.lname, users.id from purchases, purchased, users, carts where cartid = carts.id and carts.userid = users.id and purchaseid = purchases.id and purchases.id = {0}'.format(purchaseid))
    res = cur.fetchall()
    html = '''
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
        <table class="simple">
            <tr class="simple">
                <td style="text-align: center;" class="simple">
                    <b>PARCIAL 1</b><br>
                    CASA MATRIZ<br>
                    Nro. Punto de Venta 102<br>
                    AVENIDA SANTA CRUZ ZONA CENTRO DE LA CIUDAD<br>
                    UV 1 MZA 6
                </td>
                <td style="text-align: right;" class="simple">
                    <b>NIT</b><br>
                    <b>FACTURA NRO.</b><br>
                    <b>COD. AUTORIZACIÓN</b><br>
                </td>
                <td style="text-align: right;" class="simple">
                    <br>
                    4083024010
                    <br>
    '''
    html += '{0}'.format(res[0][0])
    html += '''
                    <br>
                    1175F30E1861D4BF16C70E95BA64E8<br>E661901D1682241922F06EC6D74
                </td>
            </tr>
        </table>

        <div style="text-align: center">
            <br><br>
            <b style="font-size: 30px">FACTURA</b><br>
        </div>
        <br>
        <table style="width: auto" class="simple">
            <tr class="simple">
                <td colspan="2" class="simple"><div style="width: 350px;"></div></td>
            </tr>
            <tr class="simple">
                <td class="simple">
                    <b>Fecha:</b>
                </td>
                <td class="simple">
    '''
    html += '{0}'.format(res[0][2]).split(" ")[0]
    html += '''
                </td>
                <td class="simple">
                    <b>NIT/CI/CEX:</b>
                </td>
                <td class="simple">
                    43534532
                </td>
            </tr>
            <tr class="simple">
                <td class="simple">
                    <b>Nombre/Razon Social:</b>
                </td>
                <td class="simple">
    '''
    html += '{0} {1}'.format(res[0][16], res[0][17])
    html += '''
                    </td>
                <td class="simple">
                    <b>Cod. Cliente: </b>
                </td>
                <td class="simple">
    '''
    html += '{0}'.format(res[0][18])
    html += '''
                    </td>
            </tr>
        </table>

        <div>
            <table class="products simple">
                <tr>
                    <th><b>PRODUCTO</b></th>
                    <th><b>CANTIDAD</b></th>
                    <th><b>MARCA</b></th>
                    <th><b>PRECIO<br>UNITARIO</b></th>
                    <th><b>DESCUENTO</b></th>
                    <th><b>SUBTOTAL</b></th>
                </tr>
    '''
    subtotal = 0.0
    for item in res:
        html += '''
                <tr class="items">
                    <td style="text-align: center">
                        {0}
                    </td>
                    <td style="text-align: center">
                        {1}
                    </td>
                    <td>
                        {2}
                    </td>
                    <td style="text-align: right">
                        {3}
                    </td>
                    <td style="text-align: right">
                        {4}
                    </td>
                    <td style="text-align: right">
                        {5}
                    </td>
                </tr>'''.format(item[10], item[14], item[11], item[12], '%.2f' % (float(item[12])-float(item[13])), item[13])
        subtotal += float(item[15])
        total = ('%.2f' % (subtotal*0.85)) if res[0][6] == "Y" else ('%.2f' % subtotal)
        descuento = ('%.2f' % (subtotal*0.15)) if res[0][6] == "Y" else "0.00"
    html += '''
                <tr>
                    <td class="simple" colspan="4"></td>
                    <td style="text-align: right">SUBTOTAL</td>
                    <td style="text-align: right">{0}</td>
                </tr>
                <tr>
                    <td class="simple" colspan="4"></td>
                    <td style="text-align: right">DESCUENTO</td>
                    <td style="text-align: right">{1}</td>
                </tr>
                <tr>
                    <td class="simple" colspan="4">
                        Son
                        {2}/100 Dolares americanos.
                    </td>
                    <td style="text-align: right"><b>TOTAL</b></td>
                    <td style="text-align: right">{3}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center">
            <br><br><br>
            ESTA FACTURA CONTRIBUYE AL DESARROLLO DEL PAÍS, EL USO ILÍCITO SERÁ SANCIONADO<br>PENALMENTE DE ACUERDO A LEY<br><br>
            Ley Nro 453: Tienes derecho a recibir información sobre las caracteristicas y contenidos de los<br>servicios que utilices.<br>
        </div>
        </body>
        </html>
'''.format('%.2f' % subtotal, descuento, "{0} {1}".format(numeros_a_palabras(int(total.split(".")[0])), total.split(".")[1]), total)
    return html