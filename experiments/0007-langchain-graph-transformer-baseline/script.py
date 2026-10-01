# Reconstructed from the original one-off prompt (2026-09-15). The temp file that ran
# (/tmp/graph_extract_test.py) was lost; per the run transcript, the only change from the
# prompt's script was the model on the LLM line. Run 1 used model="gpt-4o-mini" and crashed
# with LengthFinishReasonError; runs 2 and 3 used model="gpt-4.1", as below.
from langchain_neo4j import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1", temperature=0)
transformer = LLMGraphTransformer(llm=llm)  # no allowed_relationships — that's the point

paths = [
    "/Users/ghaly/Documents/Work/Personal/jobhunt/docs/specs/0006-entry-page-and-link-metadata/index.md",
    "/Users/ghaly/Documents/Work/Personal/jobhunt/docs/specs/0007-auth-and-per-user-isolation/index.md",
    "/Users/ghaly/Documents/Work/Personal/jobhunt/docs/scope/scope.md",
    "/Users/ghaly/Documents/Work/Personal/jobhunt/docs/reflexes.md",
]
docs = []
for p in paths:
    with open(p) as f:
        docs.append(Document(page_content=f.read(), metadata={"source": p}))

graph_docs = transformer.convert_to_graph_documents(docs)

for gd in graph_docs:
    print(f"=== {gd.source.metadata.get('source')} ===")
    print("NODES")
    for n in gd.nodes:
        print(f"  {n.id} ({n.type})")
    print("RELATIONSHIPS")
    for r in gd.relationships:
        print(f"  {r.source.id} --[{r.type}]--> {r.target.id}")
    print()
