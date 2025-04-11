# Instrucciones para Convertir Diagramas a PNG

Debido a que Node.js no está instalado en el sistema, se recomiendan los siguientes métodos alternativos para convertir los diagramas Mermaid a PNG:

## Método 1: Usando Mermaid Live Editor (Recomendado)

1. Visite [Mermaid Live Editor](https://mermaid.live)
2. Para cada archivo .txt en la carpeta recursos:
   - Abra el archivo en un editor de texto
   - Copie el contenido (sin incluir las líneas ```mermaid y ```)
   - Péguelo en el editor de Mermaid Live
   - Use el botón "Download PNG" para guardar la imagen
   - Guarde el archivo con el mismo nombre pero extensión .png

Archivos a convertir:
- arquitectura_diagrama.txt → arquitectura_diagrama.png
- autenticacion_diagrama.txt → autenticacion_diagrama.png
- componentes_diagrama.txt → componentes_diagrama.png
- flujo_datos_diagrama.txt → flujo_datos_diagrama.png
- mensajes_flujo_diagrama.txt → mensajes_flujo_diagrama.png

## Método 2: Usando Visual Studio Code

1. Instale la extensión "Markdown Preview Mermaid Support" en VS Code
2. Abra cada archivo .txt
3. Use el comando "Markdown: Open Preview" para ver el diagrama
4. Capture la pantalla del diagrama
5. Guarde la captura como PNG

## Método 3: Instalación de Node.js (Opcional)

Si desea automatizar el proceso en el futuro:

1. Descargue e instale Node.js desde [nodejs.org](https://nodejs.org/)
2. Instale mermaid-cli globalmente:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   ```
3. Use el script convertir_diagramas.ps1 incluido en la carpeta recursos

## Ubicación de los Archivos

Los archivos fuente están en la carpeta 'recursos':
- Archivos Mermaid (.txt)
- Script de conversión (convertir_diagramas.ps1)
- Este archivo de instrucciones

## Después de la Conversión

1. Verifique que las imágenes PNG generadas son legibles
2. Confirme que están correctamente referenciadas en la documentación
3. Mantenga los archivos .txt originales para futuras modificaciones

