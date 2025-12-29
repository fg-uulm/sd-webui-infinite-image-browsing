# Folder Statistics API Documentation

## Overview

Die neue Folder Statistics API bietet umfassende Analysefunktionen für Ordner im Dateisystem. Sie ermöglicht es, detaillierte Statistiken über Dateien, Medien, Tags und Metadaten zu sammeln und zu cachen.

## Features

- **Datei- und Ordnerstatistiken**: Anzahl von Dateien, Unterordnern und Gesamtgröße
- **Medienanalyse**: Separate Zählung von Bildern und Videos, getaggte vs. ungetaggte Medien
- **Tag-Aggregation**: Die am häufigsten verwendeten Tags im Ordner
- **Prompt-Wortanalyse**: Häufigste Wörter aus Bildprompts mit anpassbarer Stoppwort-Liste
- **Metadaten-Zusammenfassung**: Verwendete Models und Bildgrößen
- **Intelligentes Caching**: Automatische Cache-Invalidierung bei Ordneränderungen
- **Flexible Limits**: Konfigurierbare Analyse-Limits für Performance

## API Endpoints

### 1. Get Folder Statistics

**POST** `/infinite_image_browsing/folder_stats`

Ruft umfassende Statistiken für einen Ordner ab (mit Cache).

**Request Body:**
```json
{
  "folder_path": "/path/to/folder",
  "recursive": true,
  "force_refresh": false,
  "include_metadata": true,
  "analysis_limit": 1000
}
```

**Parameters:**
- `folder_path` (string, required): Pfad zum zu analysierenden Ordner
- `recursive` (boolean, default: true): Ob Unterordner rekursiv analysiert werden sollen
- `force_refresh` (boolean, default: false): Cache-Bypass erzwingen
- `include_metadata` (boolean, default: true): Detaillierte Metadaten-Analyse einschließen
- `analysis_limit` (integer, optional): Maximale Anzahl zu analysierender Bilder (null = unbegrenzt)

**Response:**
```json
{
  "folder_path": "/path/to/folder",
  "recursive": true,
  "file_count": 1523,
  "subfolder_count": 45,
  "total_size_bytes": 5234567890,
  "media_file_count": 1200,
  "media_stats": {
    "total_images": 1000,
    "total_videos": 200,
    "indexed_media": 1100,
    "tagged_images": 850,
    "untagged_images": 250,
    "analyzed_count": 1000,
    "limit_applied": true
  },
  "top_tags": [
    {
      "tag_id": 5,
      "tag_name": "landscape",
      "tag_type": "custom",
      "display_name": "Landscape",
      "count": 234,
      "percentage": 27.5
    }
  ],
  "prompt_analysis": {
    "total_prompts_analyzed": 950,
    "total_words_found": 5420,
    "top_words": [
      {
        "word": "masterpiece",
        "count": 723,
        "percentage": 13.3
      },
      {
        "word": "detailed",
        "count": 612,
        "percentage": 11.3
      }
    ]
  },
  "metadata_summary": {
    "models": {
      "model_name_1": 456,
      "model_name_2": 234
    },
    "sizes": {
      "512x512": 678,
      "768x768": 322
    }
  },
  "cache_info": {
    "is_cached": true,
    "computed_at": "2025-12-28T10:30:00",
    "cache_valid": true
  },
  "analysis_limit": 1000
}
```

### 2. Refresh Folder Statistics

**POST** `/infinite_image_browsing/folder_stats/refresh`

Erzwingt eine Neuberechnung der Statistiken (Cache-Bypass).

**Request Body:** Gleich wie bei GET Folder Statistics

**Response:** Gleich wie bei GET Folder Statistics

### 3. Clear Folder Statistics Cache

**DELETE** `/infinite_image_browsing/folder_stats/cache`

Löscht den Cache für spezifische Ordner.

**Request Body:**
```json
{
  "paths": ["/path/to/folder1", "/path/to/folder2"]
}
```

**Response:**
```json
{
  "cleared": 2
}
```

### 4. Clear All Folder Statistics Cache

**DELETE** `/infinite_image_browsing/folder_stats/cache/all`

Löscht den gesamten Statistik-Cache.

**Response:**
```json
{
  "message": "All folder statistics cache cleared"
}
```

### 5. Get Stopwords

**GET** `/infinite_image_browsing/folder_stats/stopwords`

Ruft die aktuelle Stoppwort-Liste ab.

**Response:**
```json
{
  "stopwords": ["a", "an", "and", "are", ...],
  "count": 62,
  "default_count": 62
}
```

