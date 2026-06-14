---
deck: AnkCompiler Example
tags:
  - example
---

A source deck is YAML frontmatter (above) followed by card blocks. Prose like
this paragraph is ignored — only the `---`-delimited blocks become cards. Each
block is followed by footnotes: a required `[^uid]` (stable card identity, so
re-importing updates rather than duplicates) and optional `[^tag]` / `[^type]`.

---

What is the capital of France? ::: Paris

---
[^uid]: aaAA11bb22

---

A question and answer
:::
may also span multiple lines.

---
[^uid]: ccCC33dd44
[^tag]: geography

---

Cloze deletions use {{c1:: curly braces}} and are detected automatically.

---
[^uid]: eeEE55ff66

---

front ::: back

---
[^uid]: ggGG77hh88
[^type]: reversed

---

What is 9 times 6? ::: 54

---
[^uid]: iiII99jj00
[^type]: type-in

---

Inline ($...$) and block ($$...$$) LaTeX render via Anki's MathJax.
Area of a circle with radius $r$? ::: $A = \pi r^2$

---
[^uid]: kkKKllmmNN
[^tag]: math
