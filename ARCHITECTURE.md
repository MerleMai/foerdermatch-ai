ARCHITECTURE.md (Final)
Technische Architektur – FörderMatch AI
Systemübersicht
Das System besteht aus fünf Hauptkomponenten:
Dokumentpipeline
Vektorbasierte Suche
Regelbasierte Matching-Engine
Backend API
Web-Frontend
Diese Komponenten arbeiten zusammen, um Förderprogramme analysierbar und vergleichbar zu machen.
Dokumentpipeline
Förderrichtlinien liegen meist als PDF vor und enthalten komplexe juristische Texte.
Die Pipeline verarbeitet diese Dokumente in mehreren Schritten.
Schritte
PDF-Parsing
Text-Extraktion
Chunking
Embedding-Generierung
Speicherung in der Vektor-Datenbank
Die Chunks enthalten zusätzlich Metadaten:
Program ID
Dokumenttyp
Quelle
Seitenreferenz
Datenhaltung
SQLite
Speichert strukturierte Programmdaten:
Programme
Dokumentmetadaten
Programmkonfigurationen
SQLite dient als strukturierte Wissensbasis.
Chroma
Speichert:
Text-Chunks
Embeddings
Metadaten
Chroma ermöglicht semantische Suche über Richtlinieninhalte.
Retrieval Service
Der Retrieval Service führt eine semantische Suche durch:
Query-Embedding erzeugen
Ähnliche Dokument-Chunks suchen
Ergebnisse nach Programm filtern
Top-Chunks für Analyse zurückgeben
Diese Chunks bilden die evidenzbasierte Grundlage für das Matching.
Rule Engine
Die Rule Engine prüft strukturelle Förderbedingungen wie:
Unternehmensgröße
Umsatzgrenzen
Projektstatus
Branchenrestriktionen
Förderausschlüsse
Die Regeln sind bewusst deterministisch implementiert, um eine nachvollziehbare Bewertung zu gewährleisten.
Scoring System
Für jedes Förderprogramm wird ein Score berechnet.
Der Score kombiniert:
Regelbasierte Kriterien
semantische Relevanz der Dokumentstellen
Das Ergebnis ist ein Ranking der Förderprogramme.
Backend API
Die Backend-API basiert auf FastAPI.
Zentrale Endpunkte:
/health
Systemstatus prüfen.
/evaluate
Unternehmensprofil analysieren und Programme bewerten.
/rank
Ranking passender Programme abrufen.
/detail
Detailanalyse eines Förderprogramms.
Frontend
Die Web-App dient als Demonstrationsoberfläche.
Funktionen:
Eingabe eines Unternehmensprofils
Anzeige des Förderprogrammrankings
Detailanalyse einzelner Programme
Anzeige der Quellenstellen
Export eines Förderreports als PDF
Skalierbarkeit
Die Architektur ist modular aufgebaut.
Mögliche Erweiterungen:
Integration weiterer Förderprogramme
Erweiterte Regelmodelle
LLM-gestützte Dokumentanalyse
Multi-User Web-Application