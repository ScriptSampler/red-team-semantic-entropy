# Week 3 Wed: NLI bidirectional entailment (DeBERTa-large-MNLI)
GPU: AMD Radeon RX 9070 XT

## Load
NLI loaded in 145.3s, VRAM 1550 MB

## Hand-crafted pairs
Expected column is the human judgement, EQ column is what NLI says, OK if they match.

| # | expected | EQ | a -> b (entail prob) | b -> a (entail prob) | category | a / b |
| - | -------- | -- | -------------------- | -------------------- | -------- | ----- |
|  0 |  True | False | neutr 0.22 | neutr 0.06 | synonym/definition | Paris / the capital of France |
|  1 | False | False | contr 0.00 | contr 0.00 | different cities | Paris / London |
|  2 |  True |  True | entai 1.00 | entai 1.00 | syntactic paraphrase | Paris is the capital of France. / France's capital is Paris. |
|  3 | False | False | contr 0.00 | contr 0.00 | negation | It is hot today. / It is not hot today. |
|  4 |  True | False | neutr 0.12 | neutr 0.01 | person/description | Albert Einstein / the physicist who developed relativity |
|  5 | False | False | contr 0.00 | contr 0.00 | different people | Albert Einstein / Isaac Newton |
|  6 | False | False | entai 0.99 | neutr 0.00 | specific vs vague | The book has 200 pages. / The book has many pages. |
|  7 |  True | False | entai 0.95 | neutr 0.02 | specific implies general | World War II ended in 1945. / World War II ended in the 1940s. |
|  8 | False | False | neutr 0.02 | entai 0.95 | general does not imply specific | World War II ended in the 1940s. / World War II ended in 1945. |
|  9 |  True | False | neutr 0.11 | entai 0.99 | scope | Cats are mammals. / All cats are mammals. |
| 10 | False | False | contr 0.00 | contr 0.03 | scope, existential vs universal | Some cats are black. / All cats are black. |
| 11 |  True |  True | entai 0.99 | entai 1.00 | active/passive | The Eiffel Tower is in Paris. / Paris contains the Eiffel Tower. |
| 12 |  True |  True | entai 0.82 | entai 1.00 | implicit context | Mount Everest is the tallest mountain. / Mount Everest is the tallest mountain in |
| 13 | False | False | contr 0.00 | contr 0.00 | common misconception | Canberra is the capital of Australia. / Sydney is the capital of Australia. |
| 14 |  True | False | neutr 0.00 | entai 1.00 | additional consistent detail | Sunset Boulevard premiered in 1993. / Sunset Boulevard, the Lloyd Webber music |
| 15 | False | False | neutr 0.00 | neutr 0.23 | premise lacks the artist; expected to fall short of full equivalence | The answer is Octopussy. / Rita Coolidge sang the title song for Oc |

hand-crafted accuracy: 11/16

## NLI clustering on five Monday questions
Picks five from results/wk3_mon_samples_inspect.md to look at, mixing right and wrong cases.

selected 5 of the 5 target ids found

### tc_2
Q: Who was the man behind The Chipmunks?
canonical: David Seville
greedy:    The Chipmunks were a popular animated musical group created by Ross Bagdasarian Sr. (also known as David Seville) in the...
sample correctness: 7/10

NLI clusters: 5
  cluster of size 6:
    [0] ok The character of Alvin, Simon, and Theodore, popularly known as The Chipmunks, was created by Ross B...
    [2] ok The character of David Seville, the man in charge of The Chipmunks, was created by Ross Bagdasarian ...
    [3] ok Alfred "Al" Shank was not the main figure behind The Chipmunks but most notable is  a man named Ross...
    [4] ok The man behind The Chipmunks was Ross Bagdasarian Sr., also known as David Seville.
    [7] no The man behind The Chipmunks was Ross Bagdasarian Sr.
    [9] ok Alvin and the Chipmunks are an American animated musical group created by Ross Bagdasarian Sr., an A...
  cluster of size 1:
    [1] no The character "Alvin" from The Chipmunks was based off a mouse character named Maxwell Smart's boss'...
  cluster of size 1:
    [5] no The main characters in The Chipmunks were led by Dave Seville's three singing chipmunks, Alvin, Simo...
  cluster of size 1:
    [6] ok The brain behind the iconic singing group The Chipmunks was the American singer, songwriter, and rec...
  cluster of size 1:
    [8] ok The character of the original leader of the Chipmunks, Alvin was inspired by a popular actor David S...

### tc_69
Q: Rita Coolidge sang the title song for which Bond film?
canonical: Octopussy
greedy:    The song you are referring to is "All Through the Night" but more famously known as "All Through the Night" is not the s...
sample correctness: 8/10

