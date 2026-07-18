"""
SAKURA INTELLIGENCE — Monitor automático v3 (optimizado)
"""

import feedparser
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ============================================================
# FEEDS A MONITOREAR
# ============================================================

FEEDS = [
    {'url': 'https://news.google.com/rss/search?q=vuelo+directo+Panam%C3%A1+Tokio&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=ANA+Tocumen&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=All+Nippon+Airways+Panama&hl=en-US&gl=US&ceid=US:en', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=Panama+Japan+aviation+agreement&hl=en-US&gl=US&ceid=US:en', 'route': 'JP-PTY'},
    {'url': 'https://news.google.com/rss/search?q=Jap%C3%B3n+Panam%C3%A1+vuelo+directo&hl=es-419&gl=PA&ceid=PA:es-419', 'route': 'JP-PTY'},
    {'url': 'https://www.aeroroutes.com/?format=rss', 'route': 'JP-PTY'},
]

# ============================================================
# FUNCIONES
# ============================================================

def fetch_feed(url):
    """Obtiene y parsea un feed RSS"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"   ⚠️ Error {response.status_code} al leer {url}")
            return []
        feed = feedparser.parse(response.content)
        return feed.entries
    except Exception as e:
        print(f"   ❌ Error al leer feed: {e}")
        return []

def get_existing_urls():
    """Obtiene las URLs ya existentes en Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return set()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/feed_bruto?select=url"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {item['url'] for item in data}
        return set()
    except:
        return set()

def save_articles(articles):
    """Guarda artículos nuevos en Supabase"""
    if not articles or not SUPABASE_URL or not SUPABASE_KEY:
        return 0
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    data = []
    for article in articles:
        data.append({
            "title": article.get('title', 'Sin título')[:300],
            "url": article.get('link', ''),
            "source": article.get('source', ''),
            "publication_date": article.get('published', ''),
            "detection_date": datetime.now().isoformat(),
            "route_code": "JP-PTY",
            "processed": False,
            "evidence_level": 1,
            "confidence_score": 0.5,
            "category": "general",
        })
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/feed_bruto",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code in [200, 201]:
            return len(data)
        else:
            print(f"   ⚠️ Error guardando: {response.status_code}")
            return 0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0

# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():
    print(f"🚀 Sakura Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    existing_urls = get_existing_urls()
    print(f"📊 {len(existing_urls)} noticias ya almacenadas")
    
    new_articles = []
    for feed in FEEDS:
        print(f"📡 Leyendo: {feed['url'][:60]}...")
        entries = fetch_feed(feed['url'])
        
        for entry in entries:
            url = entry.get('link', '')
            if not url:
                continue
            if url in existing_urls:
                continue
            existing_urls.add(url)
            new_articles.append({
                'title': entry.get('title', 'Sin título'),
                'link': url,
                'source': entry.get('source', ''),
                'published': entry.get('published', ''),
            })
        
        print(f"   ➕ {len([a for a in new_articles if a.get('link')])} nuevas")
    
    if new_articles:
        saved = save_articles(new_articles)
        print(f"\n✅ {saved} artículos guardados en Supabase")
    else:
        print("\nℹ️ Sin artículos nuevos")
    
    print("=" * 60)
    print("✅ Monitor completado")

if __name__ == "__main__":
    main()
