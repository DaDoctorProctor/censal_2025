README.MD

# Glosario de variables

The CSV files in this dataset use shortened headers in the format: VariableCode_Year.
The descriptive text has been removed to save space. The following glossary maps each code to its full description.


* A111A: Producción bruta total (millones de pesos)
* A121A: Consumo intermedio (millones de pesos)
* A131A: Valor agregado censal bruto (millones de pesos)
* A211A: Inversión total (millones de pesos)
* A221A: Formación bruta de capital fijo (millones de pesos)
* H001A: Personal ocupado total
* Q000A: Acervo total de activos fijos (millones de pesos)

# Notes
- "Actividad económica" column retains the cleaned sector names without the "Sector XX" prefix.
- Years are appended to the variable code for each column, e.g., H001A_2008, A111A_2013.
- CSV files for 00_Total_Nacional and 28_Tamaulipas are split by variable in their respective subfolders.

# **Obtencion de las proporciones** 
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


Frontera Norte del Pais	2006 - 2024	4to trimestre	suma de todos los 4to trimestres
Baja California			
Coahuila			
Chihuahua			
Nuevo Leon			
Sonora			
Tamaulipas			
	