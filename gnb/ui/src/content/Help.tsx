import React from 'react';
import Modal from "../common/Modal";

export default function Help() {

  const [isOpen, setIsOpen] = React.useState(false);

  function openModal(e: any) {
    setIsOpen(true);
  }

  return (
    <>
      <button className="btn btn-outline-info search-help-btn mt-3 mr-3" type="button" onClick={openModal}>
        <i className="fas fa-question-circle" /> Help
      </button>
      <Modal isOpen={isOpen} handleClose={() => setIsOpen(false)} title="GNB">
        <HelpHtml />
      </Modal>
    </>
  );
}

function HelpHtml() {
  return <>
    <strong>Zoeken in de resoluties van de Staten-Generaal.</strong>
    <p className="pt-3">GNB staat voor <i>Governance, Netwerken en Besluitvorming</i> in de Staten-Generaal. GNB probeert inzicht te geven in het sociale netwerk rondom de Staten-Generaal, in de periode van 1626 tot en met 1630. Wie was wanneer aanwezig? Welke plaatsen speelden een rol? Waren er onderwerpen die in een bepaalde samenstelling van de Staten-Generaal aan de orde kwamen?</p>
    <h2>Zoeken, visualiseren, exporteren</h2>
    <p>GNB bestaat uit drie stappen:</p>
    <p>Ten eerste kunt u zoeken op aanwezigen, genoemden, locaties en zoektermen. In het resoluties-histogram worden de gevonden resoluties getoond. Als u niet zoekt, worden alle resoluties getoond.</p>
    <p>Hierna kunt u grafieken toevoegen voor specifieke personen, locaties en zoektermen. Deze grafieken tonen het voorkomen aan binnen de selectie van gevonden resoluties.</p>
    <p>Wanneer u dieper wilt duiken in de gevonden resoluties en het bijbehorende sociale netwerk van aanwezigen en genoemden, dan kunt u de huidige selectie exporteren:</p>
    <ul>
      <li>Als <strong>json</strong>: de gevonden <a href="https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-simple-query-string-query.html" target="_blank" rel="noreferrer">elasticsearch</a>-documenten</li>
      <li>Als <strong>csv</strong>: een lijst met nodes en edges geschikt voor <a href="https://gephi.org/users/quick-start/" target="_blank" rel="noreferrer">gephi</a></li>
    </ul>
    <p>(Aan deze functionaliteit wordt nog gewerkt.)</p>
    <h2>Zoeken</h2>
    <h3>Aanwezigen en genoemden</h3>
    <p>Aanwezigen zijn mensen genoemd in de presentielijst van een zittingsdag. Genoemden zijn de mensen getagd in de resoluties zelf.</p>
    <h3>Full-text zoeken in resoluties</h3>
    <p>Zoek 'full-text' in de resoluties met behulp van <a href="https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html" target="_blank" rel="noreferrer" ><code>query string</code></a> zoektaal van elasticsearch. Hieronder twee voorbeelden:</p>
    <ul>
      <li>Zoek op resoluties die 'brief' en niet 'regiment' bevatten: <pre>brief -regiment</pre></li>
      <li>Zoek zowel op 'RvS' als 'Raad van State': <pre>(RvS | "Raad van State")</pre></li>
    </ul>
    <h3>Zoeken in de tijd</h3>
    <p>Gebruik de linker en rechter pijltjestoets of de kalender-<i>widget</i> om door de tijd (1626-1630) te lopen. De periodelengte kunt u veranderd door de einddatum in te stellen.</p>
    <h3>Functies en functiecategorieën</h3>
    <p>Personen kunnen functies bekleden. Deze functies zijn vervolgens weer ingedeeld in een aantal categorieën. Op deze functies en categorieën kunt u zoeken.</p>
    <p className="font-italic">NB: Wanneer u zoekt op personen met functies en categorieën, dan wordt er enkel gezocht binnen de genoemden, niet de aanwezigen. Daarnaast wordt er geen rekening gehouden met de periode waarbinnen iemand de functie bekleedde: een persoon zal dus ook buiten deze functieperiode om worden gevonden op de functie.</p>
    <h2>Exporteren</h2>
    <p>U kunt de huidige selectie exporteren, op het moment enkel in de vorm van twee csv-bestanden: de nodes en edges van de huidige selectie, geschikt voor bijvoorbeeld Gephi. Naast de standaard kolommen is aan het nodes.csv een Type-kolom toegevoegd met de waarde <code>searched</code> of <code>plotted</code> bij de gezochte dan wel geplotte entities.</p>
  </>
}
