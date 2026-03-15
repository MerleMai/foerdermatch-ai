README.md (Finale Jury-Version)
FörderMatch AI
Überblick
FörderMatch AI ist ein KI-gestütztes System zur Analyse der Förderfähigkeit von Unternehmen gegenüber staatlichen Förderprogrammen.
Die Förderlandschaft in Deutschland ist komplex: Förderprogramme bestehen aus juristischen Richtlinien, Merkblättern und ergänzenden Dokumenten, deren Anforderungen häufig schwer nachvollziehbar sind.
FörderMatch AI löst dieses Problem durch eine strukturierte Wissensbasis für Förderprogramme, die mit Retrieval-Augmented Generation (RAG), semantischer Suche und einer regelbasierten Matching-Engine kombiniert wird.
Das System analysiert ein Unternehmensprofil und ermittelt:
welche Förderprogramme potenziell passen
warum sie passen oder nicht passen
welche Richtlinienstellen diese Bewertung begründen
Damit entsteht ein transparentes KI-Assistenzsystem für Fördermittelentscheidungen.
Kernfunktionen
1. Semantische Analyse von Förderprogrammen
Förderrichtlinien werden:
aus PDFs extrahiert
in Text-Chunks aufgeteilt
als Embeddings gespeichert
über eine Vektor-Datenbank semantisch durchsuchbar gemacht
So kann das System relevante Richtlinienstellen gezielt abrufen.
2. Regelbasierte Förderfähigkeitsprüfung
Eine Python Rule Engine prüft zentrale Kriterien wie:
Unternehmensgröße
Umsatzgrenzen
Projektstatus
Förderausschlüsse
Programmrestriktionen
Das Ergebnis ist ein transparenter Score pro Programm.
3. Evidenzbasierte Ergebnisdarstellung
Zu jedem Förderprogramm liefert das System:
eine strukturierte Programmzusammenfassung
eine Förderfähigkeitsbewertung
relevante Textstellen aus Richtlinien
direkte Quellenlinks zu Originaldokumenten
Alle Aussagen sind nachvollziehbar auf Dokumente zurückführbar.
4. Webbasierte Demo-Anwendung
Die Demo-Web-App ermöglicht:
Eingabe eines Unternehmensprofils
Ranking passender Förderprogramme
Detailanalyse einzelner Programme
Export eines Förderreports als PDF
Technologiestack
Frontend
HTML
CSS
Vanilla JavaScript
Backend
Python
FastAPI
Datenhaltung
SQLite (Programmdaten und Metadaten)
Chroma (Vektor-Datenbank)
KI-Komponenten
Embeddings für semantische Suche
Retrieval-Augmented Generation (RAG)
Regelbasierte Matching-Engine
Systemarchitektur
Die Architektur trennt drei Ebenen:
Dokumentverarbeitung
Semantisches Retrieval
Programm-Matching
PDF Dokumente
      ↓
Text-Extraktion
      ↓
Chunking
      ↓
Embeddings
      ↓
Chroma Vector DB
      ↓
Retrieval Service
      ↓
Rule Engine
      ↓
Scoring Service
      ↓
API
      ↓
Web Demo
Demo Ablauf
Unternehmensprofil wird eingegeben
Backend analysiert das Profil
Programme werden semantisch durchsucht
Matching-Regeln werden angewendet
Programme werden nach Score gerankt
Detailanalyse zeigt relevante Richtlinienstellen
Projektziel
Das Projekt zeigt, wie KI-basierte Dokumentanalyse und regelbasierte Entscheidungslogik kombiniert werden können, um komplexe juristische Richtlinien transparent und nutzbar zu machen.