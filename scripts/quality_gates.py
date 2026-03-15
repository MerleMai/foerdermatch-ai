from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]

INGEST_DEFAULTS = {
    "KFW-ERP-DIGI-511": {"max_words": 350, "overlap_words": 80},
    "KFW-ERP-DIGI-512": {"max_words": 220, "overlap_words": 60},
    "ZIM": {"max_words": 260, "overlap_words": 70},
    "KMU-INNOVATIV": {"max_words": 260, "overlap_words": 70},

    # EEW
    "EEW-BAFA-M1": {"max_words": 260, "overlap_words": 70},
    "EEW-BAFA-M2": {"max_words": 260, "overlap_words": 70},
    "EEW-BAFA-M3": {"max_words": 220, "overlap_words": 60},
    "EEW-BAFA-M4-BASIS": {"max_words": 260, "overlap_words": 70},
    "EEW-BAFA-M4-PREMIUM": {"max_words": 260, "overlap_words": 70},

    # GRW
    "GRW-MV-GEWERBE": {"max_words": 260, "overlap_words": 70},

    # GO-INNO
    "GO-INNO": {"max_words": 220, "overlap_words": 60},
}


@dataclass(frozen=True)
class Gate:
    program_id: str
    query: str
    expect_doc_type: str
    max_dist: float
    expect_page_contains: Optional[str] = None
    must_contain: Optional[str] = None
    must_contain_any: Optional[str] = None


