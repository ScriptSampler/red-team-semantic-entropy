# Week 2 Fri: end-to-end pipeline + timing
GPU: AMD Radeon RX 9070 XT

## Load model and dataset
model loaded in 55.9 s, VRAM 5440 MB
TriviaQA validation: 17944 examples

## Greedy generation for 10 real questions
Correctness flag is a rough containment check; the full SE scorer ships in Week 3.

[0] ok  (2.36 s)
    Q: Who was the man behind The Chipmunks?
    canonical: David Seville
    model:     The Chipmunks were a popular animated musical group created by Ross Bagdasarian Sr. (also known as David Seville) in the 1950s.

[1] ok  (1.30 s)
    Q: Which Lloyd Webber musical premiered in the US on 10th December 1993?
    canonical: Sunset Boulevard
    model:     The Lloyd Webber musical that premiered in the US on 10th December 1993 is Sunset Boulevard.

[2] ok  (1.02 s)
    Q: Who was the next British Prime Minister after Arthur Balfour?
    canonical: Campbell-Bannerman
    model:     The next British Prime Minister after Arthur Balfour was Henry Campbell-Bannerman.

[3] ok  (1.16 s)
    Q: Who had a 70s No 1 hit with Kiss You All Over?
    canonical: Exile
    model:     Exile had a 1978 No 1 hit with "Kiss You All Over".

[4] ok  (1.45 s)
    Q: What claimed the life of singer Kathleen Ferrier?
    canonical: Cancer
    model:     Kathleen Ferrier, a renowned British contralto, died of breast cancer on October 8, 1953.

[5] no  (3.22 s)
    Q: Rita Coolidge sang the title song for which Bond film?
    canonical: Octopussy
    model:     The song you are referring to is "All Through the Night" but more famously known as "All Through the Night" is not the song. The song you are looking for is "All Through the Night" is not the song, but "All Through the Night" is not the song. The song you are looking

[6] no  (0.87 s)
    Q: What was the last US state to reintroduce alcohol after prohibition?
    canonical: Utah
    model:     The last US state to reintroduce alcohol after Prohibition was Mississippi.

[7] no  (1.01 s)
    Q: Which actress was voted Miss Greenwich Village in 1942?
    canonical: Lauren Bacall
    model:     I am unable to verify which actress was voted Miss Greenwich Village in 1942.

[8] ok  (0.83 s)
    Q: What is the Japanese share index called?
    canonical: Nikkei
    model:     The Japanese share index is called the Nikkei 225.

[9] ok  (1.69 s)
    Q: What was the name of Michael Jackson's autobiography written in 1988?
    canonical: Moonwalk
    model:     Michael Jackson's autobiography was not written in 1988. His autobiography, "Moonwalk," was written by Michael Jackson and published in 1988.

greedy: 7/10 acceptable, mean 1.49 s per question

## Timing: N=10 sampling over 100 questions
This is the actual SE sampling primitive. The number drives the Week 4 eval budget.

N=10 samples for 100 questions: 1427.2 s total
  per question:  14.27 s
  per sample:    1.427 s
  peak VRAM:     5804 MB (5.67 GB)

## Runtime extrapolations at N=10
    1000 questions: 3.96 h
    2000 questions: 7.93 h
    5000 questions: 19.82 h
   17944 questions: 71.14 h

## Verdict
Full validation eval projects to 71.1 h, over the 36 h budget. Drop N to 5 or use a 2000-question subset for Week 4 first pass.
