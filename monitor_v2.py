"""
SAKURA INTELLIGENCE V2 - Motor de Inteligencia OSINT
Clasificación automática, extracción de entidades, detección de duplicados,
sistema de puntuación, dashboard y alertas.
"""

import feedparser
import requests
from datetime import datetime
import sys
import json
import hashlib
import re
import time

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SUPABASE_URL = "https://iwydoymmpojjzanuweur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml3eWRveW1tcG9qanphbnV3ZXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNDAwMzcsImV4cCI6MjA5OTgxNjAzN30.Q-5bsEBkHFKcU7eC2l99zVdLfdeYvjgLg1DrwxIb32I"

# Feeds
FEEDS = [
    {'url': 'https://news.google.com/rss/search?q=vuelo+directo+Panam%C3%A1+Tokio&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=ANA+Tocumen&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=All+Nippon+Airways+Panama&hl=en-US&gl=US&ceid=US:en', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=Panama+Japan+aviation+agreement&hl=en-US&gl=US&ceid=US:en', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=Jap%C3%B3n+Panam%C3%A1+vuelo+directo&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'}
        # ============================================================
    # FUENTES OFICIALES (Nuevas)
    # ============================================================
    {'url': 'https://www.aac.gob.pa/noticias/', 'route': 'JP-PTY'},  # Autoridad Aeronáutica de Panamá
    {'url': 'https://www.mlit.go.jp/report/press/', 'route': 'JP-PTY'},  # Ministerio de Transporte de Japón
    {'url': 'https://www.ana.co.jp/group/en/investors/ir-news/', 'route': 'JP-PTY'},  # Noticias de ANA
    {'url': 'https://www.tocumenpanama.aero/noticias/', 'route': 'JP-PTY'},  # Aeropuerto de Panamá
]

# ============================================================================
# 1. CLASIFICACIÓN AUTOMÁTICA
# ============================================================================

def classify_article(title, source, text=""):
    """Clasifica automáticamente una noticia según su fuente y contenido."""
    
    # Mapeo de fuentes a nivel de evidencia (0-10)
    source_weight = {
        'AAC': 8,           # Antes era 6
    'MLIT': 8,          # Antes era 6
    'ANA': 7,           # Antes era 5
    'Tocumen S.A.': 6,  # Antes era 4
    'Copa Airlines': 4, # Antes era 3
    'Infobae': 3,       # Antes era 2
    'La Prensa': 2,     # Sigue igual
    'TVN': 2,           # Sigue igual
    'Bloomberg': 4,     # Antes era 3
    'Reuters': 4,       # Antes era 3
    'Google News': 1    # Sigue igual
    }
    
    # Palabras clave que aumentan la confianza
    keywords_high = ['firma', 'acuerdo', 'autorización', 'oficial', 'RoD', 'derechos de tráfico', 'tratado', 'firmado']
    keywords_medium = ['evaluación', 'visita', 'reunión', 'negociación', 'inspección', 'auditoría']
    keywords_low = ['rumor', 'posible', 'fuentes', 'especulación', 'podría']
    
    # Calcular nivel de evidencia
    evidence_level = source_weight.get(source, 1)
    
    # Ajustar por contenido
    confidence = 0.5
    combined_text = (title + " " + text).lower()
    
    for keyword in keywords_high:
        if keyword.lower() in combined_text:
            confidence += 0.25
            evidence_level = min(10, evidence_level + 2)
    for keyword in keywords_medium:
        if keyword.lower() in combined_text:
            confidence += 0.15
            evidence_level = min(10, evidence_level + 1)
    for keyword in keywords_low:
        if keyword.lower() in combined_text:
            confidence -= 0.2
            evidence_level = max(1, evidence_level - 1)
    
    # Normalizar
    confidence = max(0, min(1, confidence))
    
    # Determinar categoría
    if evidence_level >= 8:
        category = "oficial"
    elif evidence_level >= 5:
        category = "especializada"
    elif evidence_level >= 3:
        category = "general"
    else:
        category = "rumor"
    
    return {
        'evidence_level': evidence_level,
        'confidence_score': confidence,
        'category': category,
        'source_weight': source_weight.get(source, 1)
    }

# ============================================================================
# 2. EXTRACCIÓN DE ENTIDADES
# ============================================================================

