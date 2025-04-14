# Instrucciones para Convertir Diagramas a PNG

Para convertir los archivos de diagrama Mermaid (.txt) a imágenes PNG, siga estos pasos:

## Método 1: Usando Mermaid Live Editor

1. Visite [Mermaid Live Editor](https://mermaid.live)
2. Copie el contenido del archivo .txt (sin incluir los delimitadores markdown)
3. Péguelo en el panel de edición
4. Utilice la opción "Export PNG" para guardar la imagen
5. Guarde el archivo con el nombre correspondiente (ejemplo: arquitectura_diagrama.png)

## Método 2: Usando mermaid-cli (línea de comandos)

Si prefiere automatizar el proceso, puede usar mermaid-cli:

1. Instale Node.js si no lo tiene instalado
2. Instale mermaid-cli globalmente:
   ```
   npm install -g @mermaid-js/mermaid-cli
   ```
3. Use el siguiente comando para cada archivo:
   ```
   mmdc -i arquitectura_diagrama.txt -o arquitectura_diagrama.png -t dark
   ```

## Método 3: Con Extensión de Visual Studio Code

1. Instale la extensión "Mermaid Preview" o "Markdown Preview Mermaid Support"
2. Abra el archivo .txt en VS Code
3. Use la vista previa para verificar el diagrama
4. Use la opción de exportar a PNG (si está disponible) o capture la pantalla

## Nota Importante

Recuerde eliminar las comillas invertidas y "mermaid" del principio y final del archivo de texto antes de procesarlo.

