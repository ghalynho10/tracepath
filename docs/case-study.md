# How I built and evaluated tracepath

## The problem

A project's reasons live in its decision records: specs, acceptance criteria, design notes. But those records don't stay still. A criterion gets amended, struck through, or replaced by one in another spec, and as the corpus grows, finding the current answer gets harder. I also noticed it in my own work: after stepping away from a project for a while, I'd forget most of the decisions behind it and have to dig them back up.

I wanted a tool I could ask "why was this built this way?" and get an exact answer, one I could check. That's why citations were the point from the start. I also wanted to learn knowledge graphs and GraphRAG properly, by building with them.

## What I tried first

My first attempt was decision-memory, a cited RAG tool with hybrid retrieval (keyword plus embeddings). My main goal was to limit hallucinations while still getting the right answers, so I added a verification layer that checked each sentence against its cited evidence. It ended up too strict: it threw away good answers along with the bad ones.

That led to tracepath. Instead of checking prose after the fact, I extract the specs into a graph of small, typed items, each with an id and a source line. Every answer has to cite those items, and code checks that each citation points to an item the model was actually given, and that any link it claims between two items really exists in the graph.

For the extraction itself, I first tried LangChain's LLMGraphTransformer at its default settings. It didn't go well: it dropped the acceptance criterion ids, split one feature into three unlinked identities, and invented 86 different link types. I also wanted the skill of building an extraction pipeline myself, so I built one, with a closed set of item and link types, three extraction runs per section, and code that compares the runs.

## The redesign

Before building anything new, I tested the idea by hand. A Claude Code session played the model's part on the five eval questions: it searched the extracted items, read what it found, and wrote an answer citing them, with no API call. I marked its answers against the expected ones: 4 right, 1 partly right.

I did this so I'd know what I was building toward. Without it, I'd have had no way to tell how close I was. The hand run gave me a reference point, and from it I wrote the success bar down before designing anything: at least 4 of the 5 eval questions right, and 3 of the 4 held out questions, the ones it had never seen.

Then I built `tracepath ask`. It picks the question's words, finds the extracted items that share them, and adds connected items up to two links away, at most 90 in all. It prices the call before making it, sends those items to Claude once, and gets back an answer whose every claim cites item ids. Code then checks each citation against the items it sent, marks any claimed link it can't find in the graph, and labels replaced items as history. Every answer, with its cost, is saved to a record.

![tracepath runtime architecture](architecture.png)

## The result

I decided in advance what passing meant, so the result would tell me something.

On the eval questions, it answered 5 of 5 right. Then I froze the prompt in a commit and ran the held out questions once each. It answered 3 right and 1 partly right. The partly right one was a retrieval miss: the item holding the answer sat more than two links away from what the search found, so it was never sent to the model.

Both parts of the bar were met. I judged every answer myself against expected answers written before the run. All nine answers cost $0.38 together.

Then I tested it the way someone would actually use it ([experiment 0018](../experiments/0018-realistic-usage-questions/README.md)). I wrote 22 questions in everyday words: 12 the specs answer, and 10 they don't, because the thing never existed or the premise was false. I committed the expected answers before running anything, ran each question once, and marked the answers myself. It answered 9 of the 12 right and 1 partly right, and declined all 10 of the others without inventing anything. The misses had two causes: the search matches exact words, so my phrasing ("emergency stop toggle") didn't find the spec's ("kill switch"), and the reasons behind several decisions live in rationale files the tool doesn't read yet.

## Against my earlier tool

I ran decision-memory on the same nine questions, against the same pinned specs. It abstained on all nine: each time it printed "not enough evidence here". Its search found the right specs on most questions; the verifier is what refused. It checks every sentence against its cited text, drops the whole sentence if any piece of it isn't supported, and refuses the whole answer if any part of the question is left uncovered.

tracepath answered all nine. It checks less in code than decision-memory does: it confirms every citation points to a real item it sent, and that any link it claims exists, but it doesn't check that an item's text says what the claim says. Instead, every claim points at one exact item and line, so I can check it myself in seconds. I'd rather have an answer I can verify than a verifier that leaves me with no answer.

This compares two whole systems, on different models, so it doesn't prove a graph beats vector search. It shows which design gave me usable answers.

## What the links are for

Once tracepath was answering, I wanted to know which part of it was doing the work: the search, or the links between items. So I added a setting for how many links to follow and asked the five eval questions twice, once following links up to two steps out and once following none.

Both versions answered all five right. On these questions, the search over the extracted items found what each answer needed, without the links.

With none followed, answers still labelled a replaced criterion as history, and code still confirmed claims that two items are connected. Both come from the links stored in the graph, so on these questions the links did more to make answers checkable and aware of what has changed than to find items. I kept following two links by default: it costs a few cents a question, and one held out answer showed that sometimes the item that matters sits further out.

This measures the links as they are today. Better link resolution is my next step, and this is the test I'll rerun to see if it helps.

## How I kept it controlled

A few habits kept the project honest and cheap.

`tracepath eval` scores each eval question pass, fail or inconclusive, and gives the reason for every expected item it didn't reach. It reads the graph and makes no API call, so I could rerun it for free after every change.

Every paid call in the tool goes through a guard that works out the most the call could cost and stops if that's above a ceiling I set. A failed call is counted at that worst case. A dry run prices a question for free. A test in CI fails if any file outside a short allowlist imports the Anthropic SDK, so no new code can spend money without going through the guard. The worst case is deliberately cautious: the first real question was bounded at $0.21 and cost $0.05.

Each extraction run is saved as a file holding the model, the prompt version, the corpus commit and the token usage, and nothing is ever overwritten. Runs I replaced are moved aside, not deleted. So the cost of the whole extraction, $30.33 over 719 calls, can be recomputed from the repository.

Each experiment has a written record: what I asked, how I tested it, what happened, and what I decided. In several of them I committed my predictions or my decision rule before running anything, and scored the result as written, including when I got it wrong.

The project has 1,229 tests. The integration tests run against a real Neo4j database, and every database write checks that it wrote exactly what it was given.

## What I learned, and what's next

The biggest lesson was to measure first. With decision-memory I built most of the tool before deciding how to tell whether it worked. With tracepath I wrote the questions before any code, and every decision after that had something to stand on. I also learned to change one thing at a time, and to evaluate before adding strict automatic checks: decision-memory's verifier was built before I knew what a good answer looked like, and it ended up refusing everything. The last lesson was proportion. I wanted everything to work perfectly, so for a while I added more rigor than the project needed. Then I stepped back and leaned on common industry practice instead: guard what can lose money, lose data or mislead, and skip the rest.

What surprised me most was how much simpler tracepath turned out than decision-memory. decision-memory makes several model calls per question to search, check and judge its own answer, and still gave me less precision. tracepath makes one. It does the hard work once, up front, by extracting the specs into small cited items, so answering becomes simple.

Next, I want to improve how links resolve, so connections land on the right item instead of a whole spec. Experiment 0018 pointed at two more: finding the right spec when a question uses different words than the spec does, and reading the rationale files where the reasons live. I'd like to try an agentic version, where the model decides what to search and which links to follow. And further out, I want to link decisions to the code that implements them, so a question can go from a file to the decisions behind it, and a change can show which decisions it touches.
