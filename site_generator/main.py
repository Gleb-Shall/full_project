import os
import json
import re
import operator
from typing import Annotated, List, Dict, Any, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

# --- CONFIG ---
# Переменные окружения берутся из GitHub Secrets
# Для локальной разработки можно использовать .env файл (опционально)
API_KEY = os.getenv('OPENROUTER_API_KEY')
BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

# --- STATE ---
class AgentState(TypedDict):
    input_data: Dict[str, Any]
    ctm_identity: Dict[str, str]
    generated_files: Annotated[List[Dict[str, Any]], operator.add]

# --- SITE GENERATOR CLASS ---
class SiteGenerator:
    """Класс для генерации Astro сайта из JSON данных"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """Инициализация генератора сайта"""
        self.api_key = api_key or API_KEY
        self.base_url = base_url or BASE_URL
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не найден в переменных окружения")
        
        # LLM Config
        self.llm_coder = ChatOpenAI(
            model="anthropic/claude-3.5-sonnet",
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.25,
            max_tokens=4000,
            model_kwargs={"extra_headers": {"X-Title": "Astro Premium Architect"}}
        )
        
        # Создаем workflow
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
    
    def _create_workflow(self) -> StateGraph:
        """Создает workflow для генерации сайта"""
        workflow = StateGraph(AgentState)
        
        # Добавляем узлы
        workflow.add_node("parse_ctm", self.parse_ctm_node)
        workflow.add_node("scaffold", self.scaffold_node)
        workflow.add_node("assets", self.assets_node)
        workflow.add_node("styles", self.styles_node)
        workflow.add_node("layout", self.layout_node)
        workflow.add_node("components", self.components_node)
        workflow.add_node("pages", self.pages_node)
        workflow.add_node("finalizer", self.finalizer_node)
        
        # Определяем порядок выполнения
        workflow.set_entry_point("parse_ctm")
        workflow.add_edge("parse_ctm", "scaffold")
        workflow.add_edge("scaffold", "assets")
        workflow.add_edge("assets", "styles")
        workflow.add_edge("styles", "layout")
        workflow.add_edge("layout", "components")
        workflow.add_edge("components", "pages")
        workflow.add_edge("pages", "finalizer")
        workflow.add_edge("finalizer", END)
        
        return workflow
    
    def generate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Генерирует сайт из JSON данных и возвращает результат"""
        print("🚀 Starting Generator (Final Polish)...")
        result = self.app.invoke({"input_data": input_data, "generated_files": []})
        
        return {
            "files": [result['ctm_identity']] + result['generated_files']
        }
    
    # --- HELPERS ---
    def enforce_variable_existence(self, code: str, data_context: dict) -> str:
        """Гарантирует наличие переменной data"""
        if re.search(r'const\s+data\s*=', code) or re.search(r'let\s+data\s*=', code):
            return code
        js_object = json.dumps(data_context, ensure_ascii=False)
        injection_line = f"const data = {js_object};"
        if code.strip().startswith("---"):
            lines = code.splitlines()
            lines.insert(1, injection_line)
            return "\n".join(lines)
        else:
            return f"---\n{injection_line}\n---\n{code}"

    def get_component_names(self, files: List[Dict]) -> List[str]:
        return [f['name'] for f in files if f['name'].startswith('src/components/') and f['name'].endswith('.astro')]

    def get_thematic_image(self, business_info: Dict[str, Any], image_type: str = "hero", 
                           width: int = 800, height: int = 600) -> str:
        """Заглушка для изображений - возвращает пустую строку"""
        # TODO: Убрать эту заглушку после реализации поиска изображений
        print(f"   ⚠️ Image placeholder for {image_type} (width={width}, height={height})")
        return ""

    # --- NODES ---
    def parse_ctm_node(self, state: AgentState):
        print("--- [1/7] Parsing Data ---")
        client = state['input_data']['project']['client']
        ctm = {}
        if client.get('telegram id'): ctm['telegram id'] = client['telegram id']
        return {"ctm_identity": ctm, "generated_files": []}

    def scaffold_node(self, state: AgentState):
        print("--- [2/7] Scaffolding System ---")
        project_name = "lysinka-site"
        
        colors = state['input_data']['design']['colors']
        c_primary = colors.get('primary', '#000000')
        c_secondary = colors.get('secondary', '#333333')
        
        pkg_json = {
            "name": project_name,
            "type": "module",
            "version": "1.0.0",
            "scripts": {
                "dev": "astro dev",
                "start": "astro dev",
                "build": "astro build",
                "preview": "astro preview",
                "astro": "astro"
            },
            "dependencies": {
                "astro": "^4.0.0",
                "tailwindcss": "^3.4.0",
                "@astrojs/tailwind": "^5.1.0",
                "lucide-astro": "^0.300.0",
                "clsx": "^2.0.0",
                "tailwind-merge": "^2.0.0"
            }
        }
        
        astro_config = """
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
export default defineConfig({
  integrations: [tailwind()],
  server: { host: true }
});
"""
        
        tailwind_config = f"""
/** @type {{import('tailwindcss').Config}} */
export default {{
  content: ['./src/**/*.{{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}}'],
  theme: {{
    extend: {{
      colors: {{
        primary: '{c_primary}',
        secondary: '{c_secondary}',
        dark: '#0f172a',
        light: '#f8fafc',
      }},
      fontFamily: {{
        heading: ['var(--font-heading)', 'sans-serif'],
        body: ['var(--font-body)', 'sans-serif'],
      }},
      animation: {{
        'blob': 'blob 10s infinite',
        'fade-up': 'fadeUp 0.8s ease-out forwards',
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'slide-up': 'slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 3s linear infinite',
        'gradient': 'gradient 8s ease infinite',
      }},
      keyframes: {{
        blob: {{
          '0%': {{ transform: 'translate(0px, 0px) scale(1)' }},
          '33%': {{ transform: 'translate(30px, -50px) scale(1.1)' }},
          '66%': {{ transform: 'translate(-20px, 20px) scale(0.9)' }},
          '100%': {{ transform: 'translate(0px, 0px) scale(1)' }},
        }},
        fadeUp: {{
          '0%': {{ opacity: '0', transform: 'translateY(20px)' }},
          '100%': {{ opacity: '1', transform: 'translateY(0)' }},
        }},
        fadeIn: {{
          '0%': {{ opacity: '0' }},
          '100%': {{ opacity: '1' }},
        }},
        slideUp: {{
          '0%': {{ opacity: '0', transform: 'translateY(40px)' }},
          '100%': {{ opacity: '1', transform: 'translateY(0)' }},
        }},
        float: {{
          '0%, 100%': {{ transform: 'translateY(0)' }},
          '50%': {{ transform: 'translateY(-20px)' }},
        }},
        shimmer: {{
          '0%': {{ backgroundPosition: '-200% 0' }},
          '100%': {{ backgroundPosition: '200% 0' }},
        }},
        gradient: {{
          '0%, 100%': {{ backgroundPosition: '0% 50%' }},
          '50%': {{ backgroundPosition: '100% 50%' }},
        }}
      }},
      backdropBlur: {{
        xs: '2px',
      }},
      boxShadow: {{
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 20px rgba(var(--primary-rgb), 0.3)',
      }}
    }},
  }},
  plugins: [],
}}
"""
    
        files = [
            {"name": "package.json", "content": pkg_json},
            {"name": "astro.config.mjs", "content": astro_config},
            {"name": "tailwind.config.mjs", "content": tailwind_config},
            {"name": "src/env.d.ts", "content": "/// <reference types=\"astro/client\" />"},
            {"name": "public/robots.txt", "content": "User-agent: *\nAllow: /"}
        ]
        return {"generated_files": files}

    def assets_node(self, state: AgentState):
        print("--- [3/7] Generating Assets ---")
        color = state['input_data']['design']['colors'].get('primary', '#000')
        favicon = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="{color}"/></svg>'
        return {"generated_files": [{"name": "public/favicon.svg", "content": favicon}]}

    def styles_node(self, state: AgentState):
        print("--- [4/7] Generating Premium CSS ---")
        colors = state['input_data']['design']['colors']
        primary = colors.get('primary', '#000000')
        secondary = colors.get('secondary', '#333333')
        
        # Convert hex to RGB for CSS variables
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return ','.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))
        
        primary_rgb = hex_to_rgb(primary)
        secondary_rgb = hex_to_rgb(secondary)
        
        css = f"""
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --font-heading: 'Inter', sans-serif;
  --font-body: 'Inter', sans-serif;
  --primary-rgb: {primary_rgb};
  --secondary-rgb: {secondary_rgb};
}}

@layer base {{
  html {{ 
    scroll-behavior: smooth; 
    scroll-padding-top: 100px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
  
  body {{ 
    @apply bg-gradient-to-br from-slate-50 via-white to-slate-50 text-slate-800 antialiased;
    @apply selection:bg-primary/20 selection:text-slate-900;
    background-image: 
      radial-gradient(at 0% 0%, rgba(var(--primary-rgb), 0.03) 0px, transparent 50%),
      radial-gradient(at 100% 100%, rgba(var(--secondary-rgb), 0.03) 0px, transparent 50%),
      url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.02'/%3E%3C/svg%3E");
    min-height: 100vh;
  }}
  
  h1 {{ 
    @apply font-heading font-extrabold text-slate-900 tracking-tight text-balance;
    @apply text-4xl md:text-5xl lg:text-6xl leading-[1.1];
    letter-spacing: -0.03em;
    font-weight: 800;
    line-height: 1.1;
  }}
  
  h2 {{ 
    @apply font-heading font-bold text-slate-900 tracking-tight text-balance; 
    @apply text-3xl md:text-4xl lg:text-5xl leading-[1.15];
    letter-spacing: -0.02em;
    font-weight: 700;
    line-height: 1.15;
  }}
  
  h3 {{ 
    @apply font-heading font-bold text-slate-800 tracking-tight;
    @apply text-2xl md:text-3xl leading-snug;
    letter-spacing: -0.01em;
    font-weight: 700;
    line-height: 1.3;
  }}
  
  h4 {{ 
    @apply font-heading font-semibold text-slate-800 tracking-tight;
    @apply text-xl md:text-2xl leading-snug;
    font-weight: 600;
    line-height: 1.4;
  }}
  
  p {{
    @apply text-slate-600 leading-relaxed text-pretty;
    @apply text-base md:text-lg;
    line-height: 1.75;
    font-weight: 400;
    margin-bottom: 1rem;
  }}
  
  p + p {{
    margin-top: 0.75rem;
  }}
  
  strong, b {{
    @apply font-semibold text-slate-900;
    font-weight: 600;
  }}
  
  em, i {{
    font-style: italic;
  }}
  
  small {{
    @apply text-sm text-slate-500;
    font-size: 0.875rem;
    line-height: 1.5;
  }}
  
  blockquote {{
    @apply border-l-4 border-primary/30 pl-6 italic text-slate-700;
    margin: 1.5rem 0;
  }}
  
  code {{
    @apply bg-slate-100 text-slate-800 px-2 py-1 rounded text-sm font-mono;
  }}
  
  ul, ol {{
    @apply text-slate-600 leading-relaxed;
    padding-left: 1.5rem;
  }}
  
  li {{
    @apply mb-2;
    line-height: 1.75;
  }}
  
  a {{
    @apply transition-colors duration-200 text-primary hover:text-primary/80;
    text-decoration: none;
  }}
  
  a:hover {{
    text-decoration: underline;
    text-underline-offset: 3px;
    text-decoration-thickness: 1.5px;
  }}
  
  button {{
    @apply focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2;
    font-weight: 600;
    letter-spacing: 0.01em;
  }}
  
  img {{
    @apply select-none;
  }}
  
  /* Улучшенная типографика для лучшей читаемости */
  .text-lead {{
    @apply text-lg md:text-xl text-slate-700 leading-relaxed;
    font-weight: 400;
    line-height: 1.8;
  }}
  
  .text-muted {{
    @apply text-slate-500 text-sm md:text-base;
    line-height: 1.6;
  }}
  
  .text-accent {{
    @apply text-primary font-semibold;
  }}
  
  /* Улучшенные отступы для секций - более компактные */
  section {{
    @apply py-12 md:py-16 lg:py-20;
  }}
  
  /* Улучшенные списки */
  ul.list-disc li::marker {{
    @apply text-primary;
  }}
  
  ol.list-decimal li::marker {{
    @apply text-primary font-semibold;
  }}
}}

@layer components {{
  /* Premium Button Styles */
  .btn-primary {{
    @apply inline-flex items-center justify-center gap-2 px-8 py-4;
    @apply bg-primary text-white font-semibold;
    @apply rounded-full shadow-lg shadow-primary/30;
    @apply hover:shadow-primary/50 hover:-translate-y-0.5;
    @apply active:translate-y-0 active:shadow-primary/30;
    @apply transition-all duration-300 ease-out;
    @apply focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2;
    position: relative;
    overflow: hidden;
  }}
  
  .btn-primary::before {{
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
  }}
  
  .btn-primary:hover::before {{
    left: 100%;
  }}
  
  .btn-secondary {{
    @apply inline-flex items-center justify-center gap-2 px-6 py-3;
    @apply bg-white/90 backdrop-blur-sm text-primary font-semibold;
    @apply border-2 border-primary/20 rounded-full;
    @apply hover:bg-primary hover:text-white hover:border-primary;
    @apply transition-all duration-300 ease-out;
    @apply shadow-sm hover:shadow-md;
  }}
  
  /* Glass Morphism Cards */
  .glass-card {{
    @apply bg-white/70 backdrop-blur-xl border border-white/50;
    @apply shadow-soft rounded-2xl;
    @apply hover:shadow-xl hover:bg-white/80;
    @apply transition-all duration-300;
  }}
  
  .glass-card-strong {{
    @apply bg-white/90 backdrop-blur-2xl border border-white/60;
    @apply shadow-xl rounded-3xl;
    @apply hover:shadow-2xl;
    @apply transition-all duration-300;
  }}
  
  /* Cards have light background, so text inside must be dark */
  .glass-card,
  .glass-card-strong {{
    @apply text-slate-800;
  }}
  
  .glass-card p,
  .glass-card-strong p {{
    @apply text-slate-700;
  }}
  
  .glass-card h1,
  .glass-card h2,
  .glass-card h3,
  .glass-card h4,
  .glass-card-strong h1,
  .glass-card-strong h2,
  .glass-card-strong h3,
  .glass-card-strong h4 {{
    @apply text-slate-900;
  }}
  
  .glass-card a,
  .glass-card-strong a {{
    @apply text-primary hover:text-primary/80;
  }}
  
  /* Only force light text if card is explicitly on dark background AND card itself is dark */
  .dark-bg.dark-card .glass-card,
  .dark-bg.dark-card .glass-card-strong {{
    @apply bg-slate-800/50 text-white;
  }}
  
  /* Text Effects */
  .text-gradient {{
    @apply bg-clip-text text-transparent;
    background-image: linear-gradient(135deg, {primary}, {secondary});
    -webkit-background-clip: text;
    background-clip: text;
  }}
  
  .text-gradient-animated {{
    @apply bg-clip-text text-transparent;
    background: linear-gradient(-45deg, {primary}, {secondary}, {primary}, {secondary});
    background-size: 400% 400%;
    animation: gradient 8s ease infinite;
    -webkit-background-clip: text;
    background-clip: text;
  }}
  
  /* Section Styles */
  .section-container {{
    @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8;
  }}
  
  .section-padding {{
    @apply py-12 md:py-16 lg:py-20;
  }}
  
  /* Card Hover Effects */
  .hover-lift {{
    @apply transition-all duration-300 ease-out;
    @apply hover:-translate-y-2 hover:shadow-xl;
  }}
  
  .hover-glow {{
    @apply transition-all duration-300;
    @apply hover:shadow-glow;
  }}
  
  /* Image Styles */
  .image-cover {{
    @apply w-full h-full object-cover;
    @apply transition-transform duration-500 ease-out;
  }}
  
  .image-hover-zoom {{
    @apply image-cover;
    @apply hover:scale-110;
  }}
  
  /* Navigation Styles */
  .nav-link {{
    @apply relative px-4 py-2 text-slate-700 font-medium;
    @apply transition-colors duration-200;
    @apply hover:text-primary;
    font-weight: 500;
    letter-spacing: 0.01em;
  }}
  
  .nav-link::after {{
    content: '';
    @apply absolute bottom-0 left-1/2 w-0 h-0.5 bg-primary;
    @apply transition-all duration-300 ease-out;
    transform: translateX(-50%);
  }}
  
  .nav-link:hover::after {{
    @apply w-3/4;
  }}
  
  /* Улучшенные стили для контента - более компактные */
  .content-rich p {{
    @apply mb-3;
    line-height: 1.75;
  }}
  
  .content-rich p:last-child {{
    @apply mb-0;
  }}
  
  .content-rich h2 {{
    @apply mt-6 mb-3;
  }}
  
  .content-rich h3 {{
    @apply mt-5 mb-2;
  }}
  
  /* Стили для карточек с текстом */
  .card-text {{
    @apply text-slate-700 leading-relaxed;
    line-height: 1.7;
    margin-bottom: 0.75rem;
  }}
  
  .card-title {{
    @apply font-bold text-slate-900 mb-1.5;
    font-weight: 700;
    letter-spacing: -0.01em;
  }}
  
  .card-description {{
    @apply text-slate-600 text-sm md:text-base;
    line-height: 1.65;
    margin-bottom: 0.5rem;
  }}
  
  /* Компактные отступы для grid и flex контейнеров */
  .compact-grid {{
    @apply gap-6 md:gap-8;
  }}
  
  .compact-flex {{
    @apply gap-4 md:gap-6;
  }}
  
  /* Loading States */
  .skeleton {{
    @apply animate-pulse bg-slate-200 rounded;
  }}
  
  /* Focus Visible */
  .focus-visible-ring {{
    @apply focus-visible:outline-none focus-visible:ring-2;
    @apply focus-visible:ring-primary/50 focus-visible:ring-offset-2;
  }}
  
  /* Smooth Scroll Indicator */
  .scroll-indicator {{
    @apply fixed bottom-8 left-1/2 -translate-x-1/2 z-50;
    @apply w-6 h-10 border-2 border-primary/30 rounded-full;
    @apply flex items-start justify-center p-2;
    @apply animate-float;
  }}
  
  .scroll-indicator::before {{
    content: '';
    @apply w-1.5 h-1.5 bg-primary rounded-full;
    @apply animate-pulse;
  }}
}}

@layer utilities {{
  /* Custom Utilities */
  .text-balance {{
    text-wrap: balance;
  }}
  
  .text-pretty {{
    text-wrap: pretty;
  }}
  
  /* Gradient Text */
  .gradient-text {{
    @apply bg-gradient-to-r from-primary via-secondary to-primary;
    @apply bg-clip-text text-transparent;
    background-size: 200% auto;
    animation: shimmer 3s linear infinite;
  }}
  
  /* Smooth Transitions */
  .transition-smooth {{
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }}
  
  /* Container Queries Support */
  .container-responsive {{
    container-type: inline-size;
  }}
  
  /* Accessibility */
  .sr-only {{
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }}
  
  /* Reduced Motion */
  @media (prefers-reduced-motion: reduce) {{
    *,
    *::before,
    *::after {{
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }}
  }}
}}
"""
        return {"generated_files": [{"name": "src/styles/global.css", "content": css}]}

    def layout_node(self, state: AgentState):
        print("--- [5/7] Generating Layout ---")
        layout_code = """---
import '../styles/global.css';
interface Props { title: string; }
const { title } = Astro.props;
---
<!doctype html>
<html lang="ru">
	<head>
		<meta charset="UTF-8" />
		<meta name="viewport" content="width=device-width" />
		<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap" rel="stylesheet">
		<title>{title}</title>
	</head>
	<body class="overflow-x-hidden">
        <!-- Animated Background Blobs -->
        <div class="fixed top-0 left-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 -z-10 animate-blob"></div>
        <div class="fixed bottom-0 right-0 w-[600px] h-[600px] bg-secondary/5 rounded-full blur-[120px] translate-x-1/3 translate-y-1/3 -z-10 animate-blob" style="animation-delay: 2s;"></div>
        <div class="fixed top-1/2 left-1/2 w-[400px] h-[400px] bg-primary/3 rounded-full blur-[100px] -translate-x-1/2 -translate-y-1/2 -z-10 animate-pulse-slow"></div>
		<slot />
	</body>
</html>
"""
        return {"generated_files": [{"name": "src/layouts/Base.astro", "content": layout_code}]}

    def components_node(self, state: AgentState):
        print("--- [6/7] Generating Components (Images Uniform & Russian) ---")
        
        content = state['input_data']['content']
        biz = state['input_data']['project']['business']
        design_images = state['input_data']['design'].get('images', {})

        # Подготовка полного контекста для поиска изображений
        # Используем все доступные данные из JSON для более точного определения тематики
        business_context = {
            'name': biz.get('name', ''),
            'industry': biz.get('industry', ''),
            'content': content,
            'project': state['input_data'].get('project', {}),
            'design': state['input_data'].get('design', {}),
            'structure': state['input_data'].get('structure', {}),
            'full_input': state['input_data']  # Полный контекст для анализа
        }

        # Hero изображение
        hero_data = content.get('hero', {})
        hero_url = design_images.get('hero', {}).get('url', '').strip()
        if not hero_url:
            # Заглушка - пустое изображение
            hero_url = ""
        hero_data['image'] = hero_url
        print(f"   ✓ Hero image: {'provided' if hero_url else 'empty (placeholder)'}")

        # About изображение
        sections = content.get('sections', [])
        about_data = sections[0] if sections and len(sections) > 0 else {}
        about_url = design_images.get('about', {}).get('url', '').strip()
        if not about_url:
            # Заглушка - пустое изображение
            about_url = ""
        about_data['image'] = about_url
        print(f"   ✓ About image: {'provided' if about_url else 'empty (placeholder)'}")

        # Gallery изображения
        gallery_items = design_images.get('gallery', [])
        if not gallery_items or len(gallery_items) == 0:
            # Заглушка - пустой массив изображений
            gallery_items = []
            print("   ✓ Gallery images: empty (placeholder)")
        else:
            # Проверяем, что все URL валидны
            valid_items = []
            for item in gallery_items:
                url = item.get('url', '').strip() if isinstance(item, dict) else str(item).strip()
                if url:
                    valid_items.append({
                        "url": url,
                        "name": item.get('name', f"Image {len(valid_items)+1}") if isinstance(item, dict) else f"Image {len(valid_items)+1}"
                    })
            gallery_items = valid_items if valid_items else gallery_items
        print(f"   ✓ Gallery images: {len(gallery_items)} items")

        # Получаем данные логотипа
        logo_data = state['input_data']['design'].get('images', {}).get('logo', {})
        logo_url = logo_data.get('url', '').strip() if logo_data else ''
        logo_width = logo_data.get('width', '200px') if logo_data else '200px'
        biz_name = state['input_data']['project']['business'].get('name', '')
        
        components_queue = [
        {
            "name": "Navigation",
            "data": {
                "navigation": state['input_data']['structure']['navigation'],
                "logo": {
                    "url": logo_url,
                    "width": logo_width,
                    "alt": f"Логотип {biz_name}" if biz_name else "Логотип"
                },
                "business_name": biz_name
            },
            "blueprint": """
            **Fixed Glass Header**.
            - Sticky navigation with glass morphism effect (`backdrop-blur-xl bg-white/80`).
            - Links: Anchor links (`#about`, `#features`, `#gallery`, `#contact`) with smooth scroll.
            - **Logo** (CRITICAL):
              - Check if data.logo.url exists and is not empty
              - If logo URL exists: Display as image using `<img src={data.logo.url} alt={data.logo.alt} class="h-10 md:h-12 object-contain" style="width: {data.logo.width}; max-width: 200px;" />`
              - If logo URL is empty or missing: Display text logo with gradient effect using data.business_name (use `text-gradient` class)
              - Logo should be wrapped in clickable link `<a href="#hero">` or `<a href="/">` (home)
              - Logo should have smooth hover scale effect (`hover:scale-105 transition-transform duration-200`)
              - Logo should be on the left side of navigation
            - Language: Russian links.
            - Add hover effects on links (underline animation).
            - Mobile: Hamburger menu with smooth transitions.
            - Use `nav-link` class for link styling.
            - Layout: Logo left, navigation links center/right, mobile menu button right.
            """
        },
        {
            "name": "Hero",
            "data": hero_data,
            "blueprint": """
            **Hero Section (ID: hero)**.
            - Layout: Text Left / Image Right with responsive stacking.
            - **Typography**: H1 with gradient text effect, P with good spacing, Button with `btn-primary` class.
            - **Content**: Use provided data. If text is short, expand it in RUSSIAN.
            - **Image**: Compact, `max-h-[500px]`, `rounded-[2rem]` with `image-hover-zoom` class.
            - Add fade-up animation on load (`animate-fade-up`).
            - Use `section-container` and `section-padding` classes.
            - Add subtle shadow and hover effects.
            - **Spacing**: Use compact spacing - `gap-8 md:gap-12` between text and image, `mb-4` for paragraphs.
            """
        },
        {
            "name": "Features",
            "data": content.get('features', []),
            "blueprint": """
            **Features (ID: features)**.
            - Bento Grid (responsive: 1 col mobile, 2 cols tablet, 3 cols desktop).
            - **Language**: RUSSIAN ONLY.
            - Icons: `lucide-astro` with gradient or primary color.
            - Use `glass-card` class for each feature card.
            - Add `hover-lift` effect on cards.
            - Stagger animations on scroll (`animate-slide-up` with delays).
            - Icons should be prominent with background circle or gradient.
            - **Spacing**: Use compact grid spacing - `gap-6 md:gap-8` between cards, compact padding inside cards.
            """
        },
        {
            "name": "About",
            "data": about_data,
            "blueprint": """
            **About Us (ID: about)**.
            - Layout: Image Left / Text Right with responsive stacking.
            - **Content**: RUSSIAN ONLY. Write 2-3 elegant, marketing-oriented paragraphs.
            - **TEXT GENERATION RULES**:
              - Write naturally and elegantly, like a premium brand description
              - Focus on: quality, craftsmanship, experience, unique approach, atmosphere
              - DO NOT include technical details from JSON like:
                * Target audience details (income levels, demographics like "мужчины с доходом 100+к рублей")
                * Technical specifications
                * Business goals or metrics
              - **IMPORTANT**: If location/address data exists and is valid (not placeholder like "улица геолокации йй"), USE IT AS IS
              - Only rewrite location if it's clearly a placeholder or technical data
              - Instead, write about: the art of the craft, attention to detail, premium experience, tradition, expertise
              - Make it sound premium and professional, not technical
              - Use elegant language that appeals to clients who value quality
            - Stats Row below text with animated numbers (use `glass-card` for stat cards).
            - Image: Use `image-cover` class with rounded corners.
            - Add fade-in animations.
            - Use `section-container` and `section-padding` classes.
            - **Spacing**: Use compact spacing - `gap-8 md:gap-10` between image and text columns, `mb-3` between paragraphs, `mt-6` for stats row.
            """
        },
        {
            "name": "Gallery",
            "data": {"items": gallery_items},
            "blueprint": """
            **Gallery (ID: gallery)**.
            - Grid: Responsive (`grid-cols-2 md:grid-cols-3 lg:grid-cols-4`).
            - **IMAGES**: 
              - Uniform Size: `aspect-square` for consistency.
              - Fit: Use `image-hover-zoom` class.
              - Style: `rounded-xl overflow-hidden` with smooth transitions.
              - Add overlay on hover (optional subtle dark overlay).
            - **NO TEXT**: Do NOT add captions/names under images. Just the images.
            - Use `glass-card` wrapper for each image container.
            - Add gap spacing between items.
            """
        },
        {
            "name": "Contact",
            "data": {
                "contacts": content.get('contacts', {}),
                "client": state['input_data'].get('project', {}).get('client', {}),
                "footer": state['input_data'].get('structure', {}).get('footer', {}),
                "social": state['input_data'].get('structure', {}).get('footer', {}).get('social', {})
            },
            "blueprint": """
            **Contact & Footer (ID: contact)**.
            - Bg: Dark gradient (`bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900`).
            - Language: RUSSIAN ONLY.
            - **NO FORM**: Do NOT add contact form. Only display contact information.
            - **CRITICAL COLOR RULES** (MANDATORY - CHECK EVERY ELEMENT):
              - Background is DARK (slate-900/800), so ALL text MUST be LIGHT:
              - **EVERY text element** must use: `text-white` or `text-slate-100` or `text-slate-200`
              - **Address**: `text-white` class (NEVER default text color)
              - **Phone**: `text-white` class
              - **Email**: `text-white` class  
              - **Telegram**: `text-white` class
              - **Labels** (like "Адрес", "Телефон"): `text-slate-200` or `text-slate-300` class
              - **Card text**: Cards have LIGHT backgrounds, so text inside cards MUST be DARK: `text-slate-800` or `text-slate-900` (NEVER white)
              - **Icons**: `text-white` or `text-slate-200` class
              - **Links**: `text-white hover:text-primary/80` class
              - **NEVER use default text colors** - always explicitly set `text-white` or `text-slate-100/200`
              - **NEVER use**: `text-slate-800`, `text-slate-900`, `text-black`, `text-gray-800`, `text-slate-700`, or any dark color
              - **Check**: Every `<p>`, `<span>`, `<div>` with text MUST have explicit light color class
            - **Contact Information** (check BOTH data.contacts AND data.client, priority: client first):
              - Address: Display if data.contacts.address exists - USE THE EXACT FULL ADDRESS from data.contacts.address (display completely, do NOT truncate), use MapPin icon from lucide-astro, DARK color (`text-slate-700`), text must be `text-slate-800` class (DARK, not white - cards have light background)
              - Phone: Display if data.client.phone OR data.contacts.phone exists - format as CLICKABLE link: `<a href="tel:{phone}" class="text-slate-800 hover:text-primary">`, use Phone icon (DARK: `text-slate-700`)
              - Email: Display if data.client.email OR data.contacts.email exists - format as CLICKABLE link: `<a href="mailto:{email}" class="text-slate-800 hover:text-primary">`, use Mail icon (DARK: `text-slate-700`)
              - Telegram: Display if data.client["telegram id"] exists - format as CLICKABLE link: `<a href="https://t.me/{id}" target="_blank" class="text-slate-800 hover:text-primary">@{{id}}</a>` OR if username exists: `<a href="https://t.me/{{username}}" target="_blank" class="text-slate-800 hover:text-primary">@{{username}}</a>`, use custom Telegram icon (DARK: `text-slate-700`)
              - Telegram Username: Display if data.client["telegram username"] exists - format as CLICKABLE link: `<a href="https://t.me/{{username}}" target="_blank" class="text-slate-800 hover:text-primary">@{{username}}</a>`
              - Work hours: Display if data.contacts.work_hours exists, use `text-slate-700` class (DARK, not white)
              - **CRITICAL**: 
                * Display addresses EXACTLY as they appear in data.contacts.address - do not rewrite, generalize, or truncate
                * ALL contact info must be CLICKABLE links where applicable (phone, email, telegram)
                * ALL text in cards must have explicit DARK color class (`text-slate-800` or `text-slate-900`) - cards have light backgrounds!
            - Display contact info in cards with `glass-card-strong` class.
            - **CARD COLOR RULES** (CRITICAL):
              - Cards have LIGHT background (white/light), so text inside cards MUST be DARK:
              - Text in cards: `text-slate-800` or `text-slate-900` (NEVER white or light colors)
              - Labels in cards: `text-slate-600` or `text-slate-700`
              - Links in cards: `text-primary hover:text-primary/80` or `text-slate-800 hover:text-primary`
              - Icons in cards: `text-slate-700` or `text-primary` (NEVER white)
              - **NEVER use white/light text on light card backgrounds**
              - Cards are on dark background, but cards themselves are light, so text inside must be dark
            - **Social Links** (from data.social or data.footer.social):
              - Telegram: if data.social.telegram exists (display as icon link, WHITE color)
              - WhatsApp: if data.social.whatsapp exists (WHITE color)
              - VK: if data.social.vk exists (WHITE color)
              - Instagram: if data.social.instagram exists (WHITE color)
            - Socials: Inline SVG icons with hover glow effects, WHITE or light colored.
            - **Footer Links** (from data.footer.links): Display navigation links if available, use `text-white hover:text-primary/80`.
            - Copyright: Display data.footer.copyright if available, use `text-slate-300` or `text-slate-400`.
            - Add subtle animations on load.
            - Use `section-container` class.
            - **SPACING**: Use COMPACT padding - `py-12 md:py-16` (NOT section-padding which is too large)
            - **REMEMBER**: 
              * Dark background section = Light text for section text
              * Light card backgrounds = Dark text inside cards
            - Layout: Contact info cards at top, social links below, footer links and copyright at bottom.
            - Keep footer compact - reduce vertical spacing between elements.
            """
        }
        ]

        new_files = []

        for comp in components_queue:
            print(f"   > Designing {comp['name']}...")
            
            # Отладочный вывод для проверки данных
            if 'image' in comp['data']:
                print(f"      Image URL in data: {comp['data'].get('image', 'NOT FOUND')[:80]}")
            if 'items' in comp['data']:
                print(f"      Gallery items count: {len(comp['data'].get('items', []))}")
                for idx, item in enumerate(comp['data'].get('items', [])[:2]):
                    print(f"      Item {idx} URL: {item.get('url', 'NOT FOUND')[:80] if isinstance(item, dict) else str(item)[:80]}")
            
            prompt = f"""
        Act as a Senior UI/UX Designer. Write the Astro component `src/components/{comp['name']}.astro`.
        
        CONTEXT:
        Business: {biz.get('name')}
        RAW_DATA: {json.dumps(comp['data'], ensure_ascii=False)}
        
        VISUAL BLUEPRINT:
        {comp['blueprint']}
        
        STRICT RULES:
        1. **LANGUAGE**: ALL GENERATED TEXT MUST BE IN RUSSIAN. Even if you hallucinate content, write it in Russian.
        2. **IMAGES** (CRITICAL):
           - **Hero/About**: MUST use img tag with src attribute pointing to data.image variable
           - Example: use data.image in the src attribute - the syntax should be src with curly braces containing data.image
           - The URL is already provided in data.image, use it directly in the img src attribute
           - **Gallery**: Use data.items array. Each item has url property. Display as: img tag with src using item.url in curly braces
           - **Logo** (for Navigation component):
             * Check if data.logo.url exists and is not empty
             * If logo URL exists: Use img tag with src pointing to data.logo.url, alt to data.logo.alt, class "h-10 md:h-12 object-contain", and style with width from data.logo.width
             * If logo URL is empty: Display text logo using data.business_name with gradient effect (text-gradient class)
             * Logo should be wrapped in clickable link to home (href="#hero" or href="/")
           - **NO placeholders**: Never use "https://placehold.co" or similar. Always use the provided URLs from data.
           - **NO fake paths**: No `src="/image.jpg"` or relative paths. Only use URLs from data.
           - **Gallery images**: Use `aspect-square object-cover w-full` to make them uniform.
           - Check data structure: if data.image exists, use it. If data.items exists, iterate over it. If data.logo exists, check data.logo.url.
        3. **TEXT GENERATION** (IMPORTANT):
           - Write naturally, elegantly, and professionally - like premium brand copy
           - DO NOT include technical/metadata details from JSON:
             * Target audience specifics (income levels, demographics like "мужчины с доходом 100+к рублей")
             * Business goals, metrics, technical specifications
             * Internal data that shouldn't be public-facing
           - **ADDRESS/LOCATION RULES**:
             * If address exists in data.contacts.address or data.client data and is VALID (real address, not placeholder):
               - USE THE EXACT ADDRESS as provided
               * Only rewrite if address is clearly a placeholder (like "улица геолокации йй" or "test location")
               * DO NOT replace real addresses with generic phrases like "в центре города"
               * For Contact component: Display the actual address from data.contacts.address if it exists
           - Instead, focus on: quality, craftsmanship, experience, atmosphere, expertise, tradition, attention to detail
           - Make text sound premium and appealing, not technical or data-driven
           - For About section: Write about the art, mastery, premium experience, unique approach
           - Use elegant, marketing-oriented language that appeals to clients who value quality
           - Transform technical data into natural, elegant descriptions, BUT keep real addresses as-is
        4. **ICONS**: Use `lucide-astro`.
        5. **CLICKABLE LINKS** (IMPORTANT):
           - **On dark backgrounds**: Links MUST have `text-white hover:text-primary/80` class
           - **On light card backgrounds**: Links MUST have `text-slate-800 hover:text-primary` or `text-primary hover:text-primary/80` class
           - Phone numbers: MUST be clickable links with href="tel:PHONE_NUMBER"
           - Email addresses: MUST be clickable links with href="mailto:EMAIL"
           - Telegram IDs: MUST be clickable links with href="https://t.me/TELEGRAM_ID" target="_blank", display as @TELEGRAM_ID
           - Telegram usernames: MUST be clickable links with href="https://t.me/USERNAME" target="_blank", display as @USERNAME
           - Social links: MUST be clickable with proper href and target="_blank"
           - **CRITICAL**: Check if link is inside glass-card or glass-card-strong - if yes, use DARK colors, if no (on dark bg), use LIGHT colors
        6. **FORMS**: For Contact component - DO NOT add any contact form. Only display contact information (address, phone, email) in cards. NO input fields, NO submit buttons, NO forms.
        7. **SPACING** (IMPORTANT): Use COMPACT spacing throughout:
           - Between columns: `gap-8 md:gap-10` (not gap-12 or gap-16)
           - Between paragraphs: `mb-3` (not mb-4 or mb-6)
           - Between sections: Use `section-padding` class (already compact)
           - In grids: `gap-6 md:gap-8` (not gap-12)
           - Card padding: `p-6 md:p-8` (not p-10 or p-12)
        8. **COLOR CONTRAST** (CRITICAL - NEVER VIOLATE):
           - On DARK backgrounds (slate-900, slate-800, dark gradients, black): ALWAYS use LIGHT text:
             * **EVERY text element** MUST have explicit class: `text-white`, `text-slate-100`, or `text-slate-200`
             * **NEVER rely on default/inherited colors** - always set color explicitly on every element
             * Text: `text-white`, `text-slate-100`, `text-slate-200` (NEVER dark colors like slate-800, slate-900, black)
             * Links: `text-white hover:text-primary/80` or `text-slate-200 hover:text-white` (ALWAYS set explicitly)
             * Icons: `text-white` or `text-slate-200` (ALWAYS set explicitly)
             * Labels: `text-slate-200` or `text-slate-300` (ALWAYS set explicitly)
             * **RULE**: Every `<p>`, `<span>`, `<div>`, `<a>`, `<h1-h6>` with text MUST have explicit `text-white` or `text-slate-100/200` class
           - On LIGHT backgrounds (white, slate-50, light colors, glass cards): Use DARK text:
             * **CRITICAL**: Glass cards (glass-card, glass-card-strong) have LIGHT backgrounds, so text inside MUST be DARK
             * Text in cards: `text-slate-800` or `text-slate-900` (NEVER white or light colors)
             * Labels in cards: `text-slate-600` or `text-slate-700`
             * Links in cards: `text-primary hover:text-primary/80` or `text-slate-800 hover:text-primary`
             * Icons in cards: `text-slate-700` or `text-primary` (NEVER white)
             * **RULE**: Every text element inside glass-card or glass-card-strong MUST have explicit dark color class
             * Text: `text-slate-800`, `text-slate-900`, `text-slate-700`
             * Links: `text-primary` or `text-slate-700`
           - **FORBIDDEN COMBINATIONS**:
             * NEVER: `text-slate-800` or `text-slate-900` or `text-black` on `bg-slate-900` or dark backgrounds
             * NEVER: `text-white` on `bg-white` or light backgrounds (unless intentional)
             * NEVER: Default/inherited text colors on dark backgrounds - ALWAYS set explicitly
             * Check background color FIRST, then choose appropriate text color!
           - Contact/Footer component: Background is DARK, so ALL text MUST have explicit `text-white` or `text-slate-100/200` class
           - **EXAMPLE**: `<p class="text-white">Адрес</p>` NOT `<p>Адрес</p>` (always add color class!)
        9. **REQUIRED**: Every image tag MUST have a valid src attribute pointing to data.image or item.url
        
        START FILE WITH:
        ```astro
        ---
        const data = {json.dumps(comp['data'])};
        import {{ Star, Scissors, Zap, MapPin, Phone, Mail, ArrowRight, Check }} from 'lucide-astro';
        ---
        ```
        
            OUTPUT: Only the code block.
            """
            
            try:
                response = self.llm_coder.invoke([HumanMessage(content=prompt)])
                raw = response.content
                match = re.search(r'```(?:astro)?(.*?)```', raw, re.DOTALL)
                code = match.group(1).strip() if match else raw
                
                secure_code = self.enforce_variable_existence(code, comp['data'])
                new_files.append({"name": f"src/components/{comp['name']}.astro", "content": secure_code})
                
            except Exception as e:
                print(f"❌ Error {comp['name']}: {e}")
                fallback = f"---\nconst data={{}};\n---\n<div class='p-10'>Error</div>"
                new_files.append({"name": f"src/components/{comp['name']}.astro", "content": fallback})

        return {"generated_files": new_files}

    def pages_node(self, state: AgentState):
        print("--- [7/7] Assembling One-Page Site ---")
        comps = self.get_component_names(state['generated_files'])
        order = ["Navigation", "Hero", "Features", "About", "Gallery", "Contact"]
        
        imports = []
        tags = []
        
        for item in order:
            found = next((c for c in comps if item in c), None)
            if found:
                name = found.split('/')[-1].replace('.astro', '')
                imports.append(f"import {name} from '../components/{name}.astro';")
                tags.append(f"\t\t<{name} />")
                
        page_code = f"""---
import BaseLayout from '../layouts/Base.astro';
{chr(10).join(imports)}
const title = "{state['input_data']['project']['business'].get('name', 'Site')}";
---
<BaseLayout title={{title}}>
    <main class="relative space-y-0">
{chr(10).join(tags)}
    </main>
</BaseLayout>
"""
        return {"generated_files": [{"name": "src/pages/index.astro", "content": page_code}]}

    def finalizer_node(self, state: AgentState):
        """Финальный узел - просто завершает workflow, все данные уже в состоянии"""
        print("--- [FINISH] Finalizing ---")
        # Не возвращаем ничего - все данные уже в state
        # generate() соберет их из result['ctm_identity'] и result['generated_files']
        return {}

