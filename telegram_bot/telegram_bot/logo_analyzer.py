import os
from PIL import Image
import numpy as np
from collections import Counter
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class LogoAnalyzer:
    def __init__(self):
        pass
    
    def analyze_logo(self, image_path: str) -> Dict[str, Any]:
        """Анализ логотипа: извлечение цветов и контура"""
        try:
            # Открываем изображение
            img = Image.open(image_path)
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Анализируем цвета
            colors = self._extract_colors(img)
            
            # Анализируем контур
            outline_color = self._detect_outline_color(img)
            
            return {
                "colors": colors,
                "outline_color": outline_color,
                "image_path": image_path
            }
        
        except Exception as e:
            logger.error(f"Ошибка при анализе логотипа: {e}")
            return {
                "colors": [],
                "outline_color": "",
                "error": str(e)
            }
    
    def _extract_colors(self, img: Image.Image, num_colors: int = 10) -> List[Dict[str, Any]]:
        """Извлечение основных цветов из изображения"""
        try:
            # Уменьшаем размер для ускорения обработки
            img_resized = img.resize((150, 150), Image.Resampling.LANCZOS)
            
            # Конвертируем в numpy array
            img_array = np.array(img_resized)
            
            # Получаем все пиксели
            pixels = img_array.reshape(-1, 3)
            
            # Удаляем прозрачные/белые пиксели (если фон белый)
            # Можно настроить под конкретные случаи
            pixels_filtered = pixels
            
            # Группируем похожие цвета
            colors_grouped = self._group_similar_colors(pixels_filtered)
            
            # Сортируем по частоте
            colors_sorted = sorted(colors_grouped.items(), key=lambda x: x[1], reverse=True)
            
            # Конвертируем в формат результата
            total_pixels = len(pixels_filtered)
            result = []
            
            for (r, g, b), count in colors_sorted[:num_colors]:
                percentage = (count / total_pixels) * 100
                hex_color = self._rgb_to_hex(r, g, b)
                
                result.append({
                    "color": hex_color,
                    "rgb": [int(r), int(g), int(b)],
                    "percentage": round(percentage, 2)
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Ошибка при извлечении цветов: {e}")
            return []
    
    def _group_similar_colors(self, pixels: np.ndarray, threshold: int = 30) -> Dict[Tuple[int, int, int], int]:
        """Группировка похожих цветов"""
        color_groups = {}
        
        for pixel in pixels:
            r, g, b = pixel
            
            # Находим ближайшую группу
            found_group = False
            for (gr, gg, gb) in list(color_groups.keys()):
                if (abs(r - gr) < threshold and 
                    abs(g - gg) < threshold and 
                    abs(b - gb) < threshold):
                    color_groups[(gr, gg, gb)] += 1
                    found_group = True
                    break
            
            if not found_group:
                color_groups[(int(r), int(g), int(b))] = 1
        
        return color_groups
    
    def _detect_outline_color(self, img: Image.Image) -> str:
        """Определение цвета контура/границы"""
        try:
            # Конвертируем в grayscale для детекции краев
            gray = img.convert('L')
            gray_array = np.array(gray)
            
            # Находим края (простой метод через градиент)
            # Используем разницу между соседними пикселями
            edges = []
            height, width = gray_array.shape
            
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    # Проверяем градиент
                    grad_x = abs(int(gray_array[y, x+1]) - int(gray_array[y, x-1]))
                    grad_y = abs(int(gray_array[y+1, x]) - int(gray_array[y-1, x]))
                    
                    if grad_x > 30 or grad_y > 30:  # Порог для детекции края
                        # Получаем цвет из оригинального изображения
                        r, g, b = img.getpixel((x, y))
                        edges.append((r, g, b))
            
            if not edges:
                return ""
            
            # Находим наиболее частый цвет на краях
            edge_colors = Counter(edges)
            most_common = edge_colors.most_common(1)[0][0]
            
            return self._rgb_to_hex(most_common[0], most_common[1], most_common[2])
        
        except Exception as e:
            logger.error(f"Ошибка при определении цвета контура: {e}")
            return ""
    
    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Конвертация RGB в HEX"""
        return f"#{r:02x}{g:02x}{b:02x}".upper()

