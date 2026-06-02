# Week 2 Wed: TriviaQA rc.nocontext inspection
split: validation

## Load
total examples: 17944

## Field shape (first record)
question_id: tc_2
question:    'Who was the man behind The Chipmunks?'
answer:      'David Seville'
aliases (2): ['David Seville', 'david seville']

## First 20 examples
### [0] tc_2
Q: Who was the man behind The Chipmunks?
A: David Seville

### [1] tc_33
Q: Which Lloyd Webber musical premiered in the US on 10th December 1993?
A: Sunset Boulevard
accepted (5): ['Sunset Boulevard', 'Sunset Blvd', 'West Sunset Boulevard', 'Sunset Bulevard', 'Sunset Blvd.']

### [2] tc_40
Q: Who was the next British Prime Minister after Arthur Balfour?
A: Campbell-Bannerman
accepted (6): ['Campbell-Bannerman', 'Sir Henry Campbell-Bannerman', 'Campbell Bannerman', 'Sir Henry Campbell Bannerman', 'Henry Campbell Bannerman', 'Henry Campbell-Bannerman']

### [3] tc_49
Q: Who had a 70s No 1 hit with Kiss You All Over?
A: Exile
accepted (15): ['Exile', 'Internal exile', 'Exiles', 'Transported for life', 'Exile (politics and government)', 'Voluntary exile']...

### [4] tc_56
Q: What claimed the life of singer Kathleen Ferrier?
A: Cancer
accepted (46): ['Cancer', 'Cancer pathology', 'Deaths by cancer', 'Anti-cancer', 'Cancer (disease)', 'Cancerophobia']...

### [5] tc_69
Q: Rita Coolidge sang the title song for which Bond film?
A: Octopussy
accepted (19): ['Octopussy', 'Kamal kahn', 'List of Bond girls in Octopussy', 'Magda (James Bond)', 'List of James Bond allies in Octopussy', 'Vijay (James Bond)']...

### [6] tc_79
Q: What was the last US state to reintroduce alcohol after prohibition?
A: Utah
accepted (34): ['Utah', 'Utah (State)', 'Forty-Fifth State', 'Sports in Utah', 'Climate of Utah', 'Education in Utah']...

### [7] tc_106
Q: Which actress was voted Miss Greenwich Village in 1942?
A: Lauren Bacall
accepted (10): ['Lauren Bacall', 'Bacall', 'Lauren Becal', 'Lauren Becall', 'Betty J. Perske', 'Loren Bacall']...

### [8] tc_133
Q: What is the Japanese share index called?
A: Nikkei
accepted (3): ['Nikkei', 'Nikkei (disambiguation)', 'nikkei disambiguation']

### [9] tc_137
Q: What was the name of Michael Jackson's autobiography written in 1988?
A: Moonwalk
accepted (13): ['Moonwalk', 'Walk on the Moon', 'Moonwalk (disambiguation)', 'Lunar walks', 'Moon Walk', 'Moonwalking']...

### [10] tc_149
Q: In which decade did stereo records first go on sale?
A: 1930s
accepted (18): ['1930s', '1930’s', 'Thirties', '1930s literature', 'Nineteen-thirties', '1930–1939']...

### [11] tc_165
Q: In what year's Olympics were electric timing devices and a public-address system used for the first time?
A: In 1912, in Stockholm
accepted (2): ['In 1912, in Stockholm', 'in 1912 in stockholm']

### [12] tc_217
Q: Which volcano in Tanzania is the highest mountain in Africa?
A: Kilimanjaro
accepted (32): ['Kilimanjaro', 'Mawensi', 'Mt. Kilimanjaro', 'Kibo (volcano)', 'Mount killimanjaro', 'Highest mountain in Africa']...

### [13] tc_219
Q: The flag of Libya is a plain rectangle of which color?
A: Green
accepted (22): ['Green', 'Greenishly', 'Avacado (color)', 'Green (color)', 'Rgb(0, 255, 0)', 'Greenishness']...

### [14] tc_241
Q: Of which African country is Niamey the capital?
A: Niger
accepted (14): ['Niger', 'Niger Republic', 'Nigerois', 'Republic Of Niger', 'The Republic of Niger', 'Nigerien']...

### [15] tc_245
Q: Who was the director of the CIA from 1976-81?
A: George Bush
accepted (15): ['George Bush', 'Goerge Bush', 'George W. Bush (disambiguation)', 'GeorgeBush', 'George Bushe', 'Georg bush']...

### [16] tc_261
Q: Which musical featured the song The Street Where You Live?
A: My Fair Lady
accepted (18): ['My Fair Lady', 'My Fair Lady (2010 film)', 'Enry Iggins', "Why Can't the English%3F", 'My Fair Lady (upcoming film)', 'My Fair Lady (musical)']...

### [17] tc_267
Q: "Who was the target of the failed ""Bomb Plot"" of 1944?"
A: Hitler
accepted (62): ['Hitler', 'Hitlerian', 'Adolph Schicklgruber', 'HitlerAdolf', "Hitler's medical health", 'Adolf Hitle']...

### [18] tc_276
Q: Who had an 80s No 1 hit with Hold On To The Nights?
A: Richard Marx
accepted (2): ['Richard Marx', 'Richard Noel Marx']

### [19] tc_280
Q: Who directed the classic 30s western Stagecoach?
A: John Ford
accepted (22): ['John Ford', 'John Ford (1895-1973)', "Sean O'Feeney", 'John Ford (film director)', 'Ford, John (1895-1973)', 'Argosy Pictures']...

## Stats over the full split
question length chars: mean=79.6, median=70, min=18, max=854
answer length chars:   mean=10.4, median=9, min=1, max=282
accepted forms per Q:  mean=17.2, median=11, max=403
empty canonical answers: 0

## Notes for SE scoring
Use TriviaQAExample.all_acceptable() to match a model output against any accepted form of the answer. Farquhar et al. consider a generation correct if it contains any of these forms after light normalisation (lowercase, strip punctuation). We will replicate that in Week 3 when we build the SE correctness check.
