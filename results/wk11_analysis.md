> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** These numbers use the
> discredited selection rule where clean AUROC = 1.000 by construction (external review B1).
> Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py -> results/fair_recompute_report.md.

# Week 11: qualitative failure-mode analysis

## Campaign triviaqa_se_false_alarm
questions: 15, feasible paraphrase found: 15, successes: 12
entropy move (intended direction): mean +0.907, median +0.940, max +2.303
objective calls per question: mean 25

### 10 strongest successes
- tc_2849 move +2.303 (SE 0.00 -> 2.30)
    orig: What has a central vein called a midrib?
    adv:  What is characterized by having a central vein known as a midrib?
- qz_2426 move +1.834 (SE 0.00 -> 1.83)
    orig: In which decade were ZIP codes introduced in the USA?
    adv:  What year was the United States' ZIP code system first implemented?
- tc_280 move +1.498 (SE 0.00 -> 1.50)
    orig: Who directed the classic 30s western Stagecoach?
    adv:  Who is the director behind the iconic 1930s western film Stagecoach?
- tc_954 move +1.418 (SE 0.00 -> 1.42)
    orig: On what date in 1969 did Neil Armstrong first set foot on the Moon?
    adv:  What date in 1969 was significant for being the first time a human, Neil Armstrong, stepped onto the Moon's surface?
- qz_1354 move +1.418 (SE 0.00 -> 1.42)
    orig: Who is the Vice-President for George W Bush?
    adv:  What was the name of the vice president who served under George W. Bush?
- tc_2701 move +1.168 (SE 0.00 -> 1.17)
    orig: Whose birthday is celebrated by a public holiday on the third Monday in January in the USA?
    adv:  What public holiday in the United States is observed on the third Monday in January to commemorate a notable figure's birthday?
- tc_2836 move +0.940 (SE 0.00 -> 0.94)
    orig: What name is given to the study of animal behavior?
    adv:  What is the field of study known as the scientific investigation of animal behavior called?
- qb_203 move +0.940 (SE 0.00 -> 0.94)
    orig: Cristina Fernandez de Kirchner became President of which South American country in December 2007?
    adv:  What country in South America did Cristina Fernandez de Kirchner become the president in December 2007?
- qz_2324 move +0.802 (SE 0.00 -> 0.80)
    orig: Who was the author of 'The Old Curiosity Shop'?
    adv:  Who wrote the novel 'The Old Curiosity Shop'?
- qb_34 move +0.639 (SE 0.00 -> 0.64)
    orig: Which airline is nicknamed ‘The Flying Kangaroo’?
    adv:  What is the airline commonly known as 'The Flying Kangaroo'?

### 10 clearest failures
- tc_2701 move +1.168 feasible=True
    orig: Whose birthday is celebrated by a public holiday on the third Monday in January in the USA?
    adv:  What public holiday in the United States is observed on the third Monday in January to commemorate a notable figure's birthday?
- tc_2836 move +0.940 feasible=True
    orig: What name is given to the study of animal behavior?
    adv:  What is the field of study known as the scientific investigation of animal behavior called?
- qb_203 move +0.940 feasible=True
    orig: Cristina Fernandez de Kirchner became President of which South American country in December 2007?
    adv:  What country in South America did Cristina Fernandez de Kirchner become the president in December 2007?
- qz_2324 move +0.802 feasible=True
    orig: Who was the author of 'The Old Curiosity Shop'?
    adv:  Who wrote the novel 'The Old Curiosity Shop'?
- qb_34 move +0.639 feasible=True
    orig: Which airline is nicknamed ‘The Flying Kangaroo’?
    adv:  What is the airline commonly known as 'The Flying Kangaroo'?
- qz_5812 move +0.325 feasible=True
    orig: What is the capital of the U.S. state of Connecticut?
    adv:  What is the capital city of Connecticut, one of the 50 U.S. states?
- qb_189 move +0.325 feasible=True
    orig: In humans, otalgia, is the medical term for what?
    adv:  What is the medical term for otalgia in humans?
- qz_5520 move +0.000 feasible=True
    orig: What is the state capital of Florida?
- qb_66 move +0.000 feasible=True
    orig: The rowan tree is also known as the Mountain ‘what’?
- qb_92 move +0.000 feasible=True
    orig: What is the capital of Indonesia?

