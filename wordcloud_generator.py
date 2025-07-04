#!/usr/bin/env python3
"""
Script para generar nubes de palabras (word clouds) a partir de archivos CSV
con tecnologías informáticas extraídas de documentos PDF.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
import pandas as pd

try:
    from wordcloud import WordCloud
except ImportError:
    print("❌ Error: wordcloud no está instalado. Instálalo con: pip install wordcloud")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
except ImportError:
    print("❌ Error: matplotlib no está instalado. Instálalo con: pip install matplotlib")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("❌ Error: numpy no está instalado. Instálalo con: pip install numpy")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WordCloudGenerator:
    def __init__(self, output_dir: str = "wordclouds"):
        """
        Inicializar el generador de nubes de palabras.
        
        Args:
            output_dir: Directorio donde guardar las nubes de palabras generadas
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configuración por defecto para las nubes de palabras
        self.default_config = {
            'width': 1600,
            'height': 800,
            'background_color': 'white',
            'max_words': 100,
            'colormap': 'viridis',
            'relative_scaling': 0.5,
            'min_font_size': 10,
            'max_font_size': 100,
            'prefer_horizontal': 0.7
        }
        
        # Paletas de colores predefinidas
        self.color_schemes = {
            'tech_blue': ['#1e3a8a', '#3b82f6', '#60a5fa', '#93c5fd', '#dbeafe'],
            'tech_green': ['#065f46', '#059669', '#10b981', '#34d399', '#a7f3d0'],
            'tech_purple': ['#581c87', '#7c3aed', '#8b5cf6', '#a78bfa', '#ddd6fe'],
            'sunset': ['#dc2626', '#ea580c', '#f59e0b', '#eab308', '#84cc16'],
            'ocean': ['#0c4a6e', '#0369a1', '#0284c7', '#0ea5e9', '#38bdf8'],
            'forest': ['#14532d', '#166534', '#15803d', '#16a34a', '#22c55e'],
            'default': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        }
    
    def load_csv_data(self, csv_file: str) -> pd.DataFrame:
        """
        Cargar datos desde archivo CSV.
        
        Args:
            csv_file: Ruta del archivo CSV
            
        Returns:
            DataFrame con los datos cargados
        """
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"Archivo CSV no encontrado: {csv_file}")
        
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            logger.info(f"CSV cargado: {len(df)} filas")
            
            # Verificar columnas esperadas
            if 'Tecnologia_Encontrada' not in df.columns:
                raise ValueError("El CSV debe tener una columna 'Tecnologia_Encontrada'")
            
            return df
            
        except Exception as e:
            logger.error(f"Error cargando CSV: {e}")
            raise
    
    def count_technologies(self, df: pd.DataFrame) -> Counter:
        """
        Contar frecuencia de tecnologías.
        
        Args:
            df: DataFrame con los datos
            
        Returns:
            Counter con frecuencias de tecnologías
        """
        tech_counts = Counter(df['Tecnologia_Encontrada'].str.lower())
        logger.info(f"Tecnologías únicas encontradas: {len(tech_counts)}")
        logger.info(f"Total de menciones: {sum(tech_counts.values())}")
        
        return tech_counts
    
    def get_color_function(self, color_scheme: str):
        """
        Crear función de color para la nube de palabras.
        
        Args:
            color_scheme: Nombre del esquema de colores
            
        Returns:
            Función de color para wordcloud
        """
        if color_scheme in self.color_schemes:
            colors = self.color_schemes[color_scheme]
        else:
            colors = self.color_schemes['default']
        
        def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
            # Seleccionar color basado en la frecuencia (font_size)
            if font_size > 60:
                return colors[0]  # Más frecuente - color más intenso
            elif font_size > 40:
                return colors[1]
            elif font_size > 25:
                return colors[2]
            elif font_size > 15:
                return colors[3]
            else:
                return colors[4]  # Menos frecuente - color más claro
        
        return color_func
    
    def create_wordcloud(self, 
                        word_frequencies: Dict[str, int], 
                        title: str = "Tecnologías Informáticas",
                        color_scheme: str = 'tech_blue',
                        custom_config: Optional[Dict] = None) -> WordCloud:
        """
        Crear nube de palabras.
        
        Args:
            word_frequencies: Diccionario con frecuencias de palabras
            title: Título para la nube de palabras
            color_scheme: Esquema de colores a usar
            custom_config: Configuración personalizada
            
        Returns:
            Objeto WordCloud generado
        """
        # Combinar configuración por defecto con personalizada
        config = self.default_config.copy()
        if custom_config:
            config.update(custom_config)
        
        logger.info(f"Generando nube de palabras: {title}")
        logger.info(f"Esquema de colores: {color_scheme}")
        logger.info(f"Palabras a incluir: {len(word_frequencies)}")
        
        # Crear función de color personalizada
        color_func = self.get_color_function(color_scheme)
        
        # Generar nube de palabras
        wordcloud = WordCloud(
            width=config['width'],
            height=config['height'],
            background_color=config['background_color'],
            max_words=config['max_words'],
            relative_scaling=config['relative_scaling'],
            min_font_size=config['min_font_size'],
            max_font_size=config['max_font_size'],
            prefer_horizontal=config['prefer_horizontal'],
            color_func=color_func
        ).generate_from_frequencies(word_frequencies)
        
        return wordcloud
    
    def save_wordcloud(self, 
                      wordcloud: WordCloud, 
                      filename: str, 
                      title: str = "",
                      show_stats: bool = True,
                      dpi: int = 300,
                      original_frequencies: Dict[str, int] = None):
        """
        Guardar nube de palabras como imagen.
        
        Args:
            wordcloud: Objeto WordCloud a guardar
            filename: Nombre del archivo (sin extensión)
            title: Título a mostrar en la imagen
            show_stats: Si mostrar estadísticas en la imagen
            dpi: Resolución de la imagen
            original_frequencies: Frecuencias originales sin normalizar
        """
        # Crear figura
        plt.figure(figsize=(16, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        
        if title:
            plt.title(title, fontsize=20, fontweight='bold', pad=20)
        
        # Agregar estadísticas si se solicita
        if show_stats:
            total_words = len([word for word in wordcloud.words_])
            
            # Usar las frecuencias originales si están disponibles
            if original_frequencies:
                max_freq = max(original_frequencies.values()) if original_frequencies else 0
            else:
                max_freq = max(wordcloud.words_.values()) if wordcloud.words_ else 0
                
            stats_text = f"Tecnologías únicas: {total_words} | Frecuencia máxima: {max_freq}"
            plt.figtext(0.5, 0.02, stats_text, ha='center', fontsize=12, style='italic')
        
        # Guardar imagen
        output_path = self.output_dir / f"{filename}.png"
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Nube de palabras guardada: {output_path}")
        return str(output_path)
    
    def generate_multiple_wordclouds(self, 
                                   word_frequencies: Dict[str, int],
                                   main_title: str = "Tecnologías Informáticas",
                                   base_filename: str = "wordcloud_tecnologias"):
        """
        Generar múltiples nubes de palabras con diferentes estilos.
        
        Args:
            word_frequencies: Diccionario con frecuencias de palabras
            main_title: Título base para personalizar
            base_filename: Nombre base para los archivos
            
        Returns:
            Lista de rutas de archivos generados
        """
        generated_files = []
        
        # Configuraciones predefinidas
        configurations = [
            {
                'color_scheme': 'tech_blue',
                'title': f'{main_title} - Estilo Azul',
                'filename': f"{base_filename}_azul"
            },
            {
                'color_scheme': 'tech_green',
                'title': f'{main_title} - Estilo Verde',
                'filename': f"{base_filename}_verde"
            },
            {
                'color_scheme': 'sunset',
                'title': f'{main_title} - Estilo Sunset',
                'filename': f"{base_filename}_sunset"
            },
            {
                'color_scheme': 'ocean',
                'title': f'{main_title} - Estilo Océano',
                'filename': f"{base_filename}_oceano"
            }
        ]
        
        for config in configurations:
            try:
                wordcloud = self.create_wordcloud(
                    word_frequencies, 
                    title=config['title'],
                    color_scheme=config['color_scheme']
                )
                
                file_path = self.save_wordcloud(
                    wordcloud, 
                    config['filename'], 
                    config['title'],
                    original_frequencies=word_frequencies
                )
                
                generated_files.append(file_path)
                
            except Exception as e:
                logger.error(f"Error generando {config['filename']}: {e}")
        
        return generated_files
    
    def create_top_technologies_wordcloud(self, 
                                        word_frequencies: Dict[str, int], 
                                        top_n: int = 50,
                                        color_scheme: str = 'tech_purple') -> str:
        """
        Crear nube de palabras solo con las top N tecnologías.
        
        Args:
            word_frequencies: Diccionario con frecuencias de palabras
            top_n: Número de tecnologías top a incluir
            color_scheme: Esquema de colores
            
        Returns:
            Ruta del archivo generado
        """
        # Obtener top N tecnologías
        counter = Counter(word_frequencies)
        top_technologies = dict(counter.most_common(top_n))
        
        logger.info(f"Generando nube con top {top_n} tecnologías")
        
        wordcloud = self.create_wordcloud(
            top_technologies,
            title=f"Top {top_n} Tecnologías Más Mencionadas",
            color_scheme=color_scheme
        )
        
        filename = f"wordcloud_top_{top_n}_tecnologias"
        return self.save_wordcloud(wordcloud, filename, 
                                 f"Top {top_n} Tecnologías Más Mencionadas",
                                 original_frequencies=top_technologies)
    
    def generate_summary_report(self, word_frequencies: Dict[str, int]) -> str:
        """
        Generar reporte de resumen de las tecnologías.
        
        Args:
            word_frequencies: Diccionario con frecuencias de palabras
            
        Returns:
            Ruta del archivo de reporte generado
        """
        counter = Counter(word_frequencies)
        
        report_path = self.output_dir / "resumen_tecnologias.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("RESUMEN DE TECNOLOGÍAS ENCONTRADAS\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"📊 ESTADÍSTICAS GENERALES:\n")
            f.write(f"Total de tecnologías únicas: {len(counter)}\n")
            f.write(f"Total de menciones: {sum(counter.values())}\n")
            f.write(f"Promedio de menciones por tecnología: {sum(counter.values()) / len(counter):.1f}\n\n")
            
            f.write(f"🏆 TOP 20 TECNOLOGÍAS MÁS MENCIONADAS:\n")
            f.write("-" * 50 + "\n")
            for i, (tech, count) in enumerate(counter.most_common(20), 1):
                percentage = (count / sum(counter.values())) * 100
                f.write(f"{i:2d}. {tech:25} - {count:3d} menciones ({percentage:4.1f}%)\n")
            
            f.write(f"\n📈 DISTRIBUCIÓN POR FRECUENCIA:\n")
            f.write("-" * 30 + "\n")
            
            # Agrupar por rangos de frecuencia
            freq_ranges = {
                'Muy frecuentes (>10)': len([c for c in counter.values() if c > 10]),
                'Frecuentes (5-10)': len([c for c in counter.values() if 5 <= c <= 10]),
                'Moderadas (2-4)': len([c for c in counter.values() if 2 <= c <= 4]),
                'Poco frecuentes (1)': len([c for c in counter.values() if c == 1])
            }
            
            for range_name, count in freq_ranges.items():
                f.write(f"{range_name:20}: {count:3d} tecnologías\n")
        
        logger.info(f"Reporte de resumen guardado: {report_path}")
        return str(report_path)
    
    def run(self, csv_file: str, generate_multiple: bool = True, top_n: int = 50, main_title: str = "Tecnologías Informáticas", main_color_scheme: str = "tech_blue") -> Dict:
        """
        Ejecutar la generación completa de nubes de palabras.
        
        Args:
            csv_file: Archivo CSV con los datos
            generate_multiple: Si generar múltiples estilos
            top_n: Número de tecnologías top para nube especial
            main_title: Título personalizado para la nube principal
            main_color_scheme: Esquema de colores para la nube principal
            
        Returns:
            Diccionario con información de archivos generados
        """
        logger.info(f"Iniciando generación de nubes de palabras desde: {csv_file}")
        
        # Cargar datos
        df = self.load_csv_data(csv_file)
        
        # Contar tecnologías
        tech_counts = self.count_technologies(df)
        word_frequencies = dict(tech_counts)
        
        generated_files = []
        
        # Generar nube principal con título y esquema de colores personalizados
        wordcloud = self.create_wordcloud(word_frequencies, title=main_title, color_scheme=main_color_scheme)
        main_file = self.save_wordcloud(wordcloud, "wordcloud_tecnologias_principal", main_title, 
                                      original_frequencies=word_frequencies)
        generated_files.append(main_file)
        
        # Generar múltiples estilos si se solicita
        if generate_multiple:
            multiple_files = self.generate_multiple_wordclouds(word_frequencies, main_title)
            generated_files.extend(multiple_files)
        
        # Generar nube con top tecnologías
        top_file = self.create_top_technologies_wordcloud(word_frequencies, top_n)
        generated_files.append(top_file)
        
        # Generar reporte de resumen
        report_file = self.generate_summary_report(word_frequencies)
        
        logger.info(f"Generación completada. {len(generated_files)} nubes de palabras creadas.")
        
        return {
            'wordcloud_files': generated_files,
            'report_file': report_file,
            'total_technologies': len(tech_counts),
            'total_mentions': sum(tech_counts.values()),
            'top_technology': tech_counts.most_common(1)[0] if tech_counts else None
        }


def main():
    """Función principal para ejecutar desde línea de comandos."""
    parser = argparse.ArgumentParser(description='Generar nubes de palabras de tecnologías desde CSV')
    parser.add_argument('csv_file', help='Archivo CSV con las tecnologías extraídas')
    parser.add_argument('--output-dir', default='wordclouds', 
                       help='Directorio para guardar las nubes de palabras (default: wordclouds)')
    parser.add_argument('--no-multiple', action='store_true',
                       help='No generar múltiples estilos, solo la nube principal')
    parser.add_argument('--top-n', type=int, default=50,
                       help='Número de tecnologías top para nube especial (default: 50)')
    parser.add_argument('--color-scheme', default='tech_blue',
                       choices=['tech_blue', 'tech_green', 'tech_purple', 'sunset', 'ocean', 'forest'],
                       help='Esquema de colores para la nube principal (default: tech_blue)')
    parser.add_argument('--title', default='Tecnologías Informáticas',
                       help='Título personalizado para la nube de palabras (default: Tecnologías Informáticas)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mostrar información detallada de procesamiento')
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        generator = WordCloudGenerator(output_dir=args.output_dir)
        
        results = generator.run(
            csv_file=args.csv_file,
            generate_multiple=not args.no_multiple,
            top_n=args.top_n,
            main_title=args.title,
            main_color_scheme=args.color_scheme
        )
        
        print(f"\n✅ Nubes de palabras generadas exitosamente!")
        print(f"📊 Tecnologías únicas procesadas: {results['total_technologies']}")
        print(f"📈 Total de menciones: {results['total_mentions']}")
        
        if results['top_technology']:
            tech, count = results['top_technology']
            print(f"🏆 Tecnología más mencionada: {tech} ({count} veces)")
        
        print(f"\n📁 Archivos generados:")
        for file_path in results['wordcloud_files']:
            print(f"   🖼️  {os.path.basename(file_path)}")
        print(f"   📄 {os.path.basename(results['report_file'])}")
        
        print(f"\n📂 Directorio de salida: {args.output_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
