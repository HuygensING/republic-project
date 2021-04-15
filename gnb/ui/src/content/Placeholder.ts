// Common:
export const MODAL_CLOSE = 'Sluit';
export const RESOLUTION = 'Resolutie';
export const PEOPLE = 'personen';
export const MENTIONED = 'genoemde';
export const ATTENDANT = 'aanwezige';
export const PLACE = 'plaats';
export const TERM = 'zoekterm';
export const FUNCTION = 'functie';
export const FUNCTION_CATEGORY = 'functiecategorie';

// Search:
export const WITH_ATTENDANTS = 'Zoek resoluties met de volgende aanwezen...';
export const WITH_MENTIONED = 'met genoemden...';
export const WITH_FULL_TEXT = 'met zoektermen...';
export const WITH_PLACES = 'met plaatsen...';
export const WITH_FUNCTIONS = 'met functies...';
export const WITH_FUNCTION_CATEGORIES = 'met functiecategorieën...';
export const CALENDAR_MOVE_WITH_RIGHT_ARROW = 'Of gebruik rechter pijltoets';
export const CALENDAR_MOVE_WITH_LEFT_ARROW = 'Of gebruik linker pijltoets';
export const HELP_BALLOON_MENTIONED = 'Zoek resoluties met de genoemde personen';
export const HELP_BALLOON_FUNCTIONS = 'Zoek resoluties met alle genoemde personen die deze functie bekleedden';
export const HELP_BALLOON_FUNCTION_CATEGORIES = 'Zoek resoluties met alle genoemde personen die een functie hadden binnen deze categorie';
export const HELP_BALLOON_PLACES = 'Zoek resoluties met de plaatsen';
export const HELP_BALLOON_PERIOD = 'Zoek resoluties binnen periode';
export const HELP_BALLOON_SEARCH_TERMS = 'Zoek resoluties m.b.v. een query string (zie help)';
export const HISTOGRAM = 'Histogram';
export const HEATMAP = 'Heatmap';

// Histograms:
export const RESOLUTIONS_TEXTS_TITLE = "Resoluties";
export const RESOLUTIONS_HISTOGRAM_TITLE = "# Resoluties";

// Errors:
export const ERR_ES_NOT_AVAILABLE = 'De Elasticsearch database is niet beschikbaar'
export const ERR_ES_AGGREGATE_PEOPLE = 'Mensen konden niet geaggregeerd worden';
export const ERR_ES_GET_MULTI_PEOPLE = 'Details van mensen konden niet opgehaald worden';
export const ERR_ES_AGGREGATE_RESOLUTIONS = 'Resoluties konden niet geaggregeerd worden';
export const ERR_ES_AGGREGATE_RESOLUTIONS_BY_PERSON = 'Resoluties konden niet geaggregeerd worden op basis van persoon';
export const ERR_ES_GET_MULTI_RESOLUTIONS = 'Resoluties konden niet opgehaald worden';
export const ERR_VIEW_TYPE_NOT_FOUND = 'Type is onbekend'
export const ERR_NOT_A_PERSON = 'Ingevoerde ViewType is geen persoon'
export const ERR_NOT_A_VIEW_TYPE_VALUE = 'Ingevoerde waarde bestaat niet voor ViewType'
export const ERR_NOT_A_PLOT_TYPE_VALUE = 'Ingevoerde waarde bestaat niet voor PlotType'
export const ERR_ES_AGGREGATE_LOCATION = 'Locaties konden niet geaggregeerd worden';
export const ERR_UNKNOWN_VIEW_TYPE_TO_STRING = 'View type onbekend';

// Warnings:
export const WARN_DATEPICKER_END_BEFORE_START = 'Een einddatum dient na de begindatum te liggen.';

// View composer:
export const ADD_NEW_VIEW_BALLOON = 'Plot het voorkomen van specifieke entiteiten binnen de gevonden resoluties';
export const ADD_NEW_VIEW_BTN = 'Voeg toe'
export const NEW_VIEW_MODAL_TITLE = 'Voeg nieuwe grafiek toe'
export const PICK_ATTENDANT = 'Kies aanwezige';
export const PICK_MENTIONED = 'Kies genoemde';
export const PICK_PLACE = 'Kies plaats';
export const PICK_FUNCTION = 'Kies functie';
export const PICK_FUNCTION_CATEGORY = 'Kies functiecategorie';
export const PICK_USER_VIEW = 'Kies type plot...'

// Version:
export const VERSION = 'Versie'

// Export:
export const EXPORT_BUTTON = 'Export';
export const EXPORT_DESCRIPTION = 'Hier kunt u huidige selectie downloaden als nodes en edges. Bij een grote dataset kan het genereren even duren. Voor meer informatie, zie help.';
export const EXPORT_DOWNLOAD_LINKS = 'Klik op de links om te downloaden:';