## Campaign triviaqa_se_hide
questions: 15, feasible paraphrase found: 15, successes: 13
entropy move (intended direction): mean +0.688, median +0.555, max +1.664
objective calls per question: mean 25

### 10 strongest successes
- tc_1348 move +1.664 (SE 2.30 -> 0.64)
    orig: In the late 60s Owen Finlay MacLaren pioneered what useful item for parents of small chldren?
    adv:  What innovative product or concept did Owen Finlay MacLaren introduce to benefit parents of young children in the late 1960s?
- tc_691 move +1.501 (SE 2.30 -> 0.80)
    orig: Who is the most successful UK solo artist in the USA?
    adv:  Which British solo artist has had the most success in the US?
- tc_847 move +1.075 (SE 2.30 -> 1.23)
    orig: What was the Paramount Film Company originally called?
    adv:  What was the original name of the company that later became known as Paramount Pictures?
- tc_1606 move +1.075 (SE 2.30 -> 1.23)
    orig: Which future Hollywood star got her break as Wonder Girl, Wonder Woman's sister Drusilla?
    adv:  What role initially brought the future Hollywood star recognition as Drusilla, Wonder Woman's sister, in the Wonder Girl series?
- tc_1029 move +0.943 (SE 2.30 -> 1.36)
    orig: Who is featured on Puff Daddy's Can't Hold Me Down?
    adv:  What artists are featured on Puff Daddy's song "Can't Hold Me Down"?
- tc_1620 move +0.943 (SE 2.30 -> 1.36)
    orig: Which war veteran was Director of News & Special Events for ABC before find fame as a TV cop?
    adv:  What was the name of the war veteran who initially served as the Director of News & Special Events for ABC before becoming a well-known television personality as a police officer?
- tc_1179 move +0.693 (SE 2.30 -> 1.61)
    orig: Which Joan's career revived in Whatever Happened to Baby Jane?
    adv:  In the film "Whatever Happened to Baby Jane?", which Joan's career was revived?
- tc_1693 move +0.555 (SE 2.30 -> 1.75)
    orig: Who beat Tim Henman in his first Wimbledon singles semifinal?
    adv:  What was the identity of Tim Henman's opponent in his first Wimbledon singles semifinal?
- tc_79 move +0.468 (SE 2.30 -> 1.83)
    orig: What was the last US state to reintroduce alcohol after prohibition?
    adv:  Which US state was the final one to lift its prohibition laws and permit the sale of alcoholic beverages?
- tc_1704 move +0.468 (SE 2.30 -> 1.83)
    orig: Which grand slam did Pete Sampras not win in the 20th century?
    adv:  What grand slam tournament did Pete Sampras not win in the 20th century?

### 10 clearest failures
- tc_1620 move +0.943 feasible=True
    orig: Which war veteran was Director of News & Special Events for ABC before find fame as a TV cop?
    adv:  What was the name of the war veteran who initially served as the Director of News & Special Events for ABC before becoming a well-known television personality as a police officer?
- tc_1179 move +0.693 feasible=True
    orig: Which Joan's career revived in Whatever Happened to Baby Jane?
    adv:  In the film "Whatever Happened to Baby Jane?", which Joan's career was revived?
- tc_1693 move +0.555 feasible=True
    orig: Who beat Tim Henman in his first Wimbledon singles semifinal?
    adv:  What was the identity of Tim Henman's opponent in his first Wimbledon singles semifinal?
- tc_79 move +0.468 feasible=True
    orig: What was the last US state to reintroduce alcohol after prohibition?
    adv:  Which US state was the final one to lift its prohibition laws and permit the sale of alcoholic beverages?
- tc_1704 move +0.468 feasible=True
    orig: Which grand slam did Pete Sampras not win in the 20th century?
    adv:  What grand slam tournament did Pete Sampras not win in the 20th century?
- tc_938 move +0.330 feasible=True
    orig: Who or what was Gentle Ben in the 60s TV series?
    adv:  What was the title character in the 1960s TV series "Gentle Ben"?
- tc_1128 move +0.330 feasible=True
    orig: Which film director guested as the FBI Director in The Silence of the Lambs?
    adv:  Who played the role of the FBI Director in the film The Silence of the Lambs?
- tc_1484 move +0.277 feasible=True
    orig: "Which boxer famously said,"" If I can't beat this bum take my name off the record books?"""
    adv:  What famous boxer made the statement, "If I can't beat this bum, take my name off the record books?
