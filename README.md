# Licitatron

Se me ocurrió que sería interesante conocer las tecnologías en las que el gobierno está interesado.

Partiendo de la información que transparentemente publica el estado sobre sus licitaciones [en su página sobre Datos Abiertos](https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/LicitacionesContratante.aspx) y con la inestimable ayuda de [Claude](https://claude.ai/) he cocinado unos scripts que 

* obtienen una lista de las licitaciones
* filtran las que sean de cierto tipo y lugar (por ejemplo, servicios informáticos y Andalucía)
* descargan los pliegos de prescripciones técnicas correspondientes
* buscan ciertas palabras clave en los pliegos
* crean un fichero .csv con los resultados
* crean una nube de etiquetas con las tecnologías en las contrataciones del estado.

El resultado, una imagen como esta: 

![Nube de etiquetas de tecnologías](https://github.com/alfem/licitatron/blob/main/sample/wordcloud_tecnologias_principal.png)

# Como se usa

Necesitas Python3 y algunos módulos: requests, pdfplumber, PyPDF2, pandas, numpy, wordcloud, matplotlib
Es recomendable trabajar con un entorno virtual e instalarlos en él.

1) Primero lanzas el script que descarga las licitaciones de un periodo concreto. O bien las descargas tú y le dices al script que use el fichero descargado. Conviene indicar el código que corresponde a servicios informáticos (7200000), y opcionalmente alguna ciudad o región. 
```
python3 atom_extractor.py licitacionesPerfilesContratanteCompleto3_202501.zip --local --output-dir atom_extractor_files_202501 --output-file atom_extractor_result_202501.txt --filter-name Andaluc --filter-code "7200000"
```
2) Ahora que ya tienes en local todos los pdfs, lanzas el analizador que buscará las palabras clave. Puedes añadir o quitar palabras clave en [tech_keywords.yaml](https://github.com/alfem/licitatron/blob/main/tech_keywords.yaml). Le das como parámetros el nombre del fichero csv, y el directorio donde están los pdfs:

```
python3 pdf_tech_extractor.py --csv-file tech_analysis_202502.csv atom_extractor_files_202501
```
3) Por último, crea las imágenes de nube de etiquetas:
```   
python3 wordcloud_generator.py --title "Tecnologías Andalucía 2025-01" --output-dir wordcloud_202501 --no-multiple --color-scheme "ocean" tech_analysis/tecnologias.csv
```