def extract_entities(text):
    """Extrae entidades clave de un texto."""
    
    entities = {
    'airlines': ['ANA', 'JAL', 'Copa', 'United', 'Delta', 'American', 'Air Canada', 'LATAM', 'Avianca'],
    'airports': ['PTY', 'NRT', 'HND', 'Tocumen', 'Narita', 'Haneda', 'Ciudad de Panamá', 'Tokio'],
    'organizations': ['AAC', 'MLIT', 'JCAB', 'Boeing', 'Airbus', 'IATA', 'OACI', 'DGAC'],
    'people': ['Mulino', 'Ishiba', 'Martínez-Acha', 'Bárcenas', 'Nagasawa', 'Nakayama', 'Cohen'],
    'agreements': ['RoD', 'Acuerdo bilateral', 'Derechos de tráfico', 'Código compartido', 'Tratado', 'Open Skies'],
    'aircraft': ['787', 'Dreamliner', '777', 'Boeing 787', 'Boeing 777', 'A350', 'A330'],
    'regulatory': ['slot', 'permiso', 'licencia', 'autorización', 'certificado']
}
    
    found = []
    text_lower = text.lower()
    
    for category, items in entities.items():
        for item in items:
            # Buscar coincidencia exacta o en minúsculas
            if item in text or item.lower() in text_lower:
                found.append({
                    'name': item,
                    'category': category,
                    'confidence': 0.9 if item in text else 0.7
                })
    
    return found

# ============================================================================
# 3. DETECCIÓN DE DUPLICADOS
# ============================================================================

def generate_hash(title, source):
    """Genera un hash único para una noticia."""
    return hashlib.md5((title.strip() + "|||" + source.strip()).encode()).hexdigest()

