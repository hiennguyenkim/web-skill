import sys
import os
import zipfile
import xml.etree.ElementTree as ET

def docx_to_txt(docx_path):
    if not os.path.exists(docx_path):
        print(f"Error: File {docx_path} does not exist.")
        return ""
    
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # Namespaces for OOXML
            namespaces = {
                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
            }
            
            text_runs = []
            # Iterate through all paragraph elements
            for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                p_text = []
                for run in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if run.text:
                        p_text.append(run.text)
                text_runs.append("".join(p_text))
            
            return "\n\n".join(text_runs)
    except Exception as e:
        print(f"Error reading docx: {e}")
        return ""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: docx_to_txt.py <path_to_docx>")
        sys.exit(1)
    
    docx_path = sys.argv[1]
    text = docx_to_txt(docx_path)
    print(text)
