# Records the README demo: one real, paid tracepath ask call (about $0.02).
# Run from the repo root with Neo4j up and the graph loaded: vhs demo/demo.tape

Output demo/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1400
Set Height 860
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 25ms
Set WaitTimeout 90s

Hide
Type "export PS1='$ ' && clear"
Enter
Show

Sleep 500ms
Type `uv run tracepath ask "Why is password sign in impossible on production?" --ceiling 0.25`
Sleep 500ms
Enter

Wait /\$$/
Sleep 6s
