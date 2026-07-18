"""
SAKURA INTELLIGENCE - Monitoreo Automático
Usando la API REST de Supabase (sin conexión directa a PostgreSQL)
"""

import feedparser
import requests
from datetime import datetime
import sys
import json

# ============================================================================
# CONFIGURACIÓN - TUS CREDENCIALES DE SUPABASE
# ============================================================================

SUPABASE_URL = "https://iwydoymmpojjzanuweur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml3eWRveW1tcG9qanphbnV3ZXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNDAwMzcsImV4cCI6MjA5OTgxNjAzN30.Q-5bsEBkHFKcU7eC2l99zVdLfdeYvjgLg1DrwxIb32I"

# Feeds a monitorear
FEEDS = [
    {'url': 'https://news.google.com/rss/search?q=vuelo+directo+Panam%C3%A1+Tokio&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=ANA+Tocumen&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=All+Nippon+Airways+Panama&hl=en-US&gl=US&ceid=US:en', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=Panama+Japan+aviation+agreement&hl=en-US&gl=US&ceid=US:en', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=Jap%C3%B3n+Panam%C3%A1+vuelo+directo&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'}
]

# ============================================================================
# FUNCIONES
# ============================================================================

def get_existing_urls():
    """Obtiene las URLs ya existentes en feed_bruto (vía API REST)"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/feed_bruto?select=url"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {item['url'] for item in data}
    except Exception as e:
        print(f"❌ Error al obtener URLs existentes: {e}")
        sys.exit(1)

def save_articles(articles):
    """Guarda artículos nuevos en feed_bruto (vía API REST)"""
    if not articles:
        return 0
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/feed_bruto"
    
    data = []
    for a in articles:
        data.append({
            "title": a['title'],
            "url": a['url'],
            "source": a['source'],
            "publication_date": a['pub_date'].isoformat() if a['pub_date'] else None,
            "route_code": a['route'],
            "detection_date": datetime.now().isoformat(),
            "processed": False
        })
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return len(data)
    except Exception as e:
        print(f"❌ Error al guardar artículos: {e}")
        return 0

def fetch_feed(feed_url, route_code):
    """Lee un feed RSS y extrae artículos"""
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
                'route': route_code
            })
        return articles
    except Exception as e:
        print(f"⚠️  Error al leer el feed {feed_url}: {e}")
        return []

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

def main():
    print(f"🚀 Sakura Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # Verificar conexión a Supabase API
    try:
        existing_urls = get_existing_urls()
        print(f"📊 {len(existing_urls)} noticias ya almacenadas")
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        sys.exit(1)
    
    all_articles = []
    for feed in FEEDS:
        print(f"📡 Leyendo: {feed['url'][:60]}...")
        articles = fetch_feed(feed['url'], feed['route'])
        new = [a for a in articles if a['url'] not in existing_urls]
        all_articles.extend(new)
        print(f"   ➕ {len(new)} nuevas")
    
    if all_articles:
        saved = save_articles(all_articles)
        print("=" * 50)
        print(f"✅ {saved} noticias guardadas en Supabase")
        print(f"📊 Total: {len(existing_urls) + saved}")
    else:
        print("=" * 50)
        print("✅ No hay noticias nuevas.")
        {'url': 'https://www.aeroroutes.com/?format=rss', 'route': 'JP-PTY'},
    print("📋 Revisa tus datos en Supabase → Table Editor → feed_bruto")

if __name__ == "__main__":
    main()
