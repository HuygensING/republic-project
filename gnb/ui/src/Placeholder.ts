// Common:
export const MODAL_CLOSE = 'Sluit';

// Search:
export const WITH_ATTENDANTS = 'met aanwezigen...';
export const WITH_MENTIONED = 'met genoemden...';
export const WITH_FULL_TEXT = 'met zoektermen...';

// SearchHelp:
export const HELP_TITLE = 'Zoekhulp';
export const HELP_PEOPLE_TITLE = 'Aanwezigen en genoemden';
export const HELP_PEOPLE_BODY = 'Aanwezigen zijn mensen genoemd in de presentielijst van een zittingsdag. Genoemden zijn de mensen getagd in de resoluties zelf.';
export const HELP_FULL_TEXT_TITLE = 'Zoeken in resoluties';
export const HELP_FULL_TEXT_BODY = 'Zoek \'full-text\' in de resoluties met behulp van <a href="https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html" target="_blank" rel="noreferrer" ><code>simple_query_string</code></a> zoektaal van elasticsearch';
export const HELP_START_END_TITLE = 'Zoeken in de tijd';
export const HELP_START_END_BODY = 'Gebruik de linker en rechter pijltjestoets of de kalender-\'widget\' om door de tijd (1626-1630) te lopen. De lengte van de periode kan veranderd worden met de einddatum.';

export const RESOLUTIONS_TITLE = "Resolutions";

// Errors:
export const ERR_ES_NOT_AVAILABLE = 'De Elasticsearch database is niet beschikbaar'
export const ERR_ES_AGGREGATE_PEOPLE = 'Mensen konden niet geaggregeerd worden';
export const ERR_ES_GET_MULTI_PEOPLE = 'Details van mensen konden niet opgehaald worden';
export const ERR_ES_AGGREGATE_RESOLUTIONS = 'Resoluties konden niet geaggregeerd worden';
export const ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON = 'Resoluties konden niet geaggregeerd worden op basis van persoon';
export const ERR_ES_GET_MULTI_RESOLUTIONS = 'Resoluties konden niet opgehaald worden';

// Warnings:
export const WARN_DATEPICKER_END_BEFORE_START = 'Een einddatum dient na de begindatum te liggen.';

// View compoer:
export const ADD_NEW_VIEW_BTN = '+ Voeg toe'
export const NEW_VIEW_MODAL_TITLE = 'Voeg nieuwe grafiek toe'
export const PLOT_ATTENDANT = 'Plot aanwezige';
