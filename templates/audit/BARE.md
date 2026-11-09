# Ablation: the bare backend

The control for an audit: one agent, given
[`CRUSTIFY-bare.template.md`](CRUSTIFY-bare.template.md) as its only instruction, with no
assistant, no reviewers and no skills. The template is deliberately minimal: two lines,
21 words.

## Running it

Start a container as [`docker/README.md`](../docker/README.md) describes, with the bare
file mounted, and run the backend CLI in it without the plugin, the file as its prompt:

    docker run -d --init --name bare-git2 \
        -e ANTHROPIC_API_KEY \
        -v /path/to/target:/target \
        -v /path/to/CRUSTIFY-bare.md:/campaign/CRUSTIFY-bare.md:ro \
        -v bare-git2-work:/work \
        crustify
    docker exec -it -w /target bare-git2 \
        claude -p "$(cat /campaign/CRUSTIFY-bare.md)" --dangerously-skip-permissions

Nothing spawns reviewers in bare mode, so there is no maximum spend: the run
takes whatever the single agent takes. Cap it from outside if you need one.
