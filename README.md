# Glosario de variables

Los archivos CSV de este conjunto de datos usan encabezados abreviados con el formato: CódigoVariable_Año.
El texto descriptivo se eliminó para ahorrar espacio. El siguiente glosario relaciona cada código con su descripción completa.


* A111A: Producción bruta total (millones de pesos)
* A121A: Consumo intermedio (millones de pesos)
* A131A: Valor agregado censal bruto (millones de pesos)
* A211A: Inversión total (millones de pesos)
* A221A: Formación bruta de capital fijo (millones de pesos)
* H001A: Personal ocupado total
* Q000A: Acervo total de activos fijos (millones de pesos)
* 
# **Obtención de las proporciones** 
(Estatal / Nacional)

1. A111A (Producción bruta total estatal / nacional) = Proporción del peso del estado en la producción bruta total nacional
2. A121A (Consumo intermedio estatal / nacional) = Proporción del peso del estado en el consumo intermedio nacional
3. A131A (Valor agregado censal bruto estatal / nacional) = Proporción del peso del estado en el valor agregado censal bruto nacional
4. A221A (Formación bruta de capital fijo estatal / nacional) = Proporción del peso del estado en la formación bruta de capital fijo nacional

(Región / Estatal)

1. A111A (Producción bruta total regional / estatal) = Proporción del peso de la región en la producción bruta total estatal
2. A121A (Consumo intermedio regional / estatal) = Proporción del peso de la región en el consumo intermedio estatal
3. A131A (Valor agregado censal bruto regional / estatal) = Proporción del peso de la región en el valor agregado censal bruto estatal
4. A221A (Formación bruta de capital fijo regional / estatal) = Proporción del peso de la región en la formación bruta de capital fijo estatal


# Problemas con la base de datos:
En todo momento el INEGI omite datos de mineria del Estado de Tamaulipas.
Ciudad Madero es un caso especial porque especificamente el INEGO se dio la tarea de eliminar todo rastro de estadistica censal
de minera y petrolera. La suma de Ciudad Madero con cifras oficiales hace que Mineria y petroleo de 0. 

Variable checksum indica lo que suma todo los valores de los sectores en una columna.

# Interpretacion 

# Ejemplo 1: Valores nulos o confidenciales
A continuación se muestra la fila “Sector 21 Minería” tomada del archivo municipal 009 Ciudad Madero.csv, mostrando únicamente las columnas A131 y usando exactamente los encabezados de la fila 1.

| Actividad Economica | A131A_2003 | A131A_2008 | A131A_2013 | A131A_2018 | A131A_2023 |
|---|---|---|---|---|---|
| Sector 21 Minería |  |  |  |  |  |

Como se observa faltan valores que son considerados como "nulos" o para terminos economicos confidenciales. Esto significa que la
industria esta presente en el municipio de Ciudad Madero pero los datos son confidenciales o no disponibles de manera publica.

# Ejemplo 2: Falta de una industria en un municipio.

Nota: Los valores se encuentran vacíos en el archivo fuente, reflejando que el INEGI omitió/depuró estos datos para Ciudad Madero.

Tome el ejemplo de Victoria. El municipio cuenta con un sector que es considerado raro en el Estado 

# IDE
- PyCharm 

# Base de datos
https://www.inegi.org.mx/app/saic/
		
	
# Autor 
Homero P. Mata
Freelancer
Desarrollado para la Secretaria de Economia de Tamaulipas