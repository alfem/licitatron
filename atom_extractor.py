#!/usr/bin/env python3
"""
Script para extraer datos de archivos ATOM contenidos en un ZIP
y descargar documentos PDF referenciados.
"""

import os
import sys
import zipfile
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
from pathlib import Path
import argparse
import logging
from typing import List, Dict, Optional
import time

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para más información
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtomExtractor:
    def __init__(self, download_dir: str = "downloaded_docs"):
        """
        Inicializar el extractor.
        
        Args:
            download_dir: Directorio donde guardar los documentos descargados
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Namespaces basados en la muestra real
        self.namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'cac': 'urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
            'cac-place-ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
            'cbc-place-ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2',
            'at': 'http://purl.org/atompub/tombstones/1.0',
            'ns7': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_zip(self, url: str, local_path: str = "temp.zip") -> str:
        """
        Descargar archivo ZIP desde URL.
        
        Args:
            url: URL del archivo ZIP
            local_path: Ruta local donde guardar el ZIP
            
        Returns:
            Ruta del archivo descargado
        """
        logger.info(f"Descargando ZIP desde: {url}")
        
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"ZIP descargado exitosamente: {local_path}")
            return local_path
            
        except requests.RequestException as e:
            logger.error(f"Error descargando ZIP: {e}")
            raise

    def extract_zip(self, zip_path: str, extract_dir: str = "temp_extract") -> str:
        """
        Extraer contenido del ZIP.
        
        Args:
            zip_path: Ruta del archivo ZIP
            extract_dir: Directorio donde extraer
            
        Returns:
            Ruta del directorio de extracción
        """
        extract_path = Path(extract_dir)
        extract_path.mkdir(exist_ok=True)
        
        logger.info(f"Extrayendo ZIP: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        logger.info(f"ZIP extraído en: {extract_path}")
        return str(extract_path)

    def find_atom_files(self, directory: str) -> List[str]:
        """
        Buscar archivos .atom en el directorio extraído.
        
        Args:
            directory: Directorio donde buscar
            
        Returns:
            Lista de rutas de archivos .atom
        """
        atom_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.atom'):
                    atom_files.append(os.path.join(root, file))
                    
        logger.info(f"Encontrados {len(atom_files)} archivos .atom")
        return atom_files

    def parse_atom_file(self, file_path: str) -> List[Dict]:
        """
        Parsear archivo ATOM y extraer datos de las entradas.
        
        Args:
            file_path: Ruta del archivo .atom
            
        Returns:
            Lista de diccionarios con los datos extraídos
        """
        logger.info(f"Procesando archivo ATOM: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Debug: mostrar información del archivo
            logger.debug(f"Root tag: {root.tag}")
            logger.debug(f"Root namespace: {root.nsmap if hasattr(root, 'nsmap') else 'No nsmap available'}")
            
            # Auto-detectar namespaces del archivo usando ElementTree
            detected_namespaces = {}
            # Extraer namespaces del root tag si están presentes
            for elem in root.iter():
                if elem.tag.startswith('{'):
                    # Extraer URI del namespace
                    uri = elem.tag[1:elem.tag.find('}')]
                    tag_name = elem.tag[elem.tag.find('}')+1:]
                    # Intentar mapear a prefijos conocidos
                    if 'atom' in uri:
                        detected_namespaces['atom'] = uri
                    elif 'CommonAggregateComponents' in uri:
                        detected_namespaces['cac'] = uri
                    elif 'CommonBasicComponents' in uri:
                        detected_namespaces['cbc'] = uri
                    elif 'PlaceExtensions' in uri:
                        if 'cac-place-ext' not in detected_namespaces:
                            detected_namespaces['cac-place-ext'] = uri
                        if 'cbc-place-ext' not in detected_namespaces:
                            detected_namespaces['cbc-place-ext'] = uri
                            
            # Combinar namespaces detectados con los predefinidos
            all_namespaces = {**self.namespaces, **detected_namespaces}
            logger.debug(f"Namespaces detectados: {detected_namespaces}")
            
            entries = []
            
            # Buscar todas las entradas - múltiples enfoques
            entry_elements = []
            
            # Primero registrar el namespace por defecto si es necesario
            if root.tag.startswith('{http://www.w3.org/2005/Atom}'):
                # El namespace atom es el por defecto, registrar como tal
                all_namespaces[''] = 'http://www.w3.org/2005/Atom'
            
            # Intentar diferentes formas de encontrar entries
            searches = [
                ('entry', 'Sin namespace - directo bajo feed'),
                ('.//entry', 'Sin namespace - recursivo'),
                ('{http://www.w3.org/2005/Atom}entry', 'Con namespace completo directo'),
                ('.//{http://www.w3.org/2005/Atom}entry', 'Con namespace completo recursivo'),
            ]
            
            for search_pattern, description in searches:
                try:
                    found = root.findall(search_pattern)
                    
                    if found:
                        logger.info(f"Encontradas {len(found)} entradas usando: {description}")
                        entry_elements = found
                        break
                    else:
                        logger.debug(f"No se encontraron entradas con: {description}")
                except Exception as e:
                    logger.debug(f"Error buscando con {description}: {e}")
            
            # Si aún no encontramos, buscar en toda la estructura de forma recursiva
            if not entry_elements:
                logger.debug("Buscando elementos 'entry' de forma recursiva...")
                for elem in root.iter():
                    # Extraer solo el nombre del tag sin namespace
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag_name == 'entry':
                        logger.debug(f"Entry encontrado: {elem.tag}")
                        entry_elements.append(elem)
            
            if not entry_elements:
                logger.warning("No se encontraron elementos <entry> en el archivo")
                # Debug: mostrar algunos elementos del archivo
                logger.debug("Primeros 10 elementos en el archivo:")
                for i, elem in enumerate(root.iter()):
                    if i >= 10:
                        break
                    logger.debug(f"  {elem.tag}")
                return []
                
            logger.info(f"Procesando {len(entry_elements)} entradas encontradas")
            
            for entry in entry_elements:
                entry_data = self.extract_entry_data(entry, all_namespaces)
                if entry_data:
                    entries.append(entry_data)
                    
            logger.info(f"Extraídas {len(entries)} entradas válidas del archivo")
            return entries
            
        except ET.ParseError as e:
            logger.error(f"Error parseando XML en {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error procesando {file_path}: {e}")
            return []

    def extract_entry_data(self, entry, namespaces: Dict = None) -> Optional[Dict]:
        """
        Extraer datos específicos de una entrada ATOM.
        
        Args:
            entry: Elemento XML de la entrada
            namespaces: Diccionario de namespaces a usar
            
        Returns:
            Diccionario con los datos extraídos
        """
        if namespaces is None:
            namespaces = self.namespaces
            
        data = {}
        
        # Función auxiliar para buscar elementos con namespace por defecto
        def find_element(parent, tag_name):
            # Primero intentar sin namespace
            element = parent.find(tag_name)
            if element is not None:
                return element
            
            # Intentar con namespace de Atom explícito
            element = parent.find(f'{{http://www.w3.org/2005/Atom}}{tag_name}')
            if element is not None:
                return element
                
            # Intentar búsqueda recursiva
            for elem in parent.iter():
                if elem.tag.endswith(f'}}{tag_name}') or elem.tag == tag_name:
                    return elem
            return None
        
        # Extraer campos básicos de ATOM
        data['id'] = self._get_text(find_element(entry, 'id'))
        data['title'] = self._get_text(find_element(entry, 'title'))
        data['summary'] = self._get_text(find_element(entry, 'summary'))
        data['updated'] = self._get_text(find_element(entry, 'updated'))
        
        # Extraer link - puede tener atributo href
        link_element = find_element(entry, 'link')
        if link_element is not None:
            # Primero intentar atributo href
            data['link'] = link_element.get('href')
            # Si no hay href, usar el texto del elemento
            if not data['link']:
                data['link'] = self._get_text(link_element)
        else:
            data['link'] = None
            
        # Buscar TechnicalDocumentReference en la estructura real
        # Basado en la muestra, está dentro de cac-place-ext:ContractFolderStatus
        contract_status = entry.find('.//cac-place-ext:ContractFolderStatus', namespaces)
        if contract_status is None:
            # Intentar sin namespace
            contract_status = entry.find('.//ContractFolderStatus')
            
        if contract_status is not None:
            tech_doc_ref = contract_status.find('.//cac:TechnicalDocumentReference', namespaces)
            if tech_doc_ref is None:
                tech_doc_ref = contract_status.find('.//TechnicalDocumentReference')
                
            if tech_doc_ref is not None:
                attachment = tech_doc_ref.find('.//cac:Attachment', namespaces)
                if attachment is None:
                    attachment = tech_doc_ref.find('.//Attachment')
                    
                if attachment is not None:
                    external_ref = attachment.find('.//cac:ExternalReference', namespaces)
                    if external_ref is None:
                        external_ref = attachment.find('.//ExternalReference')
                        
                    if external_ref is not None:
                        uri_element = external_ref.find('.//cbc:URI', namespaces)
                        if uri_element is None:
                            uri_element = external_ref.find('.//URI')
                            
                        if uri_element is not None:
                            data['document_uri'] = self._get_text(uri_element)
        
        # Buscar todos los cac:PartyName y concatenar sus cbc:Name
        party_names = []
        
        # Buscar en toda la entrada
        for party_name_elem in entry.findall('.//cac:PartyName', namespaces):
            name_elem = party_name_elem.find('cbc:Name', namespaces)
            if name_elem is None:
                name_elem = party_name_elem.find('Name')
            if name_elem is not None and name_elem.text:
                party_names.append(name_elem.text.strip())
        
        # Si no encontramos con namespaces, intentar sin ellos
        if not party_names:
            for party_name_elem in entry.findall('.//PartyName'):
                name_elem = party_name_elem.find('Name')
                if name_elem is not None and name_elem.text:
                    party_names.append(name_elem.text.strip())
        
        # Concatenar todos los nombres encontrados
        data['party_names'] = ' | '.join(party_names) if party_names else None
        
        # Buscar todos los códigos de clasificación de commodities
        classification_codes = []
        
        # Buscar en toda la entrada
        for classification_elem in entry.findall('.//cac:RequiredCommodityClassification', namespaces):
            code_elem = classification_elem.find('cbc:ItemClassificationCode', namespaces)
            if code_elem is None:
                code_elem = classification_elem.find('ItemClassificationCode')
            if code_elem is not None and code_elem.text:
                classification_codes.append(code_elem.text.strip())
        
        # Si no encontramos con namespaces, intentar sin ellos
        if not classification_codes:
            for classification_elem in entry.findall('.//RequiredCommodityClassification'):
                code_elem = classification_elem.find('ItemClassificationCode')
                if code_elem is not None and code_elem.text:
                    classification_codes.append(code_elem.text.strip())
        
        # Concatenar todos los códigos encontrados
        data['classification_codes'] = ' | '.join(classification_codes) if classification_codes else None
        
        # Debug: mostrar lo que se extrajo
        logger.debug(f"Datos extraídos de entry: {data}")
                            
        return data if any(v for v in data.values() if v) else None
    
    def _get_text(self, element) -> Optional[str]:
        """Obtener texto de un elemento XML de forma segura."""
        if element is not None and element.text:
            return element.text.strip()
        return None

    def download_document(self, uri: str, entry_id: str) -> Optional[str]:
        """
        Descargar documento desde URI.
        
        Args:
            uri: URI del documento
            entry_id: ID de la entrada (para nombrar el archivo)
            
        Returns:
            Ruta del archivo descargado o None si falla
        """
        try:
            logger.info(f"Descargando documento desde: {uri}")
            
            response = self.session.get(uri, stream=True)
            response.raise_for_status()
            
            # Determinar nombre del archivo
            parsed_url = urlparse(uri)
            filename = os.path.basename(parsed_url.path)
            
            if not filename or '.' not in filename:
                # Usar Content-Disposition si está disponible
                content_disp = response.headers.get('content-disposition', '')
                if 'filename=' in content_disp:
                    filename = content_disp.split('filename=')[1].strip('"\'')
                else:
                    # Generar nombre basado en entry_id
                    filename = f"{entry_id.replace('/', '_').replace(':', '_')}.pdf"
                    
            file_path = self.download_dir / filename
            
            # Evitar sobrescribir archivos
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = self.download_dir / f"{stem}_{counter}{suffix}"
                counter += 1
                
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Documento descargado: {file_path}")
            return str(file_path)
            
        except requests.RequestException as e:
            logger.error(f"Error descargando documento desde {uri}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error guardando documento: {e}")
            return None

    def process_entries(self, entries: List[Dict], name_filter: str = None, code_filter: str = None) -> List[Dict]:
        """
        Procesar entradas y descargar documentos asociados.
        
        Args:
            entries: Lista de entradas extraídas
            name_filter: Filtro opcional por subcadena en party_names
            code_filter: Filtro opcional por subcadena en classification_codes
            
        Returns:
            Lista de entradas con información de descarga
        """
        processed_entries = []
        
        for entry in entries:
            logger.info(f"Procesando entrada: {entry.get('id', 'Sin ID')}")
            
            # Aplicar filtro por nombre si se especifica
            if name_filter:
                party_names = entry.get('party_names', '')
                if not party_names or name_filter.lower() not in party_names.lower():
                    logger.debug(f"Entrada filtrada por nombre: {name_filter} no encontrado en {party_names}")
                    continue
            
            # Aplicar filtro por código si se especifica
            if code_filter:
                classification_codes = entry.get('classification_codes', '')
                if not classification_codes or code_filter.lower() not in classification_codes.lower():
                    logger.debug(f"Entrada filtrada por código: {code_filter} no encontrado en {classification_codes}")
                    continue
                    
            # Descargar documento si tiene URI
            if entry.get('document_uri'):
                downloaded_file = self.download_document(
                    entry['document_uri'], 
                    entry.get('id', 'unknown')
                )
                entry['downloaded_file'] = downloaded_file
            else:
                entry['downloaded_file'] = None
                logger.info("No se encontró URI de documento para esta entrada")
                
            processed_entries.append(entry)
            
            # Pequeña pausa para no sobrecargar el servidor
            time.sleep(0.5)
            
        return processed_entries

    def save_results(self, all_entries: List[Dict], output_file: str = "extracted_data.txt"):
        """
        Guardar resultados en archivo de texto.
        
        Args:
            all_entries: Todas las entradas procesadas
            output_file: Archivo donde guardar los resultados
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Datos extraídos - Total de entradas: {len(all_entries)}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, entry in enumerate(all_entries, 1):
                f.write(f"ENTRADA {i}:\n")
                f.write(f"ID: {entry.get('id', 'N/A')}\n")
                f.write(f"Título: {entry.get('title', 'N/A')}\n")
                f.write(f"Link: {entry.get('link', 'N/A')}\n")
                f.write(f"Resumen: {entry.get('summary', 'N/A')}\n")
                f.write(f"Actualizado: {entry.get('updated', 'N/A')}\n")
                f.write(f"URI Documento: {entry.get('document_uri', 'N/A')}\n")
                f.write(f"Nombres de Partes: {entry.get('party_names', 'N/A')}\n")
                f.write(f"Códigos de Clasificación: {entry.get('classification_codes', 'N/A')}\n")
                f.write(f"Archivo Descargado: {entry.get('downloaded_file', 'N/A')}\n")
                f.write("-" * 30 + "\n\n")
                
        logger.info(f"Resultados guardados en: {output_file}")

    def inspect_atom_file(self, file_path: str) -> None:
        """
        Inspeccionar la estructura de un archivo ATOM para debug.
        
        Args:
            file_path: Ruta del archivo .atom
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            print(f"\n=== INSPECCIÓN DE {file_path} ===")
            print(f"Root tag: {root.tag}")
            print(f"Root attrib: {root.attrib}")
            
            # Función recursiva para mostrar jerarquía
            def show_hierarchy(element, level=0, max_level=3):
                indent = "  " * level
                tag_name = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                print(f"{indent}- {tag_name} ({element.tag})")
                
                if level < max_level:
                    children_shown = 0
                    for child in element:
                        if children_shown < 5:  # Limitar a 5 hijos por nivel
                            show_hierarchy(child, level + 1, max_level)
                            children_shown += 1
                        elif children_shown == 5:
                            print(f"{indent}  ... (y {len(list(element)) - 5} más)")
                            break
            
            print(f"\nJerarquía de elementos (primeros 3 niveles):")
            show_hierarchy(root)
                    
            # Buscar cualquier elemento que sea exactamente 'entry'
            print(f"\nElementos 'entry' encontrados:")
            entry_count = 0
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'entry':
                    parent_tag = elem.getparent().tag if hasattr(elem, 'getparent') and elem.getparent() is not None else 'root'
                    parent_name = parent_tag.split('}')[-1] if '}' in parent_tag else parent_tag
                    print(f"  - entry #{entry_count + 1}: {elem.tag} (padre: {parent_name})")
                    entry_count += 1
                    
                    # Mostrar algunos hijos del entry
                    if entry_count == 1:  # Solo para el primer entry
                        print(f"    Hijos del primer entry:")
                        for child in list(elem)[:10]:  # Primeros 10 hijos
                            child_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            print(f"      - {child_name}: {child.text[:50] if child.text else 'No text'}...")
                            
            if entry_count == 0:
                print("  ❌ No se encontraron elementos 'entry'")
            else:
                print(f"  ✅ Total encontrados: {entry_count}")
                
        except Exception as e:
            print(f"Error inspeccionando archivo: {e}")
            import traceback
            traceback.print_exc()

    def run(self, source: str, is_url: bool = True, inspect_only: bool = False, is_atom_file: bool = False, name_filter: str = None, code_filter: str = None, output_file: str = "extracted_data.txt") -> List[Dict]:
        """
        Ejecutar el proceso completo de extracción.
        
        Args:
            source: URL del ZIP, ruta local del archivo ZIP, o ruta del archivo .atom
            is_url: True si source es una URL, False si es archivo local
            inspect_only: Si True, solo inspecciona el primer archivo .atom encontrado
            is_atom_file: Si True, source es un archivo .atom directamente
            name_filter: Filtro opcional por subcadena en party_names
            code_filter: Filtro opcional por subcadena en classification_codes
            output_file: Nombre del archivo donde guardar los resultados
            
        Returns:
            Lista de todas las entradas procesadas
        """
        try:
            # Caso especial: procesar archivo .atom directamente
            if is_atom_file:
                if not os.path.exists(source):
                    raise FileNotFoundError(f"Archivo .atom no encontrado: {source}")
                
                if inspect_only:
                    self.inspect_atom_file(source)
                    return []
                
                logger.info(f"Procesando archivo .atom directamente: {source}")
                entries = self.parse_atom_file(source)
                processed_entries = self.process_entries(entries, name_filter, code_filter)
                
                # Mostrar estadísticas del filtro
                filters_applied = []
                if name_filter:
                    filters_applied.append(f"nombre: '{name_filter}'")
                if code_filter:
                    filters_applied.append(f"código: '{code_filter}'")
                    
                if filters_applied:
                    filter_str = ", ".join(filters_applied)
                    logger.info(f"Filtros aplicados ({filter_str}) -> {len(processed_entries)}/{len(entries)} entradas")
                
                # Guardar resultados
                self.save_results(processed_entries, output_file)
                
                logger.info(f"Proceso completado. Total de entradas procesadas: {len(processed_entries)}")
                return processed_entries
            
            # Proceso normal con ZIP
            # Paso 1: Obtener archivo ZIP
            if is_url:
                zip_path = self.download_zip(source)
            else:
                zip_path = source
                if not os.path.exists(zip_path):
                    raise FileNotFoundError(f"Archivo ZIP no encontrado: {zip_path}")
                    
            # Paso 2: Extraer ZIP
            extract_dir = self.extract_zip(zip_path)
            
            # Paso 3: Buscar archivos .atom
            atom_files = self.find_atom_files(extract_dir)
            
            if not atom_files:
                logger.warning("No se encontraron archivos .atom")
                return []
                
            # Si solo queremos inspeccionar
            if inspect_only:
                self.inspect_atom_file(atom_files[0])
                return []
                
            # Paso 4: Procesar cada archivo .atom
            all_entries = []
            total_before_filter = 0
            
            for atom_file in atom_files:
                entries = self.parse_atom_file(atom_file)
                total_before_filter += len(entries)
                processed_entries = self.process_entries(entries, name_filter, code_filter)
                all_entries.extend(processed_entries)
                
            # Mostrar estadísticas del filtro
            filters_applied = []
            if name_filter:
                filters_applied.append(f"nombre: '{name_filter}'")
            if code_filter:
                filters_applied.append(f"código: '{code_filter}'")
                
            if filters_applied:
                filter_str = ", ".join(filters_applied)
                logger.info(f"Filtros aplicados ({filter_str}) -> {len(all_entries)}/{total_before_filter} entradas totales")
                
            # Paso 5: Guardar resultados
            self.save_results(all_entries, output_file)
            
            # Limpiar archivos temporales si se descargó de URL
            if is_url and os.path.exists(zip_path):
                os.remove(zip_path)
                
            logger.info(f"Proceso completado. Total de entradas procesadas: {len(all_entries)}")
            return all_entries
            
        except Exception as e:
            logger.error(f"Error en el proceso: {e}")
            raise


def main():
    """Función principal para ejecutar desde línea de comandos."""
    parser = argparse.ArgumentParser(description='Extraer datos de archivos ATOM desde ZIP o archivo .atom individual')
    parser.add_argument('source', help='URL del ZIP, ruta del archivo ZIP local, o ruta del archivo .atom')
    parser.add_argument('--local', action='store_true', 
                       help='Indica que source es un archivo local (ZIP o .atom), no una URL')
    parser.add_argument('--atom', action='store_true',
                       help='Indica que source es un archivo .atom directamente (no un ZIP)')
    parser.add_argument('--output-dir', default='downloaded_docs', 
                       help='Directorio para documentos descargados (default: downloaded_docs)')
    parser.add_argument('--output-file', default='extracted_data.txt',
                       help='Archivo para guardar resultados (default: extracted_data.txt)')
    parser.add_argument('--inspect', action='store_true',
                       help='Solo inspeccionar la estructura del archivo .atom')
    parser.add_argument('--filter-name', type=str, default=None,
                       help='Filtrar entradas por subcadena en nombres de partes (case-insensitive)')
    parser.add_argument('--filter-code', type=str, default=None,
                       help='Filtrar entradas por subcadena en códigos de clasificación (case-insensitive)')
    
    args = parser.parse_args()
    
    # Validaciones
    if args.atom and not args.local:
        print("❌ Error: Si usas --atom, también debes usar --local")
        sys.exit(1)
        
    if args.atom and not args.source.endswith('.atom'):
        print("❌ Error: Con --atom, el archivo debe tener extensión .atom")
        sys.exit(1)
    
    try:
        extractor = AtomExtractor(download_dir=args.output_dir)
        
        if args.inspect:
            print("🔍 Modo inspección activado...")
            if args.atom:
                extractor.inspect_atom_file(args.source)
            else:
                extractor.run(args.source, is_url=not args.local, inspect_only=True)
        else:
            # Mostrar información de los filtros si se especifican
            filters_info = []
            if args.filter_name:
                filters_info.append(f"nombre: '{args.filter_name}'")
            if args.filter_code:
                filters_info.append(f"código: '{args.filter_code}'")
            
            if filters_info:
                print(f"🔍 Aplicando filtros por {', '.join(filters_info)}")
                
            entries = extractor.run(
                args.source, 
                is_url=not args.local, 
                is_atom_file=args.atom,
                name_filter=args.filter_name,
                code_filter=args.filter_code,
                output_file=args.output_file
            )
            
            print(f"\n✅ Proceso completado exitosamente!")
            if filters_info:
                print(f"🔍 Filtros aplicados: {', '.join(filters_info)}")
            print(f"📊 Entradas procesadas: {len(entries)}")
            print(f"📁 Documentos descargados en: {args.output_dir}")
            print(f"📄 Resultados guardados en: {args.output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