GATES: list[Gate] = [
    # --- KFW 511 ---
    Gate(
        program_id="KFW-ERP-DIGI-511",
        query="De-minimis",
        expect_doc_type="allgemeines_merkblatt_beihilfen",
        max_dist=0.75,
        must_contain="de-minimis",
    ),
    Gate(
        program_id="KFW-ERP-DIGI-511",
        query="Ihren Antrag stellen Sie bei einem Finanzierungspartner Ihrer Wahl vor Beginn des Vorhabens",
        expect_doc_type="merkblatt_511",
        max_dist=0.70,
        expect_page_contains="S. 7",
        must_contain="antrag,vor beginn des vorhabens,finanzierungspartner",
    ),

    # --- KFW 512 ---
    Gate(
        program_id="KFW-ERP-DIGI-512",
        query="Haftungsfreistellung 50",
        expect_doc_type="merkblatt_512",
        max_dist=0.72,
        must_contain="haftungsfreistellung,50",
    ),

    # --- ZIM ---
    Gate(
        program_id="ZIM",
        query="Unternehmen in Schwierigkeiten Artikel 2 Nummer 18",
        expect_doc_type="richtlinie_zim",
        max_dist=0.78,
        must_contain="unternehmen in schwierigkeiten,nummer 18",
        must_contain_any="artikel 2,art. 2,art 2,artikel2,nr. 18,nr 18,651/2014,vo (eu) 651/2014,agvo,gruppenfreistellungsverordnung",
    ),
    Gate(
        program_id="ZIM",
        query="Förderung ist ausgeschlossen wenn vor dem bestätigten Antragseingang",
        expect_doc_type="richtlinie_zim",
        max_dist=0.80,
        must_contain="förderung ist ausgeschlossen,antragseingang",
    ),
    Gate(
        program_id="ZIM",
        query="Allgemeine-De-minimis-Beihilfen 300.000",
        expect_doc_type="de_minimis_infoblatt",
        max_dist=0.80,
        must_contain="de-minimis,300.000",
    ),

    # --- KMU-INNOVATIV ---
    Gate(
        program_id="KMU-INNOVATIV",
        query="Einreichungsstichtage 15. April und 15. Oktober",
        expect_doc_type="richtlinie_kmu_innovativ",
        max_dist=0.82,
        must_contain="15. april,15. oktober",
        must_contain_any="einreichungsstichtage,stichtage,projektskizzen",
    ),
    Gate(
        program_id="KMU-INNOVATIV",
        query="mittelständische Unternehmen maximal 1 000 Beschäftigte und 100 Millionen Euro Umsatz",
        expect_doc_type="richtlinie_kmu_innovativ",
        max_dist=0.82,
        must_contain="1 000,beschäftigte,100 millionen euro",
        must_contain_any="mittelständische unternehmen,jahresumsatz,antragsberechtigt",
    ),
    Gate(
        program_id="KMU-INNOVATIV",
        query="Grundsätzlich können diese bis zu 50 % anteilig finanziert werden",
        expect_doc_type="richtlinie_kmu_innovativ",
        max_dist=0.84,
        must_contain="50",
        must_contain_any="anteilig finanziert,beihilfeintensität,zuwendungen,kmu",
    ),
    Gate(
        program_id="KMU-INNOVATIV",
        query="Ab dem Stichtag 15. April 2026 entfallen die ESF Plus-Kofinanzierung",
        expect_doc_type="richtlinie_update_kmu_innovativ",
        max_dist=0.82,
        must_contain="15. april 2026,entfallen",
        must_contain_any="esf plus-kofinanzierung,esf-plus-kofinanzierung,esf",
    ),
    Gate(
        program_id="KMU-INNOVATIV",
        query="zweistufiges Antragsverfahren Projektskizze Förderantrag",
        expect_doc_type="richtlinie_kmu_innovativ",
        max_dist=0.84,
        must_contain="zweistufig",
        must_contain_any="projektskizze,förderantrag,antragsverfahren",
    ),
    Gate(
        program_id="KMU-INNOVATIV",
        query="risikoreiche vorwettbewerbliche Forschungs Entwicklungs und Transformationsvorhaben",
        expect_doc_type="richtlinie_kmu_innovativ",
        max_dist=0.86,
        must_contain="risikoreiche,vorwettbewerbliche",
        must_contain_any="forschungs,entwicklungs,transformationsvorhaben,wertschöpfung",
    ),

    # --- EEW-BAFA-M1 ---
    Gate(
        program_id="EEW-BAFA-M1",
        query="Wärmeübertrager Bestandsanlagen Abwärme innerbetrieblich genutzt",
        expect_doc_type="eew_modul1_merkblatt",
        max_dist=0.86,
        must_contain="wärmeübertrager,abwärme",
        must_contain_any="bestandsanlagen,innerbetrieblich genutzt,erschließung",
    ),
    Gate(
        program_id="EEW-BAFA-M1",
        query="Bestandsanlagen müssen zum Zeitpunkt der Antragstellung seit mindestens 5 Jahren im Einsatz sein",
        expect_doc_type="eew_modul1_merkblatt",
        max_dist=0.86,
        must_contain="5 jahren,antragstellung",
        must_contain_any="bestandsanlagen,eigentum,voll funktionstüchtig,voll funktionstuechtig",
    ),

    # --- EEW-BAFA-M2 ---
    Gate(
        program_id="EEW-BAFA-M2",
        query="Mehr als 50 Prozent der mit der geförderten Anlage bereitgestellten Energie werden als Prozesswärme genutzt",
        expect_doc_type="eew_modul2_merkblatt",
        max_dist=0.84,
        must_contain="50,prozesswärme",
        must_contain_any="mehr als 50,prozesswärmebereitstellung,überwiegend der prozesswärmebereitstellung",
    ),
    Gate(
        program_id="EEW-BAFA-M2",
        query="Nicht förderfähig sind Elektrodenkessel und Power to Heat Anlagen",
        expect_doc_type="eew_modul2_merkblatt",
        max_dist=0.86,
        must_contain_any="elektrodenkessel,power-to-heat,power to heat,nicht förderfähig,nicht foerderfaehig",
    ),

    # --- EEW-BAFA-M3 ---
    Gate(
        program_id="EEW-BAFA-M3",
        query="zu fördernde MSR Hardware in eine gelistete Energiemanagementsoftware eingebunden 3 Jahre gespeichert",
        expect_doc_type="eew_modul3_merkblatt",
        max_dist=0.82,
        must_contain="gelistete,energiemanagementsoftware,3 jahre",
        must_contain_any="eingebunden,energiekennzahlen,gespeichert",
    ),
    Gate(
        program_id="EEW-BAFA-M3",
        query="Systemkonzept Datenerfassungsplan Wirkplan",
        expect_doc_type="eew_modul3_merkblatt",
        max_dist=0.84,
        must_contain="systemkonzept,datenerfassungsplan,wirkplan",
    ),
    Gate(
        program_id="EEW-BAFA-M3",
        query="econ solutions GmbH econ 4",
        expect_doc_type="eew_softwareliste",
        max_dist=0.95,
        must_contain_any="econ 4,econ solutions gmbh,econ solutions",
    ),

    # --- EEW-BAFA-M4-BASIS ---
    Gate(
        program_id="EEW-BAFA-M4-BASIS",
        query="Der jährliche Bedarf an Endenergie muss in Folge des Anlagen Komponentenaustauschs um mindestens 15 Prozent reduziert werden",
        expect_doc_type="eew_modul4_merkblatt",
        max_dist=0.84,
        must_contain="15,endenergie",
        must_contain_any="anlagen,komponentenaustauschs,basisförderung,basisfoerderung",
    ),
    Gate(
        program_id="EEW-BAFA-M4-BASIS",
        query="Anlagen die einer Kategorie der Basisförderung zuzuordnen sind können in der Regel nicht über die Premiumförderung gefördert werden",
        expect_doc_type="eew_modul4_merkblatt",
        max_dist=0.86,
        must_contain="basisförderung",
        must_contain_any="nicht über die premiumförderung,premiumförderung,zugeordnet",
    ),

    # --- EEW-BAFA-M4-PREMIUM ---
    Gate(
        program_id="EEW-BAFA-M4-PREMIUM",
        query="Die Nachweisführung erfolgt über ein sogenanntes Einsparkonzept",
        expect_doc_type="eew_modul4_merkblatt",
        max_dist=0.84,
        must_contain="einsparkonzept",
        must_contain_any="nachweisführung,premiumförderung,premiumfoerderung",
    ),
    Gate(
        program_id="EEW-BAFA-M4-PREMIUM",
        query="Das THG Einsparpotenzial des Vorhabens muss einen Mindestwert erreichen",
        expect_doc_type="eew_modul4_merkblatt",
        max_dist=0.86,
        must_contain="thg-einsparpotenzial",
        must_contain_any="thg-einsparpotenzial,mindestwert,einsparkonzept",
    ),

    # --- GRW-MV-GEWERBE ---
    Gate(
        program_id="GRW-MV-GEWERBE",
        query="Unternehmen der gewerblichen Wirtschaft einschließlich Tourismusgewerbe",
        expect_doc_type="grw_merkblatt_mv",
        max_dist=0.86,
        must_contain_any="gewerblichen wirtschaft,tourismusgewerbe,tourismusgewerbes,gefördert werden,gefoerdert werden",
    ),
    Gate(
        program_id="GRW-MV-GEWERBE",
        query="Mit dem Investitionsvorhaben darf nicht vor Antragstellung begonnen worden sein",
        expect_doc_type="grw_koordinierungsrahmen_2026",
        max_dist=0.88,
        must_contain_any="nicht begonnen,vor antragstellung,vorhabensbeginn,begonnen worden sein",
    ),
    Gate(
        program_id="GRW-MV-GEWERBE",
        query="Fördergebiete C Gebiet D Gebiet Regionalfördergebietskarte",
        expect_doc_type="grw_foerdergebiete_2022_2027",
        max_dist=0.95,
        must_contain_any="fördergebiet,foerdergebiet,c-gebiet,d-gebiet,regionalfördergebietskarte,regionalfoerdergebietskarte",
    ),
    Gate(
        program_id="GRW-MV-GEWERBE",
        query="Primäreffekt erfüllt überwiegend Güter hergestellt oder Leistungen erbracht regelmäßig überregional",
        expect_doc_type="grw_merkblatt_mv",
        max_dist=0.88,
        must_contain_any="primäreffekt,primaereffekt,überregional,ueberregional,güter hergestellt,gueter hergestellt,leistungen erbracht",
    ),
    Gate(
        program_id="GRW-MV-GEWERBE",
        query="ergänzende Angaben Diversifizierung der Produktion Investitionsplan",
        expect_doc_type="grw_ergaenzende_angaben_mv",
        max_dist=0.92,
        must_contain_any="ergänzende angaben,ergaenzende angaben,diversifizierung,investitionsplan,produktion",
    ),

    # --- GO-INNO ---
    Gate(
        program_id="GO-INNO",
        query="Produktinnovationen technische Verfahrensinnovationen förderfähig",
        expect_doc_type="go_inno_orientierungshilfe",
        max_dist=0.90,
        must_contain_any="produktinnovationen,verfahrensinnovationen,technische verfahrensinnovationen,förderfähig,foerderfaehig",
    ),
    Gate(
        program_id="GO-INNO",
        query="Unternehmen mit weniger als 100 Beschäftigten und höchstens 20 Millionen Euro Jahresumsatz",
        expect_doc_type="go_inno_merkblatt",
        max_dist=0.92,
        must_contain_any="100 beschäftigten,100 beschaeftigten,20 millionen euro,jahresumsatz,bilanzsumme",
    ),
    Gate(
        program_id="GO-INNO",
        query="autorisierte Beratungsunternehmen Beratungsvertrag",
        expect_doc_type="go_inno_richtlinie",
        max_dist=0.92,
        must_contain_any="autorisierte beratungsunternehmen,beratungsvertrag,beratungsunternehmen",
    ),
    Gate(
        program_id="GO-INNO",
        query="bereits vor Beginn des Innovationsvorhabens durchgeführte oder begonnene Beratungsleistungen ausgeschlossen",
        expect_doc_type="go_inno_richtlinie",
        max_dist=0.92,
        must_contain_any="bereits vor beginn,begonnene beratungsleistungen,ausgeschlossen,nicht förderbar,nicht foerderbar",
    ),
]