NLI clusters: 9
  cluster of size 1:
    [0] ok Rita Coolidge sang the title song "All Through the Night" (though not released) for the James Bonds ...
  cluster of size 1:
    [1] ok Rita Coolidge sang the title song for the 1983 James Bond film 'Octopussy' and the 1979 James Bond f...
  cluster of size 1:
    [2] ok Rita Coolidge sang the title song for the 1979 James Bond film "Octopussy".
  cluster of size 2:
    [3] ok The title song for the Bond film "Octopussy" was sung by Rita Coolidge.
    [4] ok The song you are referring to is "All Through the Night", but I believe you are thinking of a differ...
  cluster of size 1:
    [5] ok Rita Coolidge sang the theme song for the James Bond film "Octopussy" (1983).
  cluster of size 1:
    [6] ok "Winning" was the theme song for the James Bond film 'Octopussy' (1983).
  cluster of size 1:
    [7] ok Rita Coolidge sang the title song for "Octopussy" (1983).
  cluster of size 1:
    [8] no The song was All Time High.
  cluster of size 1:
    [9] no Rita Coolidge sang "All That Glitters" for the film "Die Another Day."

### tc_79
Q: What was the last US state to reintroduce alcohol after prohibition?
canonical: Utah
greedy:    The last US state to reintroduce alcohol after Prohibition was Mississippi.
sample correctness: 4/10

NLI clusters: 10
  cluster of size 1:
    [0] ok The last US state to legalize the sale of alcohol after prohibition was Mississippi (not the first s...
  cluster of size 1:
    [1] no I do not have information on which US state was the very last to remove its prohibition laws. Howeve...
  cluster of size 1:
    [2] ok The last U.S. state to introduce or in this case, completely repeal the law prohibiting the sale of ...
  cluster of size 1:
    [3] no The last US state to repeal prohibition was Mississippi.
  cluster of size 1:
    [4] ok The last US state to allow alcohol to be sold for consumption off-premises was Mississippi but for o...
  cluster of size 1:
    [5] no The last US state to reintroduce alcohol was Mississippi, which did so on November 3, 1966, by holdi...
  cluster of size 1:
    [6] no I do not have specific information on which US state last reintroduced alcohol after the 18th Amendm...
  cluster of size 1:
    [7] no The last US state to end Prohibition through a statewide vote was Vermont in 1933 and then re-introd...
  cluster of size 1:
    [8] ok The last US state to lift its ban on the sale of liquor was Utah, however, the last state to elimina...
  cluster of size 1:
    [9] no Mississippi was the last US state to lift its ban on the sale of liquor, which occurred on July 1st,...

### tc_149
Q: In which decade did stereo records first go on sale?
canonical: 1930s
greedy:    Stereo records first went on sale in the 1950s.
sample correctness: 1/10

NLI clusters: 7
  cluster of size 4:
    [0] no Stereo records first went on sale in the 1950s.
    [1] no Stereo records first went on sale in the 1950s.
    [5] no Stereo records first began going on sale in the 1950s.
    [9] no Stereo records first went on sale in the 1950s.
  cluster of size 1:
    [2] no Stereo records, also known as stereo albums or mono-stereo records, first appeared in the 1950s.
  cluster of size 1:
    [3] no Stereo records first went on sale in the 1950s. Specifically, the first commercially available stere...
  cluster of size 1:
    [4] ok Stereo records first went on sale in the 1930s but were more commonly called "two-channel discs."
  cluster of size 1:
    [6] no Stereo records first went on sale in the 1950s. Specifically, the first commercial stereo record was...
  cluster of size 1:
    [7] no Stereo records, also known as stereo records or LPs (long-playing records), first became widely avai...
  cluster of size 1:
    [8] no Stereo records first went on sale in the early 1950s.

### tc_165
Q: In what year's Olympics were electric timing devices and a public-address system used for the first time?
canonical: In 1912, in Stockholm
greedy:    The 1920 Summer Olympics in Antwerp, Belgium, were the first Olympics to use electric timing devices and a public-addres...
sample correctness: 0/10

NLI clusters: 7
  cluster of size 4:
    [0] no The 1920 Summer Olympics in Antwerp, Belgium, featured electric timing devices and a public-address ...
    [3] no In the 1920 Summer Olympics, which were held in Antwerp, Belgium in 1920, a public-address system wa...
    [7] no The 1920 Summer Olympics in Antwerp, Belgium, were the first to use electric timing devices. The 192...
    [8] no The 1920 Summer Olympics in Antwerp,  which took place in 1920, is often referred to as the first Ol...
  cluster of size 1:
    [1] no At the 1928 Amsterdam Olympics electric timing devices were used for the first time. However a publi...
  cluster of size 1:
    [2] no In the 1928 Summer Olympics, electric timing devices and a public-address system were used for the f...
  cluster of size 1:
    [4] no The first Olympics where electric timing devices and a public-address system were used were the 1928...
  cluster of size 1:
    [5] no The 1920 Olympic Games held in Antwerp, Belgium used electric timing devices.
  cluster of size 1:
    [6] no At the 1928 Summer Olympics held in Amsterdam, Netherlands.
  cluster of size 1:
    [9] no In the 1920, the Olympics used electric timing devices which was a huge advancement for the times an...

