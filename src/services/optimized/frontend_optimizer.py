"""
Optimizador de Frontend y Assets para Máximo Rendimiento
Performance-Optimizer Implementation
"""

import os
import json
import gzip
import hashlib
import mimetypes
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime, timedelta
import subprocess
import shutil
from functools import wraps
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

class AssetOptimizer:
    """
    Optimizador de assets estáticos para máximo rendimiento
    """
    
    def __init__(self, static_dir: str, build_dir: str = None):
        """
        Inicializar optimizador de assets
        
        Args:
            static_dir: Directorio de archivos estáticos
            build_dir: Directorio de build optimizado
        """
        self.static_dir = Path(static_dir)
        self.build_dir = Path(build_dir) if build_dir else self.static_dir / "optimized"
        self.cache_dir = self.build_dir / ".cache"
        
        # Crear directorios si no existen
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuraciones de optimización
        self.image_quality = 85
        self.enable_webp = True
        self.enable_gzip = True
        self.enable_brotli = True
        self.minify_js = True
        self.minify_css = True
        
        # Estadísticas de optimización
        self.optimization_stats = defaultdict(lambda: {
            'original_size': 0,
            'optimized_size': 0,
            'compression_ratio': 0,
            'files_processed': 0
        })
        
        logger.info(f"Asset optimizer initialized: {self.static_dir} -> {self.build_dir}")
    
    def optimize_images(self, input_dir: str = None, output_dir: str = None) -> Dict[str, Any]:
        """
        Optimizar imágenes con compresión y conversión a WebP
        
        Args:
            input_dir: Directorio de entrada (opcional)
            output_dir: Directorio de salida (opcional)
            
        Returns:
            Estadísticas de optimización
        """
        input_path = Path(input_dir) if input_dir else self.static_dir
        output_path = Path(output_dir) if output_dir else self.build_dir
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        optimized_files = []
        total_original_size = 0
        total_optimized_size = 0
        
        for image_file in input_path.rglob('*'):
            if image_file.suffix.lower() in image_extensions:
                try:
                    # Calcular rutas de salida
                    relative_path = image_file.relative_to(input_path)
                    output_file = output_path / relative_path
                    webp_file = output_file.with_suffix('.webp')
                    
                    # Crear directorio de salida
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Obtener tamaño original
                    original_size = image_file.stat().st_size
                    total_original_size += original_size
                    
                    # Optimizar imagen original
                    optimized_size = self._optimize_single_image(image_file, output_file)
                    
                    # Crear versión WebP si está habilitado
                    webp_size = 0
                    if self.enable_webp:
                        webp_size = self._convert_to_webp(image_file, webp_file)
                    
                    # Usar la versión más pequeña
                    final_size = min(optimized_size, webp_size) if webp_size > 0 else optimized_size
                    total_optimized_size += final_size
                    
                    optimized_files.append({
                        'file': str(relative_path),
                        'original_size': original_size,
                        'optimized_size': final_size,
                        'compression_ratio': (1 - final_size / original_size) * 100,
                        'webp_available': webp_size > 0
                    })
                    
                    logger.debug(f"Optimized image: {relative_path} ({original_size} -> {final_size} bytes)")
                    
                except Exception as e:
                    logger.error(f"Error optimizing image {image_file}: {e}")
        
        # Actualizar estadísticas
        stats = {
            'files_processed': len(optimized_files),
            'total_original_size': total_original_size,
            'total_optimized_size': total_optimized_size,
            'total_compression_ratio': (1 - total_optimized_size / max(total_original_size, 1)) * 100,
            'files': optimized_files
        }
        
        self.optimization_stats['images'].update(stats)
        
        logger.info(f"Image optimization completed: {len(optimized_files)} files, "
                   f"{stats['total_compression_ratio']:.1f}% compression")
        
        return stats
    
    def _optimize_single_image(self, input_file: Path, output_file: Path) -> int:
        """
        Optimizar una imagen individual
        
        Args:
            input_file: Archivo de entrada
            output_file: Archivo de salida
            
        Returns:
            Tamaño del archivo optimizado
        """
        try:
            # Usar PIL para optimización básica
            from PIL import Image, ImageOpt
            
            with Image.open(input_file) as img:
                # Convertir a RGB si es necesario
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Optimizar y guardar
                img.save(
                    output_file,
                    format='JPEG' if output_file.suffix.lower() in ['.jpg', '.jpeg'] else 'PNG',
                    quality=self.image_quality,
                    optimize=True,
                    progressive=True
                )
            
            return output_file.stat().st_size
            
        except ImportError:
            # Fallback: copiar archivo sin optimización
            shutil.copy2(input_file, output_file)
            return output_file.stat().st_size
        except Exception as e:
            logger.error(f"Error optimizing image {input_file}: {e}")
            shutil.copy2(input_file, output_file)
            return output_file.stat().st_size
    
    def _convert_to_webp(self, input_file: Path, output_file: Path) -> int:
        """
        Convertir imagen a formato WebP
        
        Args:
            input_file: Archivo de entrada
            output_file: Archivo WebP de salida
            
        Returns:
            Tamaño del archivo WebP
        """
        try:
            from PIL import Image
            
            with Image.open(input_file) as img:
                img.save(
                    output_file,
                    format='WebP',
                    quality=self.image_quality,
                    optimize=True
                )
            
            return output_file.stat().st_size
            
        except ImportError:
            logger.warning("PIL not available for WebP conversion")
            return 0
        except Exception as e:
            logger.error(f"Error converting to WebP {input_file}: {e}")
            return 0
    
    def minify_javascript(self, input_dir: str = None, output_dir: str = None) -> Dict[str, Any]:
        """
        Minificar archivos JavaScript
        
        Args:
            input_dir: Directorio de entrada
            output_dir: Directorio de salida
            
        Returns:
            Estadísticas de minificación
        """
        if not self.minify_js:
            return {'files_processed': 0, 'message': 'JavaScript minification disabled'}
        
        input_path = Path(input_dir) if input_dir else self.static_dir
        output_path = Path(output_dir) if output_dir else self.build_dir
        
        js_files = list(input_path.rglob('*.js'))
        minified_files = []
        total_original_size = 0
        total_minified_size = 0
        
        for js_file in js_files:
            try:
                relative_path = js_file.relative_to(input_path)
                output_file = output_path / relative_path
                
                # Crear directorio de salida
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Obtener tamaño original
                original_size = js_file.stat().st_size
                total_original_size += original_size
                
                # Minificar JavaScript
                minified_size = self._minify_js_file(js_file, output_file)
                total_minified_size += minified_size
                
                minified_files.append({
                    'file': str(relative_path),
                    'original_size': original_size,
                    'minified_size': minified_size,
                    'compression_ratio': (1 - minified_size / original_size) * 100
                })
                
                logger.debug(f"Minified JS: {relative_path} ({original_size} -> {minified_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error minifying JS {js_file}: {e}")
        
        stats = {
            'files_processed': len(minified_files),
            'total_original_size': total_original_size,
            'total_minified_size': total_minified_size,
            'total_compression_ratio': (1 - total_minified_size / max(total_original_size, 1)) * 100,
            'files': minified_files
        }
        
        self.optimization_stats['javascript'].update(stats)
        
        logger.info(f"JavaScript minification completed: {len(minified_files)} files, "
                   f"{stats['total_compression_ratio']:.1f}% compression")
        
        return stats
    
    def _minify_js_file(self, input_file: Path, output_file: Path) -> int:
        """
        Minificar un archivo JavaScript individual
        
        Args:
            input_file: Archivo de entrada
            output_file: Archivo de salida
            
        Returns:
            Tamaño del archivo minificado
        """
        try:
            # Intentar usar terser si está disponible
            result = subprocess.run([
                'npx', 'terser', str(input_file),
                '--compress', '--mangle',
                '--output', str(output_file)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return output_file.stat().st_size
            else:
                logger.warning(f"Terser failed for {input_file}, using basic minification")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.debug("Terser not available, using basic minification")
        
        # Minificación básica (remover comentarios y espacios)
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Minificación básica
        minified = self._basic_js_minify(content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(minified)
        
        return output_file.stat().st_size
    
    def _basic_js_minify(self, content: str) -> str:
        """
        Minificación básica de JavaScript
        
        Args:
            content: Contenido del archivo
            
        Returns:
            Contenido minificado
        """
        import re
        
        # Remover comentarios de línea
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remover comentarios de bloque
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remover espacios en blanco extra
        content = re.sub(r'\s+', ' ', content)
        
        # Remover espacios alrededor de operadores
        content = re.sub(r'\s*([{}();,])\s*', r'\1', content)
        
        return content.strip()
    
    def minify_css(self, input_dir: str = None, output_dir: str = None) -> Dict[str, Any]:
        """
        Minificar archivos CSS
        
        Args:
            input_dir: Directorio de entrada
            output_dir: Directorio de salida
            
        Returns:
            Estadísticas de minificación
        """
        if not self.minify_css:
            return {'files_processed': 0, 'message': 'CSS minification disabled'}
        
        input_path = Path(input_dir) if input_dir else self.static_dir
        output_path = Path(output_dir) if output_dir else self.build_dir
        
        css_files = list(input_path.rglob('*.css'))
        minified_files = []
        total_original_size = 0
        total_minified_size = 0
        
        for css_file in css_files:
            try:
                relative_path = css_file.relative_to(input_path)
                output_file = output_path / relative_path
                
                # Crear directorio de salida
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Obtener tamaño original
                original_size = css_file.stat().st_size
                total_original_size += original_size
                
                # Minificar CSS
                minified_size = self._minify_css_file(css_file, output_file)
                total_minified_size += minified_size
                
                minified_files.append({
                    'file': str(relative_path),
                    'original_size': original_size,
                    'minified_size': minified_size,
                    'compression_ratio': (1 - minified_size / original_size) * 100
                })
                
                logger.debug(f"Minified CSS: {relative_path} ({original_size} -> {minified_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error minifying CSS {css_file}: {e}")
        
        stats = {
            'files_processed': len(minified_files),
            'total_original_size': total_original_size,
            'total_minified_size': total_minified_size,
            'total_compression_ratio': (1 - total_minified_size / max(total_original_size, 1)) * 100,
            'files': minified_files
        }
        
        self.optimization_stats['css'].update(stats)
        
        logger.info(f"CSS minification completed: {len(minified_files)} files, "
                   f"{stats['total_compression_ratio']:.1f}% compression")
        
        return stats
    
    def _minify_css_file(self, input_file: Path, output_file: Path) -> int:
        """
        Minificar un archivo CSS individual
        
        Args:
            input_file: Archivo de entrada
            output_file: Archivo de salida
            
        Returns:
            Tamaño del archivo minificado
        """
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Minificación básica de CSS
        minified = self._basic_css_minify(content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(minified)
        
        return output_file.stat().st_size
    
    def _basic_css_minify(self, content: str) -> str:
        """
        Minificación básica de CSS
        
        Args:
            content: Contenido del archivo
            
        Returns:
            Contenido minificado
        """
        import re
        
        # Remover comentarios
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remover espacios en blanco extra
        content = re.sub(r'\s+', ' ', content)
        
        # Remover espacios alrededor de caracteres especiales
        content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', content)
        
        # Remover punto y coma antes de }
        content = re.sub(r';\s*}', '}', content)
        
        return content.strip()
    
    def compress_assets(self, input_dir: str = None, output_dir: str = None) -> Dict[str, Any]:
        """
        Comprimir assets con gzip y brotli
        
        Args:
            input_dir: Directorio de entrada
            output_dir: Directorio de salida
            
        Returns:
            Estadísticas de compresión
        """
        input_path = Path(input_dir) if input_dir else self.build_dir
        output_path = Path(output_dir) if output_dir else self.build_dir
        
        compressible_extensions = {'.js', '.css', '.html', '.json', '.xml', '.txt', '.svg'}
        compressed_files = []
        
        for asset_file in input_path.rglob('*'):
            if asset_file.suffix.lower() in compressible_extensions and asset_file.is_file():
                try:
                    relative_path = asset_file.relative_to(input_path)
                    
                    # Comprimir con gzip
                    gzip_size = 0
                    if self.enable_gzip:
                        gzip_file = output_path / f"{relative_path}.gz"
                        gzip_file.parent.mkdir(parents=True, exist_ok=True)
                        gzip_size = self._compress_gzip(asset_file, gzip_file)
                    
                    # Comprimir con brotli
                    brotli_size = 0
                    if self.enable_brotli:
                        brotli_file = output_path / f"{relative_path}.br"
                        brotli_file.parent.mkdir(parents=True, exist_ok=True)
                        brotli_size = self._compress_brotli(asset_file, brotli_file)
                    
                    original_size = asset_file.stat().st_size
                    
                    compressed_files.append({
                        'file': str(relative_path),
                        'original_size': original_size,
                        'gzip_size': gzip_size,
                        'brotli_size': brotli_size,
                        'gzip_ratio': (1 - gzip_size / original_size) * 100 if gzip_size > 0 else 0,
                        'brotli_ratio': (1 - brotli_size / original_size) * 100 if brotli_size > 0 else 0
                    })
                    
                    logger.debug(f"Compressed: {relative_path} (gzip: {gzip_size}, brotli: {brotli_size})")
                    
                except Exception as e:
                    logger.error(f"Error compressing {asset_file}: {e}")
        
        stats = {
            'files_processed': len(compressed_files),
            'files': compressed_files
        }
        
        self.optimization_stats['compression'].update(stats)
        
        logger.info(f"Asset compression completed: {len(compressed_files)} files")
        
        return stats
    
    def _compress_gzip(self, input_file: Path, output_file: Path) -> int:
        """
        Comprimir archivo con gzip
        
        Args:
            input_file: Archivo de entrada
            output_file: Archivo comprimido de salida
            
        Returns:
            Tamaño del archivo comprimido
        """
        try:
            with open(input_file, 'rb') as f_in:
                with gzip.open(output_file, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            return output_file.stat().st_size
            
        except Exception as e:
            logger.error(f"Error compressing with gzip {input_file}: {e}")
            return 0
    
    def _compress_brotli(self, input_file: Path, output_file: Path) -> int:
        """
        Comprimir archivo con brotli
        
        Args:
            input_file: Archivo de entrada
            output_file: Archivo comprimido de salida
            
        Returns:
            Tamaño del archivo comprimido
        """
        try:
            import brotli
            
            with open(input_file, 'rb') as f_in:
                data = f_in.read()
                compressed_data = brotli.compress(data, quality=11)
                
                with open(output_file, 'wb') as f_out:
                    f_out.write(compressed_data)
            
            return output_file.stat().st_size
            
        except ImportError:
            logger.debug("Brotli not available for compression")
            return 0
        except Exception as e:
            logger.error(f"Error compressing with brotli {input_file}: {e}")
            return 0
    
    def generate_manifest(self, output_dir: str = None) -> Dict[str, Any]:
        """
        Generar manifest de assets optimizados
        
        Args:
            output_dir: Directorio de salida
            
        Returns:
            Manifest de assets
        """
        output_path = Path(output_dir) if output_dir else self.build_dir
        
        manifest = {
            'generated_at': datetime.now().isoformat(),
            'optimization_stats': dict(self.optimization_stats),
            'assets': {},
            'versions': {}
        }
        
        # Generar hashes para versionado
        for asset_file in output_path.rglob('*'):
            if asset_file.is_file() and not asset_file.name.startswith('.'):
                relative_path = str(asset_file.relative_to(output_path))
                
                # Calcular hash del archivo
                file_hash = self._calculate_file_hash(asset_file)
                
                # Información del asset
                asset_info = {
                    'path': relative_path,
                    'size': asset_file.stat().st_size,
                    'hash': file_hash,
                    'modified': datetime.fromtimestamp(asset_file.stat().st_mtime).isoformat(),
                    'mime_type': mimetypes.guess_type(str(asset_file))[0]
                }
                
                # Verificar si existen versiones comprimidas
                gzip_file = output_path / f"{relative_path}.gz"
                brotli_file = output_path / f"{relative_path}.br"
                
                if gzip_file.exists():
                    asset_info['gzip_size'] = gzip_file.stat().st_size
                    asset_info['gzip_available'] = True
                
                if brotli_file.exists():
                    asset_info['brotli_size'] = brotli_file.stat().st_size
                    asset_info['brotli_available'] = True
                
                manifest['assets'][relative_path] = asset_info
                manifest['versions'][relative_path] = f"{file_hash[:8]}"
        
        # Guardar manifest
        manifest_file = output_path / 'asset-manifest.json'
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Asset manifest generated: {len(manifest['assets'])} assets")
        
        return manifest
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calcular hash SHA-256 de un archivo
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Hash hexadecimal del archivo
        """
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def optimize_all(self) -> Dict[str, Any]:
        """
        Ejecutar todas las optimizaciones
        
        Returns:
            Estadísticas completas de optimización
        """
        logger.info("Starting complete asset optimization")
        
        start_time = datetime.now()
        
        # Ejecutar optimizaciones
        image_stats = self.optimize_images()
        js_stats = self.minify_javascript()
        css_stats = self.minify_css()
        compression_stats = self.compress_assets()
        manifest = self.generate_manifest()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Estadísticas completas
        complete_stats = {
            'optimization_started': start_time.isoformat(),
            'optimization_completed': end_time.isoformat(),
            'duration_seconds': duration,
            'images': image_stats,
            'javascript': js_stats,
            'css': css_stats,
            'compression': compression_stats,
            'manifest': {
                'total_assets': len(manifest['assets']),
                'total_size': sum(asset['size'] for asset in manifest['assets'].values())
            }
        }
        
        logger.info(f"Asset optimization completed in {duration:.2f}s")
        
        return complete_stats
    
    def get_optimization_report(self) -> str:
        """
        Generar reporte de optimización
        
        Returns:
            Reporte formateado
        """
        stats = dict(self.optimization_stats)
        
        report = f"""
REPORTE DE OPTIMIZACIÓN DE ASSETS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

IMÁGENES:
{'-'*20}
Archivos procesados: {stats.get('images', {}).get('files_processed', 0)}
Tamaño original: {stats.get('images', {}).get('total_original_size', 0):,} bytes
Tamaño optimizado: {stats.get('images', {}).get('total_optimized_size', 0):,} bytes
Compresión: {stats.get('images', {}).get('total_compression_ratio', 0):.1f}%

JAVASCRIPT:
{'-'*20}
Archivos procesados: {stats.get('javascript', {}).get('files_processed', 0)}
Tamaño original: {stats.get('javascript', {}).get('total_original_size', 0):,} bytes
Tamaño minificado: {stats.get('javascript', {}).get('total_minified_size', 0):,} bytes
Compresión: {stats.get('javascript', {}).get('total_compression_ratio', 0):.1f}%

CSS:
{'-'*20}
Archivos procesados: {stats.get('css', {}).get('files_processed', 0)}
Tamaño original: {stats.get('css', {}).get('total_original_size', 0):,} bytes
Tamaño minificado: {stats.get('css', {}).get('total_minified_size', 0):,} bytes
Compresión: {stats.get('css', {}).get('total_compression_ratio', 0):.1f}%

COMPRESIÓN:
{'-'*20}
Archivos comprimidos: {stats.get('compression', {}).get('files_processed', 0)}
Gzip habilitado: {self.enable_gzip}
Brotli habilitado: {self.enable_brotli}
"""
        
        return report

class FrontendOptimizer:
    """
    Optimizador completo de frontend con caché y CDN
    """
    
    def __init__(self, app_dir: str):
        """
        Inicializar optimizador de frontend
        
        Args:
            app_dir: Directorio de la aplicación
        """
        self.app_dir = Path(app_dir)
        self.static_dir = self.app_dir / "static"
        self.build_dir = self.app_dir / "dist"
        
        # Inicializar optimizador de assets
        self.asset_optimizer = AssetOptimizer(
            static_dir=str(self.static_dir),
            build_dir=str(self.build_dir)
        )
        
        # Configuraciones de caché
        self.cache_headers = {
            'images': 'public, max-age=31536000',  # 1 año
            'css': 'public, max-age=31536000',     # 1 año
            'js': 'public, max-age=31536000',      # 1 año
            'fonts': 'public, max-age=31536000',   # 1 año
            'html': 'public, max-age=3600'         # 1 hora
        }
        
        logger.info(f"Frontend optimizer initialized for {app_dir}")
    
    def build_production(self) -> Dict[str, Any]:
        """
        Construir versión de producción optimizada
        
        Returns:
            Estadísticas de construcción
        """
        logger.info("Building production version")
        
        # Limpiar directorio de build
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True)
        
        # Optimizar todos los assets
        optimization_stats = self.asset_optimizer.optimize_all()
        
        # Generar service worker para caché
        self._generate_service_worker()
        
        # Generar configuración de servidor
        self._generate_server_config()
        
        build_stats = {
            'build_completed': datetime.now().isoformat(),
            'build_dir': str(self.build_dir),
            'optimization': optimization_stats
        }
        
        logger.info("Production build completed")
        
        return build_stats
    
    def _generate_service_worker(self):
        """
        Generar service worker para caché offline
        """
        sw_content = f"""
// Service Worker para caché de assets
// Generado automáticamente por FrontendOptimizer

const CACHE_NAME = 'social-media-analytics-v{int(datetime.now().timestamp())}';
const STATIC_CACHE = 'static-cache-v1';

// Assets a cachear
const CACHE_ASSETS = [
    '/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/images/logo.png'
];

// Instalar service worker
self.addEventListener('install', (event) => {{
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(CACHE_ASSETS))
            .then(() => self.skipWaiting())
    );
}});

// Activar service worker
self.addEventListener('activate', (event) => {{
    event.waitUntil(
        caches.keys().then((cacheNames) => {{
            return Promise.all(
                cacheNames.map((cacheName) => {{
                    if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE) {{
                        return caches.delete(cacheName);
                    }}
                }})
            );
        }}).then(() => self.clients.claim())
    );
}});

// Interceptar requests
self.addEventListener('fetch', (event) => {{
    event.respondWith(
        caches.match(event.request)
            .then((response) => {{
                // Retornar desde caché si existe
                if (response) {{
                    return response;
                }}
                
                // Fetch desde red
                return fetch(event.request)
                    .then((response) => {{
                        // Cachear respuestas exitosas
                        if (response.status === 200) {{
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE)
                                .then((cache) => {{
                                    cache.put(event.request, responseClone);
                                }});
                        }}
                        return response;
                    }});
            }})
    );
}});
"""
        
        sw_file = self.build_dir / 'sw.js'
        with open(sw_file, 'w', encoding='utf-8') as f:
            f.write(sw_content)
        
        logger.info("Service worker generated")
    
    def _generate_server_config(self):
        """
        Generar configuración de servidor para optimizaciones
        """
        # Configuración Nginx
        nginx_config = f"""
# Configuración Nginx para máximo rendimiento
# Generado por FrontendOptimizer

# Compresión gzip
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/javascript
    application/xml+rss
    application/json;

# Headers de caché
location ~* \\.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|eot|svg)$ {{
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
}}