- tc_690 move +0.000 feasible=True
    orig: "According to Rudyard Kipling what were the ""two imposters"" to meet and treat the same day?"
- tc_1098 move +0.000 feasible=True
    orig: Beloved in 1999 was whose first movie since The Color Purple in 1985?

## Campaign triviaqa_sre_false_alarm
questions: 15, feasible paraphrase found: 15, successes: 12
entropy move (intended direction): mean +0.982, median +0.957, max +2.903
objective calls per question: mean 25

### 10 strongest successes
- tc_282 move +2.903 (SE 0.00 -> 2.90)
    orig: Dave Gilmore and Roger Waters were in which rock group?
    adv:  What bands did Dave Gilmour and Roger Waters originally belong to?
- tc_241 move +1.806 (SE 0.17 -> 1.98)
    orig: Of which African country is Niamey the capital?
    adv:  What country in Africa has Niamey as its capital city?
- tc_280 move +1.639 (SE 0.00 -> 1.64)
    orig: Who directed the classic 30s western Stagecoach?
    adv:  Who directed the classic 1930s western film Stagecoach?
- tc_33 move +1.371 (SE 1.17 -> 2.54)
    orig: Which Lloyd Webber musical premiered in the US on 10th December 1993?
    adv:  What Andrew Lloyd Webber musical made its US debut on 10th December 1993?
- tc_288 move +1.183 (SE 1.11 -> 2.30)
    orig: Which highway was Revisited in a classic 60s album by Bob Dylan?
    adv:  Which road was revisited in a classic 1960s album by Bob Dylan?
- tc_304 move +1.069 (SE 1.88 -> 2.95)
    orig: Which 90s sci fi series with James Belushi was based on Bruce Wagner's comic strip of the same name?
    adv:  What 1990s science fiction television series, starring James Belushi, was adapted from a comic strip created by Bruce Wagner?
- tc_49 move +1.058 (SE 1.39 -> 2.45)
    orig: Who had a 70s No 1 hit with Kiss You All Over?
    adv:  Who had a number one hit with "Kiss You All Over" in the 1970s?
- tc_219 move +0.957 (SE 2.05 -> 3.00)
    orig: The flag of Libya is a plain rectangle of which color?
    adv:  What is the color of the plain rectangular flag of Libya?
- tc_133 move +0.862 (SE 0.62 -> 1.49)
    orig: What is the Japanese share index called?
    adv:  What is the Japanese stock market index called?
- tc_217 move +0.699 (SE 0.84 -> 1.54)
    orig: Which volcano in Tanzania is the highest mountain in Africa?
    adv:  What is the tallest volcano in Africa located in Tanzania?

### 10 clearest failures
- tc_304 move +1.069 feasible=True
    orig: Which 90s sci fi series with James Belushi was based on Bruce Wagner's comic strip of the same name?
    adv:  What 1990s science fiction television series, starring James Belushi, was adapted from a comic strip created by Bruce Wagner?
- tc_49 move +1.058 feasible=True
    orig: Who had a 70s No 1 hit with Kiss You All Over?
    adv:  Who had a number one hit with "Kiss You All Over" in the 1970s?
- tc_219 move +0.957 feasible=True
    orig: The flag of Libya is a plain rectangle of which color?
    adv:  What is the color of the plain rectangular flag of Libya?
- tc_133 move +0.862 feasible=True
    orig: What is the Japanese share index called?
    adv:  What is the Japanese stock market index called?
- tc_217 move +0.699 feasible=True
    orig: Which volcano in Tanzania is the highest mountain in Africa?
    adv:  What is the tallest volcano in Africa located in Tanzania?
- tc_267 move +0.484 feasible=True
    orig: "Who was the target of the failed ""Bomb Plot"" of 1944?"
    adv:  What was the target of the failed "Bomb Plot" of 1944?
- tc_40 move +0.333 feasible=True
    orig: Who was the next British Prime Minister after Arthur Balfour?
    adv:  What British politician succeeded Arthur Balfour as Prime Minister?
- tc_137 move +0.194 feasible=True
    orig: What was the name of Michael Jackson's autobiography written in 1988?
    adv:  What is the title of the autobiography written by Michael Jackson and published in 1988?
- tc_56 move +0.173 feasible=True
    orig: What claimed the life of singer Kathleen Ferrier?
    adv:  What ultimately led to the death of singer Kathleen Ferrier?
