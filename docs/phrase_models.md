# REPUBLIC Phrase models and fuzzy search

One of the core information extraction strategies in the project is the
use of phrase models in combination with fuzzy string search and
matching. The language use in the resolutions is extremely repetitive,
with many standard formulas to signal important aspects of the text,
like the start of meetings, the president and attendants lists and the
start of individual resolutions.

These standard formulas were used at the time as an information access
point. By clearly signaling different structural elements with layout
conventions and standard phrasings, finding back relevant information
was made easier than if variable language was used.

## Fuzzy search

A typical problem in extracting information from digitised historical
corpora is that they contain historical language that differs in
spelling and vocabulary from current language. Moreover, in the case of
Dutch, variation in spelling was common, such that the same word was
spelled in multiple ways, sometimes even within the same page. Beyond
the differences and variation in spelling, OCR and HTR techniques rarely
generate 100% correct output, so the recognised text also contains
character errors.

## Phrase models

The idea behind phrase models is that they represent standardised
phrases that identify textual elements with a fixed meaning. Similar to
classic information extraction techniques that rely on templates with
fixed sequences of words, phrase models contain lists of _template_
phrases with a category label that indicate what the phrase represents.

Below is an example phrase model in JSON format:

```json
[
  {
    'phrase': 'Nihil actum est',
    'label': 'no_meeting',
    'max_offset': 4
  },
  {
    'phrase': 'PRAESIDE',
    'variants': [
      'P R A E S I D E'
    ],
    'label': 'presiding',
    'max_offset': 4
  }
]
```

This model contains two phrases. The first, `Nihil actum est`, is the
standard phrase to indicate that there was no meeting on that day. The
`label` property is used to category any matches found. The `max_offset`  
property is an optional property that can be used to indicate that a  
OCR/HTR string is considered a fuzzy or approximate match only if it  
 occurs at most 4 characters from the start of a text element (e.g. a  
 line or a paragraph).

The second phrase, `PRAESIDE`, is the standard prefix to indicate that
the name mentioned after it is the president of the meeting that day.
Here, the `variants` property is added to also find strings that are  
 not similar to the original phrase, but to a common variant. In this  
 case, the original phrase consists of all uppercase characters, which  
 OCR processes tend to recognise as containing whitespace characters  
 between the uppercase characters. The string distance between the  
 original phrase and those separated by whitespaces is large, so this  
 variant can be included to match these cases as well.

### Phrases and external knowledge for finding meeting openings

Each meeting starts with a standard phrase for identifying the date of
the meeting, followed by information on who the president was and who
else attended the meeting. After that, a standard paragraph followed
stating that the resolutions of the previous session were summarised.

Each meeting date phrase is printed in centre-aligned text, and consists  
of:

- the name of the week day in Latin (e.g. Lunae, Martis, Mercurii)
- the day and the month
- the year (on a separate line

An example is:

`Lunae den 2. Januarii. 1725`

Because we can compute what day of the week of each day was, we can
determine what date phrases to expect. We can also compute in advance
what the default holidays and other rest days were. For instance,
Christmas day is always on the 25th of December, (and in the Dutch  
Republic, second Christmas day is the 26th of December and also a rest
day). Easter falls on different dates each year, but is determined by a
fixed formula.

Using this knowledge, we can construct all the meeting date formulas
for a given year and use those to find the starts of meetings.

On days when there was no meeting (holidays, Sundays and from 1754 also
most Saturdays), the same meeting date structured is used, followed by
the statement

`Nihil actum est`

To indicate that there was no activity that day. Using our knowledge of  
what days were rest days, we also know which meeting dates should be  
followed by `Nihil actum est`.