def get_existing_hashes():
    """Obtiene los hashes existentes de la base de datos."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/feed_bruto?select=content_hash"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {item['content_hash'] for item in data if item.get('content_hash')}
    except:
        pass
    return set()

# ============================================================================
# 4. SISTEMA DE PUNTUACIÓN (ÍNDICE SAKURA)
# ============================================================================

def calculate_sakura_index():
    """Calcula el índice de confianza basado en eventos y señales."""
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    # Obtener eventos
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/events?select=event_type",
            headers=headers,
            timeout=10
        )
        events = response.json() if response.status_code == 200 else []
    except:
        events = []
    
    # Obtener hipótesis
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/hypotheses?select=status,confidence_score",
            headers=headers,
            timeout=10
        )
        hypotheses = response.json() if response.status_code == 200 else []
    except:
        hypotheses = []
    
    # Obtener señales
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/signals?select=impact_level",
            headers=headers,
            timeout=10
        )
        signals = response.json() if response.status_code == 200 else []
    except:
        signals = []
    
    # Calcular puntuación
    total_score = 0
    
    # 1. Puntuación por eventos (40%)
    event_types = {
        'diplomatic': 10,
        'technical': 20,
        'juridical': 30,
        'commercial': 25,
        'corporate': 15
    }
    event_score = sum(event_types.get(e.get('event_type', ''), 0) for e in events)
    event_score = min(40, event_score)
    total_score += event_score
    
    # 2. Puntuación por hipótesis (30%)
    if hypotheses:
        avg_confidence = sum(h.get('confidence_score', 0) for h in hypotheses) / len(hypotheses)
        hypothesis_score = (avg_confidence / 100) * 30
        total_score += hypothesis_score
    
    # 3. Puntuación por señales críticas (30%)
    critical_signals = sum(1 for s in signals if s.get('impact_level') == 'critical')
    signal_score = min(30, critical_signals * 10)
    total_score += signal_score
    
    # Calcular nivel de confianza
    if total_score >= 80:
        level = "🟢 ALTA"
    elif total_score >= 50:
        level = "🟡 MEDIA"
    elif total_score >= 30:
        level = "🟠 BAJA"
    else:
        level = "🔴 MUY BAJA"
    
    return {
        'score': round(total_score, 1),
        'max_score': 100,
        'level': level,
        'details': {
            'event_score': round(event_score, 1),
            'hypothesis_score': round(hypothesis_score, 1) if hypotheses else 0,
            'signal_score': round(signal_score, 1),
            'total_events': len(events),
            'total_hypotheses': len(hypotheses),
            'critical_signals': critical_signals
        }
    }

# ============================================================================
# 5. DASHBOARD ESTRATÉGICO
# ============================================================================

def get_strategic_dashboard():
    """Obtiene el dashboard estratégico desde la base de datos."""
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    # Consultar las vistas
    try:
        # Noticias totales
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/feed_bruto?select=count",
            headers=headers,
            timeout=10
        )
        total_news = len(response.json()) if response.status_code == 200 else 0
        
        # Fuentes distintas
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/feed_bruto?select=source",
            headers=headers,
            timeout=10
        )
        sources = response.json() if response.status_code == 200 else []
        distinct_sources = len(set(s.get('source') for s in sources if s.get('source')))
        
        # Noticias procesadas
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/feed_bruto?select=processed&processed=eq.true",
            headers=headers,
            timeout=10
        )
        processed = len(response.json()) if response.status_code == 200 else 0
        
        return {
            'total_noticias': total_news,
            'fuentes_distintas': distinct_sources,
            'noticias_procesadas': processed,
            'noticias_pendientes': total_news - processed
        }
    except:
        return {
            'total_noticias': 0,
            'fuentes_distintas': 0,
            'noticias_procesadas': 0,
            'noticias_pendientes': 0
        }

# ============================================================================
# 6. SISTEMA DE ALERTAS
# ============================================================================

def send_alert(level, message, details=""):
    """Envía alertas según el nivel de importancia."""
    
    emoji = {
        'critical': '🚨',
        'high': '⚠️',
        'medium': '📌',
        'low': 'ℹ️'
    }
    
    print(f"{emoji.get(level, 'ℹ️')} ALERTA {level.upper()}: {message}")
    if details:
        print(f"   {details}")
    
    # Aquí se podría agregar envío de email o notificación
    if level in ['critical', 'high']:
        # Log de alerta crítica
        with open('alert_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} | {level.upper()} | {message}\n")

# ============================================================================
# 7. FUNCIONES PRINCIPALES
# ============================================================================

def fetch_feed(feed_url, route_code):
    """Lee un feed RSS y extrae artículos."""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:10]:
            pub_date = None
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            source = ''
            if hasattr(entry, 'source'):
                source = entry.source.title if hasattr(entry.source, 'title') else ''
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'source': source,
                'pub_date': pub_date,
                'route': route_code,
                'text': entry.summary if hasattr(entry, 'summary') else ''
            })
        return articles
    except Exception as e:
        print(f"⚠️ Error al leer el feed {feed_url}: {e}")
        return []

def save_articles_v2(articles):
    """Guarda artículos con clasificación, entidades y duplicados."""
    if not articles:
        return 0
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/feed_bruto"
    
    # Obtener hashes existentes
    existing_hashes = get_existing_hashes()
    
    saved_count = 0
    for article in articles:
        content_hash = generate_hash(article['title'], article['source'])
        
        # Saltar duplicados
        if content_hash in existing_hashes:
            print(f"   ⏭️ Duplicado: {article['title'][:50]}...")
            continue
        
        # Clasificar
        classification = classify_article(article['title'], article['source'], article.get('text', ''))
        entities = extract_entities(article['title'] + ' ' + article.get('text', ''))
        
        # Preparar datos
        data = {
            "title": article['title'],
            "url": article['url'],
            "source": article['source'],
            "publication_date": article['pub_date'].isoformat() if article['pub_date'] else None,
            "route_code": article['route'],
            "detection_date": datetime.now().isoformat(),
            "processed": False,
            "content_hash": content_hash,
            "evidence_level": classification['evidence_level'],
            "confidence_score": classification['confidence_score'],
            "category": classification['category'],
            "entities": entities,
            "metadata": {
                "source_weight": classification['source_weight'],
                "text_preview": article.get('text', '')[:500]
            }
        }
        
        # Guardar
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code in [200, 201]:
                saved_count += 1
                existing_hashes.add(content_hash)
                print(f"   ✅ Guardado: {article['title'][:50]}...")
                
                # Verificar si es una señal crítica
                if classification['evidence_level'] >= 7 and classification['confidence_score'] >= 0.7:
                    send_alert(
                        'high',
                        f"Señal fuerte detectada: {article['title'][:100]}",
                        f"Fuente: {article['source']} | Nivel: {classification['evidence_level']}"
                    )
            else:
                print(f"   ❌ Error al guardar: {article['title'][:50]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return saved_count

# ============================================================================
# 8. EJECUCIÓN PRINCIPAL V2
# ============================================================================

def main():
    print(f"🐋 SAKURA INTELLIGENCE V2 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 1. Dashboard inicial
    dashboard = get_strategic_dashboard()
    print(f"📊 ESTADO ACTUAL:")
    print(f"   - Noticias totales: {dashboard['total_noticias']}")
    print(f"   - Fuentes distintas: {dashboard['fuentes_distintas']}")
    print(f"   - Por procesar: {dashboard['noticias_pendientes']}")
    
    # 2. Índice de confianza
    index = calculate_sakura_index()
    print(f"\n📈 ÍNDICE SAKURA: {index['score']}/100 - {index['level']}")
    print(f"   Detalles: {json.dumps(index['details'], indent=2)}")
    
    # 3. Procesar feeds
    print(f"\n📡 PROCESANDO FEEDS...")
    all_articles = []
    for feed in FEEDS:
        print(f"   Leyendo: {feed['url'][:60]}...")
        articles = fetch_feed(feed['url'], feed['route'])
        all_articles.extend(articles)
    
    print(f"\n📰 Total de artículos encontrados: {len(all_articles)}")
    
    # 4. Guardar artículos
    if all_articles:
        saved = save_articles_v2(all_articles)
        print(f"\n✅ {saved} artículos guardados en Supabase")
    
    # 5. Verificar señales críticas
    print(f"\n🔍 Verificando señales críticas...")
    # Esta parte se podría expandir
    
    print("=" * 60)
    print("✅ SAKURA V2 COMPLETADO")

if __name__ == "__main__":
    main()
