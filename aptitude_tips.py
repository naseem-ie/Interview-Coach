"""Tips and tricks for aptitude questions: a quick trick per question type and a study guide."""

# One quick trick for each kind of question. The keys match the generator names in aptitude.py.
TIPS = {
    "percentage_change": {
        "title": "Percentage change",
        "trick": "Change ÷ ORIGINAL × 100. Never divide by the new number.",
        "example": "400 → 460: the change is 60. 10% of 400 is 40 and 5% is 20, so 60 is 15%.",
    },
    "sla_adherence": {
        "title": "Success rate (SLA adherence)",
        "trick": "Work out the small number first (the failures as a %), then take it away from 100.",
        "example": "8 breaches out of 400: 1% of 400 is 4, so 8 is 2%. Adherence = 100 − 2 = 98%. "
                   "The trap option is usually the breach rate (2%).",
    },
    "work_rate": {
        "title": "Rate and time",
        "trick": "Time = amount ÷ rate. Turn decimal hours into minutes: 0.5 h = 30 min, 0.25 h = 15 min.",
        "example": "36 tickets at 8 per hour: 36 ÷ 8 = 4.5 h = 4 h 30 min. Check: 8 × 4.5 = 36.",
    },
    "ratio_split": {
        "title": "Ratios",
        "trick": "Add the parts, divide the total by that to get one part, then multiply.",
        "example": "2:3 with 40 in total: 5 parts, so one part is 8. The answers are 16 and 24, "
                   "and they add back up to 40.",
    },
    "average": {
        "title": "Averages",
        "trick": "Mean = total ÷ how many. Shortcut: guess a value, add how far each number is above "
                 "or below it, divide by how many, and adjust your guess.",
        "example": "10, 30, 20, 25, 15 with a guess of 20: −10 +10 +0 +5 −5 = 0, so the mean is 20. "
                   "The trap option is often the middle number (the median).",
    },
    "arithmetic_sequence": {
        "title": "Same gap each time",
        "trick": "Take each number away from the next one. If every gap is the same, add it once more.",
        "example": "5, 12, 19, 26: the gap is always 7, so the next number is 33.",
    },
    "geometric_sequence": {
        "title": "Multiplying pattern",
        "trick": "If the gaps grow fast, divide each number by the one before. The same answer each "
                 "time (×2, ×3) means multiply again.",
        "example": "3, 6, 12, 24: each number is ×2, so the next number is 48.",
    },
    "alternating_sequence": {
        "title": "Two alternating steps",
        "trick": "Write the gaps underneath. If they swap between two values, carry the pattern on "
                 "and count carefully which step is next.",
        "example": "4, 7, 12, 15, 20: the gaps are +3, +5, +3, +5, so the next gap is +3 and the answer is 23.",
    },
    "squares_sequence": {
        "title": "Square numbers",
        "trick": "If the gaps grow by 2 each time (3, 5, 7, 9…), the numbers are squares, perhaps "
                 "plus or minus a fixed amount.",
        "example": "5, 10, 17, 26: these are 4, 9, 16, 25 plus 1, so the next number is 36 + 1 = 37.",
    },
    "fibonacci_sequence": {
        "title": "Add the two before",
        "trick": "If the gaps look like earlier numbers in the list, add the last two numbers together.",
        "example": "2, 3, 5, 8, 13: 8 + 13 = 21.",
    },
    "verbal": {
        "title": "True, False or Cannot say",
        "trick": "True = the passage says it. False = the passage says the opposite. Cannot say = "
                 "the passage doesn't tell you. Use only the passage, never what you know.",
        "example": "\"Response times fell after the new tool\" does not prove the tool CAUSED it. "
                   "Words like caused, all, always and never usually mean Cannot say or False.",
    },
}


def tip_for(question):
    """The quick trick for a question, or None. Bank questions use their topic."""
    return TIPS.get(question.get("kind") or question.get("topic"))


# A short study guide, shown on the Tips & tricks screen. Each section is (title, markdown).
GUIDE = [
    ("🎯 Test-day strategy", """
- **Read the instructions first.** Check whether you may use a calculator (most SHL-style numerical
  tests allow one; the CCAT does not) and whether wrong answers lose marks (usually they don't).
- **No penalty for wrong answers? Never leave a blank.** Guess, then move on.
- **Use a skip rule.** If you have no idea after about 30 seconds (15 to 20 in a CCAT-style test), guess and move on.
  The easy marks later on are worth the same.
- **Read the question before the data.** Then you know which numbers to look for.
- **Eliminate options.** Rough estimates often rule out two answers straight away.
- **Before the test:** a quiet room, scrap paper, a pen, a charged laptop and a stable connection.
"""),
    ("🔢 Numerical shortcuts", """
**Percentages you can build in your head**
- 10% = move the decimal point one place (10% of 360 = 36)
- 5% = half of 10% · 1% = move it two places · 15% = 10% + 5%
- 25% = ¼ · 20% = ⅕ · 12.5% = ⅛ · 33⅓% = ⅓ · 50% = ½

**The formulas that come up most**
- Percentage change = (new − old) ÷ **old** × 100
- Reverse percentage: after a 20% rise the price is 120 → original = 120 ÷ 1.2 = 100
- Ratio a:b of a total → one part = total ÷ (a + b)
- Mean = total ÷ how many · Time = amount ÷ rate
- Percentage of a percentage: 50% of 40% = 0.5 × 0.4 = 20%

**Checks**
- Is the answer sensible? A 10% rise can't give a smaller number.
- Units: hours or minutes? Percentage or a count?
"""),
    ("🧩 Number sequences: try these in order", """
1. **Gaps:** take each number from the next. Same gap? Add it again.
2. **Gaps of the gaps:** if the gaps go 3, 5, 7, 9, look for square numbers.
3. **Multiply:** if the gaps grow fast, divide each number by the one before (×2, ×3).
4. **Alternating:** gaps like +3, +5, +3, +5, or two sequences mixed together (odd and even positions).
5. **Add the two before:** 2, 3, 5, 8, 13.
6. **Special numbers:** squares, cubes, primes.

**Worth knowing by heart**
- Squares: 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225
- Cubes: 1, 8, 27, 64, 125, 216
- Primes: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
"""),
    ("📖 Verbal reasoning (True / False / Cannot say)", """
- **True:** the passage states it, or it follows directly from what the passage says.
- **False:** the passage says the opposite.
- **Cannot say:** the passage doesn't give enough to decide either way. This is the most common trap.
- **Use only the passage.** Even if you know it's true in real life, if the passage doesn't say it,
  the answer is Cannot say.
- **Watch strong words:** all, always, never, only, caused, proves. One exception makes "all" False.
- **Correlation isn't cause.** "A happened after B" doesn't mean B caused A.
- **Read the statement first**, then find the sentence in the passage that it's about.
"""),
]
