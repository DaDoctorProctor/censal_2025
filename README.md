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

# Notas
- La columna "Actividad económica" conserva los nombres de sector depurados sin el prefijo "Sector XX".
- Los años se agregan al código de variable en cada columna, p. ej., H001A_2008, A111A_2013.
- Los archivos CSV de 00_Total_Nacional y 28_Tamaulipas están divididos por variable en sus respectivas subcarpetas.

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

(Región / Nacional)

1. A111A (Producción bruta total regional / nacional) = Proporción del peso de la región en la producción bruta total nacional
2. A121A (Consumo intermedio regional / nacional) = Proporción del peso de la región en el consumo intermedio nacional
3. A131A (Valor agregado censal bruto regional / nacional) = Proporción del peso de la región en el valor agregado censal bruto nacional
4. A221A (Formación bruta de capital fijo regional / nacional) = Proporción del peso de la región en la formación bruta de capital fijo nacional

# IDE
- PyCharm 

# Base de datos
https://www.inegi.org.mx/app/saic/
		
	