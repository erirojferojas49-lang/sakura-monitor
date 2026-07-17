"""
SAKURA INTELLIGENCE - Monitoreo Automático
Ejecución diaria vía GitHub Actions
"""

import feedparser
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import os
import sys

# ============================================================================
# CONFIGURACIÓN - TUS CREDENCIALES DE SUPABASE
# ============================================================================

# ¡¡¡CAMBIA ESTOS VALORES POR LOS TUYOS!!!
DB_HOST = "db.iwydoymmpojjzanuweur.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = r"7D4Ve8Kf^*aAFA&"

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

def get_db_connection():
    """Intenta conectar a Supabase y maneja errores explícitamente."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✅ Conexión a Supabase exitosa.")
        return conn
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: No se pudo conectar a Supabase.")
        print(f"   Detalle del error: {e}")
        print("   Revisa tus credenciales en el script (DB_HOST, DB_PASSWORD).")
        sys.exit(1)

def get_existing_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM feed_bruto")
    return {row[0] for row in cursor.fetchall()}

def save_articles(conn, articles):
    if not articles:
        return 0
    cursor = conn.cursor()
    data = []
    for a in articles:
        data.append((a['title'], a['url'], a['source'], a['pub_date'], a['route']))
    
    query = """
    INSERT INTO feed_bruto (title, url, source, publication_date, route_code)
    VALUES %s
    ON CONFLICT (url) DO NOTHING
    """
    try:
        execute_values(cursor, query, data)
        conn.commit()
        return len(data)
    except Exception as e:
        print(f"❌ Error al guardar artículos en la base de datos: {e}")
        conn.rollback()
        return 0

def fetch_feed(feed_url, route_code):
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
    
    conn = get_db_connection()
    
    existing_urls = get_existing_urls(conn)
    print(f"📊 {len(existing_urls)} noticias ya almacenadas")
    
    all_articles = []
    for feed in FEEDS:
        print(f"📡 Leyendo: {feed['url'][:60]}...")
        articles = fetch_feed(feed['url'], feed['route'])
        new = [a for a in articles if a['url'] not in existing_urls]
        all_articles.extend(new)
        print(f"   ➕ {len(new)} nuevas")
    
    saved = save_articles(conn, all_articles)
    print("=" * 50)
    print(f"✅ {saved} noticias guardadas en Supabase")
    print(f"📊 Total: {len(existing_urls) + saved}")
    conn.close()

if __name__ == "__main__":
    main()