### 6. Update Stopwords

**POST** `/infinite_image_browsing/folder_stats/stopwords`

Aktualisiert die Stoppwort-Liste für die Prompt-Analyse.

**Request Body:**
```json
{
  "words": ["custom", "word", "list", ...]
}
```

**Response:**
```json
{
  "message": "Stopwords updated successfully",
  "count": 45
}
```

### 7. Reset Stopwords

**POST** `/infinite_image_browsing/folder_stats/stopwords/reset`

Setzt die Stoppwort-Liste auf die Standardwerte zurück.

**Response:**
```json
{
  "message": "Stopwords reset to default",
  "count": 62
}
```

## Caching Strategy

### Cache-Invalidierung

Der Cache wird automatisch invalidiert, wenn:
- Die `modified_date` des Ordners sich ändert (via `Folder.modified_date`)
- `force_refresh=true` im Request gesetzt ist

### Cache-Verhalten

- **Cache Hit**: Wenn der Cache gültig ist, werden sofort gecachte Daten zurückgegeben
- **Cache Miss**: Neue Statistiken werden berechnet und automatisch gecacht
- **Cache-Speicherung**: In der `folder_stats` Tabelle in der Datenbank

## Performance-Überlegungen

### Analysis Limit

Der `analysis_limit` Parameter ermöglicht Performance-Optimierung:

```json
{
  "folder_path": "/large/folder",
  "analysis_limit": 1000
}
```

- **Datei-/Ordnerzählung**: Immer vollständig, kein Limit
- **Statistik-Analyse**: Begrenzt auf `analysis_limit` Bilder
- **Empfehlung**: 500-2000 für gutes Balance zwischen Performance und Genauigkeit

### Rekursive vs. Nicht-Rekursive Analyse

```json
{
  "folder_path": "/path",
  "recursive": false
}
```

- `recursive: true` - Analysiert alle Unterordner (langsamer, vollständig)
- `recursive: false` - Nur direkter Ordnerinhalt (schneller, begrenzt)

## Datenbank-Schema

### folder_stats Tabelle

```sql
CREATE TABLE folder_stats (
    folder_path TEXT PRIMARY KEY,
    modified_time TEXT,
    stats_json TEXT,
    computed_at TEXT
)
```

## Beispiel-Nutzung (Frontend)

```typescript
// Statistiken für einen Ordner abrufen
const response = await fetch('/infinite_image_browsing/folder_stats', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    folder_path: '/path/to/images',
    recursive: true,
    analysis_limit: 1000
  })
});

const stats = await response.json();

console.log(`Files: ${stats.file_count}`);
console.log(`Subfolders: ${stats.subfolder_count}`);
console.log(`Tagged images: ${stats.media_stats.tagged_images}`);
console.log(`Top tag: ${stats.top_tags[0]?.tag_name}`);
console.log(`Most used word: ${stats.prompt_analysis.top_words[0]?.word}`);
```

## Error Handling

Alle Endpoints können folgende Fehler zurückgeben:

- **400 Bad Request**: Ungültiger Ordnerpfad
- **403 Forbidden**: Zugriff auf Pfad nicht erlaubt (Access Control)
- **401 Unauthorized**: Fehlende oder ungültige Authentifizierung
- **500 Internal Server Error**: Fehler bei der Statistikberechnung

## Konfiguration

### Default Stopwords

Die Standard-Stoppwörter sind in `scripts/iib/folder_stats.py` definiert:

```python
DEFAULT_STOPWORDS = [
    "a", "an", "and", "are", "as", "at", "be", "by", ...
]
```

### Anpassung

Stoppwörter können über die API angepasst werden oder direkt in der `global_setting` Tabelle:

```sql
SELECT * FROM global_setting WHERE name = 'folder_stats_stopwords';
```

## Sicherheit

- Alle Endpoints erfordern Authentifizierung (`verify_secret`)
- Schreib-Endpoints erfordern zusätzlich `write_permission_required`
- Path-Validierung durch `check_path_trust()`
- Access Control wird respektiert

## Zukünftige Erweiterungen

Mögliche zukünftige Features:

- [ ] Zeitbasierte Trends (Statistiken über Zeit)
- [ ] Vergleichsansicht zwischen Ordnern
- [ ] Export als JSON/CSV
- [ ] Batch-Analyse mehrerer Ordner
- [ ] Background-Jobs für sehr große Ordner
- [ ] Zusätzliche Metadaten (Sampler, Steps, CFG Scale)
- [ ] Mehrsprachige Stoppwörter-Listen
