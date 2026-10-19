# Ablation: the bare backend

`crustify <workdir> --settings <file> --campaign audit --task-only --start` starts the backend CLI
with the task file, here `CRUSTIFY-bare.template.md`, as its **entire** prompt: no
assistant role, no conventions, no skill index.

`CRUSTIFY-bare.template.md` is deliberately minimal -- two lines, 21 words.

## Running it

    docker run -d --name bare-git2 \
        -e OPENROUTER_API_KEY \
        -v /path/to/target:/target \
        -v /path/to/CRUSTIFY-bare.md:/campaign/CRUSTIFY.md:ro \
        -v bare-git2-work:/work \
        crustify
    docker exec -it bare-git2 \
        crustify /target --settings /campaign/CRUSTIFY.md --campaign audit --task-only --start \
        --model openrouter/anthropic/claude-opus-5 --billing api

Nothing spawns reviewers in bare mode, so there is no maximum spend: the run
takes whatever the single agent takes. Cap it from outside if you need one.
