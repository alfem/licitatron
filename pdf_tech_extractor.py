#!/usr/bin/env python3
"""
Script para extraer tecnologías y productos informáticos de documentos PDF.
Analiza documentos en un directorio y busca palabras clave relacionadas con IT.
"""

import os
import sys
import re
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
import json
from collections import Counter, defaultdict

try:
    import PyPDF2
except ImportError:
    print("❌ Error: PyPDF2 no está instalado. Instálalo con: pip install PyPDF2")
    sys.exit(1)

try:
    import pdfplumber
except ImportError:
    print("⚠️  Advertencia: pdfplumber no está instalado. Funcionalidad limitada.")
    print("   Para mejor extracción de texto: pip install pdfplumber")
    pdfplumber = None

try:
    import yaml
except ImportError:
    print("❌ Error: PyYAML no está instalado. Instálalo con: pip install PyYAML")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechExtractor:
    def __init__(self, output_dir: str = "tech_analysis", keywords_file: str = "tech_keywords.yaml"):
        """
        Inicializar el extractor de tecnologías.
        
        Args:
            output_dir: Directorio donde guardar los resultados del análisis
            keywords_file: Archivo YAML con las palabras clave de tecnologías
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.keywords_file = keywords_file
        
        # Cargar palabras clave desde archivo YAML
        self.tech_keywords = self.load_keywords()
        
        # Crear un conjunto plano de todas las palabras clave para búsqueda rápida
        self.all_keywords = set()
        for category, keywords in self.tech_keywords.items():
            self.all_keywords.update([kw.lower() for kw in keywords])
    
    def create_default_keywords_file(self) -> Dict:
        """
        Crear archivo de palabras clave por defecto.
        
        Returns:
            Diccionario con las palabras clave por defecto
        """
        default_keywords = {
            'lenguajes_programacion': [
                'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'php', 'ruby', 'go', 'rust',
                'scala', 'kotlin', 'swift', 'dart', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell',
                'visual basic', 'vb.net', 'objective-c', 'assembly', 'cobol', 'fortran', 'lua', 'groovy'
            ],
            'frameworks_web': [
                'react', 'angular', 'vue.js', 'svelte', 'django', 'flask', 'spring', 'laravel', 'symfony',
                'express.js', 'next.js', 'nuxt.js', 'gatsby', 'ember.js', 'backbone.js', 'jquery', 'bootstrap',
                'tailwind', 'material-ui', 'ant design', 'semantic ui', 'foundation', 'bulma'
            ],
            'bases_datos': [
                'mysql', 'postgresql', 'oracle', 'sql server', 'mongodb', 'redis', 'elasticsearch',
                'cassandra', 'dynamodb', 'firebase', 'sqlite', 'mariadb', 'couchdb', 'neo4j',
                'influxdb', 'clickhouse', 'snowflake', 'bigquery', 'redshift', 'teradata'
            ],
            'sistemas_operativos': [
                'windows', 'linux', 'ubuntu', 'centos', 'red hat', 'debian', 'fedora', 'suse',
                'macos', 'android', 'ios', 'unix', 'solaris', 'aix', 'freebsd', 'alpine'
            ],
            'cloud_platforms': [
                'aws', 'amazon web services', 'azure', 'google cloud', 'gcp', 'alibaba cloud',
                'ibm cloud', 'oracle cloud', 'digitalocean', 'linode', 'vultr', 'heroku',
                'vercel', 'netlify', 'cloudflare', 'fastly'
            ],
            'contenedores_orquestacion': [
                'docker', 'kubernetes', 'k8s', 'openshift', 'rancher', 'helm', 'istio',
                'containerd', 'podman', 'lxc', 'docker swarm', 'nomad', 'mesos'
            ],
            'devops_ci_cd': [
                'jenkins', 'gitlab ci', 'github actions', 'azure devops', 'bamboo', 'teamcity',
                'circle ci', 'travis ci', 'ansible', 'terraform', 'puppet', 'chef', 'saltstack',
                'vagrant', 'packer', 'consul', 'vault', 'prometheus', 'grafana', 'elk stack',
                'elasticsearch', 'logstash', 'kibana', 'fluentd', 'splunk'
            ],
            'metodologias': [
                'agile', 'scrum', 'kanban', 'devops', 'lean', 'waterfall', 'xp', 'safe',
                'itil', 'cobit', 'prince2', 'pmp', 'six sigma', 'design thinking'
            ],
            'herramientas_desarrollo': [
                'git', 'svn', 'mercurial', 'jira', 'confluence', 'slack', 'teams', 'zoom',
                'visual studio', 'vs code', 'intellij', 'eclipse', 'netbeans', 'atom',
                'sublime text', 'vim', 'emacs', 'postman', 'insomnia', 'swagger', 'figma',
                'sketch', 'adobe xd', 'invision', 'zeplin'
            ],
            'tecnologias_frontend': [
                'html', 'css', 'sass', 'less', 'webpack', 'parcel', 'rollup', 'vite',
                'babel', 'eslint', 'prettier', 'jest', 'cypress', 'selenium', 'playwright',
                'storybook', 'chromatic', 'pwa', 'service worker'
            ],
            'tecnologias_backend': [
                'node.js', 'express', 'fastapi', 'tornado', 'aiohttp', 'gin', 'echo',
                'spring boot', 'quarkus', 'micronaut', 'nestjs', 'adonis', 'koa',
                'hapi', 'restify', 'graphql', 'apollo', 'prisma', 'typeorm', 'sequelize',
                'mongoose', 'sqlalchemy', 'hibernate', 'mybatis'
            ],
            'arquitectura_patrones': [
                'microservicios', 'monolito', 'serverless', 'soa', 'api rest', 'graphql',
                'grpc', 'websockets', 'mqtt', 'kafka', 'rabbitmq', 'activemq', 'redis pub/sub',
                'event sourcing', 'cqrs', 'saga pattern', 'circuit breaker', 'bulkhead',
                'strangler fig', 'ambassador pattern'
            ],
            'seguridad': [
                'oauth', 'jwt', 'saml', 'ldap', 'active directory', 'ssl', 'tls', 'https',
                'vpn', 'firewall', 'waf', 'ids', 'ips', 'siem', 'soar', 'penetration testing',
                'vulnerability assessment', 'devsecops', 'owasp', 'nist', 'iso 27001'
            ],
            'ia_machine_learning': [
                'tensorflow', 'pytorch', 'scikit-learn', 'keras', 'pandas', 'numpy',
                'jupyter', 'anaconda', 'spark', 'hadoop', 'airflow', 'kubeflow',
                'mlflow', 'wandb', 'hugging face', 'openai', 'gpt', 'bert', 'transformer',
                'neural networks', 'deep learning', 'computer vision', 'nlp', 'reinforcement learning'
            ],
            'protocolos_comunicacion': [
                'http', 'https', 'tcp', 'udp', 'smtp', 'pop3', 'imap', 'ftp', 'sftp',
                'ssh', 'telnet', 'snmp', 'dhcp', 'dns', 'ntp', 'sip', 'rtmp', 'webrtc'
            ]
        }
        
        return default_keywords
    
    def load_keywords(self) -> Dict:
        """
        Cargar palabras clave desde archivo YAML.
        
        Returns:
            Diccionario con las palabras clave
        """
        keywords_path = Path(self.keywords_file)
        
        # Si el archivo no existe, crear uno por defecto
        if not keywords_path.exists():
            logger.info(f"Archivo de palabras clave no encontrado. Creando: {self.keywords_file}")
            default_keywords = self.create_default_keywords_file()
            
            # Guardar archivo por defecto
            with open(keywords_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_keywords, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False, indent=2)
            
            logger.info(f"Archivo creado: {self.keywords_file}")
            logger.info("Puedes editarlo para personalizar las tecnologías a buscar")
            
            return default_keywords
        
        # Cargar archivo existente
        try:
            with open(keywords_path, 'r', encoding='utf-8') as f:
                keywords = yaml.safe_load(f)
            
            if not isinstance(keywords, dict):
                raise ValueError("El archivo YAML debe contener un diccionario")
                
            logger.info(f"Palabras clave cargadas desde: {self.keywords_file}")
            logger.info(f"Categorías encontradas: {list(keywords.keys())}")
            
            return keywords
            
        except Exception as e:
            logger.error(f"Error cargando {self.keywords_file}: {e}")
            logger.info("Usando palabras clave por defecto")
            return self.create_default_keywords_file()
    
    def extract_text_pypdf2(self, pdf_path: str) -> str:
        """
        Extraer texto usando PyPDF2.
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    try:
                        text += page.extract_text() + "\n"
                    except Exception as e:
                        logger.debug(f"Error extrayendo página: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error leyendo PDF con PyPDF2: {e}")
        
        return text
    
    def extract_text_pdfplumber(self, pdf_path: str) -> str:
        """
        Extraer texto usando pdfplumber (mejor calidad).
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        logger.debug(f"Error extrayendo página: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error leyendo PDF con pdfplumber: {e}")
        
        return text
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extraer texto de un PDF usando el mejor método disponible.
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        logger.debug(f"Extrayendo texto de: {pdf_path}")
        
        # Intentar primero con pdfplumber si está disponible
        if pdfplumber:
            text = self.extract_text_pdfplumber(pdf_path)
            if text.strip():
                return text
        
        # Fallback a PyPDF2
        text = self.extract_text_pypdf2(pdf_path)
        return text
    
    def normalize_text(self, text: str) -> str:
        """
        Normalizar texto para búsqueda de palabras clave.
        
        Args:
            text: Texto a normalizar
            
        Returns:
            Texto normalizado
        """
        # Convertir a minúsculas
        text = text.lower()
        
        # Reemplazar caracteres especiales con espacios
        text = re.sub(r'[^\w\s\.\-]', ' ', text)
        
        # Normalizar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def find_technologies(self, text: str) -> Dict[str, List[str]]:
        """
        Buscar tecnologías en el texto.
        
        Args:
            text: Texto donde buscar
            
        Returns:
            Diccionario con tecnologías encontradas por categoría
        """
        normalized_text = self.normalize_text(text)
        found_technologies = defaultdict(list)
        
        for category, keywords in self.tech_keywords.items():
            found_in_category = []
            
            for keyword in keywords:
                # Crear patrón de búsqueda con límites de palabra
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                
                if re.search(pattern, normalized_text):
                    found_in_category.append(keyword)
            
            if found_in_category:
                found_technologies[category] = found_in_category
        
        return dict(found_technologies)
    
    def analyze_pdf(self, pdf_path: str) -> Dict:
        """
        Analizar un PDF individual.
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Diccionario con el análisis del PDF
        """
        logger.info(f"Analizando: {os.path.basename(pdf_path)}")
        
        # Extraer texto
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            logger.warning(f"No se pudo extraer texto de: {pdf_path}")
            return {
                'file': os.path.basename(pdf_path),
                'file_path': pdf_path,
                'text_extracted': False,
                'technologies': {},
                'total_technologies': 0,
                'error': 'No se pudo extraer texto'
            }
        
        # Buscar tecnologías
        technologies = self.find_technologies(text)
        
        # Contar total de tecnologías únicas
        total_tech = sum(len(tech_list) for tech_list in technologies.values())
        
        return {
            'file': os.path.basename(pdf_path),
            'file_path': pdf_path,
            'text_extracted': True,
            'text_length': len(text),
            'technologies': technologies,
            'total_technologies': total_tech,
            'text_preview': text[:500] + "..." if len(text) > 500 else text
        }
    
    def process_directory(self, directory: str, pattern: str = "*.pdf") -> List[Dict]:
        """
        Procesar todos los PDFs en un directorio.
        
        Args:
            directory: Directorio a procesar
            pattern: Patrón de archivos a procesar
            
        Returns:
            Lista de análisis de todos los PDFs
        """
        pdf_dir = Path(directory)
        
        if not pdf_dir.exists():
            raise FileNotFoundError(f"Directorio no encontrado: {directory}")
        
        # Buscar archivos PDF
        pdf_files = list(pdf_dir.glob(pattern))
        
        if not pdf_files:
            logger.warning(f"No se encontraron archivos PDF en: {directory}")
            return []
        
        logger.info(f"Encontrados {len(pdf_files)} archivos PDF para procesar")
        
        results = []
        for pdf_file in pdf_files:
            try:
                result = self.analyze_pdf(str(pdf_file))
                results.append(result)
            except Exception as e:
                logger.error(f"Error procesando {pdf_file}: {e}")
                results.append({
                    'file': pdf_file.name,
                    'file_path': str(pdf_file),
                    'text_extracted': False,
                    'technologies': {},
                    'total_technologies': 0,
                    'error': str(e)
                })
        
        return results
    
    def generate_summary(self, results: List[Dict]) -> Dict:
        """
        Generar resumen de todos los análisis.
        
        Args:
            results: Lista de análisis de PDFs
            
        Returns:
            Diccionario con el resumen
        """
        # Contadores globales
        all_technologies = defaultdict(Counter)
        total_files = len(results)
        files_with_tech = 0
        files_with_errors = 0
        
        for result in results:
            if result.get('error'):
                files_with_errors += 1
                continue
                
            if result.get('total_technologies', 0) > 0:
                files_with_tech += 1
                
            # Contar tecnologías por categoría
            for category, tech_list in result.get('technologies', {}).items():
                for tech in tech_list:
                    all_technologies[category][tech] += 1
        
        # Crear ranking de tecnologías más comunes
        tech_ranking = []
        for category, tech_counter in all_technologies.items():
            for tech, count in tech_counter.most_common():
                tech_ranking.append({
                    'technology': tech,
                    'category': category,
                    'count': count,
                    'percentage': round((count / total_files) * 100, 1)
                })
        
        # Ordenar por frecuencia
        tech_ranking.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            'total_files': total_files,
            'files_with_technologies': files_with_tech,
            'files_with_errors': files_with_errors,
            'success_rate': round((files_with_tech / total_files) * 100, 1) if total_files > 0 else 0,
            'technology_ranking': tech_ranking,
            'categories_summary': {
                category: len(tech_counter) 
                for category, tech_counter in all_technologies.items()
            }
        }
    
    def save_results_csv(self, results: List[Dict], csv_filename: str = "tecnologias_encontradas.csv"):
        """
        Guardar resultados en un único archivo CSV.
        
        Args:
            results: Lista de análisis de documentos
            csv_filename: Nombre del archivo CSV a generar
        """
        import csv
        
        csv_path = self.output_dir / csv_filename
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Cabecera
            writer.writerow(['Documento', 'Tecnologia_Encontrada'])
            
            # Procesar cada documento
            for result in results:
                if result.get('error') or not result.get('technologies'):
                    continue
                    
                # Recopilar todas las tecnologías únicas encontradas en este documento
                all_technologies = set()
                for tech_list in result['technologies'].values():
                    all_technologies.update(tech_list)
                
                # Una fila por cada tecnología única encontrada
                for tech in sorted(all_technologies):
                    writer.writerow([result['file'], tech])
        
        # Contar totales para el log
        total_technologies = 0
        docs_with_tech = 0
        for result in results:
            if result.get('technologies'):
                docs_with_tech += 1
                all_techs = set()
                for tech_list in result['technologies'].values():
                    all_techs.update(tech_list)
                total_technologies += len(all_techs)
        
        logger.info(f"CSV generado: {csv_path}")
        logger.info(f"Total de filas: {total_technologies} (tecnologías de {docs_with_tech} documentos)")
    
    def run(self, directory: str, pattern: str = "*.pdf", csv_filename: str = "tecnologias_encontradas.csv") -> Dict:
        """
        Ejecutar el análisis completo.
        
        Args:
            directory: Directorio con los PDFs
            pattern: Patrón de archivos a procesar
            csv_filename: Nombre del archivo CSV a generar
            
        Returns:
            Diccionario con resultados y resumen
        """
        logger.info(f"Iniciando análisis de tecnologías en: {directory}")
        logger.info(f"Usando archivo de palabras clave: {self.keywords_file}")
        
        # Procesar directorio
        results = self.process_directory(directory, pattern)
        
        if not results:
            logger.warning("No se procesaron archivos")
            return {'results': [], 'summary': {}}
        
        # Generar resumen simple
        summary = self.generate_summary(results)
        
        # Guardar resultados en un único CSV
        self.save_results_csv(results, csv_filename)
        
        logger.info(f"Análisis completado. Procesados {len(results)} archivos.")
        
        return {
            'results': results,
            'summary': summary
        }


def main():
    """Función principal para ejecutar desde línea de comandos."""
    parser = argparse.ArgumentParser(description='Extraer tecnologías informáticas de documentos PDF')
    parser.add_argument('directory', help='Directorio con los archivos PDF a analizar')
    parser.add_argument('--pattern', default='*.pdf', 
                       help='Patrón de archivos a procesar (default: *.pdf)')
    parser.add_argument('--output-dir', default='tech_analysis', 
                       help='Directorio para guardar resultados (default: tech_analysis)')
    parser.add_argument('--keywords-file', default='tech_keywords.yaml',
                       help='Archivo YAML con palabras clave (default: tech_keywords.yaml)')
    parser.add_argument('--csv-file', default='tecnologias_encontradas.csv',
                       help='Nombre del archivo CSV a generar (default: tecnologias_encontradas.csv)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mostrar información detallada de procesamiento')
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        extractor = TechExtractor(output_dir=args.output_dir, keywords_file=args.keywords_file)
        results = extractor.run(args.directory, args.pattern, args.csv_file)
        
        summary = results['summary']
        
        print(f"\n✅ Análisis completado exitosamente!")
        print(f"📊 Archivos procesados: {summary.get('total_files', 0)}")
        print(f"🔍 Archivos con tecnologías: {summary.get('files_with_technologies', 0)}")
        print(f"📈 Tasa de éxito: {summary.get('success_rate', 0)}%")
        
        if summary.get('technology_ranking'):
            print(f"\n🏆 Top 5 tecnologías encontradas:")
            for i, tech in enumerate(summary['technology_ranking'][:5], 1):
                print(f"   {i}. {tech['technology']} ({tech['count']} documentos)")
        
        print(f"\n📁 Archivo CSV generado: {args.output_dir}/{args.csv_file}")
        print(f"📝 Archivo de palabras clave: {args.keywords_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