def run(cmd: list[str]) -> int:
    print("\n$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-id", choices=sorted(INGEST_DEFAULTS.keys()))
    parser.add_argument("--skip-ingest", action="store_true", help="Only run gates (assumes already ingested).")
    parser.add_argument("--k", type=int, default=5, help="Top-k for query_demo.")
    args = parser.parse_args()

    program_ids = [args.program_id] if args.program_id else list(INGEST_DEFAULTS.keys())

    if not args.skip_ingest:
        for pid in program_ids:
            cfg = INGEST_DEFAULTS[pid]
            rc = run(
                [
                    sys.executable,
                    "-m",
                    "scripts.ingest_program",
                    "--program-id",
                    pid,
                    "--max-words",
                    str(cfg["max_words"]),
                    "--overlap-words",
                    str(cfg["overlap_words"]),
                ]
            )
            if rc != 0:
                print(f"[FAIL] ingest failed for {pid}")
                return rc

    for g in GATES:
        if g.program_id not in program_ids:
            continue

        cmd = [
            sys.executable,
            "-m",
            "scripts.query_demo",
            "--program-id",
            g.program_id,
            "--q",
            g.query,
            "--k",
            str(args.k),
            "--gate",
            "--expect-doc-type",
            g.expect_doc_type,
            "--max-dist",
            str(g.max_dist),
        ]

        if g.expect_page_contains:
            cmd += ["--expect-page-contains", g.expect_page_contains]

        if g.must_contain:
            cmd += ["--must-contain", g.must_contain]

        if g.must_contain_any:
            cmd += ["--must-contain-any", g.must_contain_any]

        rc = run(cmd)
        if rc != 0:
            print(f"[FAIL] gate failed for {g.program_id} q={g.query!r}")
            return rc

    print("\n[OK] Quality gates executed (reproducible + hardened + OR-robust).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())