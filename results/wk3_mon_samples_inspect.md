# Week 3 Mon: N=10 sample collection on 50 TriviaQA questions
GPU: AMD Radeon RX 9070 XT

## Load model and dataset
model loaded in 58.1s, VRAM 5440 MB
selected first 50 validation examples

## Generate samples
config: N=10, T=1.0, max_new_tokens=48, seed=0
output: /home/abhi/.cache/se-research/samples/wk3_mon_50q

collected 50 records in 662.0s (13.24s/Q)

## Diversity inspection
greedy correctness:     35/50
all 10 samples right:   17/50
all 10 samples wrong:   6/50
distinct samples per Q: mean=8.96, median=10, min=4, max=10

### Distinct-count histogram
   4 distinct: ## (2)
   5 distinct: # (1)
   6 distinct: # (1)
   7 distinct: #### (4)
   8 distinct: #### (4)
   9 distinct: ########### (11)
  10 distinct: ########################### (27)

### Greedy-correct vs greedy-wrong, sample correctness rate
when greedy correct (35): mean sample correctness 0.80
when greedy wrong   (15): mean sample correctness 0.21

## Five questions the greedy answer got wrong
These should be high-entropy under SE if the method is working.

### tc_69
Q: Rita Coolidge sang the title song for which Bond film?
canonical: Octopussy
greedy:    The song you are referring to is "All Through the Night" but more famously known as "All Through the Night" is not the song. The song you are looking for is "All Through the Night" is not the song, but
distinct sample forms: 10
sample correctness:    8/10
  [0] ok Rita Coolidge sang the title song "All Through the Night" (though not released) for the James Bonds film "Octopussy" however, that is incorrect. She sang the title  (lyrics written by Bill Dohen
  [1] ok Rita Coolidge sang the title song for the 1983 James Bond film 'Octopussy' and the 1979 James Bond film 'Force Ten from Navarone' did not, but 'The man with the Golden gun
  [2] ok Rita Coolidge sang the title song for the 1979 James Bond film "Octopussy".
  [3] ok The title song for the Bond film "Octopussy" was sung by Rita Coolidge.
  [4] ok The song you are referring to is "All Through the Night", but I believe you are thinking of a different song. Rita Coolidge sang the title song for the James Bond film "Octopussy".
  [5] ok Rita Coolidge sang the theme song for the James Bond film "Octopussy" (1983).
  [6] ok "Winning" was the theme song for the James Bond film 'Octopussy' (1983).
  [7] ok Rita Coolidge sang the title song for "Octopussy" (1983).
  [8] no The song was All Time High.
  [9] no Rita Coolidge sang "All That Glitters" for the film "Die Another Day."

### tc_79
Q: What was the last US state to reintroduce alcohol after prohibition?
canonical: Utah
greedy:    The last US state to reintroduce alcohol after Prohibition was Mississippi.
distinct sample forms: 10
sample correctness:    4/10
  [0] ok The last US state to legalize the sale of alcohol after prohibition was Mississippi (not the first state). However the state that allowed the sale of alcohol the latest after a constitutional amendment passed was Utah,  (the 1933 amendment to the
  [1] no I do not have information on which US state was the very last to remove its prohibition laws. However, Mississippi was one of the last two remaining dry states (states prohibiting the sale of alcohol) prior to a national repeal in the USA.
  [2] ok The last U.S. state to introduce or in this case, completely repeal the law prohibiting the sale of alcohol, to actually legalise alcohol, making them're-introduce alcohol' a weird title, was Utah in 1935
  [3] no The last US state to repeal prohibition was Mississippi.
  [4] ok The last US state to allow alcohol to be sold for consumption off-premises was Mississippi but for on-premises (e.g., bars) it was Utah. Utah prohibited the sale of alcohol on-premises until July 1
  [5] no The last US state to reintroduce alcohol was Mississippi, which did so on November 3, 1966, by holding a statewide referendum allowing the sale of package liquor, not counting the date when states were permitted to hold their own statewide
  [6] no I do not have specific information on which US state last reintroduced alcohol after the 18th Amendment and the Prohibition Act of 1919. However, I can provide you with information on how the Prohibition Era ended in the United
  [7] no The last US state to end Prohibition through a statewide vote was Vermont in 1933 and then re-introduction by a vote in 1962 (though many states had ended prohibition by 1933).
  [8] ok The last US state to lift its ban on the sale of liquor was Utah, however, the last state to eliminate the remaining specific conditions which made alcohol sales illegal after the repeal of prohibition was Oklahoma's 1959 repeal, thereby allowing retail
  [9] no Mississippi was the last US state to lift its ban on the sale of liquor, which occurred on July 1st, 1966. Not all of its counties allowed the sale until 1967

### tc_106
Q: Which actress was voted Miss Greenwich Village in 1942?
canonical: Lauren Bacall
greedy:    I am unable to verify which actress was voted Miss Greenwich Village in 1942.
distinct sample forms: 9
sample correctness:    0/10
  [0] no I am unable to verify which actress was voted Miss Greenwich Village in 1942.
  [1] no I'm sorry, but I am unable to verify which actress was voted Miss Greenwich Village in 1942.
  [2] no I am unable to verify the person voted Miss Greenwich Village in 1942.
  [3] no I am not aware of any information regarding an actress being voted "Miss Greenwich Village in 1942."
  [4] no I don't have information on which actress was voted Miss Greenwich Village in 1942.
  [5] no I'm sorry, but I do not know which actress was voted Miss Greenwich Village in 1942.
  [6] no I do not have access to that information.
  [7] no I could not find any information about the 1942 Miss Greenwich Village pageant winner.
  [8] no I don't have the information that a particular actress was voted Miss Greenwich Village in 1942.
  [9] no I am unable to verify, which actress was voted Miss Greenwich Village in 1942.

### tc_149
Q: In which decade did stereo records first go on sale?
canonical: 1930s
greedy:    Stereo records first went on sale in the 1950s.
distinct sample forms: 8
sample correctness:    1/10
  [0] no Stereo records first went on sale in the 1950s.
  [1] no Stereo records first went on sale in the 1950s.
  [2] no Stereo records, also known as stereo albums or mono-stereo records, first appeared in the 1950s.
  [3] no Stereo records first went on sale in the 1950s. Specifically, the first commercially available stereo records were released in 1958 by RCA Records.
  [4] ok Stereo records first went on sale in the 1930s but were more commonly called "two-channel discs."
  [5] no Stereo records first began going on sale in the 1950s.
  [6] no Stereo records first went on sale in the 1950s. Specifically, the first commercial stereo record was the "Kissing Bug" by The Dinning Sisters, released in September 1958. However, the first stereo records were
  [7] no Stereo records, also known as stereo records or LPs (long-playing records), first became widely available in the late 1950s.
  [8] no Stereo records first went on sale in the early 1950s.
  [9] no Stereo records first went on sale in the 1950s.

### tc_165
Q: In what year's Olympics were electric timing devices and a public-address system used for the first time?
canonical: In 1912, in Stockholm
greedy:    The 1920 Summer Olympics in Antwerp, Belgium, were the first Olympics to use electric timing devices and a public-address system.
distinct sample forms: 10
sample correctness:    0/10
  [0] no The 1920 Summer Olympics in Antwerp, Belgium, featured electric timing devices and a public-address system for the first time.
  [1] no At the 1928 Amsterdam Olympics electric timing devices were used for the first time. However a public-address system was used for the first time at the 1936 Berlin Olympics.
  [2] no In the 1928 Summer Olympics, electric timing devices and a public-address system were used for the first time.
  [3] no In the 1920 Summer Olympics, which were held in Antwerp, Belgium in 1920, a public-address system was used for the first time.
  [4] no The first Olympics where electric timing devices and a public-address system were used were the 1928 Summer Olympics which took place in Amsterdam, Netherlands.
  [5] no The 1920 Olympic Games held in Antwerp, Belgium used electric timing devices.
  [6] no At the 1928 Summer Olympics held in Amsterdam, Netherlands.
  [7] no The 1920 Summer Olympics in Antwerp, Belgium, were the first to use electric timing devices. The 1920 Summer Olympics introduced electric timing devices for the first time at the Olympics.

However, the first time for a public-address
  [8] no The 1920 Summer Olympics in Antwerp,  which took place in 1920, is often referred to as the first Olympics to use electric timing devices and a public-address system.
  [9] no In the 1920, the Olympics used electric timing devices which was a huge advancement for the times and a public-address system.

## Five questions the greedy answer got right
These should be low-entropy under SE.

### tc_2
Q: Who was the man behind The Chipmunks?
canonical: David Seville
greedy:    The Chipmunks were a popular animated musical group created by Ross Bagdasarian Sr. (also known as David Seville) in the 1950s.
distinct sample forms: 10
sample correctness:    7/10
  [0] ok The character of Alvin, Simon, and Theodore, popularly known as The Chipmunks, was created by Ross Bagdasarian Sr., also known as David Seville, an American singer, songwriter, record producer, and cartoonist
  [1] no The character "Alvin" from The Chipmunks was based off a mouse character named Maxwell Smart's boss's "Chief of the U.N." "Chief- assistant named Alvin's boss was named a squirrel, but the main
  [2] ok The character of David Seville, the man in charge of The Chipmunks, was created by Ross Bagdasarian Sr. (also known as David Seville).
  [3] ok Alfred "Al" Shank was not the main figure behind The Chipmunks but most notable is  a man named Ross Bagdasarian Sr., also known as David Seville on screen.

However, Ross Bagdasarian Sr.
  [4] ok The man behind The Chipmunks was Ross Bagdasarian Sr., also known as David Seville.
  [5] no The main characters in The Chipmunks were led by Dave Seville's three singing chipmunks, Alvin, Simon, and Theodore but the one behind creating them is not one but three individuals: 

Ross Bagdasarian Sr (
  [6] ok The brain behind the iconic singing group The Chipmunks was the American singer, songwriter, and record producer Ross Bagdasarian Sr.. However, he is more often referred to as David Seville or the name of the narrator in his song
  [7] no The man behind The Chipmunks was Ross Bagdasarian Sr.
  [8] ok The character of the original leader of the Chipmunks, Alvin was inspired by a popular actor David Seville from the popular 1958 animated short film "The Chip-an-Nips."  David Seville's voice was provided by
  [9] ok Alvin and the Chipmunks are an American animated musical group created by Ross Bagdasarian Sr., an American singer, songwriter, and record producer, who is often credited as David Seville.

### tc_33
Q: Which Lloyd Webber musical premiered in the US on 10th December 1993?
canonical: Sunset Boulevard
greedy:    The Lloyd Webber musical that premiered in the US on 10th December 1993 is Sunset Boulevard.
distinct sample forms: 8
sample correctness:    7/10
  [0] no This is not a well known piece of information, but I can tell you what I know about Andrew Lloyd Webber. 

But, I do know that one of the lesser-known musicals,  (that was written by Andrew Lloyd Web
  [1] no I'm sorry, I do not know which Lloyd webber musical premiered on the 10 December in the US.
  [2] ok The musical that premiered in the United States on December 10, 1993, is "Sunset Boulevard."
  [3] ok The musical "Sunset Boulevard" premiered in the US on 11th December 1993, however a musical by Andrew Lloyd Webber did premiere in the US on 10th December 1993 - it was "Sunset Boulevard
  [4] ok The Lloyd Webber musical that premiered in the US on 10th December 1993 is Sunset Boulevard.
  [5] ok The Lloyd Webber musical that premiered in the US on 10th December 1993 was 'Sunset Boulevard'.
  [6] no I cant verify which musical by Andrew Lloyd Webber premiered in the US on 10th December 1993
  [7] ok The Lloyd Webber musical that premiered in the US on 10th December 1993 was Sunset Boulevard.
  [8] ok The Lloyd Webber musical that premiered in the US on 10th December 1993 was Sunset Boulevard
  [9] ok The Lloyd Webber musical, 'Sunset Boulevard', premiered on the 10th December 1993.

### tc_40
Q: Who was the next British Prime Minister after Arthur Balfour?
canonical: Campbell-Bannerman
greedy:    The next British Prime Minister after Arthur Balfour was Henry Campbell-Bannerman.
distinct sample forms: 9
sample correctness:    4/10
  [0] ok The next British Prime Minister after Arthur Balfour was Henry Campbell-Bannerman (1905-1908).
  [1] no H.H. Asquith succeeded Arthur Balfour as the British Prime Minister in 1908
  [2] no The person after Arthur Balfour was Henry James, Lord Herbert Asquith
  [3] no The next British Prime Minister after Arthur Balfour was H.H. Asquith.
  [4] ok The next British Prime Minister after Arthur Balfour was Henry Campbell-Bannerman. He served as the Prime Minister of the United Kingdom from March 1905 to April 1908.
  [5] no The next British Prime Minister after Arthur Balfour was Herbert Henry Asquith.
  [6] ok The Prime Minister after Arthur Balfour was Henry Campbell-Bannerman.
  [7] no The next British Prime Minister after Sir Arthur Balfour was H.H. Asquith in 1908.
  [8] no The next British Prime Minister after Arthur Balfour was H.H. Asquith.
  [9] ok Arthur Balfour served as the British Prime Minister from 1902 to 1905. The next British Prime Minister after him was Sir Henry Campbell-Bannerman (acting, though only for a couple of weeks), but the one that

### tc_49
Q: Who had a 70s No 1 hit with Kiss You All Over?
canonical: Exile
greedy:    Exile had a 1978 No 1 hit with "Kiss You All Over".
distinct sample forms: 6
sample correctness:    9/10
  [0] ok Exile had a 1978 No 1 hit with "Kiss You All Over".
  [1] ok Exile had a 1978 No 1 hit with "Kiss You All Over".
  [2] ok The 1970s No 1 hit was actually "Kiss You All Over" by Exile.
  [3] ok Exile had a 1978 No.1 hit with "Kiss You All Over."
  [4] no The Righteous Brothers had a 1974 cover of "You've Got a Hold on Me".
  [5] ok Exile had a 70's No 1 hit with Kiss You All Over.
  [6] ok Exile had a 1978 No 1 hit with Kiss You All Over.
  [7] ok Exile had a 1978 No 1 hit with Kiss You All Over.
  [8] ok The 1970s No 1 hit "Kiss You All Over" was by Exile.
  [9] ok Exile had a 70s No 1 hit with "Kiss You All Over."

### tc_56
Q: What claimed the life of singer Kathleen Ferrier?
canonical: Cancer
greedy:    Kathleen Ferrier, a renowned British contralto, died of breast cancer on October 8, 1953.
distinct sample forms: 10
sample correctness:    10/10
  [0] ok Kathleen Ferrier, a British contralto, passed away on October 6, 1953.  She suffered from breast cancer.
  [1] ok Kathleen Ferrier died of breast cancer.
  [2] ok Kathleen Ferrier passed away after a prolonged battle with cancer.
  [3] ok Singer Kathleen Ferrier passed away on October 8, 1953. She died of ovarian cancer.
  [4] ok Kathleen Ferrier passed away due to ovarian cancer.
  [5] ok Kathleen Ferrier, a renowned English opera singer, died from skin cancer.
  [6] ok Kathleen Ferrier, the British contralto, died on October 8, 1953 due to ovarian cancer.
  [7] ok Kathleen Ferrier died of ovarian cancer in 1953.
  [8] ok The life of the singer Kathleen Ferrier ended due to breast cancer.
  [9] ok Kathleen Ferrier, a renowned British contralto, claimed the life of ovarian cancer in 1953.