location ~* \\.(html|htm)$ {{
    expires 1h;
    add_header Cache-Control "public";
}}

# Soporte para Brotli
location ~* \\.(js|css|html|svg|json|xml)$ {{
    gzip_static on;
    brotli_static on;
}}

# Security headers
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
"""
        
        config_file = self.build_dir / 'nginx.conf'
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(nginx_config)
        
        # Configuración Apache
        apache_config = """
# Configuración Apache para máximo rendimiento
# Generado por FrontendOptimizer

# Compresión
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/xhtml+xml
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/x-javascript
</IfModule>

# Headers de caché
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/pdf "access plus 1 year"
    ExpiresByType text/javascript "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType application/x-shockwave-flash "access plus 1 year"
    ExpiresByType image/x-icon "access plus 1 year"
    ExpiresByType text/html "access plus 1 hour"
</IfModule>
"""
        
        htaccess_file = self.build_dir / '.htaccess'
        with open(htaccess_file, 'w', encoding='utf-8') as f:
            f.write(apache_config)
        
        logger.info("Server configurations generated")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Obtener métricas de rendimiento del frontend
        
        Returns:
            Métricas de rendimiento
        """
        manifest_file = self.build_dir / 'asset-manifest.json'
        
        if not manifest_file.exists():
            return {'error': 'No manifest found, run build_production first'}
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Calcular métricas
        total_size = sum(asset['size'] for asset in manifest['assets'].values())
        gzip_size = sum(asset.get('gzip_size', 0) for asset in manifest['assets'].values())
        brotli_size = sum(asset.get('brotli_size', 0) for asset in manifest['assets'].values())
        
        metrics = {
            'total_assets': len(manifest['assets']),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'gzip_size_bytes': gzip_size,
            'gzip_size_mb': gzip_size / (1024 * 1024),
            'brotli_size_bytes': brotli_size,
            'brotli_size_mb': brotli_size / (1024 * 1024),
            'gzip_compression_ratio': (1 - gzip_size / total_size) * 100 if total_size > 0 else 0,
            'brotli_compression_ratio': (1 - brotli_size / total_size) * 100 if total_size > 0 else 0,
            'optimization_stats': manifest.get('optimization_stats', {})
        }
        
        return metrics

# Instancia global del optimizador
frontend_optimizer = None

def initialize_frontend_optimizer(app_dir: str):
    """
    Inicializar optimizador de frontend global
    
    Args:
        app_dir: Directorio de la aplicación
    """
    global frontend_optimizer
    frontend_optimizer = FrontendOptimizer(app_dir)
    logger.info("Frontend optimizer initialized")

def optimize_for_production():
    """
    Optimizar aplicación para producción
    
    Returns:
        Estadísticas de optimización
    """
    if not frontend_optimizer:
        raise RuntimeError("Frontend optimizer not initialized")
    
    return frontend_optimizer.build_production()

# Decorador para optimización automática
def auto_optimize(func):
    """
    Decorador para optimización automática de assets
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Optimizar assets si es necesario
        if frontend_optimizer:
            try:
                frontend_optimizer.asset_optimizer.optimize_all()
            except Exception as e:
                logger.error(f"Auto-optimization failed: {e}")
        
        return result
    
    return wrapper