# --- GRAPH BUILD ---

# --- DEPLOY FUNCTION ---
def generate_site(json_data: Dict[str, Any], api_key: str = None, base_url: str = None) -> Dict[str, Any]:
    """
    Функция для деплоя: принимает JSON и возвращает результат генерации сайта
    
    Args:
        json_data: Словарь с данными для генерации сайта
        api_key: API ключ для LLM (опционально, использует дефолтный если не указан)
        base_url: Base URL для LLM (опционально, использует дефолтный если не указан)
    
    Returns:
        Словарь с ключом "files", содержащий список сгенерированных файлов
    """
    generator = SiteGenerator(api_key=api_key, base_url=base_url)
    return generator.generate(json_data)

# --- RUN ---
if __name__ == "__main__":
    # Вставьте сюда ваш JSON
    sample_input = {
  "project": {
    "client": {
      "name": "",
      "phone": "+79998147243",
      "email": "",
      "telegram id": "7052064142",
      "preferred_contact": "telegram"
    },
    "business": {
      "name": "лысинка",
      "type": "визитка",
      "industry": "услуги",
      "location": "Москва, улица геолокации 11",
      "goal": "предоставляю стрижку на лысину топором, огнем, и бритвой"
    },
    "content": {
      "contacts": {
        "phone": "+79998147243"
      }
    }
  },
  "design": {
    "style": "",
    "colors": {
      "primary": "#8B7A5D",
      "secondary": "#9C917B",
      "accent": "#2D2112",
      "background": "#ffffff",
      "text": "#62575B",
      "custom": [
        "#0C100D",
        "#463C30",
        "#BB9C86",
        "#6D5C3F",
        "#DAB3A1",
        "#9BA099",
        "#A97361"
      ]
    },
    "fonts": {
      "heading": "Inter",
      "body": "Inter",
      "sizes": {
        "h1": "3rem",
        "h2": "2.5rem",
        "h3": "2rem",
        "body": "1rem"
      }
    },
    "images": {
      "hero": {
        "url": "",
        "alt": "",
        "position": "center"
      },
      "features": [],
      "about": {
        "url": "",
        "alt": ""
      },
      "gallery": [
        {
          "url": "",
          "file_id": "",
          "name": "Example Image 1",
          "alt": "Example Image 1"
        },
        {
          "url": "",
          "file_id": "",
          "name": "Example Image 2",
          "alt": "Example Image 2"
        }
      ],
      "logo": {
        "url": "",
        "width": "200px"
      }
    }
  },
  "content": {
    "language": "ru",
    "hero": {
      "headline": "Стрижка на лысину с искусством",
      "subheadline": "Ваш стиль — наша забота",
      "cta_text": "Связаться",
      "cta_url": "#contacts"
    },
    "sections": [],
    "features": [],
    "services": [],
    "testimonials": [],
    "contacts": {
      "phone": "+79998147243",
      "email": "",
      "telegram": "",
      "address": "",
      "work_hours": "",
      "map_embed": ""
    }
  },
  "structure": {
    "pages": [],
    "navigation": [],
    "footer": {
      "links": [],
      "social": {
        "telegram": "",
        "whatsapp": "",
        "vk": "",
        "instagram": ""
      },
      "copyright": "© 2025 лысинка"
    }
  },
  "technical": {
    "domain": "",
    "seo": {
      "title": "",
      "description": "",
      "keywords": [],
      "opengraph": {
        "image": "",
        "title": "",
        "description": ""
      }
    },
    "analytics": {
      "google_analytics": "",
      "yandex_metrika": ""
    },
    "features": {
      "forms": False,
      "animations": "subtle",
      "responsive": True,
      "pwa": False
    }
  },
  "files": {
    "base_astro_template": {
      "content": ""
    },
    "package_json": {
      "content": {}
    },
    "data_yaml": {
      "content": ""
    }
  },
  "timeline": {
    "status": "ready",
    "generated_at": "2025-12-28T10:20:32.882686",
    "deployed_at": "",
    "notes": ""
  }
}


    # Пример использования
    generator = SiteGenerator()
    result = generator.generate(sample_input)
    
    filename = "result_site_fixed.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
    print(f"✅ DONE! Saved to {filename}")