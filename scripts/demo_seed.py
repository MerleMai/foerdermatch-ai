from pathlib import Path

from backend.db.repo import (
    init_db,
    upsert_program,
    upsert_program_project_form,
    insert_document,
    upsert_program_rule,
)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "programs.db"
SCHEMA = ROOT / "backend" / "db" / "schema.sql"


def _insert_eew_shared_docs(program_id: str) -> None:
    base = ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS"

    shared_docs = [
        (
            "eew_merkblatt",
            base / "core" / "eew-merkblatt.pdf",
            "https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_merkblatt_2025.pdf?__blob=publicationFile&v=3",
            "20.05.2025",
        ),
        (
            "eew_foerderrichtlinie",
            base / "core" / "foerderrichtlinien.pdf",
            "https://www.wettbewerb-energieeffizienz.de/WENEFF/Redaktion/DE/PDF-Anlagen-FW/PDF-Anlagen-Transf/richtlinie-bmwk-zuschuss-kredit-25-01-2024.pdf?__blob=publicationFile&v=7",
            "25.01.2024",
        ),
        (
            "eew_glossar",
            base / "annex" / "glossar.pdf",
            "https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_glossar_2025.pdf?__blob=publicationFile&v=3",
            "20.05.2025",
        ),
        (
            "eew_zuschusstabellen",
            base / "annex" / "zuschusstabellen.pdf",
            "https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Evaluationen/Foerdermassnahmen/evaluation-bundesfoerderung-fuer-energie-und-ressourceneffizienz-in-der-wirtschaft.pdf?__blob=publicationFile&v=2",
            "31.10.2023",
        ),
        (
            "eew_faq_energieaudit_eneffg",
            base / "annex" / "faq-merkblatt.pdf",
            "https://www.bafa.de/SharedDocs/Downloads/DE/Energie/ea_merkblatt_faq.pdf?__blob=publicationFile&v=2",
            "07.07.2025",
        ),
    ]

    for doc_type, path, source_url, version_date in shared_docs:
        insert_document(
            DB,
            program_id=program_id,
            doc_type=doc_type,
            file_path=path,
            project_root=ROOT,
            source_url=source_url,
            version_date=version_date,
        )


def _insert_eew_program(
    *,
    program_id: str,
    name: str,
    name_official: str,
    name_display: str,
    focus_area: str,
    variant: str,
    notes: str,
    module_doc_type: str,
    module_file: Path,
    module_source_url: str,
    module_version_date: str,
    include_co2: bool = False,
    include_software_list: bool = False,
) -> None:
    upsert_program(
        DB,
        program_id=program_id,
        name=name,
        name_official=name_official,
        name_display=name_display,
        provider="BAFA / BMWE",
        funding_type="Zuschuss",
        focus_area=focus_area,
        geography="Deutschland",
        variant=variant,
        source_url="https://www.bafa.de/DE/Energie/Energieeffizienz/Energieeffizienz_und_Prozesswaerme/Uebersicht/uebersicht_node.html",
        status="active",
        notes=notes,
    )

    _insert_eew_shared_docs(program_id)

    insert_document(
        DB,
        program_id=program_id,
        doc_type=module_doc_type,
        file_path=module_file,
        project_root=ROOT,
        source_url=module_source_url,
        version_date=module_version_date,
    )

    if include_co2:
        insert_document(
            DB,
            program_id=program_id,
            doc_type="eew_infoblatt_co2_faktoren",
            file_path=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "annex" / "infoblatt-co2-faktoren.pdf",
            project_root=ROOT,
            source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_infoblatt_co2_faktoren_2025.pdf?__blob=publicationFile&v=4",
            version_date="20.05.2025",
        )

    if include_software_list:
        insert_document(
            DB,
            program_id=program_id,
            doc_type="eew_softwareliste",
            file_path=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "annex" / "energiemanagement-software.pdf",
            project_root=ROOT,
            source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_liste_foerderfaehige_software.pdf?__blob=publicationFile&v=4",
            version_date="27.02.2026",
        )