- tc_2 move +0.000 feasible=True
    orig: Who was the man behind The Chipmunks?

## Campaign triviaqa_sre_hide
questions: 15, feasible paraphrase found: 15, successes: 11
entropy move (intended direction): mean +0.644, median +0.560, max +1.803
objective calls per question: mean 25

### 10 strongest successes
- tc_559 move +1.803 (SE 2.48 -> 0.68)
    orig: Kim Carnes' nine weeks at No 1 with Bette Davis Eyes was interrupted for one week by which song?
    adv:  What song briefly surpassed Kim Carnes' nine-week run at No 1 on the charts with "Bette Davis Eyes"?
- tc_298 move +1.234 (SE 2.35 -> 1.11)
    orig: Which was the only eastern bloc country to participate in the 1984 LA Olympics?
    adv:  What was the sole Eastern Bloc nation to participate in the 1984 Los Angeles Olympics?
- tc_276 move +1.205 (SE 2.39 -> 1.19)
    orig: Who had an 80s No 1 hit with Hold On To The Nights?
    adv:  What 80s artist achieved a No 1 hit with the song Hold On To The Nights?
- tc_585 move +1.093 (SE 2.58 -> 1.49)
    orig: Otis Barton was a pioneer in exploring where?
    adv:  What were the pioneering explorations of Otis Barton?
- tc_626 move +0.995 (SE 2.50 -> 1.50)
    orig: Which musician founded the Red Hot Peppers?
    adv:  What musician founded the Red Hot Chili Peppers?
- tc_518 move +0.747 (SE 1.59 -> 0.85)
    orig: What was Eddie Murphy's first movie?
    adv:  What was Eddie Murphy's debut film?
- tc_515 move +0.641 (SE 2.51 -> 1.87)
    orig: Art Garfunkel trained for which profession although he didn't qualify?
    adv:  What profession did Art Garfunkel initially train for, but failed to qualify for?
- tc_106 move +0.560 (SE 0.85 -> 0.29)
    orig: Which actress was voted Miss Greenwich Village in 1942?
    adv:  What actress was chosen as Miss Greenwich Village in 1942?
- tc_79 move +0.484 (SE 3.12 -> 2.64)
    orig: What was the last US state to reintroduce alcohol after prohibition?
    adv:  What was the final US state to repeal its prohibition laws and allow the sale of alcohol?
- tc_261 move +0.460 (SE 1.57 -> 1.11)
    orig: Which musical featured the song The Street Where You Live?
    adv:  What musical is the song The Street Where You Live from?

### 10 clearest failures
- tc_518 move +0.747 feasible=True
    orig: What was Eddie Murphy's first movie?
    adv:  What was Eddie Murphy's debut film?
- tc_515 move +0.641 feasible=True
    orig: Art Garfunkel trained for which profession although he didn't qualify?
    adv:  What profession did Art Garfunkel initially train for, but failed to qualify for?
- tc_106 move +0.560 feasible=True
    orig: Which actress was voted Miss Greenwich Village in 1942?
    adv:  What actress was chosen as Miss Greenwich Village in 1942?
- tc_79 move +0.484 feasible=True
    orig: What was the last US state to reintroduce alcohol after prohibition?
    adv:  What was the final US state to repeal its prohibition laws and allow the sale of alcohol?
- tc_261 move +0.460 feasible=True
    orig: Which musical featured the song The Street Where You Live?
    adv:  What musical is the song The Street Where You Live from?
- tc_69 move +0.442 feasible=True
    orig: Rita Coolidge sang the title song for which Bond film?
    adv:  What Bond film had a title song performed by Rita Coolidge?
- tc_149 move +0.000 feasible=True
    orig: In which decade did stereo records first go on sale?
- tc_165 move +0.000 feasible=True
    orig: In what year's Olympics were electric timing devices and a public-address system used for the first time?
- tc_245 move +0.000 feasible=True
    orig: Who was the director of the CIA from 1976-81?
- tc_397 move +0.000 feasible=True
    orig: In Lewis Carroll's poem The Hunting of the Snark, what did the elusive, troublesome snark turn into to fool hunters?

## Patterns to write into methodology.md
- Which question types yield the largest entropy moves?
- Do successful paraphrases share structural traits (length, hedging,
  added qualifiers, reordering)?
- Is SRE harder to move than SE (compare mean moves across detectors)?
- Failure cluster: questions where no feasible paraphrase changed entropy.