def main():
    init_db(DB, SCHEMA)

    # -------------------------
    # Program 511
    # -------------------------
    upsert_program(
        DB,
        program_id="KFW-ERP-DIGI-511",
        name="ERP-Förderkredit Digitalisierung",
        name_official="ERP-Förderkredit Digitalisierung",
        name_display="ERP-Förderkredit Digitalisierung (Standard)",
        provider="KfW",
        funding_type="Darlehen",
        focus_area="Digitalisierung & Innovation",
        geography="Deutschland",
        variant="511",
        source_url="https://www.kfw.de/inlandsfoerderung/Unternehmen/Innovation-und-Digitalisierung/Förderprodukte/ERP-Förderkredit-Digitalisierung-(511-512)/",
        status="active",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-511",
        doc_type="merkblatt_511",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-511" / "merkblatt_511.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Förderprogramme-(Inlandsförderung)/PDF-Dokumente/6000005251_M_511.pdf",
        version_date="23.10.2025",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-511",
        doc_type="kmu_definition",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-511" / "kmu_definition.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Förderprogramme-(Inlandsförderung)/PDF-Dokumente/6000000196_M_F_KMU-Definition.pdf",
        version_date="10/2025",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-511",
        doc_type="investitionskredite_bestimmungen",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-511" / "investitionskredite_bestimmungen.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Förderprogramme-(Inlandsförderung)/PDF-Dokumente/6000002388_AB_Investitionskredite_EKN.pdf",
        version_date="07/2021",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-511",
        doc_type="ausschlussliste_kfw",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-511" / "ausschlussliste_kfw.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Konzernthemen/Nachhaltigkeit/Ausschlussliste.pdf",
        version_date="14.12.2023",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-511",
        doc_type="allgemeines_merkblatt_beihilfen",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-511" / "allgemeines_merkblatt_beihilfen.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Förderprogramme-(Inlandsförderung)/PDF-Dokumente/6000000065_M_Beihilfen.pdf",
        version_date="10.12.2025",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-511",
        doc_type="allgemeine_bedingungen_erp",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-511" / "allgemeine_bedingungen_erp.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Förderprogramme-(Inlandsförderung)/PDF-Dokumente/6000000194_AB_ERP.pdf",
        version_date="03/2009",
    )

    # -------------------------
    # Program 512
    # -------------------------
    upsert_program(
        DB,
        program_id="KFW-ERP-DIGI-512",
        name="ERP-Förderkredit Digitalisierung (mit Haftungsfreistellung)",
        name_official="ERP-Förderkredit Digitalisierung",
        name_display="ERP-Förderkredit Digitalisierung (mit Haftungsfreistellung)",
        provider="KfW",
        funding_type="Darlehen",
        focus_area="Digitalisierung & Innovation",
        geography="Deutschland",
        variant="512",
        source_url="https://www.kfw.de/inlandsfoerderung/Unternehmen/Innovation-und-Digitalisierung/Förderprodukte/ERP-Förderkredit-Digitalisierung-(511-512)/",
        status="active",
        notes="Eigenständige Variante (512) für Inhalte wie Haftungsfreistellung / Risikoübernahme.",
    )

    insert_document(
        DB,
        program_id="KFW-ERP-DIGI-512",
        doc_type="merkblatt_512",
        file_path=ROOT / "data" / "documents" / "KFW-ERP-DIGI-512" / "merkblatt_512.pdf",
        project_root=ROOT,
        source_url="https://www.kfw.de/PDF/Download-Center/Förderprogramme-(Inlandsförderung)/PDF-Dokumente/6000005250_M_512.pdf",
        version_date="23.10.2025",
    )

    # -------------------------
    # Program ZIM
    # -------------------------
    upsert_program(
        DB,
        program_id="ZIM",
        name="Zentrales Innovationsprogramm Mittelstand (ZIM)",
        name_official="Zentrales Innovationsprogramm Mittelstand (ZIM)",
        name_display="Zentrales Innovationsprogramm Mittelstand (ZIM)",
        provider="BMWK/BMWE",
        funding_type="Zuschuss",
        focus_area="Forschung & Entwicklung / Innovation",
        geography="Deutschland (bundesweit)",
        variant=None,
        source_url="https://www.zim.de/ZIM/Navigation/DE/Home/home.html",
        status="active",
        notes="Programmkern; Projektform wird über program_project_forms abgebildet (ENUM).",
    )

    for form in [
        "fue_single",
        "fue_coop",
        "innovation_network",
        "feasibility_study",
        "market_launch",
    ]:
        upsert_program_project_form(DB, program_id="ZIM", project_form=form)

    insert_document(
        DB,
        program_id="ZIM",
        doc_type="richtlinie_zim",
        file_path=ROOT / "data" / "documents" / "ZIM" / "richtlinie-zim-2025.pdf",
        project_root=ROOT,
        source_url="https://www.zim.de/ZIM/Redaktion/DE/Downloads/Richtlinien/richtlinie-zim-2025.pdf?__blob=publicationFile&v=7",
        version_date="28.11.2024",
    )

    insert_document(
        DB,
        program_id="ZIM",
        doc_type="de_minimis_infoblatt",
        file_path=ROOT / "data" / "documents" / "ZIM" / "de-minimis-infoblatt.pdf",
        project_root=ROOT,
        source_url="https://www.zim.de/ZIM/Redaktion/DE/Downloads/Sonstiges/de-minimis-infoblatt.pdf?__blob=publicationFile&v=2",
        version_date="06/2024",
    )

    # -------------------------
    # Program KMU-innovativ
    # -------------------------
    upsert_program(
        DB,
        program_id="KMU-INNOVATIV",
        name="KMU-innovativ: Zukunft der Wertschöpfung",
        name_official="KMU-innovativ: Zukunft der Wertschöpfung",
        name_display="KMU-innovativ: Zukunft der Wertschöpfung",
        provider="BMBF",
        funding_type="Zuschuss",
        focus_area="Forschung & Entwicklung / Zukunft der Wertschöpfung",
        geography="Deutschland",
        variant=None,
        source_url="https://www.kmu-innovativ.de/",
        status="active",
        notes="Themenoffene BMBF-Förderung für risikoreiche vorwettbewerbliche FuE-Vorhaben von KMU und mittelständischen Unternehmen.",
    )

    for form in ["fue_single", "fue_coop"]:
        upsert_program_project_form(DB, program_id="KMU-INNOVATIV", project_form=form)

    insert_document(
        DB,
        program_id="KMU-INNOVATIV",
        doc_type="richtlinie_kmu_innovativ",
        file_path=ROOT / "data" / "documents" / "KMU" / "richtlinie_kmu_innovativ.pdf",
        project_root=ROOT,
        source_url="https://www.zukunft-der-wertschoepfung.de/wp-content/uploads/2023/07/BK_KMU-innovativ_BAnz-AT-26.07.2023-B3-1.pdf",
        version_date="28.06.2023",
    )

    insert_document(
        DB,
        program_id="KMU-INNOVATIV",
        doc_type="richtlinie_update_kmu_innovativ",
        file_path=ROOT / "data" / "documents" / "KMU" / "richtlinie_update_kmu_innovativ.pdf",
        project_root=ROOT,
        source_url="https://www.zukunft-der-wertschoepfung.de/wp-content/uploads/2025/01/Aenderung_BK_KMU-i_BAnz-AT-23.01.2025-B5.pdf",
        version_date="08.01.2025",
    )

    insert_document(
        DB,
        program_id="KMU-INNOVATIV",
        doc_type="informationsbroschuere_kmu_innovativ",
        file_path=ROOT / "data" / "documents" / "KMU" / "informationsbroschuere_kmu_innovativ.pdf",
        project_root=ROOT,
        source_url="https://www.bmbf.de/SharedDocs/Publikationen/DE/1/30295_KMU-innovativ_Vorfahrt_fuer_Spitzenforschung.pdf?__blob=publicationFile&v=7",
        version_date="04/2024",
    )

    insert_document(
        DB,
        program_id="KMU-INNOVATIV",
        doc_type="auswahlrunde_kmu_innovativ",
        file_path=ROOT / "data" / "documents" / "KMU" / "auswahlrunde_kmu_innovativ.pdf",
        project_root=ROOT,
        source_url="https://www.foerderinfo.bund.de/SharedDocs/Publikationen/de/bmbf/5/31710_KMU_innovativ_9_und_10_Auswahlrunde.pdf?__blob=publicationFile&v=7",
        version_date="01/2022",
    )

    insert_document(
        DB,
        program_id="KMU-INNOVATIV",
        doc_type="leitfaden_kmu_innovativ",
        file_path=ROOT / "data" / "documents" / "KMU" / "leitfaden_kmu_innovativ.pdf",
        project_root=ROOT,
        source_url="https://www.elektronikforschung.de/dateien/publikationen/leitfaden-kmu-innovativ_2016.pdf",
        version_date="12/2017",
    )

    # -------------------------
    # EEW BAFA family (M1-M4)
    # -------------------------
    _insert_eew_program(
        program_id="EEW-BAFA-M1",
        name="EEW BAFA Zuschuss Modul 1 Querschnittstechnologien",
        name_official="Bundesförderung für Energie- und Ressourceneffizienz in der Wirtschaft – Modul 1",
        name_display="EEW – Modul 1 (Querschnittstechnologien)",
        focus_area="Energieeffizienz / Querschnittstechnologien",
        variant="M1",
        notes="Nur BAFA-Zuschussvariante; Modul 1 richtet sich ausschließlich an KMU und fokussiert Austauschinvestitionen in hocheffiziente Querschnittstechnologien.",
        module_doc_type="eew_modul1_merkblatt",
        module_file=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "module1" / "eew_modul1_merkblatt.pdf",
        module_source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_modul1_qst_merkblatt_2024.pdf?__blob=publicationFile&v=8",
        module_version_date="20.05.2025",
    )

    _insert_eew_program(
        program_id="EEW-BAFA-M2",
        name="EEW BAFA Zuschuss Modul 2 Prozesswärme aus Erneuerbaren Energien",
        name_official="Bundesförderung für Energie- und Ressourceneffizienz in der Wirtschaft – Modul 2",
        name_display="EEW – Modul 2 (Prozesswärme aus erneuerbaren Energien)",
        focus_area="Prozesswärme / Erneuerbare Energien",
        variant="M2",
        notes="Nur BAFA-Zuschussvariante; Modul 2 fördert Wärmeerzeuger für Prozesswärme aus erneuerbaren Energien.",
        module_doc_type="eew_modul2_merkblatt",
        module_file=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "module2" / "eew_modul2_merkblatt.pdf",
        module_source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_modul2_pw_merkblatt_2025.pdf?__blob=publicationFile&v=3",
        module_version_date="20.05.2025",
        include_co2=True,
    )

    _insert_eew_program(
        program_id="EEW-BAFA-M3",
        name="EEW BAFA Zuschuss Modul 3 MSR, Sensorik und Energiemanagement-Software",
        name_official="Bundesförderung für Energie- und Ressourceneffizienz in der Wirtschaft – Modul 3",
        name_display="EEW – Modul 3 (MSR, Sensorik und Energiemanagement-Software)",
        focus_area="Energiemanagement / MSR / Sensorik",
        variant="M3",
        notes="Nur BAFA-Zuschussvariante; Modul 3 setzt auf gelistete Energiemanagementsoftware sowie mess-, steuer- und regelungstechnische Komponenten.",
        module_doc_type="eew_modul3_merkblatt",
        module_file=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "module3" / "eew_modul3_merkblatt.pdf",
        module_source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_modul3_ems_merkblatt_2025.pdf?__blob=publicationFile&v=5",
        module_version_date="20.05.2025",
        include_software_list=True,
    )

    _insert_eew_program(
        program_id="EEW-BAFA-M4-BASIS",
        name="EEW BAFA Zuschuss Modul 4 Basisförderung",
        name_official="Bundesförderung für Energie- und Ressourceneffizienz in der Wirtschaft – Modul 4",
        name_display="EEW – Modul 4 Basis",
        focus_area="Energie- und Ressourceneffizienz / Anlagenaustausch",
        variant="M4-BASIS",
        notes="Nur BAFA-Zuschussvariante; Modul 4 Basisförderung ist auf KMU begrenzt und verlangt insbesondere 15 % Endenergieeinsparung beim Austausch definierter Anlagenkategorien.",
        module_doc_type="eew_modul4_merkblatt",
        module_file=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "module4" / "eew_modul4_merkblatt.pdf",
        module_source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_modul_4_oap_merkblatt_2025.pdf?__blob=publicationFile&v=5",
        module_version_date="20.05.2025",
        include_co2=True,
    )

    _insert_eew_program(
        program_id="EEW-BAFA-M4-PREMIUM",
        name="EEW BAFA Zuschuss Modul 4 Premiumförderung",
        name_official="Bundesförderung für Energie- und Ressourceneffizienz in der Wirtschaft – Modul 4",
        name_display="EEW – Modul 4 Premium",
        focus_area="Energie- und Ressourceneffizienz / technologieoffene Prozessoptimierung",
        variant="M4-PREMIUM",
        notes="Nur BAFA-Zuschussvariante; Modul 4 Premiumförderung ist technologieoffen, verlangt ein Einsparkonzept und ein Mindest-THG-Einsparpotenzial.",
        module_doc_type="eew_modul4_merkblatt",
        module_file=ROOT / "data" / "documents" / "EEW-BAFA-ZUSCHUSS" / "module4" / "eew_modul4_merkblatt.pdf",
        module_source_url="https://www.bafa.de/SharedDocs/Downloads/DE/Energie/eew_modul_4_oap_merkblatt_2025.pdf?__blob=publicationFile&v=5",
        module_version_date="20.05.2025",
        include_co2=True,
    )

    # -------------------------
    # Program GRW-MV-GEWERBE
    # -------------------------
    upsert_program(
        DB,
        program_id="GRW-MV-GEWERBE",
        name="GRW Mecklenburg-Vorpommern Gewerbliche Wirtschaft",
        name_official="Gemeinschaftsaufgabe Verbesserung der regionalen Wirtschaftsstruktur",
        name_display="GRW – Gewerbliche Wirtschaft Mecklenburg-Vorpommern",
        provider="Bund / Land Mecklenburg-Vorpommern",
        funding_type="Zuschuss",
        focus_area="Regionalförderung / gewerbliche Investitionen",
        geography="Mecklenburg-Vorpommern",
        variant="MV-GEWERBE",
        source_url="https://www.lfi-mv.de/foerderfinder/gemeinschaftsaufgabe-verbesserung-der-regionalen-wirtschaftsstruktur-gewerbliche-wirtschaft/",
        status="active",
        notes="Landesspezifische Umsetzung der GRW für die gewerbliche Wirtschaft in Mecklenburg-Vorpommern auf Basis des Koordinierungsrahmens ab 01.01.2026.",
    )

    insert_document(
        DB,
        program_id="GRW-MV-GEWERBE",
        doc_type="grw_koordinierungsrahmen_2026",
        file_path=ROOT / "data" / "documents" / "GRW-MV-GEWERBE" / "core" / "grw_koordinierungsrahmen_2026.pdf",
        project_root=ROOT,
        source_url="https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Downloads/G/koordinierungsrahmen-der-grw-ab-januar-2026.pdf?__blob=publicationFile&v=10",
        version_date="01.01.2026",
    )

    insert_document(
        DB,
        program_id="GRW-MV-GEWERBE",
        doc_type="grw_foerdergebiete_2022_2027",
        file_path=ROOT / "data" / "documents" / "GRW-MV-GEWERBE" / "core" / "grw_foerdergebiete_2022_2027.pdf",
        project_root=ROOT,
        source_url="https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Downloads/grw-fordergebiete-2022-2027.pdf?__blob=publicationFile&v=3",
        version_date="11.01.2022",
    )

    insert_document(
        DB,
        program_id="GRW-MV-GEWERBE",
        doc_type="grw_merkblatt_mv",
        file_path=ROOT / "data" / "documents" / "GRW-MV-GEWERBE" / "core" / "grw_merkblatt_mv.pdf",
        project_root=ROOT,
        source_url="https://www.lfi-mv.de/export/sites/lfi/.galleries/grw-gewerbliche-wirtschaft/merkblatt.pdf",
        version_date="05.07.2024",
    )

    insert_document(
        DB,
        program_id="GRW-MV-GEWERBE",
        doc_type="grw_merkblatt_tiefenpruefung_mv",
        file_path=ROOT / "data" / "documents" / "GRW-MV-GEWERBE" / "annex" / "grw_merkblatt_tiefenpruefung_mv.pdf",
        project_root=ROOT,
        source_url="https://www.lfi-mv.de/export/sites/lfi/.galleries/grw-gewerbliche-wirtschaft/merkblatt-tiefenpruefung.pdf",
        version_date="01.01.2022",
    )

    insert_document(
        DB,
        program_id="GRW-MV-GEWERBE",
        doc_type="grw_ergaenzende_angaben_mv",
        file_path=ROOT / "data" / "documents" / "GRW-MV-GEWERBE" / "annex" / "grw_ergaenzende_angaben_mv.pdf",
        project_root=ROOT,
        source_url="https://www.lfi-mv.de/export/sites/lfi/.galleries/grw-gewerbliche-wirtschaft/ergaenzende-angaben-zum-formantrag.pdf",
        version_date="28.03.2025",
    )

    insert_document(
        DB,
        program_id="GRW-MV-GEWERBE",
        doc_type="grw_antragsformular_mv",
        file_path=ROOT / "data" / "documents" / "GRW-MV-GEWERBE" / "forms" / "grw_antragsformular_mv.pdf",
        project_root=ROOT,
        source_url="https://www.lfi-mv.de/export/sites/lfi/.galleries/grw-sonderprogramme/antrag-grw-gewerbe-01.01.2022.pdf",
        version_date="01.01.2022",
    )

    # -------------------------
    # Program GO-INNO
    # -------------------------
    upsert_program(
        DB,
        program_id="GO-INNO",
        name="BMWK/INNO Innovationsgutscheine go-inno",
        name_official="go-inno",
        name_display="go-inno – Innovationsgutscheine",
        provider="BMWE / EURONORM",
        funding_type="Zuschuss",
        focus_area="Innovationsberatung / Produkt- und Verfahrensinnovation",
        geography="Deutschland",
        variant=None,
        source_url="https://www.innovation-beratung-foerderung.de/INNO/Navigation/DE/go-inno/go-inno.html",
        status="active",
        notes="Bundesprogramm für externe Innovationsberatungen kleiner Technologieunternehmen und Handwerksbetriebe vor allem zu Produktinnovationen und technischen Verfahrensinnovationen.",
    )

    insert_document(
        DB,
        program_id="GO-INNO",
        doc_type="go_inno_richtlinie",
        file_path=ROOT / "data" / "documents" / "GO-INNO" / "go_inno_richtlinie.pdf",
        project_root=ROOT,
        source_url="https://www.innovation-beratung-foerderung.de/INNO/Redaktion/DE/Downloads/Unterlagen_go-inno/go-inno_Richtlinie_26112020.pdf?__blob=publicationFile&v=2",
        version_date="26.11.2020",
    )

    insert_document(
        DB,
        program_id="GO-INNO",
        doc_type="go_inno_merkblatt",
        file_path=ROOT / "data" / "documents" / "GO-INNO" / "go_inno_merkblatt.pdf",
        project_root=ROOT,
        source_url="https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Publikationen/Technologie/bmwk-innovationsgutscheine-go-inno-flyer.pdf?__blob=publicationFile&v=5",
        version_date="März 2021",
    )

    insert_document(
        DB,
        program_id="GO-INNO",
        doc_type="go_inno_orientierungshilfe",
        file_path=ROOT / "data" / "documents" / "GO-INNO" / "go_inno_orientierungshilfe.pdf",
        project_root=ROOT,
        source_url="https://www.innovation-beratung-foerderung.de/INNO/Redaktion/DE/Downloads/Unterlagen_go-inno/go-inno_orientierungshilfe_foerderfaehigkeit.pdf?__blob=publicationFile&v=1",
        version_date="31.03.2022",
    )


    # --- Rules for KFW-ERP-DIGI-511 ---
    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-511",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Projekt hat noch nicht begonnen (Antrag vor Vorhabensbeginn möglich).",
        reason_fail="Projekt ist bereits gestartet (Antrag muss vor Vorhabensbeginn gestellt werden).",
        missing_field="project.start_status",
    )

    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-511",
        rule_id="RULE_IS_KMU",
        rule_type="boolean",
        path="company.is_kmu",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Unternehmen ist KMU (grundsätzlich förderfähig im KMU-Kontext).",
        reason_fail="Unternehmen ist kein KMU (kann Einschränkungen haben; prüfen).",
        missing_field="company.is_kmu",
    )

    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-511",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Sitz in Deutschland.",
        reason_fail="Kein Sitz in Deutschland.",
        missing_field="company.country",
    )

    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-511",
        rule_id="RULE_DE_MINIMIS_OK_OR_UNKNOWN",
        rule_type="enum",
        path="constraints.de_minimis_status",
        op="in",
        value=["ok", "unknown"],
        weight=10,
        hard_fail=False,
        reason_ok="De-minimis Status ok/unklar (muss im Einzelfall bestätigt werden).",
        reason_fail="De-minimis Status problematisch (kann Ausschluss/Limit bedeuten).",
        missing_field="constraints.de_minimis_status",
    )

    # --- Rules for KFW-ERP-DIGI-512 ---
    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-512",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Projekt hat noch nicht begonnen.",
        reason_fail="Projekt ist bereits gestartet.",
        missing_field="project.start_status",
    )

    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-512",
        rule_id="RULE_IS_KMU",
        rule_type="boolean",
        path="company.is_kmu",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Unternehmen ist KMU.",
        reason_fail="Unternehmen ist kein KMU.",
        missing_field="company.is_kmu",
    )

    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-512",
        rule_id="RULE_WANTS_GUARANTEE",
        rule_type="boolean",
        path="financing.needs_guarantee",
        op="eq",
        value=True,
        weight=10,
        hard_fail=False,
        reason_ok="Haftungsfreistellung / Risikoübernahme ist relevant (512 passt).",
        reason_fail="Haftungsfreistellung nicht relevant (512 evtl. weniger passend).",
        missing_field="financing.needs_guarantee",
    )

    upsert_program_rule(
        DB,
        program_id="KFW-ERP-DIGI-512",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Sitz in Deutschland.",
        reason_fail="Kein Sitz in Deutschland.",
        missing_field="company.country",
    )

    # --- Rules for ZIM ---
    upsert_program_rule(
        DB,
        program_id="ZIM",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Projekt hat noch nicht begonnen (Antrag muss vor Start eingereicht werden).",
        reason_fail="Projekt ist bereits gestartet (ZIM-Förderung in der Regel ausgeschlossen).",
        missing_field="project.start_status",
    )

    upsert_program_rule(
        DB,
        program_id="ZIM",
        rule_id="RULE_IS_KMU",
        rule_type="boolean",
        path="company.is_kmu",
        op="eq",
        value=True,
        weight=15,
        hard_fail=False,
        reason_ok="KMU passt zur Programmausrichtung.",
        reason_fail="Kein KMU (kann je nach Programmteil relevant sein; prüfen).",
        missing_field="company.is_kmu",
    )

    upsert_program_rule(
        DB,
        program_id="ZIM",
        rule_id="RULE_IS_R_AND_D",
        rule_type="boolean",
        path="project.is_r_and_d",
        op="eq",
        value=True,
        weight=15,
        hard_fail=False,
        reason_ok="Vorhaben ist F&E/Innovation (ZIM-Fokus).",
        reason_fail="Vorhaben ist nicht primär F&E/Innovation.",
        missing_field="project.is_r_and_d",
    )

    upsert_program_rule(
        DB,
        program_id="ZIM",
        rule_id="RULE_TECH_RISK",
        rule_type="boolean",
        path="project.has_technical_risk",
        op="eq",
        value=True,
        weight=10,
        hard_fail=False,
        reason_ok="Technisches Risiko / Innovationshöhe plausibel.",
        reason_fail="Technisches Risiko/Innovationshöhe unklar oder gering.",
        missing_field="project.has_technical_risk",
    )

    # --- Rules for KMU-innovativ ---
    upsert_program_rule(
        DB,
        program_id="KMU-INNOVATIV",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Vorhaben hat noch nicht begonnen; Antragstellung vor Projektstart ist plausibel.",
        reason_fail="Vorhaben ist bereits gestartet; Förderung setzt Anreizeffekt bzw. Antrag vor Projektbeginn voraus.",
        missing_field="project.start_status",
    )

    upsert_program_rule(
        DB,
        program_id="KMU-INNOVATIV",
        rule_id="RULE_IS_KMU_OR_MIDCAP",
        rule_type="enum",
        path="company.size_class",
        op="in",
        value=["kmu", "midcap_1000"],
        weight=20,
        hard_fail=False,
        reason_ok="Unternehmen fällt in den förderfähigen Kreis aus KMU bzw. mittelständischen Unternehmen bis 1.000 Beschäftigte.",
        reason_fail="Unternehmen liegt voraussichtlich außerhalb der adressierten Zielgruppe.",
        missing_field="company.size_class",
    )

    upsert_program_rule(
        DB,
        program_id="KMU-INNOVATIV",
        rule_id="RULE_HAS_GERMAN_SITE",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Unternehmen/Betriebsstätte in Deutschland passt zur Richtlinie.",
        reason_fail="Kein klarer Deutschlandbezug; Förderfähigkeit prüfen.",
        missing_field="company.country",
    )

    upsert_program_rule(
        DB,
        program_id="KMU-INNOVATIV",
        rule_id="RULE_IS_R_AND_D",
        rule_type="boolean",
        path="project.is_r_and_d",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Vorhaben ist FuE-getrieben und passt zum Programmfokus.",
        reason_fail="Vorhaben ist nicht klar als FuE-/Transformationsvorhaben erkennbar.",
        missing_field="project.is_r_and_d",
    )

    upsert_program_rule(
        DB,
        program_id="KMU-INNOVATIV",
        rule_id="RULE_HAS_TECHNICAL_OR_PROCESS_INNOVATION",
        rule_type="boolean",
        path="project.has_technical_risk",
        op="eq",
        value=True,
        weight=15,
        hard_fail=False,
        reason_ok="Innovationshöhe bzw. technisches/umsetzungsbezogenes Risiko ist plausibel.",
        reason_fail="Innovationshöhe oder Risiko des Vorhabens ist unklar bzw. zu gering.",
        missing_field="project.has_technical_risk",
    )

    upsert_program_rule(
        DB,
        program_id="KMU-INNOVATIV",
        rule_id="RULE_FOCUS_VALUE_CREATION",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "produktion",
            "dienstleistung",
            "arbeit",
            "industrie_4_0",
            "robotik",
            "wertschoepfung",
            "prozessinnovation",
            "geschaeftsmodell",
        ],
        weight=15,
        hard_fail=False,
        reason_ok="Thema passt zur Zukunft der Wertschöpfung.",
        reason_fail="Thematischer Bezug zur Zukunft der Wertschöpfung ist schwach oder unklar.",
        missing_field="project.category",
    )

    # --- Rules for EEW-BAFA-M1 ---
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M1",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Vorhaben hat noch nicht begonnen; Antrag vor Maßnahmenbeginn ist plausibel.",
        reason_fail="Vorhaben ist bereits gestartet; EEW setzt Antragstellung vor Maßnahmenbeginn voraus.",
        missing_field="project.start_status",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M1",
        rule_id="RULE_IS_KMU",
        rule_type="boolean",
        path="company.is_kmu",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Unternehmen ist KMU; Modul 1 ist auf KMU ausgerichtet.",
        reason_fail="Unternehmen ist kein KMU; Modul 1 passt voraussichtlich nicht.",
        missing_field="company.is_kmu",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M1",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Betriebsstätte/Niederlassung in Deutschland ist plausibel.",
        reason_fail="Deutschlandbezug unklar oder nicht gegeben.",
        missing_field="company.country",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M1",
        rule_id="RULE_EFFICIENCY_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "energieeffizienz",
            "querschnittstechnologie",
            "motor",
            "pumpe",
            "ventilator",
            "druckluft",
            "abwaerme",
            "waermedaemmung",
        ],
        weight=20,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zu Querschnittstechnologien.",
        reason_fail="Thematischer Bezug zu Modul 1 ist schwach oder unklar.",
        missing_field="project.category",
    )

    # --- Rules for EEW-BAFA-M2 ---
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M2",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Vorhaben hat noch nicht begonnen.",
        reason_fail="Vorhaben ist bereits gestartet.",
        missing_field="project.start_status",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M2",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Deutschlandbezug ist plausibel.",
        reason_fail="Deutschlandbezug unklar oder nicht gegeben.",
        missing_field="company.country",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M2",
        rule_id="RULE_PROCESS_HEAT_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "prozesswaerme",
            "erneuerbare_energie",
            "solarkollektor",
            "waermepumpe",
            "geothermie",
            "biomasse",
            "kwk",
        ],
        weight=25,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zu Prozesswärme aus erneuerbaren Energien.",
        reason_fail="Thematischer Bezug zu Modul 2 ist schwach oder unklar.",
        missing_field="project.category",
    )

    # --- Rules for EEW-BAFA-M3 ---
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M3",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Vorhaben hat noch nicht begonnen.",
        reason_fail="Vorhaben ist bereits gestartet.",
        missing_field="project.start_status",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M3",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Deutschlandbezug ist plausibel.",
        reason_fail="Deutschlandbezug unklar oder nicht gegeben.",
        missing_field="company.country",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M3",
        rule_id="RULE_ENERGY_MANAGEMENT_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "energiemanagement",
            "sensorik",
            "msr",
            "mess_steuer_regelung",
            "software",
            "iso50001",
            "umweltmanagement",
        ],
        weight=25,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zu Modul 3.",
        reason_fail="Thematischer Bezug zu Modul 3 ist schwach oder unklar.",
        missing_field="project.category",
    )

    # --- Rules for EEW-BAFA-M4-BASIS ---
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-BASIS",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Vorhaben hat noch nicht begonnen.",
        reason_fail="Vorhaben ist bereits gestartet.",
        missing_field="project.start_status",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-BASIS",
        rule_id="RULE_IS_KMU",
        rule_type="boolean",
        path="company.is_kmu",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Unternehmen ist KMU; Basisförderung ist auf KMU ausgerichtet.",
        reason_fail="Unternehmen ist kein KMU; Basisförderung passt voraussichtlich nicht.",
        missing_field="company.is_kmu",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-BASIS",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Deutschlandbezug ist plausibel.",
        reason_fail="Deutschlandbezug unklar oder nicht gegeben.",
        missing_field="company.country",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-BASIS",
        rule_id="RULE_PROCESS_OPTIMIZATION_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "energieeffizienz",
            "prozessoptimierung",
            "abwaerme",
            "elektrifizierung",
            "ressourceneffizienz",
            "anlagenaustausch",
        ],
        weight=25,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zur Basisförderung von Modul 4.",
        reason_fail="Thematischer Bezug zur Basisförderung ist schwach oder unklar.",
        missing_field="project.category",
    )

    # --- Rules for EEW-BAFA-M4-PREMIUM ---
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-PREMIUM",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Vorhaben hat noch nicht begonnen.",
        reason_fail="Vorhaben ist bereits gestartet.",
        missing_field="project.start_status",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-PREMIUM",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Deutschlandbezug ist plausibel.",
        reason_fail="Deutschlandbezug unklar oder nicht gegeben.",
        missing_field="company.country",
    )
    upsert_program_rule(
        DB,
        program_id="EEW-BAFA-M4-PREMIUM",
        rule_id="RULE_PROCESS_OPTIMIZATION_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "energieeffizienz",
            "prozessoptimierung",
            "abwaerme",
            "elektrifizierung",
            "ressourceneffizienz",
            "dekarbonisierung",
            "prozesswaerme",
        ],
        weight=25,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zur Premiumförderung von Modul 4.",
        reason_fail="Thematischer Bezug zur Premiumförderung ist schwach oder unklar.",
        missing_field="project.category",
    )

    # --- Rules for GRW-MV-GEWERBE ---
    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Mit dem Investitionsvorhaben wurde noch nicht begonnen; Antrag vor Vorhabensbeginn ist plausibel.",
        reason_fail="Mit dem Investitionsvorhaben wurde bereits begonnen; GRW setzt Antragstellung vor Beginn voraus.",
        missing_field="project.start_status",
    )

    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Deutschlandbezug ist plausibel.",
        reason_fail="Deutschlandbezug unklar oder nicht gegeben.",
        missing_field="company.country",
    )

    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_IN_FUNDING_AREA",
        rule_type="boolean",
        path="company.in_grw_funding_area",
        op="eq",
        value=True,
        weight=25,
        hard_fail=True,
        reason_ok="Betriebsstätte liegt im GRW-Fördergebiet.",
        reason_fail="Betriebsstätte liegt nicht im GRW-Fördergebiet.",
        missing_field="company.in_grw_funding_area",
    )

    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_HAS_PRIMARY_EFFECT",
        rule_type="boolean",
        path="project.has_primary_effect",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Primäreffekt des Vorhabens ist plausibel.",
        reason_fail="Primäreffekt ist unklar oder nicht gegeben.",
        missing_field="project.has_primary_effect",
    )

    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_INVESTMENT_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "errichtungsinvestition",
            "erweiterungsinvestition",
            "diversifizierung",
            "grundlegende_aenderung",
            "regionalinvestition",
            "gewerbliche_wirtschaft",
            "tourismus",
            "betriebsstaette",
        ],
        weight=15,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zu förderfähigen GRW-Investitionen.",
        reason_fail="Thematischer Bezug zu einer förderfähigen GRW-Investition ist schwach oder unklar.",
        missing_field="project.category",
    )

    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_MEETS_10_OR_50",
        rule_type="boolean",
        path="project.meets_10_percent_jobs_or_50_percent_depreciation",
        op="eq",
        value=True,
        weight=15,
        hard_fail=False,
        reason_ok="Zusätzliche landesspezifische Fördervoraussetzung (10 % Arbeitsplätze oder 50 % Abschreibungen) ist plausibel erfüllt.",
        reason_fail="Die zusätzliche landesspezifische Fördervoraussetzung ist unklar oder nicht erfüllt.",
        missing_field="project.meets_10_percent_jobs_or_50_percent_depreciation",
    )

    upsert_program_rule(
        DB,
        program_id="GRW-MV-GEWERBE",
        rule_id="RULE_NOT_EXCLUDED_SECTOR",
        rule_type="boolean",
        path="constraints.is_excluded_sector",
        op="eq",
        value=False,
        weight=20,
        hard_fail=True,
        reason_ok="Kein Hinweis auf eine ausgeschlossene Branche.",
        reason_fail="Vorhaben liegt in einer ausgeschlossenen Branche bzw. einem nicht förderfähigen Wirtschaftszweig.",
        missing_field="constraints.is_excluded_sector",
    )

    # --- Rules for GO-INNO ---
    upsert_program_rule(
        DB,
        program_id="GO-INNO",
        rule_id="RULE_NOT_STARTED",
        rule_type="enum",
        path="project.start_status",
        op="in",
        value=["planned", "not_started"],
        weight=20,
        hard_fail=True,
        reason_ok="Beratungsvorhaben hat noch nicht begonnen; go-inno setzt Beratung vor Maßnahmenbeginn voraus.",
        reason_fail="Beratungs- oder Innovationsvorhaben ist bereits gestartet; go-inno passt dann voraussichtlich nicht mehr.",
        missing_field="project.start_status",
    )

    upsert_program_rule(
        DB,
        program_id="GO-INNO",
        rule_id="RULE_IS_KMU",
        rule_type="boolean",
        path="company.is_kmu",
        op="eq",
        value=True,
        weight=20,
        hard_fail=False,
        reason_ok="Unternehmen ist KMU; go-inno richtet sich an kleine Unternehmen.",
        reason_fail="Unternehmen ist kein KMU; go-inno passt voraussichtlich nicht.",
        missing_field="company.is_kmu",
    )

    upsert_program_rule(
        DB,
        program_id="GO-INNO",
        rule_id="RULE_IN_GERMANY",
        rule_type="enum",
        path="company.country",
        op="eq",
        value="DE",
        weight=10,
        hard_fail=False,
        reason_ok="Unternehmenssitz oder Betriebsstätte in Deutschland ist plausibel.",
        reason_fail="Deutschlandbezug ist unklar oder nicht gegeben.",
        missing_field="company.country",
    )

    upsert_program_rule(
        DB,
        program_id="GO-INNO",
        rule_id="RULE_INNOVATION_COUNSELING_CATEGORY",
        rule_type="enum",
        path="project.category",
        op="in",
        value=[
            "innovationsberatung",
            "innovation",
            "produktinnovation",
            "verfahrensinnovation",
            "technische_verfahrensinnovation",
            "machbarkeit",
            "beratung",
            "digitalisierung",
        ],
        weight=25,
        hard_fail=False,
        reason_ok="Vorhaben passt thematisch zu go-inno Innovationsberatungen.",
        reason_fail="Thematischer Bezug zu go-inno ist schwach oder unklar.",
        missing_field="project.category",
    )


if __name__ == "__main__":
    main()